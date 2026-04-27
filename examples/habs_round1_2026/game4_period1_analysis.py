"""Game 4, Period 1 ranking analyzer.

Pulls live NHL.com PBP + boxscore for game 2025030124 (TBL @ MTL, Apr 26).

Data availability constraint: NHL.com's shift chart at
stats.nhle.com/shiftcharts lags significantly behind the live PBP — at
intermission of P1 it had only ~7 min of shifts. Therefore the analyzer
DOES NOT compute per-player on-ice Corsi/HDCF, since attribution would be
unreliable. Those metrics are reserved for the post-game pass when shifts
finalize.

What we CAN report from the live data:
  - Team-level P1 totals (Corsi, HDCF, SOG, hits, faceoffs) from PBP — full
  - Per-player individual contribution (G, A1, A2, SOG, blocks, hits, faceoffs,
    individual-HDCF — shots from inside ~22 ft of net)
  - Per-player P1 TOI from boxscore (currently equals total game TOI, since
    P1 just ended)
  - Composite ranking score per player: weighted individual contribution

Output: examples/habs_round1_2026/game4_period1.numbers.json
"""

from __future__ import annotations
import json
import math
import sys
from pathlib import Path
from collections import defaultdict

import truststore; truststore.inject_into_ssl()
import requests
import yaml

GAME_ID = "2025030124"
OUT_PATH = Path(__file__).parent / "game4_period1.numbers.json"
LINEUPS_PATH = Path(__file__).parent / "game4_pregame_lineups.yaml"

PBP_URL    = f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play"
BOX_URL    = f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/boxscore"

HD_DISTANCE = 22.0   # feet from goal — slot/crease approximation


def time_to_sec(t):
    if not t: return 0
    try:
        m, s = t.split(":")
        return int(m) * 60 + int(s)
    except Exception:
        return 0


def shot_distance(x, y):
    if x is None or y is None: return None
    return math.sqrt((abs(x) - 89.0) ** 2 + (y or 0.0) ** 2)


