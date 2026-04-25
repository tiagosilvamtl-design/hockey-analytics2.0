"""Game 3 analyzer — MTL vs. TBL, 2026-04-24.

Pulls team + skater data through Game 3 (NST playoff 25-26) and per-game
Slafkovský data from NHL.com (shifts + play-by-play). Validates a set of
claims sourced from public reporting in `reearch/2026-04-26 - Game report.txt`
and outputs a JSON summary the markdown post is built from.

Run:
    .venv/Scripts/python examples/habs_round1_2026/game3_analysis.py
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd
import requests
from scipy import stats as _stats

# Use the legacy SQLite store for now (lemieux-app migration pending).
sys.path.insert(0, "legacy")
from data.nst_client import NstClient  # noqa: E402

STORE_DB = Path("legacy/data/store.sqlite")
OUT_JSON = Path("examples/habs_round1_2026/game3_analysis.numbers.json")

NHL_GAMES = {
    "G1": {"id": "2025030121", "date": "2026-04-19", "venue": "Tampa"},
    "G2": {"id": "2025030122", "date": "2026-04-21", "venue": "Tampa"},
    "G3": {"id": "2025030123", "date": "2026-04-24", "venue": "Montreal"},
}

# NHL team IDs (from API)
TEAM_ID = {"MTL": 8, "TBL": 14}

# Player IDs we care about
PLAYERS = {
    "Slafkovsky": 8483515,  # Juraj Slafkovský
    "Hagel": 8479542,       # Brandon Hagel
    "Hutson": 8483457,      # Lane Hutson
    "Suzuki": 8480018,      # Nick Suzuki
    "Caufield": 8481540,    # Cole Caufield
    "Dach": 8481523,        # Kirby Dach
    "Bolduc": 8482147,      # Zachary Bolduc (verified below)
    "Texier": 8480074,      # Alexandre Texier
    "Point": 8478010,       # Brayden Point
    "Kucherov": 8476453,    # Nikita Kucherov
}


# =====================================================================
# NHL.com helpers
# =====================================================================
_session = requests.Session()


def fetch_pbp(game_id: str) -> dict:
    return _session.get(
        f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play", timeout=30
    ).json()


def fetch_shifts(game_id: str) -> list[dict]:
    return _session.get(
        f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={game_id}",
        timeout=30,
    ).json().get("data", [])


def time_to_sec(t: str | None) -> int:
    if not t:
        return 0
    try:
        m, s = t.split(":")
        return int(m) * 60 + int(s)
    except Exception:
        return 0


# =====================================================================
# Per-game Slafkovsky breakdown
# =====================================================================
def slaf_per_game(game_label: str, game_id: str) -> dict:
    shifts = fetch_shifts(game_id)
    pbp = fetch_pbp(game_id)
    plays = pbp.get("plays", [])

    slaf_shifts = [s for s in shifts if s.get("playerId") == PLAYERS["Slafkovsky"]]
    by_period: dict[int, list[tuple[int, int]]] = {}
    total_sec = 0
    for s in slaf_shifts:
        p = s.get("period")
        start = time_to_sec(s.get("startTime"))
        end = time_to_sec(s.get("endTime"))
        if end <= start:
            continue
        by_period.setdefault(p, []).append((start, end))
        total_sec += end - start

    def on_ice(period: int, ev_sec: int) -> bool:
        for start, end in by_period.get(period, []):
            if start <= ev_sec <= end:
                return True
        return False

    counts = {
        "shifts": len(slaf_shifts),
        "toi_sec": total_sec,
        "slaf_sog": 0,
        "slaf_goals": 0,
        "slaf_missed": 0,
        "mtl_sog_oi": 0,
        "tbl_sog_oi": 0,
        "mtl_goals_oi": 0,
        "tbl_goals_oi": 0,
        "mtl_missed_oi": 0,
        "tbl_missed_oi": 0,
        "by_period_toi_sec": {p: sum(e - s for s, e in lst) for p, lst in by_period.items()},
    }
    for play in plays:
        pd_desc = play.get("periodDescriptor") or {}
        ev_period = pd_desc.get("number")
        ev_sec = time_to_sec(play.get("timeInPeriod"))
        typ = play.get("typeDescKey") or ""
        d = play.get("details") or {}
        owner = d.get("eventOwnerTeamId")
        is_mtl = owner == TEAM_ID["MTL"]
        if typ in {"shot-on-goal", "missed-shot", "goal"}:
            shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
            if shooter == PLAYERS["Slafkovsky"]:
                if typ == "shot-on-goal":
                    counts["slaf_sog"] += 1
                elif typ == "missed-shot":
                    counts["slaf_missed"] += 1
                elif typ == "goal":
                    counts["slaf_goals"] += 1
            if on_ice(ev_period, ev_sec):
                key_sog = "mtl_sog_oi" if is_mtl else "tbl_sog_oi"
                key_g = "mtl_goals_oi" if is_mtl else "tbl_goals_oi"
                key_m = "mtl_missed_oi" if is_mtl else "tbl_missed_oi"
                if typ == "shot-on-goal":
                    counts[key_sog] += 1
                elif typ == "goal":
                    counts[key_g] += 1
                    counts[key_sog] += 1  # goals are also shots-on-goal in counting
                elif typ == "missed-shot":
                    counts[key_m] += 1
    counts["toi_min"] = round(total_sec / 60.0, 2)
    counts["game"] = game_label
    return counts


# =====================================================================
# Slafkovsky pre/post fight buckets
# =====================================================================
def slaf_pre_post_fight(fight_period: int, fight_sec: int) -> dict:
    """Pre-fight = G1 entire + G2 up to fight_sec of fight_period.
    Post-fight = G2 from fight_sec of fight_period onward + G3 entire.
    """
    pre = _empty_bucket("pre-fight: G1 + G2 up to P2 5:14")
    post = _empty_bucket("post-fight: G2 from P2 5:14 + G3")

    def is_pre(label: str, p: int, sec: int) -> bool:
        if label == "G1":
            return True
        if label == "G2":
            if p < fight_period:
                return True
            if p == fight_period and sec < fight_sec:
                return True
        return False

    for label, info in NHL_GAMES.items():
        gid = info["id"]
        shifts = fetch_shifts(gid)
        plays = fetch_pbp(gid).get("plays", [])
        slaf_shifts = [s for s in shifts if s.get("playerId") == PLAYERS["Slafkovsky"]]
        for s in slaf_shifts:
            p = s.get("period")
            start = time_to_sec(s.get("startTime"))
            end = time_to_sec(s.get("endTime"))
            if end <= start:
                continue
            for sec in range(start, end):
                b = pre if is_pre(label, p, sec) else post
                b["toi_sec"] += 1
        for play in plays:
            pdesc = play.get("periodDescriptor") or {}
            ev_p = pdesc.get("number")
            ev_sec = time_to_sec(play.get("timeInPeriod"))
            typ = play.get("typeDescKey") or ""
            if typ not in {"shot-on-goal", "goal", "missed-shot"}:
                continue
            d = play.get("details") or {}
            shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
            owner = d.get("eventOwnerTeamId")
            on_ice = any(
                s.get("period") == ev_p
                and time_to_sec(s.get("startTime")) <= ev_sec <= time_to_sec(s.get("endTime"))
                for s in slaf_shifts
            )
            b = pre if is_pre(label, ev_p, ev_sec) else post
            if shooter == PLAYERS["Slafkovsky"]:
                if typ == "shot-on-goal":
                    b["slaf_sog"] += 1
                elif typ == "missed-shot":
                    b["slaf_missed"] += 1
                elif typ == "goal":
                    b["slaf_goals"] += 1
                    b["slaf_sog"] += 1
            if on_ice:
                is_mtl = owner == TEAM_ID["MTL"]
                if typ == "shot-on-goal":
                    (b["mtl_sog_oi" if is_mtl else "tbl_sog_oi"]) and None  # noqa
                    if is_mtl:
                        b["mtl_sog_oi"] += 1
                    else:
                        b["tbl_sog_oi"] += 1
                elif typ == "goal":
                    if is_mtl:
                        b["mtl_goals_oi"] += 1; b["mtl_sog_oi"] += 1
                    else:
                        b["tbl_goals_oi"] += 1; b["tbl_sog_oi"] += 1
                elif typ == "missed-shot":
                    if is_mtl:
                        b["mtl_missed_oi"] += 1
                    else:
                        b["tbl_missed_oi"] += 1

    pre["toi_min"] = round(pre["toi_sec"] / 60.0, 2)
    post["toi_min"] = round(post["toi_sec"] / 60.0, 2)
    return {"pre": pre, "post": post,
            "fight": {"period": fight_period, "sec_in_period": fight_sec, "game": "G2"}}


def _empty_bucket(label: str) -> dict:
    return {
        "label": label,
        "toi_sec": 0, "toi_min": 0,
        "slaf_sog": 0, "slaf_goals": 0, "slaf_missed": 0,
        "mtl_sog_oi": 0, "tbl_sog_oi": 0,
        "mtl_goals_oi": 0, "tbl_goals_oi": 0,
        "mtl_missed_oi": 0, "tbl_missed_oi": 0,
    }


# =====================================================================
# Game 3 game-level claim validation (team totals from PBP)
# =====================================================================
def game_level_team_stats(game_id: str) -> dict:
    pbp = fetch_pbp(game_id)
    plays = pbp.get("plays", [])
    home_id = pbp.get("homeTeam", {}).get("id")
    away_id = pbp.get("awayTeam", {}).get("id")
    home_abbr = pbp.get("homeTeam", {}).get("abbrev")
    away_abbr = pbp.get("awayTeam", {}).get("abbrev")

    counts = {
        "home": home_abbr, "away": away_abbr,
        "home_sog": 0, "away_sog": 0,
        "home_goals": 0, "away_goals": 0,
        "home_missed": 0, "away_missed": 0,
        "home_blocked": 0, "away_blocked": 0,
        "home_hits": 0, "away_hits": 0,
        "pim_total": 0,
        "events_by_type": {},
    }
    for p in plays:
        typ = p.get("typeDescKey") or ""
        counts["events_by_type"][typ] = counts["events_by_type"].get(typ, 0) + 1
        d = p.get("details") or {}
        owner = d.get("eventOwnerTeamId")
        is_home = owner == home_id
        if typ == "shot-on-goal":
            if is_home:
                counts["home_sog"] += 1
            else:
                counts["away_sog"] += 1
        elif typ == "missed-shot":
            if is_home:
                counts["home_missed"] += 1
            else:
                counts["away_missed"] += 1
        elif typ == "blocked-shot":
            # owner of blocked-shot is the BLOCKER's team
            if is_home:
                counts["home_blocked"] += 1
            else:
                counts["away_blocked"] += 1
        elif typ == "goal":
            if is_home:
                counts["home_goals"] += 1
                counts["home_sog"] += 1
            else:
                counts["away_goals"] += 1
                counts["away_sog"] += 1
        elif typ == "hit":
            if is_home:
                counts["home_hits"] += 1
            else:
                counts["away_hits"] += 1
        elif typ == "penalty":
            counts["pim_total"] += int(d.get("duration") or 0)
    # Corsi/Fenwick proxies
    counts["home_cf"] = counts["home_sog"] + counts["home_missed"] + counts["away_blocked"]  # blocks against MTL count as MTL Corsi if MTL is home
    counts["away_cf"] = counts["away_sog"] + counts["away_missed"] + counts["home_blocked"]
    counts["home_ff"] = counts["home_sog"] + counts["home_missed"]
    counts["away_ff"] = counts["away_sog"] + counts["away_missed"]
    counts["home_cf_pct"] = (
        counts["home_cf"] / (counts["home_cf"] + counts["away_cf"]) * 100
        if (counts["home_cf"] + counts["away_cf"]) > 0 else None
    )
    counts["home_ff_pct"] = (
        counts["home_ff"] / (counts["home_ff"] + counts["away_ff"]) * 100
        if (counts["home_ff"] + counts["away_ff"]) > 0 else None
    )
    return counts


# =====================================================================
# Series-level (NST playoff 25-26) — compares MTL vs TBL
# =====================================================================
def series_team_stats(sit: str = "5v5") -> pd.DataFrame:
    with sqlite3.connect(STORE_DB) as c:
        return pd.read_sql_query(
            "SELECT * FROM team_stats WHERE season='20252026' AND stype=3 AND sit=? "
            "AND team_id IN ('MTL','T.B')",
            c, params=(sit,),
        )


def mtl_player_progression() -> dict:
    """Compare each MTL skater's playoff iso impact to their regular-season pooled baseline."""
    keys_p = (("20252026", 3),)
    keys_r = (("20252026", 2),)
    # skater playoff on-ice
    with sqlite3.connect(STORE_DB) as c:
        sk_p = pd.read_sql_query(
            "SELECT * FROM skater_stats WHERE season='20252026' AND stype=3 AND sit='5v5' "
            "AND split='oi' AND team_id LIKE '%MTL%'",
            c,
        )
        sk_r = pd.read_sql_query(
            "SELECT * FROM skater_stats WHERE season='20252026' AND stype=2 AND sit='5v5' "
            "AND split='oi' AND team_id LIKE '%MTL%'",
            c,
        )
        team_p = pd.read_sql_query(
            "SELECT * FROM team_stats WHERE season='20252026' AND stype=3 AND sit='5v5' AND team_id='MTL'",
            c,
        )
        team_r = pd.read_sql_query(
            "SELECT * FROM team_stats WHERE season='20252026' AND stype=2 AND sit='5v5' AND team_id='MTL'",
            c,
        )
    if sk_p.empty or sk_r.empty or team_p.empty or team_r.empty:
        return {"status": "missing_data"}
    toi_t_p = float(team_p["toi"].iloc[0]); xgf_t_p = float(team_p["xgf"].iloc[0]); xga_t_p = float(team_p["xga"].iloc[0])
    toi_t_r = float(team_r["toi"].iloc[0]); xgf_t_r = float(team_r["xgf"].iloc[0]); xga_t_r = float(team_r["xga"].iloc[0])

    def iso(toi_on, xg_on, toi_team, xg_team):
        toi_off = max(toi_team - toi_on, 0.0)
        if toi_on <= 0 or toi_off <= 0:
            return None
        return (xg_on * 60 / toi_on) - (max(xg_team - xg_on, 0.0) * 60 / toi_off)

    rows = []
    for nm in sk_p["name"].unique():
        rp = sk_p[sk_p["name"] == nm].iloc[0]
        rr_match = sk_r[sk_r["name"] == nm]
        if rr_match.empty:
            continue
        rr = rr_match.iloc[0]
        toi_p = float(rp["toi"]); toi_r = float(rr["toi"])
        if toi_p < 15.0 or toi_r < 200.0:  # exclude tiny samples
            continue
        iso_xgf_p = iso(toi_p, float(rp["xgf"]), toi_t_p, xgf_t_p)
        iso_xga_p = iso(toi_p, float(rp["xga"]), toi_t_p, xga_t_p)
        iso_xgf_r = iso(toi_r, float(rr["xgf"]), toi_t_r, xgf_t_r)
        iso_xga_r = iso(toi_r, float(rr["xga"]), toi_t_r, xga_t_r)
        if None in (iso_xgf_p, iso_xga_p, iso_xgf_r, iso_xga_r):
            continue
        rows.append({
            "name": nm, "position": rp["position"],
            "toi_p": toi_p, "toi_r": toi_r,
            "iso_xgf60_r": iso_xgf_r, "iso_xga60_r": iso_xga_r, "net_r": iso_xgf_r - iso_xga_r,
            "iso_xgf60_p": iso_xgf_p, "iso_xga60_p": iso_xga_p, "net_p": iso_xgf_p - iso_xga_p,
            "delta_net": (iso_xgf_p - iso_xga_p) - (iso_xgf_r - iso_xga_r),
        })
    df = pd.DataFrame(rows).sort_values("delta_net", ascending=False)
    return {
        "status": "ok",
        "movers_up": df.head(6).to_dict(orient="records"),
        "movers_down": df.tail(6).iloc[::-1].to_dict(orient="records"),
        "all": df.to_dict(orient="records"),
    }


