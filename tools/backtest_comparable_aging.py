"""Aging-curve backtest for the player comparable engine.

Methodology (PECOTA-inspired):
  1. Hold out the most recent season (target year, default 25-26).
  2. For every player with both (a) ≥ 200 5v5 min in seasons < target and
     (b) ≥ 200 5v5 min in target year — i.e., a "two-fold" cohort —
     build their feature vector from seasons < target.
  3. Fit a comparable index on those feature vectors.
  4. For each held-out player, find top-k comps. Predict their target-year
     iso impact as the comps' weighted-mean target-year iso impact.
  5. Compare to:
        baseline_self  : player's own seasons-< target pooled iso
        baseline_league: league-average iso for position in target year
        comp_prediction: comps' target-year mean iso (PECOTA-style)
  6. Report MAE per position + compare against the 15% improvement bar.

A "win" for Phase 1 is the comp_prediction's MAE being ≥15% lower than the
baseline_self MAE on forwards. If that bar is met, the engine can ship into
propose-swap-scenario.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/backtest_comparable_aging.py
        [--holdout 20252026] [--k 5] [--min-toi 200]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core import FeatureMatrix, POSITION_TOKENS, build_index_from_features


ALL_SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")
DB_PATH = REPO / "legacy" / "data" / "store.sqlite"


def per60(events: float, toi_min: float) -> float:
    return events * 60.0 / toi_min if toi_min and toi_min > 0 else 0.0


def fetch_pooled_skaters_for_seasons(con: sqlite3.Connection, seasons: tuple[str, ...],
                                     sit: str, min_toi: float = 0.0) -> dict[str, dict]:
    if not seasons:
        return {}
    rows = con.execute(
        f"""
        SELECT name, position, season, stype, toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga
        FROM skater_stats
        WHERE season IN ({','.join(['?']*len(seasons))})
          AND sit = ?
          AND split = 'oi'
          AND toi IS NOT NULL
        """,
        (*seasons, sit),
    ).fetchall()
    pooled: dict[str, dict] = {}
    for r in rows:
        name, position, season, stype, toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga = r
        if not name:
            continue
        key = f"{name}|{position}"
        d = pooled.setdefault(key, {
            "name": name, "position": position,
            "toi": 0.0, "xgf": 0.0, "xga": 0.0,
            "cf": 0, "ca": 0, "scf": 0, "sca": 0,
            "hdcf": 0, "hdca": 0, "gf": 0, "ga": 0,
        })
        d["toi"] += toi or 0.0
        d["xgf"] += xgf or 0.0
        d["xga"] += xga or 0.0
        d["cf"] += cf or 0
        d["ca"] += ca or 0
        d["scf"] += scf or 0
        d["sca"] += sca or 0
        d["hdcf"] += hdcf or 0
        d["hdca"] += hdca or 0
        d["gf"] += gf or 0
        d["ga"] += ga or 0
    return {k: v for k, v in pooled.items() if v["toi"] >= min_toi}


def league_team_pool(con: sqlite3.Connection, seasons: tuple[str, ...], sit: str) -> dict[str, float]:
    rows = con.execute(
        f"""
        SELECT toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga
        FROM team_stats
        WHERE season IN ({','.join(['?']*len(seasons))}) AND sit = ?
        """,
        (*seasons, sit),
    ).fetchall()
    keys = ("toi", "xgf", "xga", "cf", "ca", "scf", "sca", "hdcf", "hdca", "gf", "ga")
    out = {k: 0.0 for k in keys}
    for r in rows:
        for i, k in enumerate(keys):
            out[k] += r[i] or 0
    return out


def iso_net(player: dict, team_pool: dict) -> float:
    """Compute a player's pooled iso net (xGF/60 - xGA/60) given a team-level baseline."""
    toi = player["toi"]
    if toi <= 0:
        return 0.0
    toi_off = max(team_pool["toi"] - toi, 1.0)
    xgf_off = max(team_pool["xgf"] - player["xgf"], 0.0)
    xga_off = max(team_pool["xga"] - player["xga"], 0.0)
    return (per60(player["xgf"], toi) - per60(xgf_off, toi_off)
            - per60(player["xga"], toi) + per60(xga_off, toi_off))


