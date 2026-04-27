"""Game 4 multi-period analyzer.

Detects which periods are complete in NHL.com PBP and computes:
  - Per-period rankings (P1, P2, P3, OT...) — same shape as game4_period1.numbers.json
  - Consolidated cumulative ranking (all completed periods so far)
  - Per-period TEAM totals (Corsi, HDCF, SOG, hits, goals at 5v5 and overall)
  - Period-vs-previous-period DELTAS per skater (P2 minus P1 etc.)
  - Line aggregation per period and consolidated for MTL

Run anytime during the game; re-run after each intermission.

Output: examples/habs_round1_2026/game4_periods.numbers.json

Usage:
    .venv/Scripts/python examples/habs_round1_2026/game4_periods.py
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
OUT_PATH = Path(__file__).parent / "game4_periods.numbers.json"
LINEUPS_PATH = Path(__file__).parent / "game4_pregame_lineups.yaml"

PBP_URL = f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play"
BOX_URL = f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/boxscore"

HD_DISTANCE = 22.0  # ft — slot/crease proxy


def time_to_sec(t):
    if not t: return 0
    try:
        m, s = t.split(":"); return int(m) * 60 + int(s)
    except Exception:
        return 0


def shot_distance(x, y):
    if x is None or y is None: return None
    return math.sqrt((abs(x) - 89.0) ** 2 + (y or 0.0) ** 2)


SHOT_TYPES = {"shot-on-goal", "missed-shot", "blocked-shot", "goal"}


def compute_period_breakdown(plays_in_period: list[dict], pinfo: dict, home_id: int, away_id: int, home_abbr: str, away_abbr: str) -> dict:
    """Run the per-player + team aggregation for a given set of plays.

    Returns a dict with skaters (sorted by score), goalies, team totals, and
    raw per-player counters.
    """
    init = lambda: {
        "g": 0, "a1": 0, "a2": 0, "sog": 0, "missed": 0, "blocked_taken": 0,
        "blocks_made": 0, "hits_for": 0, "hits_against": 0,
        "fo_won": 0, "fo_lost": 0,
        "ind_attempts": 0, "ind_hd_attempts": 0,
        "giveaways": 0, "takeaways": 0,
    }
    counters = defaultdict(init)
    team_totals = {home_abbr: defaultdict(int), away_abbr: defaultdict(int)}

    def is_5v5(play):
        return (play.get("situationCode") or "") == "1551"

    for play in plays_in_period:
        typ = play.get("typeDescKey") or ""
        d = play.get("details") or {}
        owner = d.get("eventOwnerTeamId")
        owner_abbr = home_abbr if owner == home_id else (away_abbr if owner == away_id else None)
        sc_5v5 = is_5v5(play)

        if owner_abbr and typ in SHOT_TYPES:
            team_totals[owner_abbr]["shot_attempts"] += 1
            if sc_5v5:
                team_totals[owner_abbr]["cf_5v5"] += 1
            if typ in ("shot-on-goal", "goal"):
                team_totals[owner_abbr]["sog"] += 1
            if typ == "goal":
                team_totals[owner_abbr]["goals"] += 1
            x = d.get("xCoord"); y = d.get("yCoord")
            dist = shot_distance(x, y)
            if dist is not None and dist <= HD_DISTANCE:
                team_totals[owner_abbr]["hd_attempts"] += 1
                if sc_5v5:
                    team_totals[owner_abbr]["hdcf_5v5"] += 1

        if typ == "hit" and owner_abbr:
            team_totals[owner_abbr]["hits"] += 1

        if typ in SHOT_TYPES:
            shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
            if shooter:
                c = counters[shooter]
                x = d.get("xCoord"); y = d.get("yCoord")
                dist = shot_distance(x, y)
                is_hd = dist is not None and dist <= HD_DISTANCE
                if typ == "shot-on-goal":
                    c["sog"] += 1; c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                elif typ == "missed-shot":
                    c["missed"] += 1; c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                elif typ == "blocked-shot":
                    c["blocked_taken"] += 1; c["ind_attempts"] += 1
                elif typ == "goal":
                    c["g"] += 1; c["sog"] += 1; c["ind_attempts"] += 1
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

    rows = []
    for pid, info in pinfo.items():
        c = counters.get(pid, init())
        if info["is_goalie"]:
            rows.append({
                "name": info["name"], "team": info["team"], "position": "G",
                "is_goalie": True,
            })
            continue
        score = (
            c["g"] * 3.0
            + (c["a1"] + c["a2"]) * 2.0
            + c["sog"] * 0.5
            + c["ind_hd_attempts"] * 0.75
            + (c["ind_attempts"] - c["sog"]) * 0.15
            + (c["hits_for"] + c["blocks_made"]) * 0.25
            - c["giveaways"] * 0.5
            + c["takeaways"] * 0.5
        )
        rows.append({
            "name": info["name"], "team": info["team"], "position": info["position"],
            "g": c["g"], "a1": c["a1"], "a2": c["a2"], "points": c["g"] + c["a1"] + c["a2"],
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
    skaters_sorted = sorted(skaters, key=lambda x: -x["score"])
    goalies = [r for r in rows if r.get("is_goalie")]

    def cf_pct(a, b):
        if a + b == 0: return None
        return round(100.0 * a / (a + b), 1)

    team_p = {
        home_abbr: {k: team_totals[home_abbr].get(k, 0) for k in ("shot_attempts", "cf_5v5", "hd_attempts", "hdcf_5v5", "sog", "goals", "hits")},
        away_abbr: {k: team_totals[away_abbr].get(k, 0) for k in ("shot_attempts", "cf_5v5", "hd_attempts", "hdcf_5v5", "sog", "goals", "hits")},
    }
    team_p[f"{home_abbr}_cf_pct_5v5"] = cf_pct(team_p[home_abbr]["cf_5v5"], team_p[away_abbr]["cf_5v5"])
    team_p[f"{home_abbr}_hdcf_pct_5v5"] = cf_pct(team_p[home_abbr]["hdcf_5v5"], team_p[away_abbr]["hdcf_5v5"])

    return {
        "skaters_sorted": skaters_sorted,
        "skaters_by_name": {r["name"]: r for r in skaters},
        "goalies": goalies,
        "team": team_p,
    }


def aggregate_lines(skaters_by_name: dict, lineups_block: dict) -> list[dict]:
    """Sum each player's stats over the given line groupings."""
    out = []
    for line in lineups_block.get("forwards") or []:
        members = []
        for p in line["players"]:
            # last-name fallback for boxscore short-form names ("C. Caufield")
            name = p["name"]
            if name in skaters_by_name:
                members.append(skaters_by_name[name])
            else:
                ln = name.split()[-1]
                for k, v in skaters_by_name.items():
                    if k.endswith(ln):
                        members.append(v); break
        if not members: continue
        out.append({
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
        })
    return out


