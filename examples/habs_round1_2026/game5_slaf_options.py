"""Game 5 contingency analyzer: who replaces Slafkovský if he can't play?

Computes for each lineup permutation the projected per-game xG delta vs the
status quo (with Slaf out). Uses the framework's pooled-baseline swap engine
plus the kNN comparable index + scouting tags for context.

Permutations evaluated:
  A. Direct slot: Gallagher in for Slaf on L1 (off-wing or flip Caufield).
  B. Direct slot: Laine in for Slaf on L1 LW (natural side, post-injury sample).
  C. Promote Texier to L1 LW (natural L), Gallagher into Texier's L2 LW slot.
  D. Promote Demidov to L1 LW, Gallagher down to L3 (Demidov's slot).

Also runs a "warrior-tag lift" study on Gallagher's kNN cohort: do his comps
with the `warrior` tag tend to lift their iso impact more in playoffs than
his non-warrior comps?

Output: game5_slaf_options.numbers.json
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "legacy"))
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from analytics.swap_engine import (
    PlayerImpact,
    build_pooled_player_impact,
    project_swap,
)
from lemieux.core.comparable import ComparableIndex

DB = REPO / "legacy" / "data" / "store.sqlite"
INDEX = REPO / "legacy" / "data" / "comparable_index.json"
OUT_PATH = Path(__file__).parent / "game5_slaf_options.numbers.json"

POOL_KEYS = [
    ("20242025", 2),  # 24-25 reg
    ("20242025", 3),  # 24-25 playoff
    ("20252026", 2),  # 25-26 reg
    ("20252026", 3),  # 25-26 playoff (current)
]

# Slot-time assumptions (5v5 mins per game).
L1_SLOT = 14.0   # L1 LW typical 5v5 deployment
L2_SLOT = 12.0
L3_SLOT = 10.0

CANDIDATES = ["Brendan Gallagher", "Patrik Laine", "Alexandre Texier",
              "Ivan Demidov", "Zachary Bolduc", "Joshua Roy"]
SLAF = "Juraj Slafkovský"
DEPLOYED_FORWARDS = [
    "Juraj Slafkovský", "Nick Suzuki", "Cole Caufield",
    "Alexandre Texier", "Kirby Dach", "Zachary Bolduc",
    "Alex Newhook", "Oliver Kapanen", "Ivan Demidov",
    "Phillip Danault", "Josh Anderson", "Jake Evans",
]


def fetch_player_rows(con, name):
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in POOL_KEYS)
    params = []
    for s, st in POOL_KEYS:
        params.extend([s, st])
    q = f"""
        SELECT name, team_id, season, stype, sit, split, toi, xgf, xga
        FROM skater_stats
        WHERE name = ? AND sit='5v5' AND split='oi' AND ({keys_clause})
    """
    return pd.read_sql_query(q, con, params=[name] + params)


def fetch_team_rows(con, team_id):
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in POOL_KEYS)
    params = []
    for s, st in POOL_KEYS:
        params.extend([s, st])
    q = f"""
        SELECT team_id, season, stype, sit, toi, xgf, xga
        FROM team_stats
        WHERE team_id = ? AND sit='5v5' AND ({keys_clause})
    """
    return pd.read_sql_query(q, con, params=[team_id] + params)


def player_tags(con, name, *, min_conf=0.5):
    rows = con.execute(
        "SELECT tag, confidence, source_quote, source_url FROM scouting_tags WHERE name=? ORDER BY confidence DESC",
        (name,)
    ).fetchall()
    return [
        {"tag": r[0], "confidence": round(r[1], 2),
         "source_quote": r[2][:300] if r[2] else "",
         "source_url": r[3] or ""}
        for r in rows if r[1] >= min_conf
    ]


def player_attributes(con, name, *, min_conf=0.5):
    rows = con.execute(
        "SELECT attribute, value, confidence FROM scouting_attributes WHERE name=? ORDER BY value DESC",
        (name,)
    ).fetchall()
    return [
        {"attribute": r[0], "value": round(r[1], 2), "confidence": round(r[2], 2)}
        for r in rows if r[2] >= min_conf
    ]


def impact_dict(p: PlayerImpact) -> dict:
    return {
        "name": p.name,
        "team_id": p.team_id,
        "toi_on_min": round(p.toi_on, 1),
        "xgf_on": round(p.xgf_on, 2),
        "xga_on": round(p.xga_on, 2),
        "iso_xgf60": round(p.iso_xgf60, 3),
        "iso_xga60": round(p.iso_xga60, 3),
        "iso_net60": round(p.iso_xgf60 - p.iso_xga60, 3),
    }


def pooled_iso_full(con, name, stype):
    rows = con.execute(
        """SELECT toi, xgf, xga FROM skater_stats
           WHERE name=? AND split='oi' AND sit='5v5' AND stype=?""",
        (name, stype),
    ).fetchall()
    toi = sum((r[0] or 0) for r in rows)
    xgf = sum((r[1] or 0) for r in rows)
    xga = sum((r[2] or 0) for r in rows)
    if toi <= 0:
        return None
    return {
        "toi": round(toi, 1),
        "iso_net60": round((xgf - xga) * 60.0 / toi, 3),
        "xgf60": round(xgf * 60.0 / toi, 3),
        "xga60": round(xga * 60.0 / toi, 3),
    }


def warrior_lift_study(con, idx: ComparableIndex):
    """Gallagher's kNN comps split by warrior tag; bootstrap CI on lift difference."""
    comps = idx.find_comparables("Brendan Gallagher", k=30, min_pooled_toi=200.0)
    rows = []
    for c in comps:
        if c.name.lower() == "brendan gallagher":
            continue
        # warrior tag?
        r = con.execute(
            "SELECT confidence FROM scouting_tags WHERE name=? AND tag='warrior' ORDER BY confidence DESC LIMIT 1",
            (c.name,)
        ).fetchone()
        is_warrior = bool(r and r[0] >= 0.5)
        reg = pooled_iso_full(con, c.name, 2)
        play = pooled_iso_full(con, c.name, 3)
        if reg is None or play is None or play["toi"] < 50:
            continue
        rows.append({
            "name": c.name, "comp_score": round(c.score, 1),
            "is_warrior": is_warrior,
            "warrior_conf": round(r[0], 2) if r else None,
            "reg_iso_net60": reg["iso_net60"], "reg_toi": reg["toi"],
            "play_iso_net60": play["iso_net60"], "play_toi": play["toi"],
            "lift": round(play["iso_net60"] - reg["iso_net60"], 3),
        })

    warriors = [r["lift"] for r in rows if r["is_warrior"]]
    non_warriors = [r["lift"] for r in rows if not r["is_warrior"]]

    rng = np.random.default_rng(42)
    n_boot = 5000
    diffs = []
    if warriors and non_warriors:
        wa, na = np.array(warriors), np.array(non_warriors)
        for _ in range(n_boot):
            ws = rng.choice(wa, size=len(wa), replace=True)
            ns = rng.choice(na, size=len(na), replace=True)
            diffs.append(ws.mean() - ns.mean())
        diffs = np.array(diffs)
        lo, hi = np.quantile(diffs, [0.10, 0.90])
        bootstrap = {
            "n_warrior": len(warriors),
            "n_non_warrior": len(non_warriors),
            "mean_lift_warrior": round(float(np.mean(warriors)), 3),
            "mean_lift_non_warrior": round(float(np.mean(non_warriors)), 3),
            "median_lift_warrior": round(float(np.median(warriors)), 3),
            "median_lift_non_warrior": round(float(np.median(non_warriors)), 3),
            "delta_mean": round(float(np.mean(diffs)), 3),
            "delta_ci80": [round(float(lo), 3), round(float(hi), 3)],
            "ci_excludes_zero": bool(lo > 0 or hi < 0),
        }
    else:
        bootstrap = {"n_warrior": len(warriors), "n_non_warrior": len(non_warriors),
                     "note": "insufficient data for one-sided sample"}

    return {"comp_table": rows, "bootstrap": bootstrap}