def build_feature_row(player: dict, team_pool: dict) -> tuple[list[float], dict]:
    """Backtest feature schema. Position one-hots intentionally EXCLUDED — we filter
    by position downstream, so the dummies add noise inside the cohort. Same logic
    we'd want in production once integrated with `find_comparables(position_filter=...)`.
    """
    toi = player["toi"]
    toi_off = max(team_pool["toi"] - toi, 1.0)
    xgf_off = max(team_pool["xgf"] - player["xgf"], 0.0)
    xga_off = max(team_pool["xga"] - player["xga"], 0.0)
    iso_xgf60 = per60(player["xgf"], toi) - per60(xgf_off, toi_off)
    iso_xga60 = per60(player["xga"], toi) - per60(xga_off, toi_off)
    cf60 = per60(player["cf"], toi); ca60 = per60(player["ca"], toi)
    hdcf60 = per60(player["hdcf"], toi); hdca60 = per60(player["hdca"], toi)
    scf60 = per60(player["scf"], toi)
    gf60 = per60(player["gf"], toi); ga60 = per60(player["ga"], toi)
    feats = [
        iso_xgf60, iso_xga60, iso_xgf60 - iso_xga60,
        cf60, ca60, hdcf60, hdca60, scf60, gf60, ga60,
    ]
    meta = {
        "name": player["name"], "position": (player["position"] or "").upper(),
        "pooled_toi_5v5": toi,
        "pooled_iso_xgf60": iso_xgf60,
        "pooled_iso_xga60": iso_xga60,
        "pooled_iso_net60": iso_xgf60 - iso_xga60,
    }
    return feats, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default="20252026", help="Season to hold out (predict)")
    ap.add_argument("--k", type=int, default=5, help="Top-k comps per target")
    ap.add_argument("--min-toi", type=float, default=200.0,
                    help="Min TOI in BOTH the fit window and the holdout year")
    ap.add_argument("--n-components", type=int, default=8)
    ap.add_argument("--target-toi-min", type=float, default=0.0,
                    help="Lower bound on target's fit-window TOI for evaluation (the engine "
                         "is most useful for small-sample targets — set this to filter)")
    ap.add_argument("--target-toi-max", type=float, default=float("inf"),
                    help="Upper bound on target's fit-window TOI for evaluation")
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)

    fit_seasons = tuple(s for s in ALL_SEASONS if s != args.holdout)
    holdout = (args.holdout,)
    print(f"Backtest fold: fit on {fit_seasons}, predict {args.holdout}")

    fit_pooled = fetch_pooled_skaters_for_seasons(con, fit_seasons, "5v5", min_toi=args.min_toi)
    holdout_pooled = fetch_pooled_skaters_for_seasons(con, holdout, "5v5", min_toi=args.min_toi)
    print(f"  Fit window cohort: {len(fit_pooled)} players (>= {args.min_toi} min in fit window)")
    print(f"  Holdout cohort:    {len(holdout_pooled)} players (>= {args.min_toi} min in holdout)")

    # Players in BOTH windows = the testable set
    testable_keys = sorted(set(fit_pooled) & set(holdout_pooled))
    print(f"  Two-fold cohort:   {len(testable_keys)} players (in both)")

    fit_team = league_team_pool(con, fit_seasons, "5v5")
    holdout_team = league_team_pool(con, holdout, "5v5")

    # Build features for ALL fit-window players (so kNN has the full universe to search).
    rows = []; matrix_rows = []; row_meta = []
    cols = ["iso_xgf60", "iso_xga60", "iso_net60", "cf60", "ca60",
            "hdcf60", "hdca60", "scf60", "gf60", "ga60"]
    for key, p in fit_pooled.items():
        feats, meta = build_feature_row(p, fit_team)
        rows.append(key); matrix_rows.append(feats); row_meta.append(meta)
    fm = FeatureMatrix(rows=rows, columns=cols,
                       matrix=np.asarray(matrix_rows, dtype=np.float64), row_meta=row_meta)
    index = build_index_from_features(fm, row_meta=row_meta, n_components=args.n_components)
    print(f"  Index built. PCA cumulative variance @ 5 dims: "
          f"{(index.pca_explained_variance / index.pca_explained_variance.sum())[:5].sum():.3f}")

    # Compute league-mean holdout iso per position (baseline 2)
    league_iso_by_pos: dict[str, list[float]] = {}
    for key, p in holdout_pooled.items():
        pos = (p["position"] or "").upper()
        league_iso_by_pos.setdefault(pos, []).append(iso_net(p, holdout_team))
    league_mean_iso = {pos: float(np.mean(v)) for pos, v in league_iso_by_pos.items()}
    print(f"  League-mean iso_net60 in holdout by position: "
          f"{ {k: round(v, 3) for k, v in league_mean_iso.items()} }")

    # Run the backtest
    errors_self = {pos: [] for pos in ("C", "L", "R", "D")}
    errors_league = {pos: [] for pos in ("C", "L", "R", "D")}
    errors_comp = {pos: [] for pos in ("C", "L", "R", "D")}
    n_skipped = 0

    for key in testable_keys:
        p_fit = fit_pooled[key]
        p_hold = holdout_pooled[key]
        pos = (p_fit["position"] or "").upper()
        if pos not in errors_self:
            continue
        # Target-sample-band filter — the engine is designed to help small samples.
        if not (args.target_toi_min <= p_fit["toi"] <= args.target_toi_max):
            continue

        actual = iso_net(p_hold, holdout_team)
        # baseline_self: predict using fit-window pooled iso
        pred_self = iso_net(p_fit, fit_team)
        # baseline_league: predict using league-mean for position
        pred_league = league_mean_iso.get(pos, 0.0)
        # comp_prediction: predict using top-k comps' holdout iso (mean)
        try:
            comps = index.find_comparables(
                p_fit["name"], k=args.k, position_filter=(pos,), min_pooled_toi=200.0
            )
        except ValueError:
            n_skipped += 1; continue
        # TOI-weight the comp prediction: a comp with 800 holdout-min carries more
        # signal than one with 220 holdout-min. Sum events / sum minutes is the
        # right pooling, not a flat mean of per-60 rates.
        comp_xgf_on = comp_xga_on = comp_xgf_off = comp_xga_off = 0.0
        comp_toi_on = comp_toi_off = 0.0
        for c in comps:
            ch = holdout_pooled.get(f"{c.name}|{c.position}")
            if not ch:
                continue
            ch_toi = ch["toi"]
            ch_toi_off = max(holdout_team["toi"] - ch_toi, 1.0)
            comp_toi_on += ch_toi
            comp_toi_off += ch_toi_off
            comp_xgf_on += ch["xgf"]; comp_xga_on += ch["xga"]
            comp_xgf_off += max(holdout_team["xgf"] - ch["xgf"], 0.0)
            comp_xga_off += max(holdout_team["xga"] - ch["xga"], 0.0)
        if comp_toi_on <= 0:
            n_skipped += 1; continue
        pred_comp = (per60(comp_xgf_on, comp_toi_on) - per60(comp_xgf_off, comp_toi_off)
                     - per60(comp_xga_on, comp_toi_on) + per60(comp_xga_off, comp_toi_off))

        errors_self[pos].append(abs(actual - pred_self))
        errors_league[pos].append(abs(actual - pred_league))
        errors_comp[pos].append(abs(actual - pred_comp))

    # Report
    print(f"\n  Players evaluated (skipped {n_skipped} for missing comps in holdout):")
    print(f"  {'Pos':<4} {'N':>4}  {'MAE_self':>10}  {'MAE_league':>11}  {'MAE_comp':>9}  "
          f"{'lift_vs_self':>13}  {'lift_vs_league':>15}")
    print("  " + "-" * 80)
    summary = {}
    for pos in ("C", "L", "R", "D"):
        n = len(errors_self[pos])
        if n == 0:
            print(f"  {pos:<4} {n:>4}  (no players)")
            continue
        mae_self = float(np.mean(errors_self[pos]))
        mae_league = float(np.mean(errors_league[pos]))
        mae_comp = float(np.mean(errors_comp[pos]))
        lift_self = (mae_self - mae_comp) / mae_self * 100.0 if mae_self > 0 else 0.0
        lift_league = (mae_league - mae_comp) / mae_league * 100.0 if mae_league > 0 else 0.0
        print(f"  {pos:<4} {n:>4}  {mae_self:>10.3f}  {mae_league:>11.3f}  "
              f"{mae_comp:>9.3f}  {lift_self:>+12.1f}%  {lift_league:>+14.1f}%")
        summary[pos] = {"n": n, "mae_self": mae_self, "mae_league": mae_league,
                        "mae_comp": mae_comp, "lift_vs_self": lift_self,
                        "lift_vs_league": lift_league}

    print("\n  ---- Phase 1 gating gate ----")
    fwd_lifts = [summary[p]["lift_vs_self"] for p in ("C", "L", "R") if p in summary]
    if fwd_lifts:
        avg_fwd_lift = float(np.mean(fwd_lifts))
        verdict = "PASS" if avg_fwd_lift >= 15.0 else "FAIL"
        print(f"  Forward MAE-lift vs self-baseline: {avg_fwd_lift:+.1f}% — {verdict} the 15% bar")
    print(f"  D MAE-lift vs self-baseline:       {summary.get('D', {}).get('lift_vs_self', 0):+.1f}%")
    print()


if __name__ == "__main__":
    main()