# =====================================================================
# Lineup combos from shift chart (G2 vs G3)
# =====================================================================
def line_combos_from_shifts(game_id: str, team_abbrev: str, top_n: int = 10) -> list[dict]:
    """Identify the most common 5-man on-ice combinations in a game by overlapping shift time."""
    shifts = fetch_shifts(game_id)
    team_shifts = [s for s in shifts if s.get("teamAbbrev") == team_abbrev]
    if not team_shifts:
        return []
    presence: dict[tuple[int, int], list[int]] = {}
    for s in team_shifts:
        p = s.get("period")
        start = time_to_sec(s.get("startTime"))
        end = time_to_sec(s.get("endTime"))
        pid = s.get("playerId")
        for sec in range(start, end):
            presence.setdefault((p, sec), []).append(pid)
    from collections import Counter
    combo_counter: Counter = Counter()
    for (p, sec), pids in presence.items():
        if len(pids) == 5:
            combo_counter[tuple(sorted(pids))] += 1
    name_by_pid = {s.get("playerId"): f"{s.get('firstName','')} {s.get('lastName','')}".strip() for s in team_shifts}
    out = []
    for combo, sec in combo_counter.most_common(top_n):
        out.append({
            "players": [name_by_pid.get(pid, str(pid)) for pid in combo],
            "toi_sec": sec,
            "toi_min": round(sec / 60, 2),
        })
    return out


