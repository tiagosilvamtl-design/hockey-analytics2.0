"""Comprehensive Game 4 post-game analyzer.

Mirrors examples/habs_round1_2026/game3_analysis.py in scope:
  - Series-to-date 5v5 + 5v4 from NST (through G4)
  - Per-game home/away basics (PBP)
  - Series goalscorers PBP-direct (canonical)
  - MTL skater progression vs reg season (4-game playoff iso vs full reg-season iso)
  - Goalie SV% PBP-direct
  - Reuses pre-existing analyzer outputs:
      * game4_periods.numbers.json (multi-period live, postgame block, deltas)
      * game4_slaf_hit.numbers.json (Crozier-hit pre/post buckets)
      * game4_pregame_swap.numbers.json (swap-engine projection)

Output: examples/habs_round1_2026/game4_analysis.numbers.json
"""

from __future__ import annotations
import json
import math
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

import truststore; truststore.inject_into_ssl()
import requests
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "legacy"))

GAME_ID = "2025030124"
SERIES_GAMES = ["2025030121", "2025030122", "2025030123", "2025030124"]
OUT = Path(__file__).parent / "game4_analysis.numbers.json"
DB = REPO / "legacy" / "data" / "store.sqlite"

PBP_URL = lambda gid: f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play"
BOX_URL = lambda gid: f"https://api-web.nhle.com/v1/gamecenter/{gid}/boxscore"


def fetch(url: str) -> dict:
    return requests.get(url, timeout=30).json()


def time_to_sec(t):
    if not t: return 0
    try:
        m, s = t.split(":"); return int(m) * 60 + int(s)
    except Exception:
        return 0