def aggregate_pairs(skaters_by_name: dict, lineups_block: dict) -> list[dict]:
    out = []
    for pair in lineups_block.get("defense") or []:
        members = []
        for p in pair["players"]:
            name = p["name"]
            if name in skaters_by_name:
                members.append(skaters_by_name[name])
            else:
                ln = name.split()[-1]
                for k, v in skaters_by_name.items():
                    if k.endswith(ln):
                        members.append(v); break
        if not members: continue
        out.append({
            "pair": pair["pair"],
            "players": [m["name"] for m in members],
            "ind_attempts": sum(m.get("ind_attempts", 0) for m in members),
            "ind_hd_attempts": sum(m.get("ind_hd_attempts", 0) for m in members),
            "hits_for": sum(m.get("hits_for", 0) for m in members),
            "blocks_made": sum(m.get("blocks_made", 0) for m in members),
            "score_sum": round(sum(m.get("score", 0) for m in members), 2),
        })
    return out


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

    # Build pinfo from boxscore (covers everyone who has dressed).
    pinfo: dict[int, dict] = {}
    box_toi: dict[int, str] = {}
    for side in ("homeTeam", "awayTeam"):
        team_abbr = box[side]["abbrev"]
        for grp in ("forwards", "defense", "goalies"):
            for p in box.get("playerByGameStats", {}).get(side, {}).get(grp, []):
                pinfo[p["playerId"]] = {
                    "name": p["name"]["default"] if isinstance(p["name"], dict) else p["name"],
                    "team": team_abbr,
                    "position": p["position"],
                    "is_goalie": grp == "goalies",
                }
                box_toi[p["playerId"]] = p.get("toi", "00:00")

    plays_all = pbp.get("plays", [])

    # Detect completed periods: a period is complete if a 'period-end' play exists for it.
    complete_periods = sorted({
        (p.get("periodDescriptor") or {}).get("number")
        for p in plays_all
        if p.get("typeDescKey") == "period-end"
    })
    complete_periods = [p for p in complete_periods if p is not None]

    # Per-period breakdowns
    by_period = {}
    for pn in complete_periods:
        plays_pn = [p for p in plays_all if (p.get("periodDescriptor") or {}).get("number") == pn]
        by_period[pn] = compute_period_breakdown(plays_pn, pinfo, home_id, away_id, home_abbr, away_abbr)

    # Consolidated (all completed periods)
    plays_all_complete = [p for p in plays_all if (p.get("periodDescriptor") or {}).get("number") in complete_periods]
    consolidated = compute_period_breakdown(plays_all_complete, pinfo, home_id, away_id, home_abbr, away_abbr) if complete_periods else None

    # Pairwise deltas: for each consecutive pair (1→2, 2→3, ...), per-skater score delta.
    deltas = {}
    for i in range(1, len(complete_periods)):
        prev_p = complete_periods[i - 1]
        cur_p = complete_periods[i]
        prev_by_name = by_period[prev_p]["skaters_by_name"]
        cur_by_name = by_period[cur_p]["skaters_by_name"]
        rows = []
        names = set(prev_by_name) | set(cur_by_name)
        for n in names:
            prev = prev_by_name.get(n, {})
            cur = cur_by_name.get(n, {})
            rows.append({
                "name": n,
                "team": cur.get("team") or prev.get("team"),
                "position": cur.get("position") or prev.get("position"),
                f"score_p{prev_p}": prev.get("score", 0.0),
                f"score_p{cur_p}":  cur.get("score", 0.0),
                "delta": round((cur.get("score", 0.0) or 0.0) - (prev.get("score", 0.0) or 0.0), 2),
                f"sog_p{prev_p}": prev.get("sog", 0),
                f"sog_p{cur_p}":  cur.get("sog", 0),
                f"ihd_p{prev_p}": prev.get("ind_hd_attempts", 0),
                f"ihd_p{cur_p}":  cur.get("ind_hd_attempts", 0),
                f"g_p{prev_p}": prev.get("g", 0),
                f"g_p{cur_p}":  cur.get("g", 0),
                f"a_p{prev_p}": (prev.get("a1", 0) + prev.get("a2", 0)),
                f"a_p{cur_p}":  (cur.get("a1", 0) + cur.get("a2", 0)),
            })
        rows.sort(key=lambda x: -x["delta"])
        deltas[f"P{prev_p}_to_P{cur_p}"] = rows

    # Line aggregation per period + consolidated
    mtl_lineups = LINEUPS["teams"]["MTL"]
    lines_by_period = {pn: aggregate_lines(by_period[pn]["skaters_by_name"], mtl_lineups) for pn in complete_periods}
    pairs_by_period = {pn: aggregate_pairs(by_period[pn]["skaters_by_name"], mtl_lineups) for pn in complete_periods}
    lines_consolidated = aggregate_lines(consolidated["skaters_by_name"], mtl_lineups) if consolidated else []
    pairs_consolidated = aggregate_pairs(consolidated["skaters_by_name"], mtl_lineups) if consolidated else []

    # Compose payload
    score_now = {home_abbr: pbp["homeTeam"].get("score"), away_abbr: pbp["awayTeam"].get("score")}

    def strip_by_name(snap):
        return {
            "skaters_sorted": snap["skaters_sorted"],
            "goalies": snap["goalies"],
            "team": snap["team"],
        } if snap else None

    payload = {
        "meta": {
            "game_id": GAME_ID,
            "matchup": f"{away_abbr} @ {home_abbr}",
            "as_of": "2026-04-26 (live)",
            "completed_periods": complete_periods,
            "current_period": period_now,
            "in_intermission": in_intermission,
            "score_now": score_now,
            "method_note": (
                "Live data. Team totals and individual contribution from full PBP "
                "(events with situationCode='1551' for 5v5). xG model not applied "
                "(NST publishes post-game). Per-player on-ice Corsi excluded — "
                "NHL.com shifts trail PBP and would mis-attribute. "
                "Composite ranking score = G×3 + A×2 + SOG×0.5 + ind-HD×0.75 + "
                "(missed/blocked attempts)×0.15 + (hits + blocks)×0.25 - "
                "giveaways×0.5 + takeaways×0.5."
            ),
        },
        "periods": {
            f"P{pn}": strip_by_name(by_period[pn])
            for pn in complete_periods
        },
        "consolidated": strip_by_name(consolidated),
        "deltas": deltas,
        "mtl_lines_by_period": {f"P{pn}": lines_by_period[pn] for pn in complete_periods},
        "mtl_pairs_by_period": {f"P{pn}": pairs_by_period[pn] for pn in complete_periods},
        "mtl_lines_consolidated": lines_consolidated,
        "mtl_pairs_consolidated": pairs_consolidated,
    }

    # ----- Post-game extras (only when gameState=='OFF' or 'FINAL') -----
    is_final = pbp.get("gameState") in ("FINAL", "OFF")
    if is_final:
        # Build name lookup from boxscore (full names) for goal narrative.
        full_name_by_pid = {}
        team_by_pid = {}
        for side in ("homeTeam", "awayTeam"):
            for grp in ("forwards", "defense", "goalies"):
                for p in box.get("playerByGameStats", {}).get(side, {}).get(grp, []):
                    full_name_by_pid[p["playerId"]] = p["name"]["default"] if isinstance(p["name"], dict) else p["name"]
                    team_by_pid[p["playerId"]] = box[side]["abbrev"]

        goal_sequence = []
        for play in plays_all:
            if play.get("typeDescKey") != "goal":
                continue
            d = play.get("details") or {}
            owner = d.get("eventOwnerTeamId")
            owner_abbr = home_abbr if owner == home_id else away_abbr
            sc = play.get("situationCode") or ""
            # situation interpretation: away_g away_sk home_sk home_g
            try:
                ag, asksk, hsk, hg = int(sc[0]), int(sc[1]), int(sc[2]), int(sc[3])
                if asksk == hsk:
                    sit = f"{asksk}v{hsk}"
                else:
                    if owner_abbr == away_abbr:
                        sit = f"{asksk}v{hsk}"
                    else:
                        sit = f"{hsk}v{asksk}"
                if hg == 0 or ag == 0:
                    sit += " (EN)"  # empty net
            except Exception:
                sit = sc
            goal_sequence.append({
                "period": (play.get("periodDescriptor") or {}).get("number"),
                "time": play.get("timeInPeriod"),
                "owner": owner_abbr,
                "scorer": full_name_by_pid.get(d.get("scoringPlayerId")),
                "scorer_pid": d.get("scoringPlayerId"),
                "assist1": full_name_by_pid.get(d.get("assist1PlayerId")),
                "assist2": full_name_by_pid.get(d.get("assist2PlayerId")),
                "situation": sit,
            })

        # Series goal-scorer counts for THIS game (per team).
        per_game_goalscorers = {home_abbr: {}, away_abbr: {}}
        for g in goal_sequence:
            owner = g["owner"]; name = g["scorer"]
            if owner and name:
                per_game_goalscorers[owner][name] = per_game_goalscorers[owner].get(name, 0) + 1

        # On-ice for goals — best effort using shifts (P1+P2 complete, P3 partial).
        try:
            shifts_data = requests.get(
                f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={GAME_ID}",
                timeout=20,
            ).json().get("data", [])
        except Exception:
            shifts_data = []

        # Build per-pid period -> intervals
        shifts_by_pid_period = {}
        for s in shifts_data:
            pid = s.get("playerId")
            pn = s.get("period")
            start = time_to_sec(s.get("startTime"))
            end = time_to_sec(s.get("endTime"))
            if end <= start:
                continue
            shifts_by_pid_period.setdefault((pid, pn), []).append((start, end))

        def on_ice_for(pid, period, sec):
            for st, en in shifts_by_pid_period.get((pid, period), []):
                if st <= sec <= en:
                    return True
            return False

        # For each goal, list MTL on-ice and TBL on-ice players (skaters only).
        all_skater_pids = [pid for pid, info in pinfo.items() if not info["is_goalie"]]
        for g in goal_sequence:
            on = []
            sec = time_to_sec(g["time"])
            for pid in all_skater_pids:
                if on_ice_for(pid, g["period"], sec):
                    on.append({
                        "name": full_name_by_pid.get(pid),
                        "team": team_by_pid.get(pid),
                    })
            g["on_ice"] = on
            g["on_ice_complete"] = len(on) > 0  # may be zero if shift chart hasn't caught up

        # Hagel-specific period breakdown.
        hagel_pid = None
        for pid, name in full_name_by_pid.items():
            if name and "Hagel" in name:
                hagel_pid = pid; break
        hagel_by_period = {}
        for pn in complete_periods:
            snap = by_period[pn]
            if hagel_pid:
                row = next((r for r in snap["skaters_sorted"] if r.get("name") and "Hagel" in r["name"]), None)
                if row:
                    hagel_by_period[f"P{pn}"] = {
                        "score": row.get("score"),
                        "g": row.get("g"), "a": row.get("a1", 0) + row.get("a2", 0),
                        "sog": row.get("sog"), "ind_hd_attempts": row.get("ind_hd_attempts"),
                    }

        # Crozier on-ice goal-against / goal-for tally.
        crozier_pid = None
        for pid, name in full_name_by_pid.items():
            if name and "Crozier" in name:
                crozier_pid = pid; break
        crozier_oi = {"goals_for_oi": 0, "goals_against_oi": 0, "shifts_in_p1p2": 0, "team": team_by_pid.get(crozier_pid)}
        if crozier_pid:
            for g in goal_sequence:
                sec = time_to_sec(g["time"])
                if on_ice_for(crozier_pid, g["period"], sec):
                    if g["owner"] == team_by_pid.get(crozier_pid):
                        crozier_oi["goals_for_oi"] += 1
                    else:
                        crozier_oi["goals_against_oi"] += 1
            crozier_oi["shifts_in_p1p2"] = sum(
                len(intervals)
                for (pid, pn), intervals in shifts_by_pid_period.items()
                if pid == crozier_pid and pn in (1, 2)
            )

        payload["postgame"] = {
            "final_score": {home_abbr: pbp["homeTeam"].get("score"), away_abbr: pbp["awayTeam"].get("score")},
            "winner": home_abbr if pbp["homeTeam"].get("score", 0) > pbp["awayTeam"].get("score", 0) else away_abbr,
            "series_state_after_g4": "tied 2-2",
            "goal_sequence": goal_sequence,
            "per_game_goalscorers": per_game_goalscorers,
            "hagel_by_period": hagel_by_period,
            "crozier_on_ice": crozier_oi,
            "shift_completeness": {
                f"P{p}": len([s for s in shifts_data if s.get("period") == p])
                for p in complete_periods
            },
        }

    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print(f"completed periods: {complete_periods}")
    print(f"score now: {away_abbr} {score_now[away_abbr]} – {score_now[home_abbr]} {home_abbr}")
    if consolidated:
        print(f"\nTop 5 consolidated:")
        for r in consolidated["skaters_sorted"][:5]:
            print(f"  {r['team']} {r['name']:25s} G {r['g']} A {r['a1']+r['a2']} SOG {r['sog']} iHD {r['ind_hd_attempts']} score {r['score']}")
    for key, rows in deltas.items():
        print(f"\nMovers {key} (top 3 up / bottom 3 down):")
        for r in rows[:3]:
            print(f"  ↑ {r['team']} {r['name']:25s} Δ {r['delta']:+.2f}")
        for r in rows[-3:]:
            print(f"  ↓ {r['team']} {r['name']:25s} Δ {r['delta']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