def main():
    con = sqlite3.connect(DB)

    # ---- pooled team rows (MTL) ----
    mtl_team = fetch_team_rows(con, "MTL")

    # ---- per-player pooled impacts ----
    impacts = {}
    raw_breakdown = {}
    tags = {}
    attrs = {}

    for name in [SLAF] + CANDIDATES:
        rows = fetch_player_rows(con, name)
        raw_breakdown[name] = rows[["season", "stype", "toi", "xgf", "xga"]].to_dict(orient="records") if not rows.empty else []
        if rows.empty:
            continue
        impacts[name] = build_pooled_player_impact(rows, mtl_team, team_id="MTL")
        tags[name] = player_tags(con, name)
        attrs[name] = player_attributes(con, name)

    # Slaf is the bar. Candidates project against the slot he vacates.
    slaf_imp = impacts[SLAF]

    # ---- Permutations ----
    permutations = []

    # A: direct slot, Gallagher in for Slaf at L1 LW
    if "Brendan Gallagher" in impacts:
        s = project_swap(out_player=slaf_imp, in_player=impacts["Brendan Gallagher"],
                         slot_minutes=L1_SLOT, strength_state="5v5", confidence=0.80)
        permutations.append({
            "code": "A",
            "label": "Gallagher direct to L1 LW",
            "description": (
                "Gallagher slots into Slafkovský's L1 LW spot (off-wing for him, "
                "or flip Caufield to L). Texier–Dach–Bolduc 2nd line untouched. "
                "Demidov stays on L3 with Newhook + Kapanen. No other moves."
            ),
            "out": SLAF, "in": "Brendan Gallagher", "slot_min": L1_SLOT,
            "delta_xgf60": round(s.delta_xgf60, 4),
            "delta_xga60": round(s.delta_xga60, 4),
            "delta_net": round(s.delta_xgf60 - s.delta_xga60, 4),
            "delta_xgf_ci80": [round(s.delta_xgf60_ci80[0], 4), round(s.delta_xgf60_ci80[1], 4)],
            "delta_xga_ci80": [round(s.delta_xga60_ci80[0], 4), round(s.delta_xga60_ci80[1], 4)],
            "sample_note": s.sample_note,
        })

    # B: Laine to L1 LW (natural L)
    if "Patrik Laine" in impacts:
        s = project_swap(out_player=slaf_imp, in_player=impacts["Patrik Laine"],
                         slot_minutes=L1_SLOT, strength_state="5v5", confidence=0.80)
        permutations.append({
            "code": "B",
            "label": "Laine to L1 LW (natural L side)",
            "description": (
                "Laine, a natural left winger, slots in. He has only 49 5v5 min "
                "this season post-injury and a 25-26 5v5 sample too thin to "
                "stabilize. Pool window includes 23-24 + 24-25 reg and playoffs."
            ),
            "out": SLAF, "in": "Patrik Laine", "slot_min": L1_SLOT,
            "delta_xgf60": round(s.delta_xgf60, 4),
            "delta_xga60": round(s.delta_xga60, 4),
            "delta_net": round(s.delta_xgf60 - s.delta_xga60, 4),
            "delta_xgf_ci80": [round(s.delta_xgf60_ci80[0], 4), round(s.delta_xgf60_ci80[1], 4)],
            "delta_xga_ci80": [round(s.delta_xga60_ci80[0], 4), round(s.delta_xga60_ci80[1], 4)],
            "sample_note": s.sample_note,
        })

    # C: Promote Texier to L1 LW + Gallagher to L2 LW (Texier's old slot)
    # Two-stage swap: net effect is Slaf out at L1, Gallagher in at L2.
    # Approximate as: Slaf -> Texier (L1 net delta) + Texier -> Gallagher (L2 net delta).
    # We separately project both legs and combine.
    if "Brendan Gallagher" in impacts and "Alexandre Texier" in impacts:
        s1 = project_swap(out_player=slaf_imp, in_player=impacts["Alexandre Texier"],
                          slot_minutes=L1_SLOT, strength_state="5v5", confidence=0.80)
        s2 = project_swap(out_player=impacts["Alexandre Texier"], in_player=impacts["Brendan Gallagher"],
                          slot_minutes=L2_SLOT, strength_state="5v5", confidence=0.80)
        net = (s1.delta_xgf60 - s1.delta_xga60) + (s2.delta_xgf60 - s2.delta_xga60)
        # CI combination via independent normal approx
        var_xgf = ((s1.delta_xgf60_ci80[1]-s1.delta_xgf60_ci80[0])/2.564)**2 + ((s2.delta_xgf60_ci80[1]-s2.delta_xgf60_ci80[0])/2.564)**2
        var_xga = ((s1.delta_xga60_ci80[1]-s1.delta_xga60_ci80[0])/2.564)**2 + ((s2.delta_xga60_ci80[1]-s2.delta_xga60_ci80[0])/2.564)**2
        ci_xgf = (s1.delta_xgf60 + s2.delta_xgf60 - 1.282*var_xgf**0.5,
                  s1.delta_xgf60 + s2.delta_xgf60 + 1.282*var_xgf**0.5)
        ci_xga = (s1.delta_xga60 + s2.delta_xga60 - 1.282*var_xga**0.5,
                  s1.delta_xga60 + s2.delta_xga60 + 1.282*var_xga**0.5)
        permutations.append({
            "code": "C",
            "label": "Texier up to L1 LW, Gallagher into L2 LW",
            "description": (
                "Two-stage move: Texier slides to L1 (his natural L side) with "
                "Suzuki–Caufield. Gallagher takes Texier's old L2 LW spot beside "
                "Dach + Bolduc. Combines both legs of the swap; CI propagated."
            ),
            "out": SLAF, "in": "Alexandre Texier (L1) + Brendan Gallagher (L2)",
            "slot_min": L1_SLOT + L2_SLOT,
            "delta_xgf60": round(s1.delta_xgf60 + s2.delta_xgf60, 4),
            "delta_xga60": round(s1.delta_xga60 + s2.delta_xga60, 4),
            "delta_net": round(net, 4),
            "delta_xgf_ci80": [round(ci_xgf[0], 4), round(ci_xgf[1], 4)],
            "delta_xga_ci80": [round(ci_xga[0], 4), round(ci_xga[1], 4)],
            "sample_note": "two-leg combined",
            "leg_breakdown": [
                {"leg": "Slaf -> Texier @ L1", "slot": L1_SLOT,
                 "net": round(s1.delta_xgf60 - s1.delta_xga60, 4),
                 "xgf_ci": [round(s1.delta_xgf60_ci80[0], 4), round(s1.delta_xgf60_ci80[1], 4)],
                 "xga_ci": [round(s1.delta_xga60_ci80[0], 4), round(s1.delta_xga60_ci80[1], 4)]},
                {"leg": "Texier -> Gallagher @ L2", "slot": L2_SLOT,
                 "net": round(s2.delta_xgf60 - s2.delta_xga60, 4),
                 "xgf_ci": [round(s2.delta_xgf60_ci80[0], 4), round(s2.delta_xgf60_ci80[1], 4)],
                 "xga_ci": [round(s2.delta_xga60_ci80[0], 4), round(s2.delta_xga60_ci80[1], 4)]},
            ]
        })

    # D: Promote Demidov to L1, Gallagher to L3 (Demidov's old spot)
    if "Brendan Gallagher" in impacts and "Ivan Demidov" in impacts:
        s1 = project_swap(out_player=slaf_imp, in_player=impacts["Ivan Demidov"],
                          slot_minutes=L1_SLOT, strength_state="5v5", confidence=0.80)
        s2 = project_swap(out_player=impacts["Ivan Demidov"], in_player=impacts["Brendan Gallagher"],
                          slot_minutes=L3_SLOT, strength_state="5v5", confidence=0.80)
        net = (s1.delta_xgf60 - s1.delta_xga60) + (s2.delta_xgf60 - s2.delta_xga60)
        var_xgf = ((s1.delta_xgf60_ci80[1]-s1.delta_xgf60_ci80[0])/2.564)**2 + ((s2.delta_xgf60_ci80[1]-s2.delta_xgf60_ci80[0])/2.564)**2
        var_xga = ((s1.delta_xga60_ci80[1]-s1.delta_xga60_ci80[0])/2.564)**2 + ((s2.delta_xga60_ci80[1]-s2.delta_xga60_ci80[0])/2.564)**2
        ci_xgf = (s1.delta_xgf60 + s2.delta_xgf60 - 1.282*var_xgf**0.5,
                  s1.delta_xgf60 + s2.delta_xgf60 + 1.282*var_xgf**0.5)
        ci_xga = (s1.delta_xga60 + s2.delta_xga60 - 1.282*var_xga**0.5,
                  s1.delta_xga60 + s2.delta_xga60 + 1.282*var_xga**0.5)
        permutations.append({
            "code": "D",
            "label": "Demidov to L1 LW, Gallagher to L3 RW",
            "description": (
                "Promote the 25-26 rookie to top-line minutes alongside Suzuki + "
                "Caufield. Gallagher fills Demidov's L3 RW slot beside Newhook + "
                "Kapanen. Riskier on L1 (Demidov is a natural R playing L); "
                "tightens the bottom-six with Gallagher's compete profile."
            ),
            "out": SLAF, "in": "Ivan Demidov (L1) + Brendan Gallagher (L3)",
            "slot_min": L1_SLOT + L3_SLOT,
            "delta_xgf60": round(s1.delta_xgf60 + s2.delta_xgf60, 4),
            "delta_xga60": round(s1.delta_xga60 + s2.delta_xga60, 4),
            "delta_net": round(net, 4),
            "delta_xgf_ci80": [round(ci_xgf[0], 4), round(ci_xgf[1], 4)],
            "delta_xga_ci80": [round(ci_xga[0], 4), round(ci_xga[1], 4)],
            "sample_note": "two-leg combined",
            "leg_breakdown": [
                {"leg": "Slaf -> Demidov @ L1", "slot": L1_SLOT,
                 "net": round(s1.delta_xgf60 - s1.delta_xga60, 4),
                 "xgf_ci": [round(s1.delta_xgf60_ci80[0], 4), round(s1.delta_xgf60_ci80[1], 4)],
                 "xga_ci": [round(s1.delta_xga60_ci80[0], 4), round(s1.delta_xga60_ci80[1], 4)]},
                {"leg": "Demidov -> Gallagher @ L3", "slot": L3_SLOT,
                 "net": round(s2.delta_xgf60 - s2.delta_xga60, 4),
                 "xgf_ci": [round(s2.delta_xgf60_ci80[0], 4), round(s2.delta_xgf60_ci80[1], 4)],
                 "xga_ci": [round(s2.delta_xga60_ci80[0], 4), round(s2.delta_xga60_ci80[1], 4)]},
            ]
        })

    # ---- Warrior cohort lift study on Gallagher's comps ----
    idx = ComparableIndex.load(INDEX)
    warrior_study = warrior_lift_study(con, idx)

    # ---- Slaf series-direct stats (PBP-derived) ----
    series_path = Path(__file__).parent / "playoff_rankings.numbers.json"
    series_data = {}
    if series_path.exists():
        d = json.loads(series_path.read_text(encoding="utf-8"))
        for table_name in ("rank_5v5", "rank_5v4", "individual"):
            if table_name in d:
                slaf = next((p for p in d[table_name] if "Slafkov" in p.get("name", "")), None)
                if slaf:
                    series_data.setdefault("slaf", {})[table_name] = slaf
                gal = next((p for p in d[table_name] if "Gallagher" in p.get("name", "")), None)
                if gal:
                    series_data.setdefault("gallagher", {})[table_name] = gal

    payload = {
        "meta": {
            "as_of": "2026-04-28",
            "scenario": "Game 5 contingency — Slafkovský unavailable",
            "matchup": "MTL @ TBL Game 5 (series 2-2)",
            "source_data": "NST oi 5v5 splits (24-25 reg/playoff + 25-26 reg/playoff), pooled.",
            "swap_engine": "lemieux pooled-baseline swap engine, 80% CI",
            "slot_assumptions": {"L1": L1_SLOT, "L2": L2_SLOT, "L3": L3_SLOT},
        },
        "slafkovsky": impact_dict(slaf_imp),
        "candidates": {name: impact_dict(impacts[name]) for name in CANDIDATES if name in impacts},
        "tags": tags,
        "attributes": attrs,
        "raw_pool_breakdown": raw_breakdown,
        "permutations": permutations,
        "warrior_study": warrior_study,
        "series_direct": series_data,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print()
    print("Permutation summary (net xG/game from MTL perspective):")
    for p in permutations:
        print(f"  [{p['code']}] {p['label']:50s}  net = {p['delta_net']:+.3f}  "
              f"xGF CI [{p['delta_xgf_ci80'][0]:+.2f}, {p['delta_xgf_ci80'][1]:+.2f}]  "
              f"xGA CI [{p['delta_xga_ci80'][0]:+.2f}, {p['delta_xga_ci80'][1]:+.2f}]")
    print()
    ws = warrior_study["bootstrap"]
    print(f"Gallagher warrior-cohort lift study:")
    if "delta_mean" in ws:
        print(f"  warrior n={ws['n_warrior']}  mean lift={ws['mean_lift_warrior']:+.3f}")
        print(f"  non-warrior n={ws['n_non_warrior']}  mean lift={ws['mean_lift_non_warrior']:+.3f}")
        print(f"  Δ = {ws['delta_mean']:+.3f}  80% CI [{ws['delta_ci80'][0]:+.3f}, {ws['delta_ci80'][1]:+.3f}]")
        print(f"  CI excludes zero: {ws['ci_excludes_zero']}")


if __name__ == "__main__":
    main()
