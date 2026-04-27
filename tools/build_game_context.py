"""Generate a starter game_context yaml from NHL.com PBP + boxscore.

A game_context file is the canonical fact base for everything we know about
a single game. Any later analysis that references that game by number/event
must read its corresponding context file rather than rely on prose memory.

This generator handles the data-derivable fields:
  - Final score, goalies, goalscorers (PBP-derived)
  - Major events (goals, fights/altercations, hits with hittee Slafkovský,
    penalty timing) — the kind the framework uses cross-game.
  - File pointers to related analyzer output / lineups (best-effort by
    convention; user fills in if non-standard).

Manual fields (left as TODO/null) for the user to fill:
  - significance / narrative around each key event
  - injury notes (data doesn't tell us this)
  - series state after the game (depends on schedule context)
  - related briefs (depends on what's been written)

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_game_context.py \\
        2025030121 2025030122 2025030123 2025030124 \\
        --series "Round 1, MTL vs TBL" --series-start-game 1 \\
        --output-dir examples/habs_round1_2026/

Files written: <output-dir>/game<N>_context.yaml (N = series_game number,
inferred from order on the command line if --series-start-game is set;
otherwise just by gameId).
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

import truststore; truststore.inject_into_ssl()
import requests


def time_to_sec(t):
    if not t: return 0
    try:
        m, s = t.split(":"); return int(m) * 60 + int(s)
    except Exception:
        return 0


def fmt_time(sec):
    return f"{sec // 60:02d}:{sec % 60:02d}"


def yaml_dump(data, indent=0):
    """Tiny ad-hoc YAML emitter. Keeps deps minimal and ordering deterministic.
    Handles dicts (with str/list/dict/scalar values), lists, strings, ints, floats, None.
    """
    out = []
    pad = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                if not v:
                    out.append(f"{pad}{k}: {{}}")
                else:
                    out.append(f"{pad}{k}:")
                    out.append(yaml_dump(v, indent + 1))
            elif isinstance(v, list):
                if not v:
                    out.append(f"{pad}{k}: []")
                else:
                    out.append(f"{pad}{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            inner = yaml_dump(item, indent + 1).splitlines()
                            if inner:
                                out.append(f"{pad}  - {inner[0].strip()}")
                                for line in inner[1:]:
                                    out.append(f"{pad}    {line.strip()}")
                        else:
                            out.append(f"{pad}  - {scalar(item)}")
            else:
                out.append(f"{pad}{k}: {scalar(v)}")
    return "\n".join(out)


def scalar(v):
    if v is None: return "null"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return str(v)
    s = str(v)
    # Quote if contains special chars
    if any(c in s for c in [':', '#', '\n', "'", '"']) or s.strip() != s or s == "":
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


def fetch_game(gid):
    pbp = requests.get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play", timeout=20)
    box = requests.get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/boxscore", timeout=20)
    return pbp.json(), box.json()


def build_context(gid: str, series: str | None, series_game: int | None) -> dict:
    pbp, box = fetch_game(gid)

    home_abbr = pbp["homeTeam"]["abbrev"]
    away_abbr = pbp["awayTeam"]["abbrev"]
    home_id = pbp["homeTeam"]["id"]
    away_id = pbp["awayTeam"]["id"]

    # Build pid -> name map
    name_by_pid = {}
    pos_by_pid = {}
    team_by_pid = {}
    for side in ("homeTeam", "awayTeam"):
        for grp in ("forwards", "defense", "goalies"):
            for p in box.get("playerByGameStats", {}).get(side, {}).get(grp, []):
                pid = p["playerId"]
                name_by_pid[pid] = p["name"]["default"] if isinstance(p["name"], dict) else p["name"]
                pos_by_pid[pid] = p["position"]
                team_by_pid[pid] = box[side]["abbrev"]

    plays = pbp.get("plays", [])

    # Final score
    final_score = {home_abbr: pbp["homeTeam"].get("score", 0),
                   away_abbr: pbp["awayTeam"].get("score", 0)}

    # Detect overtime / shootout
    completed_periods = sorted({(p.get("periodDescriptor") or {}).get("number")
                                for p in plays if p.get("typeDescKey") == "period-end"})
    completed_periods = [p for p in completed_periods if p is not None]
    last_period = max(completed_periods) if completed_periods else None
    last_period_type = None
    for p in plays:
        if p.get("typeDescKey") == "period-end":
            pd_ = p.get("periodDescriptor") or {}
            if pd_.get("number") == last_period:
                last_period_type = pd_.get("periodType")
    result_suffix = ""
    if last_period_type == "OT": result_suffix = " (OT)"
    elif last_period_type == "SO": result_suffix = " (SO)"
    if final_score[home_abbr] > final_score[away_abbr]:
        winner_abbr, loser_abbr = home_abbr, away_abbr
    else:
        winner_abbr, loser_abbr = away_abbr, home_abbr
    result = f"{winner_abbr} {final_score[winner_abbr]} - {loser_abbr} {final_score[loser_abbr]}{result_suffix}"

    # Goalscorers + assists per team
    goalscorers = {home_abbr: {}, away_abbr: {}}
    goal_sequence = []
    for p in plays:
        if p.get("typeDescKey") != "goal": continue
        d = p.get("details") or {}
        owner = d.get("eventOwnerTeamId")
        team = home_abbr if owner == home_id else (away_abbr if owner == away_id else None)
        scorer_pid = d.get("scoringPlayerId")
        scorer = name_by_pid.get(scorer_pid)
        if team and scorer:
            goalscorers[team][scorer] = goalscorers[team].get(scorer, 0) + 1
        sc = p.get("situationCode") or ""
        try:
            ag, asksk, hsk, hg = int(sc[0]), int(sc[1]), int(sc[2]), int(sc[3])
            if asksk == hsk:
                sit = f"{asksk}v{hsk}"
            else:
                sit = f"{asksk}v{hsk}" if team == away_abbr else f"{hsk}v{asksk}"
            if hg == 0 or ag == 0: sit += " (EN)"
        except Exception:
            sit = sc
        goal_sequence.append({
            "period": (p.get("periodDescriptor") or {}).get("number"),
            "time": p.get("timeInPeriod"),
            "team": team,
            "scorer": scorer,
            "assist1": name_by_pid.get(d.get("assist1PlayerId")),
            "assist2": name_by_pid.get(d.get("assist2PlayerId")),
            "situation": sit,
        })

    # Penalties (used to find fights — penaltyTypeCode 'FIG' or 'fighting' / minor 5 min)
    penalties = []
    for p in plays:
        if p.get("typeDescKey") != "penalty": continue
        d = p.get("details") or {}
        desc = d.get("descKey") or d.get("typeDescKey") or ""
        committed_by = name_by_pid.get(d.get("committedByPlayerId"))
        served_by = name_by_pid.get(d.get("servedByPlayerId"))
        drawn_by = name_by_pid.get(d.get("drawnByPlayerId"))
        duration = d.get("duration") or 0
        team_abbr = home_abbr if d.get("eventOwnerTeamId") == home_id else (away_abbr if d.get("eventOwnerTeamId") == away_id else None)
        penalties.append({
            "period": (p.get("periodDescriptor") or {}).get("number"),
            "time": p.get("timeInPeriod"),
            "team": team_abbr,
            "committed_by": committed_by,
            "drawn_by": drawn_by,
            "type": desc,
            "duration_min": duration,
        })

    # Detect fights / fighting majors
    fights = [pen for pen in penalties if (pen.get("type") or "").lower() in ("fighting", "fight") or pen.get("duration_min") == 5 and "fight" in (pen.get("type") or "").lower()]

    # Pull marquee hits — focus on hits taken by Slafkovský if present (cross-game framework anchor).
    SLAF_PID = 8483515
    slaf_hits_against = []
    for p in plays:
        if p.get("typeDescKey") != "hit": continue
        d = p.get("details") or {}
        if d.get("hitteePlayerId") == SLAF_PID:
            slaf_hits_against.append({
                "period": (p.get("periodDescriptor") or {}).get("number"),
                "time": p.get("timeInPeriod"),
                "hitter": name_by_pid.get(d.get("hittingPlayerId")),
                "hittee": name_by_pid.get(d.get("hitteePlayerId")),
                "zone": d.get("zoneCode"),
            })

    # Convert key events to a unified list (manual significance left blank for user fill).
    key_events = []
    for f in fights:
        key_events.append({
            "kind": "fight",
            "period": f["period"],
            "time_in_period": f["time"],
            "primary_player": f["committed_by"],
            "team": f["team"],
            "details": f"5-min fighting major; drawn by {f.get('drawn_by') or 'unknown'}",
            "significance": "TODO_MANUAL: fill in narrative significance",
        })
    for h in slaf_hits_against:
        key_events.append({
            "kind": "hit",
            "period": h["period"],
            "time_in_period": h["time"],
            "hittee": h["hittee"],
            "hitter": h["hitter"],
            "zone": h["zone"],
            "significance": "TODO_MANUAL: heavy contact event on Slafkovský — narrative significance to fill",
        })

    return {
        "schema_version": 1,
        "game_id": gid,
        "date": pbp.get("gameDate"),
        "season": pbp.get("season"),
        "game_type": pbp.get("gameType"),
        "series": series,
        "series_game": series_game,
        "matchup": f"{away_abbr} @ {home_abbr}",
        "home_team": home_abbr,
        "away_team": away_abbr,
        "final_score": final_score,
        "result": result,
        "regulation_or_overtime": last_period_type,
        "completed_periods": completed_periods,
        "goalies": {
            home_abbr: next(iter([name_by_pid[p["playerId"]] for p in box.get("playerByGameStats", {}).get("homeTeam", {}).get("goalies", []) if p.get("toi") not in (None, "00:00")]), None),
            away_abbr: next(iter([name_by_pid[p["playerId"]] for p in box.get("playerByGameStats", {}).get("awayTeam", {}).get("goalies", []) if p.get("toi") not in (None, "00:00")]), None),
        },
        "goalscorers": goalscorers,
        "goal_sequence": goal_sequence,
        "key_events": key_events,
        "series_state_after_game": "TODO_MANUAL: e.g. 'TBL leads 2-1' or 'tied 2-2'",
        "file_pointers": {
            "pbp_url": f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play",
            "boxscore_url": f"https://api-web.nhle.com/v1/gamecenter/{gid}/boxscore",
            "shifts_url": f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={gid}",
            "analyzer_output": f"TODO_MANUAL: e.g. game{series_game}_analysis.numbers.json",
            "lineups_yaml": f"TODO_MANUAL: e.g. game{series_game}_lineups.yaml",
        },
        "related_briefs": [],
        "notes": "TODO_MANUAL: free-form narrative the data alone cannot capture (deployment context, line-blender pivots, injury rumours, etc.)",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game_ids", nargs="+", help="NHL game IDs in order")
    ap.add_argument("--series", default=None, help="Series label, e.g. 'Round 1, MTL vs TBL'")
    ap.add_argument("--series-start-game", type=int, default=1, help="Which series-game number the first id corresponds to (default 1)")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--filename-template", default="game{n}_context.yaml",
                    help="Output filename pattern, '{n}' = series_game, '{gid}' = game id")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for offset, gid in enumerate(args.game_ids):
        n = args.series_start_game + offset if args.series_start_game else None
        ctx = build_context(gid, args.series, n)
        body = (
            "# Canonical game context. Read this BEFORE writing any later doc that\n"
            f"# references game {n} of {args.series or 'this series'}. The data-derivable\n"
            "# fields are populated from NHL.com; TODO_MANUAL fields require user fill-in.\n"
            "#\n"
            "# Schema: see CLAUDE.md - 'Per-game context files' section.\n\n"
            + yaml_dump(ctx) + "\n"
        )
        fname = args.filename_template.format(n=n, gid=gid)
        out_path = out_dir / fname
        out_path.write_text(body, encoding="utf-8")
        print(f"wrote {out_path}")
        # Print a quick summary
        print(f"  result: {ctx['result']}")
        print(f"  fights detected: {len([e for e in ctx['key_events'] if e['kind'] == 'fight'])}")
        print(f"  Slaf hits-against: {len([e for e in ctx['key_events'] if e['kind'] == 'hit'])}")


if __name__ == "__main__":
    main()
