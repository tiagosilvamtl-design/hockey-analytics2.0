"""Game 5 pre-game analyzer (MTL @ TBL, 2026-04-29).

Marinaro projects a four-line shake-up:
  L1 sides flipped (Caufield-Suzuki-Slafkovský)
  L2 rebuilt with Demidov promoted (Newhook-Evans-Demidov)
  L3 rebuilt as heavy/compete (Anderson-Danault-Gallagher) — Gallagher IN
  L4 = Dach line demoted intact (Bolduc-Dach-Texier)
  Kapanen scratched.

This analyzer computes for each line:
  - Average pooled iso net60 (the swap-engine baseline)
  - Pre/post-shake-up iso change

Plus three swap-engine projections:
  A. Direct Kapanen ↔ Gallagher swap (the mechanical change)
  B. Dach-line at L4 vs Dach-line at L2 (cost of demotion)
  C. Demidov L3 → L2 (cost/benefit of promotion)

Plus the Gallagher warrior-cohort lift study (loaded from yesterday's brief
or recomputed) for layered projection.

Output: game5_pregame.numbers.json
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
OUT_PATH = Path(__file__).parent / "game5_pregame.numbers.json"

POOL_KEYS = [
    ("20242025", 2), ("20242025", 3),
    ("20252026", 2), ("20252026", 3),
]

# Slot-time assumptions per role (5v5 mins/game)
SLOT_TIMES = {"L1": 14.0, "L2": 12.0, "L3": 10.0, "L4": 7.5}

# Marinaro's projected G5 lines
G5_LINES = {
    "L1": ("Cole Caufield", "Nick Suzuki", "Juraj Slafkovský"),
    "L2": ("Alex Newhook", "Jake Evans", "Ivan Demidov"),
    "L3": ("Josh Anderson", "Phillip Danault", "Brendan Gallagher"),
    "L4": ("Zachary Bolduc", "Kirby Dach", "Alexandre Texier"),
}

# G4 deployed lines
G4_LINES = {
    "L1": ("Juraj Slafkovský", "Nick Suzuki", "Cole Caufield"),
    "L2": ("Alexandre Texier", "Kirby Dach", "Zachary Bolduc"),
    "L3": ("Alex Newhook", "Oliver Kapanen", "Ivan Demidov"),
    "L4": ("Phillip Danault", "Josh Anderson", "Jake Evans"),
}

ALL_PLAYERS = sorted({p for line in (*G5_LINES.values(), *G4_LINES.values()) for p in line})


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
        (name,),
    ).fetchall()
    return [
        {"tag": r[0], "confidence": round(r[1], 2),
         "source_quote": (r[2] or "")[:300], "source_url": r[3] or ""}
        for r in rows if r[1] >= min_conf
    ]


def impact_dict(p: PlayerImpact, *, sample_size_5v5_min: float | None = None):
    return {
        "name": p.name,
        "team_id": p.team_id,
        "toi_on_min": round(p.toi_on, 1),
        "iso_xgf60": round(p.iso_xgf60, 3),
        "iso_xga60": round(p.iso_xga60, 3),
        "iso_net60": round(p.iso_xgf60 - p.iso_xga60, 3),
    }


def line_avg_iso(impacts: dict, line: tuple) -> dict:
    """Mean of pooled iso net60 across the trio. Equal weighting."""
    items = [impacts[n] for n in line if n in impacts]
    if len(items) < 3:
        return {"avg_iso_net60": None, "members_with_data": len(items),
                "min_pooled_toi": min((i.toi_on for i in items), default=0)}
    avg_xgf = sum(i.iso_xgf60 for i in items) / 3
    avg_xga = sum(i.iso_xga60 for i in items) / 3
    return {
        "avg_iso_xgf60": round(avg_xgf, 3),
        "avg_iso_xga60": round(avg_xga, 3),
        "avg_iso_net60": round(avg_xgf - avg_xga, 3),
        "members_with_data": 3,
        "min_pooled_toi": round(min(i.toi_on for i in items), 0),
    }


def warrior_lift_study(con, idx: ComparableIndex, target: str = "Brendan Gallagher"):
    comps = idx.find_comparables(target, k=30, min_pooled_toi=200.0)
    rows = []
    for c in comps:
        if c.name.lower() == target.lower():
            continue
        r = con.execute(
            "SELECT confidence FROM scouting_tags WHERE name=? AND tag='warrior' ORDER BY confidence DESC LIMIT 1",
            (c.name,),
        ).fetchone()
        is_warrior = bool(r and r[0] >= 0.5)
        # pooled reg + playoff iso
        for stype, key in ((2, "reg"), (3, "play")):
            pass
        reg = con.execute(
            "SELECT SUM(toi), SUM(xgf), SUM(xga) FROM skater_stats "
            "WHERE name=? AND split='oi' AND sit='5v5' AND stype=2", (c.name,),
        ).fetchone()
        play = con.execute(
            "SELECT SUM(toi), SUM(xgf), SUM(xga) FROM skater_stats "
            "WHERE name=? AND split='oi' AND sit='5v5' AND stype=3", (c.name,),
        ).fetchone()
        if not reg or not play or not reg[0] or not play[0] or play[0] < 50:
            continue
        reg_iso = (reg[1] - reg[2]) * 60.0 / reg[0]
        play_iso = (play[1] - play[2]) * 60.0 / play[0]
        rows.append({
            "name": c.name, "comp_score": round(c.score, 1),
            "is_warrior": is_warrior,
            "reg_iso_net60": round(reg_iso, 3), "play_iso_net60": round(play_iso, 3),
            "lift": round(play_iso - reg_iso, 3),
            "reg_toi": round(reg[0], 0), "play_toi": round(play[0], 0),
        })
    warriors = [r["lift"] for r in rows if r["is_warrior"]]
    non_warriors = [r["lift"] for r in rows if not r["is_warrior"]]
    rng = np.random.default_rng(42)
    diffs = []
    bootstrap = {}
    if warriors and non_warriors:
        wa, na = np.array(warriors), np.array(non_warriors)
        for _ in range(5000):
            ws = rng.choice(wa, size=len(wa), replace=True)
            ns = rng.choice(na, size=len(na), replace=True)
            diffs.append(ws.mean() - ns.mean())
        diffs = np.array(diffs)
        lo, hi = np.quantile(diffs, [0.10, 0.90])
        bootstrap = {
            "n_warrior": len(warriors), "n_non_warrior": len(non_warriors),
            "mean_lift_warrior": round(float(np.mean(warriors)), 3),
            "mean_lift_non_warrior": round(float(np.mean(non_warriors)), 3),
            "delta_mean": round(float(np.mean(diffs)), 3),
            "delta_ci80": [round(float(lo), 3), round(float(hi), 3)],
            "ci_excludes_zero": bool(lo > 0 or hi < 0),
        }
    return {"comp_table": rows, "bootstrap": bootstrap}


def main():
    con = sqlite3.connect(DB)
    mtl_team = fetch_team_rows(con, "MTL")

    # Build pooled impact per player
    impacts = {}
    raw = {}
    tags = {}
    for name in ALL_PLAYERS:
        rows = fetch_player_rows(con, name)
        raw[name] = rows[["season", "stype", "toi"]].to_dict(orient="records") if not rows.empty else []
        if rows.empty:
            continue
        impacts[name] = build_pooled_player_impact(rows, mtl_team, team_id="MTL")
        tags[name] = player_tags(con, name)

    # Compute line averages, G4 vs G5
    g4_avg = {role: line_avg_iso(impacts, line) for role, line in G4_LINES.items()}
    g5_avg = {role: line_avg_iso(impacts, line) for role, line in G5_LINES.items()}

    # ---- Swap A: Kapanen → Gallagher (the mechanical 18th-forward swap) ----
    kapanen = impacts.get("Oliver Kapanen")
    gallagher = impacts.get("Brendan Gallagher")
    swap_a = None
    if kapanen and gallagher:
        s = project_swap(out_player=kapanen, in_player=gallagher,
                         slot_minutes=SLOT_TIMES["L3"], strength_state="5v5", confidence=0.80)
        swap_a = {
            "out": "Oliver Kapanen", "in": "Brendan Gallagher",
            "slot_min": SLOT_TIMES["L3"],
            "delta_xgf60": round(s.delta_xgf60, 4),
            "delta_xga60": round(s.delta_xga60, 4),
            "delta_net": round(s.delta_xgf60 - s.delta_xga60, 4),
            "delta_xgf_ci80": [round(s.delta_xgf60_ci80[0], 4), round(s.delta_xgf60_ci80[1], 4)],
            "delta_xga_ci80": [round(s.delta_xga60_ci80[0], 4), round(s.delta_xga60_ci80[1], 4)],
        }

    # ---- Swap B: Dach line at L2 (G4) vs L4 (G5) — cost of demotion ----
    # We model this as: the same trio loses (L2_slot - L4_slot) minutes against
    # weaker opposition. The per-60 iso doesn't change (same trio); what changes
    # is how many xG-equivalent minutes their positive iso accumulates over.
    dach_trio = ("Alexandre Texier", "Kirby Dach", "Zachary Bolduc")
    dach_avg = line_avg_iso(impacts, dach_trio)
    minutes_lost_per_game = SLOT_TIMES["L2"] - SLOT_TIMES["L4"]
    if dach_avg.get("avg_iso_net60") is not None:
        # Per-game expected xG cost = trio_avg_iso_net60 * minutes_lost / 60
        per_game_cost = dach_avg["avg_iso_net60"] * minutes_lost_per_game / 60.0
    else:
        per_game_cost = None
    swap_b = {
        "trio": list(dach_trio),
        "trio_avg_iso_net60": dach_avg.get("avg_iso_net60"),
        "g4_slot_min": SLOT_TIMES["L2"],
        "g5_slot_min": SLOT_TIMES["L4"],
        "minutes_lost_per_game": minutes_lost_per_game,
        "per_game_xg_cost": round(per_game_cost, 3) if per_game_cost is not None else None,
        "interpretation": (
            f"The Dach trio's pooled iso net60 of {dach_avg.get('avg_iso_net60'):+.3f} suggests they "
            f"generate ~{abs(per_game_cost):.2f} expected xG/game on those 4.5 lost minutes. "
            f"That's the demotion cost — assuming their positive iso doesn't actually IMPROVE "
            f"against weaker L4 opponents (which would partly offset)."
        ) if per_game_cost is not None else None,
    }

    # ---- Swap C: Demidov L3 (G4) → L2 (G5) — cost/benefit of promotion ----
    demidov = impacts.get("Ivan Demidov")
    swap_c = None
    if demidov:
        # Same player, more minutes, against tougher opposition. Per-60 iso assumed
        # constant (model limitation — chemistry + matchup effects not isolated).
        minutes_gained = SLOT_TIMES["L2"] - SLOT_TIMES["L3"]
        per_game_gain = (demidov.iso_xgf60 - demidov.iso_xga60) * minutes_gained / 60.0
        swap_c = {
            "player": "Ivan Demidov",
            "iso_net60": round(demidov.iso_xgf60 - demidov.iso_xga60, 3),
            "iso_toi_pool_min": round(demidov.toi_on, 0),
            "g4_slot_min": SLOT_TIMES["L3"],
            "g5_slot_min": SLOT_TIMES["L2"],
            "minutes_gained_per_game": minutes_gained,
            "per_game_xg_delta": round(per_game_gain, 3),
            "caveat": (
                f"Demidov's pooled 5v5 sample is only {demidov.toi_on:.0f} min — small. "
                "Per-60 iso assumed constant across L3 → L2 quality-of-competition step. "
                "Real effect is sample-noisy."
            ),
        }

    # ---- Warrior cohort lift study (Gallagher's comps) ----
    idx = ComparableIndex.load(INDEX)
    warrior = warrior_lift_study(con, idx, target="Brendan Gallagher")

    # ---- Series-direct PBP-derived stats (from playoff_rankings) ----
    series_path = Path(__file__).parent / "playoff_rankings.numbers.json"
    series = {}
    if series_path.exists():
        d = json.loads(series_path.read_text(encoding="utf-8"))
        for player_name in ["Kirby Dach", "Zachary Bolduc", "Alexandre Texier",
                            "Oliver Kapanen", "Ivan Demidov", "Jake Evans"]:
            for tname in ("rank_5v5", "individual"):
                row = next((p for p in d.get(tname, []) if p.get("name") == player_name), None)
                if row:
                    series.setdefault(player_name, {})[tname] = row

    payload = {
        "meta": {
            "as_of": "2026-04-29",
            "matchup": "MTL @ TBL Game 5 (series 2-2)",
            "venue": "Amalie Arena (TBL has last change)",
            "lineup_source": "Tony Marinaro (@TonyMarinaro / The Sick Podcast) projection — corroborated by practice reshuffles",
            "swap_engine": "lemieux pooled-baseline swap engine, 80% CI, NST oi 5v5 splits",
            "pool_windows": "24-25 reg+playoff + 25-26 reg+playoff",
            "slot_assumptions": SLOT_TIMES,
        },
        "lines_g4": G4_LINES,
        "lines_g5_projected": G5_LINES,
        "g4_line_iso": g4_avg,
        "g5_line_iso": g5_avg,
        "player_impacts": {n: impact_dict(impacts[n]) for n in ALL_PLAYERS if n in impacts},
        "tags": tags,
        "swap_a_kapanen_for_gallagher": swap_a,
        "swap_b_dach_demotion": swap_b,
        "swap_c_demidov_promotion": swap_c,
        "warrior_study": warrior,
        "series_direct": series,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print()
    print("=" * 80)
    print("LINE ISO SUMMARY (avg pooled iso net60 per trio, 5v5 oi)")
    print("=" * 80)
    print(f"{'Role':<6} {'G4 deployed':<35} {'G4 iso':>9}  {'G5 projected':<35} {'G5 iso':>9}")
    for role in ("L1", "L2", "L3", "L4"):
        g4 = g4_avg.get(role, {})
        g5 = g5_avg.get(role, {})
        g4_str = "-".join(p.split()[-1] for p in G4_LINES[role])[:35]
        g5_str = "-".join(p.split()[-1] for p in G5_LINES[role])[:35]
        g4_iso = f"{g4.get('avg_iso_net60', 0):+.3f}" if g4.get("avg_iso_net60") is not None else "n/a"
        g5_iso = f"{g5.get('avg_iso_net60', 0):+.3f}" if g5.get("avg_iso_net60") is not None else "n/a"
        print(f"{role:<6} {g4_str:<35} {g4_iso:>9}  {g5_str:<35} {g5_iso:>9}")
    print()
    if swap_a:
        print(f"Swap A (Kapanen→Gallagher, {SLOT_TIMES['L3']:.0f} min L3 slot):")
        print(f"  net Δ {swap_a['delta_net']:+.3f} xG/game · "
              f"xGF CI [{swap_a['delta_xgf_ci80'][0]:+.2f}, {swap_a['delta_xgf_ci80'][1]:+.2f}] · "
              f"xGA CI [{swap_a['delta_xga_ci80'][0]:+.2f}, {swap_a['delta_xga_ci80'][1]:+.2f}]")
    if swap_b and swap_b.get("per_game_xg_cost") is not None:
        print(f"Swap B (Dach trio L2→L4, -{swap_b['minutes_lost_per_game']:.1f} min/game):")
        print(f"  trio iso net60 = {swap_b['trio_avg_iso_net60']:+.3f} · "
              f"projected demotion cost = {swap_b['per_game_xg_cost']:+.2f} xG/game")
    if swap_c:
        print(f"Swap C (Demidov L3→L2, +{swap_c['minutes_gained_per_game']:.1f} min/game):")
        print(f"  iso net60 = {swap_c['iso_net60']:+.3f} · "
              f"projected promotion delta = {swap_c['per_game_xg_delta']:+.2f} xG/game")
    if warrior.get("bootstrap"):
        b = warrior["bootstrap"]
        print(f"Warrior cohort study (Gallagher's comps):")
        print(f"  warrior n={b['n_warrior']} mean lift {b['mean_lift_warrior']:+.2f} · "
              f"non-warrior n={b['n_non_warrior']} mean lift {b['mean_lift_non_warrior']:+.2f}")
        print(f"  Δ {b['delta_mean']:+.3f} · 80% CI [{b['delta_ci80'][0]:+.3f}, {b['delta_ci80'][1]:+.3f}] · "
              f"excludes 0: {b['ci_excludes_zero']}")


if __name__ == "__main__":
    main()