def main() -> int:
    con = sqlite3.connect(DB)

    # ----- 1. SERIES TOTALS from NST (through G4) -----
    series_5v5 = {}
    series_5v4 = {}
    for sit, dest in [("5v5", series_5v5), ("5v4", series_5v4)]:
        for team_id in ("MTL", "T.B"):
            row = pd.read_sql_query(
                """
                SELECT gp, toi, gf, ga, xgf, xga, cf_pct, hdcf_pct, xgf_pct, sf, sa
                FROM team_stats
                WHERE season='20252026' AND stype=3 AND sit=? AND team_id=?
                """,
                con, params=[sit, team_id],
            )
            if not len(row): continue
            r = row.iloc[0]
            dest[team_id] = {
                "gp": int(r["gp"]) if pd.notna(r["gp"]) else None,
                "toi_min": float(r["toi"]) if pd.notna(r["toi"]) else None,
                "gf": float(r["gf"]) if pd.notna(r["gf"]) else None,
                "ga": float(r["ga"]) if pd.notna(r["ga"]) else None,
                "xgf": float(r["xgf"]) if pd.notna(r["xgf"]) else None,
                "xga": float(r["xga"]) if pd.notna(r["xga"]) else None,
                "cf_pct": float(r["cf_pct"]) if pd.notna(r["cf_pct"]) else None,
                "hdcf_pct": float(r["hdcf_pct"]) if pd.notna(r["hdcf_pct"]) else None,
                "xgf_pct": float(r["xgf_pct"]) if pd.notna(r["xgf_pct"]) else None,
                "sf": float(r["sf"]) if pd.notna(r["sf"]) else None,
                "sa": float(r["sa"]) if pd.notna(r["sa"]) else None,
            }

    # ----- 2. PER-GAME basics from PBP -----
    per_game = {}
    for i, gid in enumerate(SERIES_GAMES, 1):
        pbp = fetch(PBP_URL(gid))
        per_game[f"G{i}"] = {
            "game_id": gid,
            "date": pbp.get("gameDate"),
            "home": pbp["homeTeam"]["abbrev"],
            "away": pbp["awayTeam"]["abbrev"],
            "home_score": pbp["homeTeam"].get("score"),
            "away_score": pbp["awayTeam"].get("score"),
            "home_sog": pbp["homeTeam"].get("sog"),
            "away_sog": pbp["awayTeam"].get("sog"),
        }

    # ----- 3. SERIES GOALSCORERS (PBP-direct, canonical) -----
    series_goalscorers = {"MTL": defaultdict(int), "TBL": defaultdict(int)}
    individual = defaultdict(lambda: {"name": None, "g": 0, "a1": 0, "a2": 0, "sog": 0})
    name_lookup = {}
    for gid in SERIES_GAMES:
        box = fetch(BOX_URL(gid))
        for side in ("homeTeam", "awayTeam"):
            for grp in ("forwards", "defense", "goalies"):
                for p in box.get("playerByGameStats", {}).get(side, {}).get(grp, []):
                    pid = p["playerId"]
                    name = p["name"]["default"] if isinstance(p["name"], dict) else p["name"]
                    name_lookup[pid] = name
        pbp = fetch(PBP_URL(gid))
        home_id = pbp["homeTeam"]["id"]; away_id = pbp["awayTeam"]["id"]
        home_abbr = pbp["homeTeam"]["abbrev"]; away_abbr = pbp["awayTeam"]["abbrev"]
        # Map home_abbr/away_abbr to MTL/TBL keys (T.B in NST notation; we use TBL here)
        team_key = lambda owner_id: ("MTL" if (home_abbr == "MTL" and owner_id == home_id) or (away_abbr == "MTL" and owner_id == away_id) else "TBL")
        for play in pbp.get("plays", []):
            typ = play.get("typeDescKey") or ""
            d = play.get("details") or {}
            owner = d.get("eventOwnerTeamId")
            if typ == "goal":
                tk = team_key(owner)
                scorer = name_lookup.get(d.get("scoringPlayerId"))
                if scorer:
                    series_goalscorers[tk][scorer] += 1
                    individual[d.get("scoringPlayerId")]["name"] = scorer
                    individual[d.get("scoringPlayerId")]["g"] += 1
                a1 = d.get("assist1PlayerId"); a2 = d.get("assist2PlayerId")
                if a1:
                    individual[a1]["name"] = name_lookup.get(a1)
                    individual[a1]["a1"] += 1
                if a2:
                    individual[a2]["name"] = name_lookup.get(a2)
                    individual[a2]["a2"] += 1
            if typ in ("shot-on-goal", "goal"):
                shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
                if shooter:
                    individual[shooter]["name"] = name_lookup.get(shooter)
                    individual[shooter]["sog"] += 1

    series_goalscorers = {team: dict(counts) for team, counts in series_goalscorers.items()}
    individual_list = [v for v in individual.values() if v["name"]]
    individual_list.sort(key=lambda x: (-(x["g"] + x["a1"] + x["a2"]), -x["g"], -x["sog"]))

    # ----- 4. GOALIE SV% from PBP-direct (canonical method) -----
    # Sum series-level shots faced and goals against per goalie team.
    # For Dobeš: TBL shots taken vs MTL = Dobes shots faced; TBL goals = Dobes GA.
    # For Vasilevskiy: MTL shots vs TBL.
    sf_against_mtl = 0
    sf_against_tbl = 0
    for k in per_game:
        g = per_game[k]
        if g["home"] == "MTL":
            sf_against_mtl += g["away_sog"] or 0
            sf_against_tbl += g["home_sog"] or 0
        else:
            sf_against_mtl += g["home_sog"] or 0
            sf_against_tbl += g["away_sog"] or 0
    dob_ga = sum(series_goalscorers["TBL"].values())
    vas_ga = sum(series_goalscorers["MTL"].values())
    goalies = {
        "Dobeš": {"shots_faced": sf_against_mtl, "goals_against": dob_ga,
                  "sv_pct": round(1 - dob_ga / sf_against_mtl, 3) if sf_against_mtl else None,
                  "games": 4},
        "Vasilevskiy": {"shots_faced": sf_against_tbl, "goals_against": vas_ga,
                        "sv_pct": round(1 - vas_ga / sf_against_tbl, 3) if sf_against_tbl else None,
                        "games": 4},
    }

    # ----- 5. MTL PROGRESSION (vs reg season) — same shape as game3_analysis -----
    progression = pd.read_sql_query(
        """
        SELECT
            p.name AS name, p.position AS position,
            p.toi AS toi_p, r.toi AS toi_r,
            p.xgf AS xgf_p, p.xga AS xga_p, r.xgf AS xgf_r, r.xga AS xga_r,
            p.gf AS gf_p, p.ga AS ga_p
        FROM (SELECT * FROM skater_stats WHERE season='20252026' AND stype=3 AND sit='5v5' AND split='oi' AND team_id='MTL') p
        JOIN (SELECT * FROM skater_stats WHERE season='20252026' AND stype=2 AND sit='5v5' AND split='oi' AND team_id='MTL') r
          ON p.name = r.name
        WHERE p.toi > 15  -- min playoff TOI
        """,
        con,
    )
    progression_rows = []
    if len(progression):
        # Compute on/off iso net per row (vs team-without-player)
        team_p_5v5 = series_5v5.get("MTL", {})
        team_toi = team_p_5v5.get("toi_min", 0) or 0
        team_xgf = team_p_5v5.get("xgf", 0) or 0
        team_xga = team_p_5v5.get("xga", 0) or 0
        # And the team reg row
        team_r = pd.read_sql_query(
            "SELECT toi, xgf, xga FROM team_stats WHERE season='20252026' AND stype=2 AND sit='5v5' AND team_id='MTL'",
            con,
        ).iloc[0]
        team_r_toi = float(team_r["toi"]); team_r_xgf = float(team_r["xgf"]); team_r_xga = float(team_r["xga"])

        def per60(events, toi_min):
            return (events * 60.0 / toi_min) if toi_min else 0.0

        def iso_net(toi_on, xgf_on, xga_on, t_toi, t_xgf, t_xga):
            toi_off = max(t_toi - toi_on, 0)
            xgf_off = max(t_xgf - xgf_on, 0)
            xga_off = max(t_xga - xga_on, 0)
            return (per60(xgf_on, toi_on) - per60(xgf_off, toi_off)) - (per60(xga_on, toi_on) - per60(xga_off, toi_off))

        for _, r in progression.iterrows():
            net_p = iso_net(r["toi_p"], r["xgf_p"], r["xga_p"], team_toi, team_xgf, team_xga)
            net_r = iso_net(r["toi_r"], r["xgf_r"], r["xga_r"], team_r_toi, team_r_xgf, team_r_xga)
            progression_rows.append({
                "name": r["name"], "position": r["position"],
                "toi_p": float(r["toi_p"]), "toi_r": float(r["toi_r"]),
                "net_r": round(float(net_r), 3), "net_p": round(float(net_p), 3),
                "delta": round(float(net_p - net_r), 3),
            })
        progression_rows.sort(key=lambda x: -x["delta"])

    movers_up = progression_rows[:5]
    movers_down = progression_rows[-5:][::-1]

    # ----- 6. Reuse existing JSONs (load + reference key fields) -----
    periods = json.loads(Path(__file__).parent.joinpath("game4_periods.numbers.json").read_text(encoding="utf-8"))
    slaf_hit = json.loads(Path(__file__).parent.joinpath("game4_slaf_hit.numbers.json").read_text(encoding="utf-8"))
    swap = json.loads(Path(__file__).parent.joinpath("game4_pregame_swap.numbers.json").read_text(encoding="utf-8"))

    payload = {
        "meta": {
            "as_of": "2026-04-27",
            "game_id": GAME_ID,
            "matchup": "TBL @ MTL",
            "result": "TBL 3 - MTL 2 (regulation)",
            "series_state_after_g4": "tied 2-2",
            "data_sources": [
                "NHL.com PBP (live + post-game)",
                "NHL.com boxscore",
                "NHL.com shifts (post-game; complete P1+P2+P3)",
                "Natural Stat Trick — refreshed 2026-04-27 (team_stats + skater_stats, season 25-26 stype=3)",
            ],
            "method_note": (
                "5v5 + 5v4 series totals from NST teamtable through Game 4. "
                "Goalscorer counts and goalie SV% are PBP-direct (canonical method "
                "per CLAUDE.md §3). Per-skater iso impacts use the on/off formulation "
                "in legacy/analytics/swap_engine.py."
            ),
        },
        "series_5v5": series_5v5,
        "series_5v4": series_5v4,
        "per_game": per_game,
        "series_goalscorers": series_goalscorers,
        "individual": individual_list,
        "goalies": goalies,
        "mtl_progression": {
            "movers_up": movers_up,
            "movers_down": movers_down,
            "all": progression_rows,
        },
        # References to companion analyses (already on disk)
        "companion_analyses": {
            "periods_live_and_postgame": "game4_periods.numbers.json",
            "slaf_hit_buckets": "game4_slaf_hit.numbers.json",
            "pregame_swap_projection": "game4_pregame_swap.numbers.json",
        },
        # Inline the load-bearing slim copies for the renderer to consume directly
        "goal_sequence": (periods.get("postgame") or {}).get("goal_sequence", []),
        "hagel_by_period": (periods.get("postgame") or {}).get("hagel_by_period", {}),
        "crozier_on_ice": (periods.get("postgame") or {}).get("crozier_on_ice", {}),
        "slaf_hit_buckets": {
            "pre": slaf_hit["pre"],
            "post": slaf_hit["post"],
            "deltas": slaf_hit["deltas"],
            "hit_event": slaf_hit["meta"]["hit_event"],
        },
        "swap_projection": {
            "out": swap["swap"]["out"],
            "in": swap["swap"]["in"],
            "delta_xgf_per_game": swap["swap"]["delta_xgf_per_game"],
            "delta_xga_per_game": swap["swap"]["delta_xga_per_game"],
            "delta_net_per_game": swap["swap"]["delta_net_per_game"],
            "delta_xgf_ci80": swap["swap"]["delta_xgf_ci80"],
            "delta_xga_ci80": swap["swap"]["delta_xga_ci80"],
        },
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"series 5v5 MTL: {series_5v5.get('MTL')}")
    print(f"series 5v4 MTL: {series_5v4.get('MTL')}")
    print(f"goalscorers: {series_goalscorers}")
    print(f"goalies: {goalies}")
    print(f"top movers up:")
    for r in movers_up[:3]:
        print(f"  {r['name']:25s} delta={r['delta']:+.3f}")
    print(f"top movers down:")
    for r in movers_down[:3]:
        print(f"  {r['name']:25s} delta={r['delta']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
