"""Build the player comparable index from existing NST data in store.sqlite.

Phase 1 — Block A only (NST iso + rate stats). Block B (NHL Edge biometrics)
and Block C (cross-league NHLe) are added in subsequent phases.

Pulls all NHL skaters with ≥ 200 NHL min in any of seasons 21-22 → 25-26
(5-year window). Pools each player's stats across all seasons in the window
(events summed, minutes summed). Computes iso impacts at 5v5 and 5v4, plus
on-ice rate stats. Builds the feature matrix, fits standardize + PCA,
persists the index to JSON.

Sanity-test queries are run at the end.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_comparable_index.py
    [--output PATH] [--min-toi 200] [--n-components 8]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core import (
    FeatureMatrix,
    POSITION_TOKENS,
    build_index_from_features,
)


SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")
DB_PATH = REPO / "legacy" / "data" / "store.sqlite"
DEFAULT_OUT = REPO / "legacy" / "data" / "comparable_index.json"


def per60(events: float, toi_min: float) -> float:
    return events * 60.0 / toi_min if toi_min and toi_min > 0 else 0.0


def fetch_pooled_skaters(con: sqlite3.Connection, sit: str, min_toi: float = 200.0) -> dict[str, dict]:
    """For each player, pool stats across all seasons + stypes in the window for one strength state.

    Returns {player_key: {sums...}}. Player key normalizes name + position so
    a player who changed teams pools across teams.
    """
    rows = con.execute(
        f"""
        SELECT name, position, season, stype, toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga
        FROM skater_stats
        WHERE season IN ({','.join(['?']*len(SEASONS))})
          AND sit = ?
          AND split = 'oi'
          AND toi IS NOT NULL
        """,
        (*SEASONS, sit),
    ).fetchall()
    pooled: dict[str, dict] = {}
    for r in rows:
        name, position, season, stype, toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga = r
        if not name:
            continue
        # Use name+position as key; collapsing across teams + seasons + stypes.
        key = f"{name}|{position}"
        if key not in pooled:
            pooled[key] = {
                "name": name, "position": position,
                "toi": 0.0, "xgf": 0.0, "xga": 0.0,
                "cf": 0, "ca": 0, "scf": 0, "sca": 0,
                "hdcf": 0, "hdca": 0, "gf": 0, "ga": 0,
                "playoff_toi": 0.0,
            }
        d = pooled[key]
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
        if stype == 3:
            d["playoff_toi"] += toi or 0.0
    return {k: v for k, v in pooled.items() if v["toi"] >= min_toi}


def fetch_pooled_team_stats(con: sqlite3.Connection, sit: str) -> dict[str, dict]:
    """Pool team_stats across the window for a strength state.

    Used for the iso-impact denominators (off-ice rates).
    """
    rows = con.execute(
        f"""
        SELECT team_id, season, stype, toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga
        FROM team_stats
        WHERE season IN ({','.join(['?']*len(SEASONS))})
          AND sit = ?
        """,
        (*SEASONS, sit),
    ).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        team_id, season, stype, toi, xgf, xga, cf, ca, scf, sca, hdcf, hdca, gf, ga = r
        # Collapse across (team_id, season, stype) → 'league' bucket
        # We want league-level pool because individual players move teams.
        # For the iso impact, use team-level numbers indexed by team_id.
        key = team_id
        if key not in out:
            out[key] = {"toi": 0.0, "xgf": 0.0, "xga": 0.0,
                        "cf": 0, "ca": 0, "scf": 0, "sca": 0,
                        "hdcf": 0, "hdca": 0, "gf": 0, "ga": 0}
        d = out[key]
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
    return out


def fetch_player_team_map(con: sqlite3.Connection, sit: str) -> dict[str, dict]:
    """For pooled iso, we need (team_toi, team_xgf, ...) summed across the
    same team-game contexts the player played in. Simplification for v1:
    use league-average team rates (pool all teams) as the off-ice baseline.
    This is a known approximation; documented in the model output.
    """
    return fetch_pooled_team_stats(con, sit)


def league_average_team_pool(team_pools: dict[str, dict]) -> dict[str, float]:
    """Aggregate team pool across all teams to a single league-average row."""
    keys = ("toi", "xgf", "xga", "cf", "ca", "scf", "sca", "hdcf", "hdca", "gf", "ga")
    total = {k: 0.0 for k in keys}
    for d in team_pools.values():
        for k in keys:
            total[k] += d.get(k, 0)
    return total


def fetch_player_bio(con: sqlite3.Connection) -> dict[str, dict]:
    """Per-player static bio (height, weight, age, draft).

    Keyed by lowercased name for matching. Players without bio simply absent;
    caller NaN-imputes.
    """
    out: dict[str, dict] = {}
    try:
        rows = con.execute("""
            SELECT name, height_in, weight_lb, birth_date, draft_overall
            FROM edge_player_bio
        """).fetchall()
    except sqlite3.OperationalError:
        return {}
    from datetime import datetime
    today = datetime.utcnow().date()
    for r in rows:
        name, h, w, bd, draft = r
        age = float("nan")
        if bd:
            try:
                bdate = datetime.strptime(bd, "%Y-%m-%d").date()
                age = (today - bdate).days / 365.25
            except Exception:
                pass
        out[name] = {
            "height_in": float(h) if h is not None else float("nan"),
            "weight_lb": float(w) if w is not None else float("nan"),
            "age_years": age,
            "draft_overall": float(draft) if draft is not None else float("nan"),
        }
    return out


def fetch_edge_features_max(con: sqlite3.Connection) -> dict[str, dict]:
    """Per-player career-best Edge biometrics (max across all (season, game_type) rows).
    Returns {name: {max_skating_speed_mph, max_shot_speed_mph, skating_burst_count_22plus, ...}}.
    Players without Edge data are simply absent from the dict (caller NaN-imputes).
    """
    out: dict[str, dict] = {}
    try:
        rows = con.execute("""
            SELECT name,
                   MAX(max_skating_speed_mph) AS max_speed,
                   MAX(max_shot_speed_mph)    AS max_shot,
                   MAX(skating_burst_count_22plus) AS bursts_22,
                   MAX(hard_shot_count_90plus) AS shots_90
            FROM edge_player_features
            GROUP BY name
        """).fetchall()
    except sqlite3.OperationalError:
        return {}  # edge tables not yet created
    for r in rows:
        name, max_speed, max_shot, bursts, shots90 = r
        out[name] = {
            "max_skating_speed_mph": max_speed,
            "max_shot_speed_mph": max_shot,
            "skating_burst_count_22plus": bursts or 0,
            "hard_shot_count_90plus": shots90 or 0,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-toi", type=float, default=200.0,
                    help="Min pooled 5v5 TOI for inclusion in index (default 200 min)")
    ap.add_argument("--n-components", type=int, default=8)
    ap.add_argument("--no-block-b", action="store_true",
                    help="Skip Edge biometric features (rebuilds Block-A-only index)")
    ap.add_argument("--sanity-targets", nargs="*",
                    default=["Brendan Gallagher", "Cole Caufield", "Nick Suzuki",
                             "Zachary Bolduc", "Lane Hutson"])
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)

    print(f"Pooling skater_stats across {SEASONS} (5v5 + 5v4) ...")
    pooled_5v5 = fetch_pooled_skaters(con, sit="5v5", min_toi=args.min_toi)
    pooled_5v4 = fetch_pooled_skaters(con, sit="5v4", min_toi=0.0)  # PP TOI is small; don't filter
    print(f"  5v5 universe: {len(pooled_5v5)} skaters with toi >= {args.min_toi} min")
    print(f"  5v4 universe: {len(pooled_5v4)} skaters with any PP toi")

    team_5v5 = league_average_team_pool(fetch_pooled_team_stats(con, "5v5"))
    team_5v4 = league_average_team_pool(fetch_pooled_team_stats(con, "5v4"))
    print(f"  League-pool team 5v5 toi: {team_5v5['toi']:.0f} min")

    # Block A: NST iso + on-ice rates + position
    feature_columns = [
        "iso_xgf60",        # 5v5 isolated offensive impact
        "iso_xga60",        # 5v5 isolated defensive impact
        "iso_net60",        # 5v5 net iso
        "cf60",             # 5v5 on-ice Corsi for per 60
        "ca60",             # 5v5 on-ice Corsi against per 60
        "hdcf60",           # 5v5 on-ice HD chances for per 60
        "hdca60",           # 5v5 on-ice HD chances against per 60
        "scf60",            # 5v5 on-ice scoring chances for per 60
        "gf60",             # 5v5 on-ice GF per 60
        "ga60",             # 5v5 on-ice GA per 60
        "iso_xgf60_pp",     # 5v4 isolated offensive impact
        "pp_share",         # PP TOI / total TOI (proxy for special-teams role)
        "pos_C", "pos_L", "pos_R", "pos_D",   # one-hot position
    ]
    edge_features = {}
    bio_features = {}
    if not args.no_block_b:
        edge_features = fetch_edge_features_max(con)
        bio_features = fetch_player_bio(con)
        print(f"  Edge biometrics available for {len(edge_features)} players")
        print(f"  Static bio (height/weight/age/draft) for {len(bio_features)} players")
        # Block B1: NHL Edge biometric columns (NaN where unknown)
        feature_columns += [
            "max_skating_speed_mph",     # peak observed top speed
            "max_shot_speed_mph",        # peak observed hardest shot
            "skating_burst_count_22plus",  # high-speed-burst frequency proxy
            "hard_shot_count_90plus",      # heavy-shot count
        ]
        # Block B2: static bio (objective, doesn't depend on noisy LLM extraction)
        feature_columns += [
            "height_in",                 # static height in inches
            "weight_lb",                 # static weight in pounds
            "age_years",                 # current age (years, fractional)
            "draft_overall",             # draft pick number (NaN if undrafted)
        ]

    rows = []
    row_meta = []
    matrix_rows = []

    for key, p in pooled_5v5.items():
        toi_5v5 = p["toi"]
        # Off-ice (team minus player)
        toi_off = max(team_5v5["toi"] - toi_5v5, 1.0)
        xgf_off = max(team_5v5["xgf"] - p["xgf"], 0.0)
        xga_off = max(team_5v5["xga"] - p["xga"], 0.0)
        # Iso impacts
        iso_xgf60 = per60(p["xgf"], toi_5v5) - per60(xgf_off, toi_off)
        iso_xga60 = per60(p["xga"], toi_5v5) - per60(xga_off, toi_off)
        # On-ice rates
        cf60 = per60(p["cf"], toi_5v5)
        ca60 = per60(p["ca"], toi_5v5)
        hdcf60 = per60(p["hdcf"], toi_5v5)
        hdca60 = per60(p["hdca"], toi_5v5)
        scf60 = per60(p["scf"], toi_5v5)
        gf60 = per60(p["gf"], toi_5v5)
        ga60 = per60(p["ga"], toi_5v5)

        # PP iso (if player has 5v4 minutes)
        p4 = pooled_5v4.get(key)
        if p4 and p4["toi"] > 0:
            toi_pp = p4["toi"]
            toi_off_pp = max(team_5v4["toi"] - toi_pp, 1.0)
            xgf_off_pp = max(team_5v4["xgf"] - p4["xgf"], 0.0)
            iso_xgf60_pp = per60(p4["xgf"], toi_pp) - per60(xgf_off_pp, toi_off_pp)
            pp_share = toi_pp / (toi_5v5 + toi_pp)
        else:
            iso_xgf60_pp = float("nan")
            pp_share = 0.0

        # Position one-hot
        pos = (p["position"] or "").upper()
        pos_features = {f"pos_{tok}": 1.0 if pos == tok else 0.0 for tok in POSITION_TOKENS}

        feats = [
            iso_xgf60, iso_xga60, iso_xgf60 - iso_xga60,
            cf60, ca60, hdcf60, hdca60, scf60, gf60, ga60,
            iso_xgf60_pp, pp_share,
            pos_features["pos_C"], pos_features["pos_L"],
            pos_features["pos_R"], pos_features["pos_D"],
        ]
        if not args.no_block_b:
            edge = edge_features.get(p["name"], {})
            feats.extend([
                edge.get("max_skating_speed_mph", float("nan")),
                edge.get("max_shot_speed_mph", float("nan")),
                edge.get("skating_burst_count_22plus", float("nan")),
                edge.get("hard_shot_count_90plus", float("nan")),
            ])
            bio = bio_features.get(p["name"], {})
            feats.extend([
                bio.get("height_in", float("nan")),
                bio.get("weight_lb", float("nan")),
                bio.get("age_years", float("nan")),
                bio.get("draft_overall", float("nan")),
            ])
        rows.append(key)
        matrix_rows.append(feats)
        row_meta.append({
            "name": p["name"],
            "position": pos,
            "pooled_toi_5v5": toi_5v5,
            "pooled_toi_5v4": p4["toi"] if p4 else 0.0,
            "pooled_playoff_toi_5v5": p["playoff_toi"],
            "pooled_iso_xgf60": iso_xgf60,
            "pooled_iso_xga60": iso_xga60,
            "pooled_iso_net60": iso_xgf60 - iso_xga60,
        })

    matrix = np.asarray(matrix_rows, dtype=np.float64)
    print(f"  Feature matrix shape: {matrix.shape}")

    fm = FeatureMatrix(rows=rows, columns=feature_columns, matrix=matrix, row_meta=row_meta)

    print(f"Building index with PCA n_components={args.n_components} ...")
    index = build_index_from_features(
        fm, row_meta=row_meta, n_components=args.n_components,
        metadata={
            "seasons": list(SEASONS),
            "sit_5v5_min_toi": args.min_toi,
            "n_features": len(feature_columns),
            "block_a_added": True,
            "block_b_added": (not args.no_block_b),
            "block_b_coverage": (
                f"{len(edge_features)} of {len(rows)} players have Edge data; "
                "the rest are NaN-imputed to mean during standardize"
            ) if not args.no_block_b else "skipped",
            "block_c_added": False,
            "build_note": (
                f"Block A (NST oi 5v5+5v4) {'+ Block B (NHL Edge biometrics, partial coverage)' if not args.no_block_b else ''}. "
                "League-average team baseline used for iso (acknowledged approximation)."
            ),
        },
    )

    print(f"  PCA explained variance ratio: {[round(v, 3) for v in index.pca_explained_variance / index.pca_explained_variance.sum()][:8]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    index.save(args.output)
    print(f"\nWrote {args.output}\n")

    # Sanity tests
    print("=== Sanity-test top-5 comparables ===")
    for target in args.sanity_targets:
        try:
            comps = index.find_comparables(target, k=5, min_pooled_toi=200.0)
        except ValueError as e:
            print(f"  {target}: NOT FOUND ({e})")
            continue
        print(f"\nTarget: {target}")
        for c in comps:
            top_features = sorted(c.feature_contributions.items(), key=lambda kv: -kv[1])[:3]
            top_str = ", ".join(f"{k}: Δz={v:.2f}" for k, v in top_features if v > 0)
            print(f"  score {c.score:5.1f}  {c.name:25s} ({c.position})  toi={c.pooled_toi_5v5:>6.0f}  iso_net={c.pooled_iso_xgf60-c.pooled_iso_xga60:+.3f}  drivers: {top_str}")


if __name__ == "__main__":
    main()