def main() -> int:
    pbp = requests.get(PBP_URL, timeout=30).json()
    box = requests.get(BOX_URL, timeout=30).json()
    LINEUPS = yaml.safe_load(LINEUPS_PATH.read_text(encoding="utf-8"))

    home_abbr = pbp["homeTeam"]["abbrev"]
    away_abbr = pbp["awayTeam"]["abbrev"]
    home_id = pbp["homeTeam"]["id"]
    away_id = pbp["awayTeam"]["id"]
    period_now = (pbp.get("periodDescriptor") or {}).get("number")
    in_intermission = (pbp.get("clock") or {}).get("inIntermission")

    # --- Build playerId -> {name, team, position} from boxscore ---
    pinfo: dict[int, dict] = {}
    for side in ("homeTeam", "awayTeam"):
        team_abbr = box[side]["abbrev"]
        for grp in ("forwards", "defense", "goalies"):
            for p in box.get("playerByGameStats", {}).get(side, {}).get(grp, []):
                pinfo[p["playerId"]] = {
                    "name": p["name"]["default"] if isinstance(p["name"], dict) else p["name"],
                    "team": team_abbr,
                    "position": p["position"],
                    "toi": p.get("toi", "00:00"),
                    "shifts": p.get("shifts", 0),
                    # boxscore-derived (game-level, but P1 == game right now)
                    "box_g": p.get("goals", 0),
                    "box_a": p.get("assists", 0),
                    "box_pts": p.get("points", 0),
                    "box_sog": p.get("sog", 0),
                    "box_hits": p.get("hits", 0),
                    "box_blocks": p.get("blockedShots", 0),
                    "box_givea": p.get("giveaways", 0),
                    "box_takea": p.get("takeaways", 0),
                    "box_pm": p.get("plusMinus", 0),
                    "is_goalie": grp == "goalies",
                }

    # --- Init counters per player from PBP P1 ---
    p1_plays = [
        p for p in pbp.get("plays", [])
        if (p.get("periodDescriptor") or {}).get("number") == 1
    ]

    init = lambda: {
        "g": 0, "a1": 0, "a2": 0, "sog": 0, "missed": 0, "blocked_taken": 0,
        "blocks_made": 0, "hits_for": 0, "hits_against": 0,
        "fo_won": 0, "fo_lost": 0,
        "ind_attempts": 0, "ind_hd_attempts": 0,
        "giveaways": 0, "takeaways": 0,
    }
    counters = defaultdict(init)

    # --- Team-level P1 totals ---
    team_totals = {
        home_abbr: defaultdict(int),
        away_abbr: defaultdict(int),
    }

    SHOT_TYPES = {"shot-on-goal", "missed-shot", "blocked-shot", "goal"}

    def situation(play):
        sc = play.get("situationCode") or ""
        return sc

    for play in p1_plays:
        typ = play.get("typeDescKey") or ""
        d = play.get("details") or {}
        sec = time_to_sec(play.get("timeInPeriod"))
        owner = d.get("eventOwnerTeamId")
        owner_abbr = home_abbr if owner == home_id else (away_abbr if owner == away_id else None)
        sc = situation(play)
        is_5v5 = (sc == "1551")

        # Per-team event totals
        if owner_abbr and typ in SHOT_TYPES:
            team_totals[owner_abbr][f"shot_attempts"] += 1
            if is_5v5:
                team_totals[owner_abbr]["cf_5v5"] += 1
            if typ == "shot-on-goal" or typ == "goal":
                team_totals[owner_abbr]["sog"] += 1
            if typ == "goal":
                team_totals[owner_abbr]["goals"] += 1
            x = d.get("xCoord"); y = d.get("yCoord")
            dist = shot_distance(x, y)
            if dist is not None and dist <= HD_DISTANCE:
                team_totals[owner_abbr]["hd_attempts"] += 1
                if is_5v5:
                    team_totals[owner_abbr]["hdcf_5v5"] += 1

        if typ == "hit" and owner_abbr:
            team_totals[owner_abbr]["hits"] += 1

        # Individual attribution
        if typ in SHOT_TYPES:
            shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
            if shooter:
                c = counters[shooter]
                x = d.get("xCoord"); y = d.get("yCoord")
                dist = shot_distance(x, y)
                is_hd = dist is not None and dist <= HD_DISTANCE
                if typ == "shot-on-goal":
                    c["sog"] += 1
                    c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                elif typ == "missed-shot":
                    c["missed"] += 1
                    c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                elif typ == "blocked-shot":
                    c["blocked_taken"] += 1
                    c["ind_attempts"] += 1
                elif typ == "goal":
                    c["g"] += 1
                    c["sog"] += 1
                    c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                    a1 = d.get("assist1PlayerId"); a2 = d.get("assist2PlayerId")
                    if a1: counters[a1]["a1"] += 1
                    if a2: counters[a2]["a2"] += 1
            blocker = d.get("blockingPlayerId")
            if typ == "blocked-shot" and blocker:
                counters[blocker]["blocks_made"] += 1

        if typ == "hit":
            hitter = d.get("hittingPlayerId"); hittee = d.get("hitteePlayerId")
            if hitter: counters[hitter]["hits_for"] += 1
            if hittee: counters[hittee]["hits_against"] += 1

        if typ == "faceoff":
            w = d.get("winningPlayerId"); l = d.get("losingPlayerId")
            if w: counters[w]["fo_won"] += 1
            if l: counters[l]["fo_lost"] += 1

        if typ == "giveaway":
            g = d.get("playerId")
            if g: counters[g]["giveaways"] += 1
        if typ == "takeaway":
            g = d.get("playerId")
            if g: counters[g]["takeaways"] += 1

    # --- Build per-player rows ---
    def toi_to_min(t: str) -> float:
        if not t: return 0.0
        try:
            m, s = t.split(":"); return int(m) + int(s)/60.0
        except Exception:
            return 0.0

    rows = []
    for pid, info in pinfo.items():
        c = counters.get(pid, init())
        toi_min = toi_to_min(info["toi"])
        if info["is_goalie"]:
            rows.append({
                "name": info["name"],
                "team": info["team"],
                "position": "G",
                "toi_p1_min": round(toi_min, 2),
                "shifts": info["shifts"],
                "is_goalie": True,
                "saves": "—",   # not extracted live; will appear post-game
            })
            continue
        score = (
            c["g"] * 3.0
            + (c["a1"] + c["a2"]) * 2.0
            + c["sog"] * 0.5
            + c["ind_hd_attempts"] * 0.75
            + (c["ind_attempts"] - c["sog"]) * 0.15  # missed/blocked credit, lighter
            + (c["hits_for"] + c["blocks_made"]) * 0.25
            - c["giveaways"] * 0.5
            + c["takeaways"] * 0.5
        )
        rows.append({
            "name": info["name"],
            "team": info["team"],
            "position": info["position"],
            "toi_p1_min": round(toi_min, 2),
            "shifts": info["shifts"],
            "g": c["g"], "a1": c["a1"], "a2": c["a2"],
            "points": c["g"] + c["a1"] + c["a2"],
            "sog": c["sog"], "missed": c["missed"], "blocked_taken": c["blocked_taken"],
            "ind_attempts": c["ind_attempts"], "ind_hd_attempts": c["ind_hd_attempts"],
            "blocks_made": c["blocks_made"],
            "hits_for": c["hits_for"], "hits_against": c["hits_against"],
            "fo_won": c["fo_won"], "fo_lost": c["fo_lost"],
            "giveaways": c["giveaways"], "takeaways": c["takeaways"],
            "score": round(score, 2),
            "is_goalie": False,
        })

    skaters = [r for r in rows if not r.get("is_goalie")]
    goalies = [r for r in rows if r.get("is_goalie")]

    skaters_sorted = sorted(skaters, key=lambda x: (-x["score"], -x["toi_p1_min"]))
    mtl_sorted = sorted([r for r in skaters if r["team"] == "MTL"], key=lambda x: -x["score"])
    tbl_sorted = sorted([r for r in skaters if r["team"] == "TBL"], key=lambda x: -x["score"])

    # --- MTL line aggregation from lineup yaml (we have it) ---
    name_to_row = {r["name"]: r for r in skaters}
    # Boxscore returns short-form names (e.g. "C. Caufield"); lineup yaml uses
    # full names. Build a name normalizer using last-name match.
    last_to_row = {}
    for r in skaters:
        ln = r["name"].split()[-1] if r["name"] else ""
        # account for "C. Caufield" → 'Caufield'
        last_to_row[ln] = r

    def find_row(full_name: str) -> dict | None:
        if not full_name: return None
        # Try exact, then last-name match.
        if full_name in name_to_row: return name_to_row[full_name]
        ln = full_name.split()[-1]
        return last_to_row.get(ln)

    mtl_lines_agg = []
    for line in (LINEUPS["teams"]["MTL"].get("forwards") or []):
        members = []
        for p in line["players"]:
            r = find_row(p["name"])
            if r: members.append(r)
        if not members: continue
        agg = {
            "line": line["line"],
            "players": [m["name"] for m in members],
            "g": sum(m.get("g", 0) for m in members),
            "a": sum(m.get("a1", 0) + m.get("a2", 0) for m in members),
            "sog": sum(m.get("sog", 0) for m in members),
            "ind_attempts": sum(m.get("ind_attempts", 0) for m in members),
            "ind_hd_attempts": sum(m.get("ind_hd_attempts", 0) for m in members),
            "hits_for": sum(m.get("hits_for", 0) for m in members),
            "blocks_made": sum(m.get("blocks_made", 0) for m in members),
            "score_sum": round(sum(m.get("score", 0) for m in members), 2),
            "toi_min_sum": round(sum(m.get("toi_p1_min", 0) for m in members), 2),
        }
        mtl_lines_agg.append(agg)

    mtl_pairs_agg = []
    for pair in (LINEUPS["teams"]["MTL"].get("defense") or []):
        members = []
        for p in pair["players"]:
            r = find_row(p["name"])
            if r: members.append(r)
        if not members: continue
        agg = {
            "pair": pair["pair"],
            "players": [m["name"] for m in members],
            "ind_attempts": sum(m.get("ind_attempts", 0) for m in members),
            "ind_hd_attempts": sum(m.get("ind_hd_attempts", 0) for m in members),
            "hits_for": sum(m.get("hits_for", 0) for m in members),
            "blocks_made": sum(m.get("blocks_made", 0) for m in members),
            "score_sum": round(sum(m.get("score", 0) for m in members), 2),
            "toi_min_sum": round(sum(m.get("toi_p1_min", 0) for m in members), 2),
        }
        mtl_pairs_agg.append(agg)

    # Team-level
    def cf_pct(home_cf, away_cf):
        if (home_cf + away_cf) == 0: return None
        return round(100.0 * home_cf / (home_cf + away_cf), 1)

    team_p1 = {
        home_abbr: {
            "shot_attempts": team_totals[home_abbr].get("shot_attempts", 0),
            "cf_5v5": team_totals[home_abbr].get("cf_5v5", 0),
            "hd_attempts": team_totals[home_abbr].get("hd_attempts", 0),
            "hdcf_5v5": team_totals[home_abbr].get("hdcf_5v5", 0),
            "sog": team_totals[home_abbr].get("sog", 0),
            "goals": team_totals[home_abbr].get("goals", 0),
            "hits": team_totals[home_abbr].get("hits", 0),
        },
        away_abbr: {
            "shot_attempts": team_totals[away_abbr].get("shot_attempts", 0),
            "cf_5v5": team_totals[away_abbr].get("cf_5v5", 0),
            "hd_attempts": team_totals[away_abbr].get("hd_attempts", 0),
            "hdcf_5v5": team_totals[away_abbr].get("hdcf_5v5", 0),
            "sog": team_totals[away_abbr].get("sog", 0),
            "goals": team_totals[away_abbr].get("goals", 0),
            "hits": team_totals[away_abbr].get("hits", 0),
        },
    }
    team_p1[f"{home_abbr}_cf_pct_5v5"] = cf_pct(team_p1[home_abbr]["cf_5v5"], team_p1[away_abbr]["cf_5v5"])
    team_p1[f"{home_abbr}_hdcf_pct_5v5"] = cf_pct(team_p1[home_abbr]["hdcf_5v5"], team_p1[away_abbr]["hdcf_5v5"])

    payload = {
        "meta": {
            "game_id": GAME_ID,
            "matchup": f"{away_abbr} @ {home_abbr}",
            "as_of": "2026-04-26 (P1 complete; intermission)",
            "period": "Period 1",
            "game_state": pbp.get("gameState"),
            "current_period": period_now,
            "in_intermission": in_intermission,
            "score_after_p1": {home_abbr: pbp["homeTeam"].get("score"), away_abbr: pbp["awayTeam"].get("score")},
            "method_note": (
                "Live data limitation: NHL.com shift chart lags real-time PBP, "
                "so per-player ON-ICE Corsi/HDCF is NOT computed (attribution would "
                "be unreliable). Individual contribution stats use the full P1 PBP. "
                "Team P1 totals (Corsi, HDCF, SOG) use the full PBP. xG model not "
                "applied — NST publishes that post-game. Composite ranking score = "
                "G×3 + A×2 + SOG×0.5 + ind-HD×0.75 + (missed+blocked)×0.15 + (hits+blocks)×0.25 "
                "- giveaways×0.5 + takeaways×0.5."
            ),
        },
        "team_p1": team_p1,
        "ranked_skaters_combined": skaters_sorted,
        "mtl_ranked": mtl_sorted,
        "tbl_ranked": tbl_sorted,
        "goalies": goalies,
        "mtl_lines_agg": mtl_lines_agg,
        "mtl_pairs_agg": mtl_pairs_agg,
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH}")

    print(f"\nP1 score: {away_abbr} {pbp['awayTeam'].get('score')} – {pbp['homeTeam'].get('score')} {home_abbr}")
    print(f"P1 5v5 Corsi: {home_abbr} {team_p1[home_abbr]['cf_5v5']} – {team_p1[away_abbr]['cf_5v5']} {away_abbr}  ({team_p1[home_abbr+'_cf_pct_5v5']}% {home_abbr})")
    print(f"P1 5v5 HDCF: {home_abbr} {team_p1[home_abbr]['hdcf_5v5']} – {team_p1[away_abbr]['hdcf_5v5']} {away_abbr}")
    print(f"\nTop 8 (combined):")
    for r in skaters_sorted[:8]:
        print(f"  {r['team']} {r['name']:25s} pos={r['position']:2s} TOI {r['toi_p1_min']:.1f}  G/A {r['g']}/{r['a1']+r['a2']}  SOG {r['sog']}  iHD {r['ind_hd_attempts']}  blk {r['blocks_made']} hit {r['hits_for']}  score {r['score']}")
    print(f"\nBottom 5 (combined):")
    for r in skaters_sorted[-5:]:
        print(f"  {r['team']} {r['name']:25s} pos={r['position']:2s} TOI {r['toi_p1_min']:.1f}  G/A {r['g']}/{r['a1']+r['a2']}  SOG {r['sog']}  give {r['giveaways']} take {r['takeaways']}  score {r['score']}")
    print(f"\nMTL lines (P1):")
    for L in mtl_lines_agg:
        print(f"  L{L['line']}: {' / '.join(L['players']):65s} G {L['g']} A {L['a']} SOG {L['sog']} iHD {L['ind_hd_attempts']} score_sum {L['score_sum']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
