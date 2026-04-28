"""Build a goalie comparable index — fitted kNN over performance + bio features.

Mirrors `tools/build_comparable_index.py` but for goalies. The Phase 1 plan
deferred a "proper" goalie comparable engine to v4 because the canonical
feature space (rebound rate, glove-vs-blocker, post-up speed, recovery time)
needs play-by-play parsing or paid tracking data we don't have.

This is the v1 — built on the data we DO have:
    Block A (performance): pooled SV%, hdSV%, GSAx/60, workload share, HD-share
    Block B (bio):         height, weight, age, draft pick

Pulls every goalie with >= 200 reg-season TOI in the 5-year window. Pools
across seasons + stypes (events sum, minutes sum). Reuses the existing
embedding + Mahalanobis-equivalent kNN code unchanged — comparable.py is
feature-agnostic.

Persists to legacy/data/goalie_comparable_index.json (separate from the
skater index).

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_goalie_comparable_index.py
        [--min-toi 200] [--n-components 6]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core import FeatureMatrix, build_index_from_features

SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")
DB_PATH = REPO / "legacy" / "data" / "store.sqlite"
DEFAULT_OUT = REPO / "legacy" / "data" / "goalie_comparable_index.json"


def fetch_pooled_goalies(con: sqlite3.Connection, min_toi: float) -> dict[int, dict]:
    """Pool goalie_stats across all seasons + stypes for sit='all'.

    Keyed on player_id (goalies don't change positions; player_id is the stable
    identity carried through all seasons + teams).
    Returns {player_id: pooled-dict}.
    """
    rows = con.execute(
        f"""
        SELECT player_id, name, season, stype, sit, gp, toi, ga, sa, xga, hdga, hdca
        FROM goalie_stats
        WHERE season IN ({','.join(['?']*len(SEASONS))})
          AND sit = 'all'
          AND toi IS NOT NULL
        """,
        SEASONS,
    ).fetchall()
    pooled: dict[int, dict] = {}
    for pid, name, season, stype, sit, gp, toi, ga, sa, xga, hdga, hdca in rows:
        if not pid:
            continue
        pid = int(pid)  # goalie_stats stores player_id as TEXT; bio table is INTEGER
        d = pooled.setdefault(pid, {
            "player_id": pid, "name": name,
            "toi": 0.0, "gp": 0,
            "ga": 0, "sa": 0, "xga": 0.0, "hdga": 0, "hdca": 0,
            "playoff_toi": 0.0, "playoff_gp": 0,
            "gp_2425": 0, "gp_2526": 0, "max_season_gp": 0,
        })
        d["toi"] += toi or 0.0
        d["gp"] += gp or 0
        d["ga"] += ga or 0
        d["sa"] += sa or 0
        d["xga"] += xga or 0.0
        d["hdga"] += hdga or 0
        d["hdca"] += hdca or 0
        if stype == 3:
            d["playoff_toi"] += toi or 0.0
            d["playoff_gp"] += gp or 0
        # Career-shape signals
        if stype == 2 and season == "20242025":
            d["gp_2425"] = gp or 0
        if stype == 2 and season == "20252026":
            d["gp_2526"] = gp or 0
        if stype == 2:
            d["max_season_gp"] = max(d["max_season_gp"], gp or 0)
    # Prune low-TOI goalies
    return {k: v for k, v in pooled.items() if v["toi"] >= min_toi}


def fetch_bio(con: sqlite3.Connection) -> dict[int, dict]:
    today = date.today()
    out: dict[int, dict] = {}
    for r in con.execute(
        "SELECT player_id, height_in, weight_lb, birth_date, draft_overall FROM edge_player_bio"
    ).fetchall():
        pid, h, w, bd, draft = r
        age = float("nan")
        if bd:
            try:
                bdate = datetime.strptime(bd, "%Y-%m-%d").date()
                age = (today - bdate).days / 365.25
            except ValueError:
                pass
        out[pid] = {
            "height_in": float(h) if h is not None else float("nan"),
            "weight_lb": float(w) if w is not None else float("nan"),
            "age_years": age,
            "draft_overall": float(draft) if draft is not None else float("nan"),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-toi", type=float, default=200.0,
                    help="Min pooled all-strength reg-season TOI")
    ap.add_argument("--n-components", type=int, default=6)
    ap.add_argument("--sanity-targets", nargs="*",
                    default=["Jakub Dobes", "Connor Hellebuyck",
                             "Andrei Vasilevskiy", "Jeremy Swayman", "Logan Thompson"])
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH, timeout=60)
    pooled = fetch_pooled_goalies(con, min_toi=args.min_toi)
    print(f"Goalies with pooled TOI >= {args.min_toi}: {len(pooled)}")
    bio = fetch_bio(con)
    print(f"Bios available: {len(bio)}")
    coverage = sum(1 for pid in pooled if pid in bio)
    print(f"Goalies with bio: {coverage} of {len(pooled)}")

    # Workload reference for normalization (max pooled TOI in cohort)
    max_pooled_toi = max(d["toi"] for d in pooled.values())
    print(f"Max pooled TOI (workload-share denominator): {max_pooled_toi:.0f}")

    feature_columns = [
        # Block A: performance
        "sv_pct",            # weighted SV% (1 - GA/SA)
        "hd_sv_pct",         # 1 - HDGA / HDCA  (HDCA is chances; documented proxy)
        "gsax_per60",        # (xGA - GA) per 60 min
        "workload_share",    # toi / max(toi)  in the cohort
        "hd_share",          # HDCA / (HDCA + non-HD chances)  workload-quality proxy
        "gp_growth",         # gp_2526 / max(gp_2425, 1) — career-arc shape
        # Block B: bio
        "height_in",
        "weight_lb",
        "age_years",
        "draft_overall",
    ]

    rows = []
    row_meta = []
    matrix_rows = []

    for pid, d in pooled.items():
        toi = d["toi"]
        sa = d["sa"]
        ga = d["ga"]
        xga = d["xga"]
        hdga = d["hdga"]
        hdca = d["hdca"]
        sv_pct = (1.0 - ga / sa) if sa > 0 else float("nan")
        hd_sv_pct = (1.0 - hdga / hdca) if hdca > 0 else float("nan")
        # GSAx per 60: (xGA - GA) * 60 / toi
        gsax_per60 = ((xga - ga) * 60.0 / toi) if toi > 0 else float("nan")
        workload_share = toi / max_pooled_toi
        # Approx hd_share: HDCA / (CA against). We have HDCA but not CA at goalie
        # level; the goalie_stats sit='5v5' has CA. Approximate via SA — high-danger
        # share of shots-against. Not a true HD-share but the ratio sa-vs-hdca
        # rank-orders meaningfully.
        hd_share = hdca / sa if sa > 0 else float("nan")
        gp_growth = d["gp_2526"] / max(d["gp_2425"], 1)

        b = bio.get(pid, {})
        feats = [
            sv_pct,
            hd_sv_pct,
            gsax_per60,
            workload_share,
            hd_share,
            gp_growth,
            b.get("height_in", float("nan")),
            b.get("weight_lb", float("nan")),
            b.get("age_years", float("nan")),
            b.get("draft_overall", float("nan")),
        ]
        rows.append(str(pid))
        matrix_rows.append(feats)
        row_meta.append({
            "name": d["name"],
            "position": "G",
            "player_id": pid,
            "pooled_toi": toi,
            # The skater find_comparables() filters on pooled_toi_5v5; we alias
            # it to the goalie's all-strength TOI so goalie-vs-goalie kNN doesn't
            # get filtered out by a min_pooled_toi default tuned for skaters.
            "pooled_toi_5v5": toi,
            "pooled_gp": d["gp"],
            "pooled_playoff_toi": d["playoff_toi"],
            "sv_pct": sv_pct,
            "gsax_per60": gsax_per60,
            "max_season_gp": d["max_season_gp"],
        })

    matrix = np.asarray(matrix_rows, dtype=np.float64)
    print(f"Feature matrix shape: {matrix.shape}")

    fm = FeatureMatrix(rows=rows, columns=feature_columns, matrix=matrix, row_meta=row_meta)
    print(f"Building goalie index, n_components={args.n_components} ...")
    index = build_index_from_features(
        fm, row_meta, n_components=args.n_components,
        metadata={
            "kind": "goalie",
            "seasons": list(SEASONS),
            "min_toi": args.min_toi,
            "feature_columns": feature_columns,
            "max_pooled_toi": max_pooled_toi,
            "built_at": datetime.utcnow().isoformat(timespec="seconds"),
            "notes": (
                "v1 goalie kNN. Built on bio + pooled performance from goalie_stats. "
                "Doesn't include rebound, glove-side, or post-up tracking — those need PBP "
                "parsing not yet implemented. Sample-size warnings: workload_share captures "
                "starter-vs-backup; the bio block prevents young breakouts from matching "
                "30-something veterans purely on shape."
            ),
        },
    )
    index.save(args.output)
    print(f"Persisted: {args.output}")
    print()

    # Sanity targets
    print("=" * 100)
    print("Sanity check: top-5 comps for canonical targets")
    print("=" * 100)
    for target in args.sanity_targets:
        # Find pid by name
        target_pid = None
        for pid, d in pooled.items():
            if d["name"].lower() == target.lower():
                target_pid = pid
                break
        if target_pid is None:
            print(f"\nTarget: {target}  (not in pool)")
            continue
        try:
            comps = index.find_comparables(target, k=5)
        except Exception as e:
            print(f"\nTarget: {target}  failed: {e}")
            continue
        print(f"\nTarget: {target}")
        for c in comps:
            drivers = sorted(c.feature_contributions.items(), key=lambda x: -x[1])[:3]
            drv_str = "  ".join(f"{k}=Δz{v:+.2f}" for k, v in drivers)
            print(f"  score {c.score:5.1f}  {c.name:24s}  toi={c.pooled_toi_5v5:6.0f}  drivers: {drv_str}")


if __name__ == "__main__":
    main()
