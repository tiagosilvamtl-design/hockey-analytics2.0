"""Game 5 post-game analyzer (MTL @ TBL, 2026-04-29).

Inputs:
  - game5_box_score.yaml      G5 official box score (manually encoded from press)
  - playoff_rankings.numbers.json   G1-G4 series totals (analyzer output from prior brief)

Computes three rankings:
  A. Game 5 only (this game)
  B. Series-to-date G1-G5 (cumulative through tonight)
  C. G5 vs G1-G4 average (who stepped up tonight, who fell off)

Plus team-level comparison.

Output: game5_postgame.numbers.json

Note: this runs IMMEDIATELY post-game with press-derived stats. NST 5v5 oi
splits for G5 won't refresh until overnight; this is the headline narrative
without the iso/pbp deep-dive.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
OUT_PATH = HERE / "game5_postgame.numbers.json"
BOX = yaml.safe_load((HERE / "game5_box_score.yaml").read_text(encoding="utf-8"))
RANK = json.loads((HERE / "playoff_rankings.numbers.json").read_text(encoding="utf-8"))


def toi_seconds(toi_str: str) -> int:
    if not toi_str: return 0
    m, s = toi_str.split(":"); return int(m) * 60 + int(s)


def ranking_g5(team_skaters: list, team: str) -> list:
    """Per-game leaderboard for G5 only — sorted by points then SOG."""
    out = []
    for sk in team_skaters:
        out.append({
            "name": sk["name"], "team": team, "pos": sk["pos"],
            "g": sk["g"], "a": sk["a"], "pts": sk["g"] + sk["a"],
            "sog": sk["sog"], "toi_min": round(toi_seconds(sk["toi"]) / 60.0, 2),
            "hits": sk["hits"], "plus_minus": sk["plus_minus"], "pim": sk["pim"],
        })
    out.sort(key=lambda r: (-r["pts"], -r["sog"], -r["toi_min"]))
    return out


def series_g1_g4_lookup() -> dict:
    """Build a name -> (g, a, sog, points) lookup from G1-G4 rankings."""
    out = {}
    for p in RANK.get("individual", []):
        out[p["name"]] = {
            "g": p.get("g", 0), "a": p.get("a", 0),
            "sog": p.get("sog", 0), "pts": p.get("points", p.get("g", 0) + p.get("a", 0)),
        }
    return out


def ranking_g1_g5(g5_skaters: dict) -> list:
    """Cumulative series rankings G1-G5 = G1-G4 totals + G5 stats.

    g5_skaters: {name: {g,a,sog}}
    """
    g14 = series_g1_g4_lookup()
    # Combine all names from both sets
    all_names = set(g14.keys()) | set(g5_skaters.keys())
    out = []
    for name in all_names:
        b = g14.get(name, {"g": 0, "a": 0, "sog": 0, "pts": 0})
        g = g5_skaters.get(name, {"g": 0, "a": 0, "sog": 0})
        out.append({
            "name": name,
            "g_g14": b["g"], "a_g14": b["a"], "sog_g14": b["sog"], "pts_g14": b["pts"],
            "g_g5": g["g"], "a_g5": g["a"], "sog_g5": g["sog"], "pts_g5": g["g"] + g["a"],
            "g_total": b["g"] + g["g"], "a_total": b["a"] + g["a"],
            "sog_total": b["sog"] + g["sog"], "pts_total": b["pts"] + g["g"] + g["a"],
        })
    out.sort(key=lambda r: (-r["pts_total"], -r["g_total"], -r["sog_total"]))
    return out


def step_up_or_off(g5_skaters: dict) -> list:
    """G5 points vs G1-G4 per-game points pace. Highlight step-ups / fall-offs."""
    g14 = series_g1_g4_lookup()
    out = []
    for name, g in g5_skaters.items():
        b = g14.get(name, {"g": 0, "a": 0, "sog": 0, "pts": 0})
        pace_g14 = b["pts"] / 4.0  # G1-G4 = 4 games per player (assume all played)
        delta = (g["g"] + g["a"]) - pace_g14
        out.append({
            "name": name,
            "pts_g14_avg": round(pace_g14, 2),
            "pts_g5": g["g"] + g["a"],
            "delta_pts": round(delta, 2),
            "sog_g14_avg": round(b["sog"] / 4.0, 2),
            "sog_g5": g["sog"],
            "delta_sog": round(g["sog"] - b["sog"] / 4.0, 2),
        })
    out.sort(key=lambda r: -r["delta_pts"])
    return out


def main():
    mtl = BOX["skaters"]["MTL"]
    tbl = BOX["skaters"]["TBL"]

    rank_g5_mtl = ranking_g5(mtl, "MTL")
    rank_g5_tbl = ranking_g5(tbl, "TBL")

    # Build {name: g5 stats} for series cumul
    all_g5_skaters = {}
    for sk in mtl + tbl:
        all_g5_skaters[sk["name"]] = {
            "g": sk["g"], "a": sk["a"], "sog": sk["sog"],
        }
    series_rank = ranking_g1_g5(all_g5_skaters)

    # Step-up / fall-off — restrict to MTL since RANK['individual'] is MTL-only.
    mtl_names = {sk["name"] for sk in mtl}
    mtl_g5 = {n: s for n, s in all_g5_skaters.items() if n in mtl_names}
    step = step_up_or_off(mtl_g5)

    # Team comparison
    team_compare = {
        "MTL": BOX["team_stats"]["MTL"] | {
            "goalie_sv_pct": BOX["goalies"]["MTL"]["sv_pct"],
            "goalie_shots_against": BOX["goalies"]["MTL"]["shots_against"],
            "goalie_saves": BOX["goalies"]["MTL"]["saves"],
        },
        "TBL": BOX["team_stats"]["TBL"] | {
            "goalie_sv_pct": BOX["goalies"]["TBL"]["sv_pct"],
            "goalie_shots_against": BOX["goalies"]["TBL"]["shots_against"],
            "goalie_saves": BOX["goalies"]["TBL"]["saves"],
        },
    }
    team_diffs = {
        "shots_diff": BOX["team_stats"]["MTL"]["shots"] - BOX["team_stats"]["TBL"]["shots"],
        "hits_diff": BOX["team_stats"]["MTL"]["hits"] - BOX["team_stats"]["TBL"]["hits"],
        "faceoff_diff_pp": BOX["team_stats"]["MTL"]["faceoff_win_pct"] - BOX["team_stats"]["TBL"]["faceoff_win_pct"],
        "sv_pct_diff": BOX["goalies"]["MTL"]["sv_pct"] - BOX["goalies"]["TBL"]["sv_pct"],
    }

    # Goalie series totals (from RANK['goalie'] = G1-G4 PBP-direct)
    goalie_g14 = RANK.get("goalie", {})
    dobes_g14 = goalie_g14.get("Jakub Dobeš") or {}
    dobes_g5 = BOX["goalies"]["MTL"]
    if dobes_g14:
        dobes_combined = {
            "shots_against_g15": dobes_g14.get("shots_against", 0) + dobes_g5["shots_against"],
            "saves_g15": dobes_g14.get("saves", 0) + dobes_g5["saves"],
            "ga_g15": dobes_g14.get("ga", 0) + dobes_g5["goals_against"],
        }
        if dobes_combined["shots_against_g15"] > 0:
            dobes_combined["sv_pct_g15"] = round(
                dobes_combined["saves_g15"] / dobes_combined["shots_against_g15"], 3
            )
    else:
        dobes_combined = None

    payload = {
        "meta": {
            "as_of": "2026-04-29 (post-game)",
            "matchup": "MTL @ TBL Game 5",
            "final_score": BOX["final_score"],
            "result": BOX["result"],
            "series_state": BOX["series_state_after_game"],
            "data_source": "ESPN game summary + CBS Sports box score (pre-NST refresh).",
        },
        "g5_box": BOX["team_stats"],
        "team_comparison": team_compare,
        "team_diffs": team_diffs,
        "goal_sequence": BOX["goal_sequence"],
        "narrative_anchors": BOX["narrative_anchors"],
        "rank_g5_mtl": rank_g5_mtl,
        "rank_g5_tbl": rank_g5_tbl,
        "series_rank_g1_g5_mtl": [r for r in series_rank if r["name"] in mtl_names],
        "step_up_or_off_mtl": step,
        "goalie_g14": dobes_g14,
        "goalie_g5_mtl": dobes_g5,
        "goalie_g15_combined": dobes_combined,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print()
    print("=" * 90)
    print(f"FINAL: {BOX['final_score']}  ·  {BOX['series_state_after_game']}")
    print("=" * 90)
    print()
    print("MTL G5 LEADERBOARD")
    print(f"{'name':<25} {'pos':<4} {'pts':>4} {'g':>3} {'a':>3} {'sog':>4} {'toi':>6} {'hits':>5} {'+/-':>5}")
    for r in rank_g5_mtl[:8]:
        print(f"{r['name']:<25} {r['pos']:<4} {r['pts']:>4} {r['g']:>3} {r['a']:>3} {r['sog']:>4} "
              f"{r['toi_min']:>6.1f} {r['hits']:>5} {r['plus_minus']:>+5}")
    print()
    print("TBL G5 LEADERBOARD")
    print(f"{'name':<25} {'pos':<4} {'pts':>4} {'g':>3} {'a':>3} {'sog':>4} {'toi':>6} {'hits':>5} {'+/-':>5}")
    for r in rank_g5_tbl[:8]:
        print(f"{r['name']:<25} {r['pos']:<4} {r['pts']:>4} {r['g']:>3} {r['a']:>3} {r['sog']:>4} "
              f"{r['toi_min']:>6.1f} {r['hits']:>5} {r['plus_minus']:>+5}")
    print()
    print("MTL SERIES G1-G5 LEADERBOARD")
    print(f"{'name':<25} {'pts_T':>5} {'g_T':>4} {'a_T':>4} {'sog_T':>5} | {'pts_g5':>6} {'pts_g14':>7}")
    for r in [x for x in series_rank if x["name"] in mtl_names][:10]:
        print(f"{r['name']:<25} {r['pts_total']:>5} {r['g_total']:>4} {r['a_total']:>4} "
              f"{r['sog_total']:>5} | {r['pts_g5']:>6} {r['pts_g14']:>7}")
    print()
    print("STEP-UP OR FALL-OFF (MTL): G5 vs G1-G4 per-game pace")
    for r in step[:6]:
        if r["delta_pts"] >= 0.5:
            arrow = "↑↑" if r["delta_pts"] >= 1.5 else "↑"
        elif r["delta_pts"] <= -0.5:
            arrow = "↓↓" if r["delta_pts"] <= -1.5 else "↓"
        else:
            arrow = "·"
        print(f"  {arrow}  {r['name']:<25}  G5 pts={r['pts_g5']:>1} vs G14 pace={r['pts_g14_avg']:>4.2f}  Δ={r['delta_pts']:>+5.2f}")
    print()
    print("TEAM DIFFS (MTL minus TBL):")
    print(f"  Shots:     {team_diffs['shots_diff']:+d}")
    print(f"  Hits:      {team_diffs['hits_diff']:+d}")
    print(f"  Faceoff%:  {team_diffs['faceoff_diff_pp']:+.1f} pp")
    print(f"  SV%:       {team_diffs['sv_pct_diff']:+.3f}")
    if dobes_combined:
        print()
        print(f"DOBEŠ G1-G5 combined: {dobes_combined['saves_g15']}/{dobes_combined['shots_against_g15']} "
              f"= .{int(dobes_combined['sv_pct_g15']*1000):03d} SV%")


if __name__ == "__main__":
    main()