def forward_line_combos(game_id: str, team_abbrev: str, top_n: int = 8) -> list[dict]:
    """Identify the most-deployed 3-forward combinations (forward lines) in a game.

    Detection: filter shifts to non-defensemen/non-goalies via the NHL position
    information embedded in shift records (when available); else heuristic.
    Returns top combos by total seconds played as a 3-forward unit.
    """
    shifts = fetch_shifts(game_id)
    team_shifts = [s for s in shifts if s.get("teamAbbrev") == team_abbrev]
    if not team_shifts:
        return []
    # Get player roster from PBP (which has positions)
    pbp = fetch_pbp(game_id)
    player_pos = {}
    for player_block_key in ("rosterSpots",):
        for sp in (pbp.get(player_block_key) or []):
            pid = sp.get("playerId")
            pos = (sp.get("positionCode") or "").upper()
            if pid:
                player_pos[pid] = pos
    # Filter to forwards
    forward_pids = {pid for pid, pos in player_pos.items() if pos in ("C", "L", "R")}
    presence: dict[tuple[int, int], list[int]] = {}
    for s in team_shifts:
        pid = s.get("playerId")
        if pid not in forward_pids:
            continue
        p = s.get("period")
        start = time_to_sec(s.get("startTime"))
        end = time_to_sec(s.get("endTime"))
        for sec in range(start, end):
            presence.setdefault((p, sec), []).append(pid)
    from collections import Counter
    combo_counter: Counter = Counter()
    for (p, sec), pids in presence.items():
        if len(pids) == 3:
            combo_counter[tuple(sorted(pids))] += 1
    name_by_pid = {s.get("playerId"): f"{s.get('firstName','')} {s.get('lastName','')}".strip() for s in team_shifts}
    out = []
    for combo, sec in combo_counter.most_common(top_n):
        out.append({
            "players": [name_by_pid.get(pid, str(pid)) for pid in combo],
            "toi_sec": sec,
            "toi_min": round(sec / 60, 2),
        })
    return out


