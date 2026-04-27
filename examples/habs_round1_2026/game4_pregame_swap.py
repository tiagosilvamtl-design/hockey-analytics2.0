"""Pre-game Game 4 swap-impact analyzer.

Computes the projected impact of the announced TBL lineup change on advanced
stats, using the framework's swap engine with pooled (regular-season + playoff)
baselines:

    OUT: Declan Carlile  (TBL 3rd-pair LD/RD this series)
    IN:  Max Crozier     (TBL replacement, RHD)

Pool windows: 24-25 reg + 24-25 playoffs + 25-26 reg + 25-26 playoffs.
Strength state: 5v5 only (3rd-pair minutes are 5v5; PP impact is irrelevant
since neither plays the unit).

Slot: 12.0 minutes per game (Carlile played 11:20 in G3; same band expected
for Crozier at 5v5).

Also computes a Lilleberg side-context note (R→L shift) — the swap engine
can't isolate side, so we report Lilleberg's pooled iso as a baseline and
flag the interpretation caveat.

Output: examples/habs_round1_2026/game4_pregame_swap.numbers.json
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "legacy"))

from analytics.swap_engine import (
    PlayerImpact,
    build_pooled_player_impact,
    project_swap,
)

DB = REPO / "legacy" / "data" / "store.sqlite"
OUT_PATH = Path(__file__).parent / "game4_pregame_swap.numbers.json"

# ---------- pool-window definition ----------
POOL_KEYS = [
    ("20242025", 2),  # 24-25 regular season
    ("20242025", 3),  # 24-25 playoffs
    ("20252026", 2),  # 25-26 regular season
    ("20252026", 3),  # 25-26 playoffs (current)
]

PLAYERS = {
    "Declan Carlile": "T.B",
    "Max Crozier":    "T.B",
    "Emil Lilleberg": "T.B",
}

SLOT_MIN_PER_GAME = 12.0  # 3rd-pair 5v5 slot estimate


def fetch_player_rows(con: sqlite3.Connection, name: str) -> pd.DataFrame:
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in POOL_KEYS)
    params: list = []
    for s, st in POOL_KEYS:
        params.extend([s, st])
    q = f"""
        SELECT name, team_id, season, stype, sit, split, toi, xgf, xga
        FROM skater_stats
        WHERE name = ?
          AND sit = '5v5' AND split = 'oi'
          AND ({keys_clause})
    """
    df = pd.read_sql_query(q, con, params=[name] + params)
    return df


def fetch_team_rows(con: sqlite3.Connection, team_id: str) -> pd.DataFrame:
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in POOL_KEYS)
    params: list = []
    for s, st in POOL_KEYS:
        params.extend([s, st])
    q = f"""
        SELECT team_id, season, stype, sit, toi, xgf, xga
        FROM team_stats
        WHERE team_id = ?
          AND sit = '5v5'
          AND ({keys_clause})
    """
    df = pd.read_sql_query(q, con, params=[team_id] + params)
    return df


def impact_dict(p: PlayerImpact) -> dict:
    return {
        "name": p.name,
        "team_id": p.team_id,
        "toi_on_min": round(p.toi_on, 1),
        "toi_off_min": round(p.toi_off, 1),
        "xgf_on": round(p.xgf_on, 2),
        "xga_on": round(p.xga_on, 2),
        "xgf_off": round(p.xgf_off, 2),
        "xga_off": round(p.xga_off, 2),
        "iso_xgf60": round(p.iso_xgf60, 3),
        "iso_xga60": round(p.iso_xga60, 3),
        "iso_net60": round(p.iso_xgf60 - p.iso_xga60, 3),
    }


def main() -> int:
    con = sqlite3.connect(DB)

    # 1. Build pooled team rows once for TBL.
    tbl_team = fetch_team_rows(con, "T.B")
    if tbl_team.empty:
        raise SystemExit("No TBL team rows in pool windows. Aborting.")

    # 2. Build pooled per-player impacts.
    impacts: dict[str, PlayerImpact] = {}
    raw_rows: dict[str, pd.DataFrame] = {}
    for name, team in PLAYERS.items():
        rows = fetch_player_rows(con, name)
        raw_rows[name] = rows
        if rows.empty:
            print(f"WARN: no NST rows for {name} in pool windows.", file=sys.stderr)
            continue
        impacts[name] = build_pooled_player_impact(rows, tbl_team, team_id=team)

    out = impacts["Declan Carlile"]
    inp = impacts["Max Crozier"]

    # 3. Project the direct swap at 12 min/game.
    swap = project_swap(
        out_player=out,
        in_player=inp,
        slot_minutes=SLOT_MIN_PER_GAME,
        strength_state="5v5",
        confidence=0.80,
    )

    # 4. Translate per-60 deltas into a per-game expectation.
    # delta_xgf60 is already in units of "TBL xG per 60 of team play during
    # the slot." Multiply by slot_share to get xG-per-game contribution.
    slot_share = SLOT_MIN_PER_GAME / 60.0
    # NB: project_swap already multiplies by slot_share, so delta_xgf60 IS
    # the per-game xG delta (over 60 min of total play). We report both
    # framings for clarity.

    # 5. Series-level expectation: assume MTL has last change and feeds
    # the slot 12 min / game. We do NOT predict series outcomes; we
    # report the projected xG delta accumulated across the remaining
    # games (4 max).

    payload = {
        "meta": {
            "as_of": "2026-04-26",
            "matchup": "TBL @ MTL Game 4",
            "swap_engine_version": "legacy/analytics/swap_engine.py (pooled)",
            "pool_windows": [
                {"season": s, "stype": st,
                 "label": ("regular" if st == 2 else "playoff")} for s, st in POOL_KEYS
            ],
            "strength_state": "5v5",
            "slot_minutes_per_game": SLOT_MIN_PER_GAME,
            "confidence": 0.80,
            "data_source": "Natural Stat Trick on-ice (oi) splits via legacy/data/store.sqlite",
        },
        "impacts": {name: impact_dict(p) for name, p in impacts.items()},
        "raw_pool_breakdown": {
            name: rows[["season", "stype", "toi", "xgf", "xga"]].to_dict(orient="records")
            for name, rows in raw_rows.items() if not rows.empty
        },
        "tbl_team_pool": {
            "toi_min": round(float(tbl_team["toi"].sum()), 1),
            "xgf": round(float(tbl_team["xgf"].sum()), 2),
            "xga": round(float(tbl_team["xga"].sum()), 2),
        },
        "swap": {
            "out": out.name,
            "in":  inp.name,
            "slot_minutes": swap.slot_minutes,
            "strength_state": swap.strength_state,
            "delta_xgf_per_game": round(swap.delta_xgf60, 4),
            "delta_xga_per_game": round(swap.delta_xga60, 4),
            "delta_net_per_game": round(swap.delta_xgf60 - swap.delta_xga60, 4),
            "delta_xgf_ci80":     [round(swap.delta_xgf60_ci80[0], 4), round(swap.delta_xgf60_ci80[1], 4)],
            "delta_xga_ci80":     [round(swap.delta_xga60_ci80[0], 4), round(swap.delta_xga60_ci80[1], 4)],
            "interpretation": (
                f"Replacing {out.name} with {inp.name} in the 3rd-pair 5v5 "
                f"slot ({SLOT_MIN_PER_GAME:.0f} min/game) changes TBL's expected "
                f"goals at 5v5 by {swap.delta_xgf60:+.3f} xGF and "
                f"{swap.delta_xga60:+.3f} xGA per game. Net delta from TBL's "
                f"perspective: {swap.delta_xgf60 - swap.delta_xga60:+.3f} xG/game."
            ),
            "caveats": swap.sample_note,
        },
        "lilleberg_side_shift_context": {
            "note": (
                "Lilleberg shifts from R to L on the third pair. The swap "
                "engine cannot isolate handedness/side effects from on/off "
                "splits. Report his pooled iso impact as ambient context only."
            ),
            "pooled_impact": impact_dict(impacts["Emil Lilleberg"]),
        },
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH}")

    # Quick console print so the call surfaces the headline number.
    s = payload["swap"]
    print()
    print(f"  OUT: {s['out']:>20s}  iso_net60 = {impacts['Declan Carlile'].iso_xgf60 - impacts['Declan Carlile'].iso_xga60:+.3f}")
    print(f"   IN: {s['in']:>20s}  iso_net60 = {impacts['Max Crozier'].iso_xgf60 - impacts['Max Crozier'].iso_xga60:+.3f}")
    print(f"  slot = {s['slot_minutes']:.0f} min, 5v5 only")
    print(f"  Δ xGF/game = {s['delta_xgf_per_game']:+.3f}  CI80 [{s['delta_xgf_ci80'][0]:+.3f}, {s['delta_xgf_ci80'][1]:+.3f}]")
    print(f"  Δ xGA/game = {s['delta_xga_per_game']:+.3f}  CI80 [{s['delta_xga_ci80'][0]:+.3f}, {s['delta_xga_ci80'][1]:+.3f}]")
    print(f"  Δ net/game = {s['delta_net_per_game']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