def detect_lineup_drift(prev_combos: list[dict], curr_combos: list[dict]) -> dict:
    """Compare top forward-line combos between two games and surface what changed."""
    def to_set(combo):
        return frozenset(combo["players"])

    prev_top = [to_set(c) for c in prev_combos[:6]]
    curr_top = [to_set(c) for c in curr_combos[:6]]

    persisted = [list(t) for t in curr_top if t in prev_top]
    new_lines = [list(t) for t in curr_top if t not in prev_top]
    dropped_lines = [list(t) for t in prev_top if t not in curr_top]

    return {
        "persisted": persisted,
        "new_lines": new_lines,
        "dropped_lines": dropped_lines,
        "n_persisted": len(persisted),
        "n_new": len(new_lines),
        "n_dropped": len(dropped_lines),
        "summary": (
            "no significant change" if len(persisted) >= 5
            else "minor reshuffle" if len(persisted) >= 3
            else "major reshuffle"
        ),
    }


# =====================================================================
# Top-level orchestrator
# =====================================================================
def compute_all() -> dict:
    out = {"meta": {"date": "2026-04-25", "series": "MTL vs TBL Round 1 2026", "after_game": 3}}

    # Per-game team stats from PBP
    out["per_game"] = {}
    for label, info in NHL_GAMES.items():
        out["per_game"][label] = game_level_team_stats(info["id"])
        out["per_game"][label]["meta"] = info

    # Slafkovsky per-game
    out["slafkovsky_per_game"] = {label: slaf_per_game(label, info["id"]) for label, info in NHL_GAMES.items()}

    # Slafkovsky pre/post Hagel fight buckets (fight: G2 P2 5:14)
    FIGHT_PERIOD = 2
    FIGHT_SEC = 5 * 60 + 14
    out["slaf_fight_buckets"] = slaf_pre_post_fight(FIGHT_PERIOD, FIGHT_SEC)

    # Series-level NST 5v5 + 5v4
    for sit in ("5v5", "5v4"):
        df = series_team_stats(sit)
        if df.empty:
            out[f"series_{sit}"] = {"status": "missing"}
            continue
        out[f"series_{sit}"] = {
            r["team_id"]: {
                k: r.get(k) for k in
                ["gp", "toi", "cf", "ca", "cf_pct", "ff", "fa", "ff_pct",
                 "sf", "sa", "sf_pct", "gf", "ga", "gf_pct",
                 "xgf", "xga", "xgf_pct", "scf", "sca", "scf_pct",
                 "hdcf", "hdca", "hdcf_pct", "pdo"]
            }
            for _, r in df.iterrows()
        }

    # MTL player progression (regular season → playoffs)
    out["mtl_progression"] = mtl_player_progression()

    # Lineup combos from G2 and G3 (5-skater on-ice slices)
    out["mtl_g2_combos"] = line_combos_from_shifts(NHL_GAMES["G2"]["id"], "MTL", top_n=6)
    out["mtl_g3_combos"] = line_combos_from_shifts(NHL_GAMES["G3"]["id"], "MTL", top_n=6)
    out["tbl_g2_combos"] = line_combos_from_shifts(NHL_GAMES["G2"]["id"], "TBL", top_n=6)
    out["tbl_g3_combos"] = line_combos_from_shifts(NHL_GAMES["G3"]["id"], "TBL", top_n=6)

    # Forward-only line combos (3-forward overlaps) and drift detection
    mtl_g2_fwd = forward_line_combos(NHL_GAMES["G2"]["id"], "MTL", top_n=8)
    mtl_g3_fwd = forward_line_combos(NHL_GAMES["G3"]["id"], "MTL", top_n=8)
    tbl_g2_fwd = forward_line_combos(NHL_GAMES["G2"]["id"], "TBL", top_n=8)
    tbl_g3_fwd = forward_line_combos(NHL_GAMES["G3"]["id"], "TBL", top_n=8)
    out["mtl_g2_forward_lines"] = mtl_g2_fwd
    out["mtl_g3_forward_lines"] = mtl_g3_fwd
    out["tbl_g2_forward_lines"] = tbl_g2_fwd
    out["tbl_g3_forward_lines"] = tbl_g3_fwd
    out["mtl_lineup_drift_g2_to_g3"] = detect_lineup_drift(mtl_g2_fwd, mtl_g3_fwd)
    out["tbl_lineup_drift_g2_to_g3"] = detect_lineup_drift(tbl_g2_fwd, tbl_g3_fwd)

    return out


def to_jsonable(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return str(o)


def sanitize(o):
    """Recursively replace NaN/inf floats with None so the JSON is strict-valid."""
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
        return o
    if isinstance(o, dict):
        return {k: sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(x) for x in o]
    return o


if __name__ == "__main__":
    data = sanitize(compute_all())
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=to_jsonable, ensure_ascii=False, allow_nan=False)
    print(f"wrote {OUT_JSON}")
    # Quick summary
    print("\n=== SLAFKOVSKY PER GAME (5v5+) ===")
    for label, d in data["slafkovsky_per_game"].items():
        print(f"  {label}: TOI={d['toi_min']}m  shifts={d['shifts']}  SOG={d['slaf_sog']}  G={d['slaf_goals']}  on-ice MTL/TBL SOG={d['mtl_sog_oi']}/{d['tbl_sog_oi']}")
    print("\n=== SERIES TEAM (5v5) ===")
    s = data.get("series_5v5", {})
    for t, vals in s.items():
        if isinstance(vals, dict):
            print(f"  {t}: GP={vals.get('gp')}  CF%={vals.get('cf_pct'):.2f}  xGF%={vals.get('xgf_pct'):.2f}  HDCF%={vals.get('hdcf_pct'):.2f}  PDO={vals.get('pdo')}")
    print("\n=== PER-GAME TEAM ===")
    for label, d in data["per_game"].items():
        print(f"  {label}: {d['away']} @ {d['home']}  SOG {d['away_sog']}-{d['home_sog']}  CF% home={d['home_cf_pct']:.1f}  hits {d['away_hits']}/{d['home_hits']}")
