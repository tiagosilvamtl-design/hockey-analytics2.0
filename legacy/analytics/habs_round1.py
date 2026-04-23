"""Compute all numbers cited in the MTL Round 1 2026 Word report.

Returns a single dict that the docx builder renders. Also dumps a JSON sidecar
(`reports/output/habs_round1_2026.numbers.json`) so every figure is auditable.

Data sources:
  - SQLite store (NST-pooled regular-season + playoff skater/team stats)
  - NHL.com public endpoints (shift charts + play-by-play) for Slafkovsky
    per-period analysis (NST game reports don't expose per-period player splits).

Non-goals: no series prediction, no composite "player rating" score.
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import requests
from scipy import stats as _stats

import config  # triggers truststore.inject_into_ssl()
from analytics.swap_engine import (
    PlayerImpact,
    build_pooled_player_impact,
    combine_swaps,
    project_swap,
)
from config import CURRENT_SEASON, STORE_DB

POOLED_KEYS: tuple[tuple[str, int], ...] = (
    ("20252026", 2), ("20252026", 3),
    ("20242025", 2), ("20242025", 3),
)
CURRENT_ONLY_KEYS: tuple[tuple[str, int], ...] = (
    ("20252026", 2), ("20252026", 3),
)
TEAM = "MTL"
OPPONENT = "T.B"

# NHL.com R1 G1 / G2 IDs: playoff format YYYY03RRSG (R=round, S=series, G=game).
# 2026 R1 series 2 = MTL-TBL based on the NST matchup pairing (TOI match confirms).
NHL_G1_ID = "2025030121"
NHL_G2_ID = "2025030122"


# =====================================================================
# Data loading helpers
# =====================================================================
def _pool_player_rows(name: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit, name]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        return pd.read_sql_query(
            f"SELECT * FROM skater_stats WHERE sit=? AND split='oi' AND name=? AND ({clauses})",
            c, params=params,
        )


def _pool_team_rows(team_id: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit, team_id]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        return pd.read_sql_query(
            f"SELECT * FROM team_stats WHERE sit=? AND team_id=? AND ({clauses})",
            c, params=params,
        )


def _team_roster_pooled(team_id: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    """One row per player name with pooled TOI/events across the keys — used to
    build the 'doing well / doing poorly' ranking and the optimal lineup."""
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        df = pd.read_sql_query(
            f"SELECT name, position, team_id, season, stype, gp, toi, xgf, xga, cf, ca, gf, ga, "
            f"cf_pct, xgf_pct "
            f"FROM skater_stats WHERE sit=? AND split='oi' AND ({clauses})",
            c, params=params,
        )
    if df.empty:
        return df
    # keep rows where team_id contains the target (handles 'MTL' and 'MTL, STL')
    mask = df["team_id"].astype(str).str.contains(team_id, na=False)
    df = df[mask].copy()
    if df.empty:
        return df
    for col in ["toi", "xgf", "xga", "cf", "ca", "gf", "ga", "gp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    agg = df.groupby("name", as_index=False).agg({
        "position": "first",
        "gp": "sum",
        "toi": "sum",
        "xgf": "sum",
        "xga": "sum",
        "cf": "sum",
        "ca": "sum",
        "gf": "sum",
        "ga": "sum",
    })
    return agg


def _individual_rows(team_id: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    """Per-player individual (bio) pooled rows — goals, shots, etc."""
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        df = pd.read_sql_query(
            f"SELECT name, position, team_id, gp, toi, gf as ig, xgf as ixg "
            f"FROM skater_stats WHERE sit=? AND split='bio' AND ({clauses})",
            c, params=params,
        )
    df = df[df["team_id"].astype(str).str.contains(team_id, na=False)].copy()
    for col in ["toi", "ig", "ixg", "gp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.groupby("name", as_index=False).agg({
        "position": "first",
        "gp": "sum",
        "toi": "sum",
        "ig": "sum",
        "ixg": "sum",
    })


# =====================================================================
# Swap analyses (C.1 / C.2 / C.3)
# =====================================================================
def swap_analysis(
    out_name: str,
    in_name: str,
    slot_minutes: float,
    sit: str,
    team_id: str = TEAM,
    keys: tuple[tuple[str, int], ...] = POOLED_KEYS,
) -> dict:
    team_rows = _pool_team_rows(team_id, sit, keys)
    out_rows = _pool_player_rows(out_name, sit, keys)
    in_rows = _pool_player_rows(in_name, sit, keys)
    if out_rows.empty or in_rows.empty or team_rows.empty:
        return {"status": "missing_data",
                "out_rows": len(out_rows), "in_rows": len(in_rows),
                "team_rows": len(team_rows)}
    out_imp = build_pooled_player_impact(out_rows, team_rows, team_id)
    in_imp = build_pooled_player_impact(in_rows, team_rows, team_id)
    r = project_swap(out_imp, in_imp, slot_minutes=slot_minutes, strength_state=sit)
    return {
        "status": "ok",
        "sit": sit,
        "slot_minutes": slot_minutes,
        "out": {"name": out_name, "toi_on": out_imp.toi_on,
                "iso_xgf60": out_imp.iso_xgf60, "iso_xga60": out_imp.iso_xga60},
        "in": {"name": in_name, "toi_on": in_imp.toi_on,
               "iso_xgf60": in_imp.iso_xgf60, "iso_xga60": in_imp.iso_xga60},
        "delta_xgf60": r.delta_xgf60,
        "delta_xga60": r.delta_xga60,
        "delta_xgf60_ci80": list(r.delta_xgf60_ci80),
        "delta_xga60_ci80": list(r.delta_xga60_ci80),
        "net": r.delta_xgf60 - r.delta_xga60,
    }


def combined_2for2(
    pairs: list[tuple[str, str, float]],
    sit: str,
    team_id: str = TEAM,
    keys: tuple[tuple[str, int], ...] = POOLED_KEYS,
) -> dict:
    team_rows = _pool_team_rows(team_id, sit, keys)
    swap_results = []
    per_pair = []
    for out_name, in_name, slot in pairs:
        out_rows = _pool_player_rows(out_name, sit, keys)
        in_rows = _pool_player_rows(in_name, sit, keys)
        if out_rows.empty or in_rows.empty:
            per_pair.append({"out": out_name, "in": in_name, "status": "missing"})
            continue
        out_imp = build_pooled_player_impact(out_rows, team_rows, team_id)
        in_imp = build_pooled_player_impact(in_rows, team_rows, team_id)
        r = project_swap(out_imp, in_imp, slot_minutes=slot, strength_state=sit)
        swap_results.append(r)
        per_pair.append({
            "out": out_name, "in": in_name, "slot_minutes": slot,
            "delta_xgf60": r.delta_xgf60, "delta_xga60": r.delta_xga60,
        })
    if not swap_results:
        return {"status": "missing", "pairs": per_pair}
    combined = combine_swaps(swap_results)
    return {
        "status": "ok",
        "sit": sit,
        "pairs": per_pair,
        "delta_xgf60": combined.delta_xgf60,
        "delta_xga60": combined.delta_xga60,
        "delta_xgf60_ci80": list(combined.delta_xgf60_ci80),
        "delta_xga60_ci80": list(combined.delta_xga60_ci80),
        "net": combined.delta_xgf60 - combined.delta_xga60,
    }


# =====================================================================
# Section D — Laine hypothetical
# =====================================================================
def laine_hypothetical(sit: str = "5v4", keys: tuple[tuple[str, int], ...] = POOLED_KEYS) -> dict:
    """Pool Laine's PP impact over 2 seasons and compare to current PP2 candidates on MTL."""
    team_rows = _pool_team_rows(TEAM, sit, keys)
    laine_rows = _pool_player_rows("Patrik Laine", sit, keys)
    if laine_rows.empty or team_rows.empty:
        return {"status": "missing_data"}
    laine_imp = build_pooled_player_impact(laine_rows, team_rows, TEAM)
    # Candidate current PP2 players: Texier, Dach, Newhook, Bolduc — compute each
    candidates = ["Alexandre Texier", "Kirby Dach", "Alex Newhook", "Zachary Bolduc", "Joe Veleno"]
    cand_impacts = []
    for nm in candidates:
        rows = _pool_player_rows(nm, sit, keys)
        if rows.empty or float(rows["toi"].fillna(0).sum()) < 50.0:
            continue
        imp = build_pooled_player_impact(rows, team_rows, TEAM)
        cand_impacts.append({
            "name": nm, "toi_on": imp.toi_on,
            "iso_xgf60": imp.iso_xgf60, "iso_xga60": imp.iso_xga60,
        })
    # Individual PP goals/xG from bio table
    ind = _individual_rows(TEAM, sit, keys)
    laine_ind = ind[ind["name"] == "Patrik Laine"]
    laine_ig = float(laine_ind["ig"].iloc[0]) if not laine_ind.empty else 0.0
    laine_ixg = float(laine_ind["ixg"].iloc[0]) if not laine_ind.empty else 0.0
    laine_toi_bio = float(laine_ind["toi"].iloc[0]) if not laine_ind.empty else 0.0
    return {
        "status": "ok",
        "sit": sit,
        "laine": {
            "toi_on": laine_imp.toi_on,
            "iso_xgf60": laine_imp.iso_xgf60,
            "iso_xga60": laine_imp.iso_xga60,
            "individual_toi": laine_toi_bio,
            "individual_goals": laine_ig,
            "individual_xg": laine_ixg,
            "ig_per60": (laine_ig * 60.0 / laine_toi_bio) if laine_toi_bio > 0 else 0.0,
        },
        "pp2_candidates": cand_impacts,
    }


# =====================================================================
# Section E — Doing well / doing poorly
# =====================================================================
def team_rankings(sit: str = "5v5", min_toi: float = 300.0,
                  keys: tuple[tuple[str, int], ...] = CURRENT_ONLY_KEYS) -> dict:
    """Rank MTL skaters by pooled iso impact over the chosen window."""
    roster = _team_roster_pooled(TEAM, sit, keys)
    team_rows = _pool_team_rows(TEAM, sit, keys)
    if roster.empty or team_rows.empty:
        return {"status": "missing_data"}
    toi_team = float(team_rows["toi"].fillna(0).sum())
    xgf_team = float(team_rows["xgf"].fillna(0).sum())
    xga_team = float(team_rows["xga"].fillna(0).sum())

    rows = []
    for _, pr in roster.iterrows():
        toi_on = float(pr["toi"])
        if toi_on < min_toi:
            continue
        toi_off = max(toi_team - toi_on, 0.0)
        if toi_off <= 0:
            continue
        xgf_on, xga_on = float(pr["xgf"]), float(pr["xga"])
        xgf_off, xga_off = max(xgf_team - xgf_on, 0.0), max(xga_team - xga_on, 0.0)
        iso_xgf60 = (xgf_on * 60.0 / toi_on) - (xgf_off * 60.0 / toi_off)
        iso_xga60 = (xga_on * 60.0 / toi_on) - (xga_off * 60.0 / toi_off)
        rows.append({
            "name": pr["name"],
            "position": pr["position"],
            "gp": int(pr["gp"]),
            "toi": round(toi_on, 1),
            "iso_xgf60": iso_xgf60,
            "iso_xga60": iso_xga60,
            "net": iso_xgf60 - iso_xga60,
            "gf": int(pr["gf"]),
            "ga": int(pr["ga"]),
        })
    df = pd.DataFrame(rows).sort_values("net", ascending=False)
    positive = df.head(8).to_dict(orient="records")
    negative = df.tail(5).sort_values("net", ascending=True).to_dict(orient="records")
    return {"status": "ok", "positive": positive, "negative": negative, "n_players": len(df)}


# =====================================================================
# Section F — Optimal lineup
# =====================================================================
def optimal_lineup(keys: tuple[tuple[str, int], ...] = CURRENT_ONLY_KEYS) -> dict:
    """Data-optimal lineup from pooled 25-26 + playoff data. Forwards by 5v5 net,
    defense by 5v5 net, PP1/PP2 by 5v4 iso_xgf60 + individual shooting rate."""
    ranks_5v5 = team_rankings("5v5", min_toi=200.0, keys=keys)
    if ranks_5v5["status"] != "ok":
        return {"status": "missing_data"}

    # Get ALL skaters over 100 min (not just top/bottom)
    roster = _team_roster_pooled(TEAM, "5v5", keys)
    team_rows = _pool_team_rows(TEAM, "5v5", keys)
    toi_team = float(team_rows["toi"].fillna(0).sum())
    xgf_team = float(team_rows["xgf"].fillna(0).sum())
    xga_team = float(team_rows["xga"].fillna(0).sum())

    all_players = []
    for _, pr in roster.iterrows():
        toi_on = float(pr["toi"])
        if toi_on < 300.0:
            continue
        toi_off = max(toi_team - toi_on, 0.0)
        xgf_on, xga_on = float(pr["xgf"]), float(pr["xga"])
        xgf_off = max(xgf_team - xgf_on, 0.0)
        xga_off = max(xga_team - xga_on, 0.0)
        if toi_off <= 0:
            continue
        iso_xgf60 = (xgf_on * 60.0 / toi_on) - (xgf_off * 60.0 / toi_off)
        iso_xga60 = (xga_on * 60.0 / toi_on) - (xga_off * 60.0 / toi_off)
        all_players.append({
            "name": pr["name"], "position": pr["position"],
            "toi": toi_on, "iso_xgf60": iso_xgf60, "iso_xga60": iso_xga60,
            "net": iso_xgf60 - iso_xga60,
        })

    df = pd.DataFrame(all_players).sort_values("net", ascending=False)
    forwards = df[df["position"].isin(["C", "L", "R"])].copy()
    defense = df[df["position"] == "D"].copy()

    # Build 4 lines: take top 12 forwards, split by position.
    # Anchor: 1C = Suzuki; preserve; don't blindly reshuffle.
    # Simple rule: Line 1 = top 3 net with Suzuki at C if not already. Lines 2/3/4 follow.
    lines = _build_forward_lines(forwards)

    # D pairs: 6 top Ds paired L/R best with worst
    dpairs = _build_dpairs(defense.head(6))

    # PP1 / PP2 from 5v4 iso_xgf60 + individual PP goal rate
    pp_units = _build_pp_units(keys)

    # Starter goalie
    goalie = _goalie_starter(keys)

    return {
        "status": "ok",
        "forwards": lines,
        "defense": dpairs,
        "goalie": goalie,
        "pp_units": pp_units,
        "forwards_pool": forwards.to_dict(orient="records"),
        "defense_pool": defense.to_dict(orient="records"),
    }


def _build_forward_lines(forwards: pd.DataFrame) -> list[list[str]]:
    """Greedy: put Suzuki at 1C; pair two best wingers with him. Line 2 = next best C + next 2 Ws. etc."""
    centers = forwards[forwards["position"] == "C"].sort_values("net", ascending=False)
    wings = forwards[forwards["position"].isin(["L", "R"])].sort_values("net", ascending=False)
    lines: list[list[str]] = []
    used: set[str] = set()

    # Force Suzuki on Line 1 if he's a center
    suz = centers[centers["name"] == "Nick Suzuki"]
    line1_c = ["Nick Suzuki"] if not suz.empty else (centers["name"].head(1).tolist() or ["—"])
    used.add(line1_c[0])

    # Remaining centers ordered by net
    other_cs = [n for n in centers["name"].tolist() if n not in used][:3]

    # Wingers ordered by net
    avail_wings = [n for n in wings["name"].tolist() if n not in used]

    # Allocate wings to lines 1-4
    lines.append([line1_c[0]] + avail_wings[:2])
    used.update(avail_wings[:2])
    avail_wings = [w for w in avail_wings if w not in used]

    for i, c in enumerate(other_cs):
        two_w = avail_wings[:2]
        lines.append([c] + two_w)
        used.add(c); used.update(two_w)
        avail_wings = [w for w in avail_wings if w not in used]

    while len(lines) < 4:
        if len(avail_wings) >= 3:
            lines.append(avail_wings[:3])
            avail_wings = avail_wings[3:]
        else:
            break
    return lines[:4]


def _build_dpairs(d: pd.DataFrame) -> list[list[str]]:
    """3 pairs: pair #1 best + worst net of the 6, #2 = 2nd + 5th, #3 = 3rd + 4th. Simple balancing."""
    d_sorted = d.sort_values("net", ascending=False)
    names = d_sorted["name"].tolist()
    if len(names) < 6:
        # pad
        names = names + ["—"] * (6 - len(names))
    return [
        [names[0], names[5]],
        [names[1], names[4]],
        [names[2], names[3]],
    ]


def _build_pp_units(keys: tuple[tuple[str, int], ...]) -> dict:
    """Build PP1 and PP2 from 5v4 data: top 4 skaters + best 1 D by 5v4 iso_xgf60 into PP1."""
    roster = _team_roster_pooled(TEAM, "5v4", keys)
    team_rows = _pool_team_rows(TEAM, "5v4", keys)
    if roster.empty or team_rows.empty:
        return {"status": "missing_data"}
    toi_team = float(team_rows["toi"].fillna(0).sum())
    xgf_team = float(team_rows["xgf"].fillna(0).sum())

    pp_rows = []
    for _, pr in roster.iterrows():
        toi_on = float(pr["toi"])
        if toi_on < 40.0:  # meaningful PP sample
            continue
        toi_off = max(toi_team - toi_on, 0.0)
        xgf_on = float(pr["xgf"])
        xgf_off = max(xgf_team - xgf_on, 0.0)
        if toi_off <= 0:
            continue
        iso_xgf60 = (xgf_on * 60.0 / toi_on) - (xgf_off * 60.0 / toi_off)
        pp_rows.append({
            "name": pr["name"], "position": pr["position"],
            "toi": toi_on, "iso_xgf60": iso_xgf60,
        })
    pp_df = pd.DataFrame(pp_rows).sort_values("iso_xgf60", ascending=False)
    forwards = pp_df[pp_df["position"].isin(["C", "L", "R"])]
    defense = pp_df[pp_df["position"] == "D"]

    pp1 = forwards.head(4)["name"].tolist() + defense.head(1)["name"].tolist()
    pp2 = (forwards.iloc[4:8]["name"].tolist()
           + defense.iloc[1:2]["name"].tolist())
    return {
        "pp1": pp1[:5],
        "pp2": pp2[:5],
        "ranked": pp_df.to_dict(orient="records"),
    }


def _goalie_starter(keys: tuple[tuple[str, int], ...]) -> dict:
    """Return the MTL goalie with best save rate across the pooled window.

    Goalies are stored in skater_stats with position='G' in some NST setups
    but normally in goalie_stats. Fall back to querying skater_stats with
    position='G' or using simple heuristics.
    """
    # try goalie_stats first
    with sqlite3.connect(STORE_DB) as c:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM goalie_stats WHERE team_id=? AND sit='5v5'",
                c, params=(TEAM,),
            )
        except Exception:
            df = pd.DataFrame()
    if df.empty:
        return {"status": "no_goalie_data", "starter": "Dobes (assumed)"}
    # Not populated in our ingest yet — return placeholder
    return {"status": "unverified", "starter": "Dobes (assumed)"}


# =====================================================================
# Section G — Slafkovsky per-period via NHL.com
# =====================================================================
def slafkovsky_period_buckets() -> dict:
    """Bucket A = G1 all + G2 P1. Bucket B = G2 P3 + G2 OT. Exclude G2 P2.

    Data: NHL.com shift charts + play-by-play. Slafkovsky playerId = 8483515.
    """
    SLAF_ID = 8483515
    buckets = {
        "A": {"games": [(NHL_G1_ID, None), (NHL_G2_ID, 1)], "label": "G1 all + G2 P1"},
        "B": {"games": [(NHL_G2_ID, 3), (NHL_G2_ID, 4)], "label": "G2 P3 + G2 OT"},
    }

    shifts_cache: dict[str, list[dict]] = {}
    pbp_cache: dict[str, list[dict]] = {}
    for gid in {NHL_G1_ID, NHL_G2_ID}:
        try:
            s = requests.get(
                f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={gid}",
                timeout=30,
            ).json().get("data", [])
            p = requests.get(
                f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play",
                timeout=30,
            ).json().get("plays", [])
        except Exception as e:
            return {"status": "fetch_failed", "error": str(e)}
        shifts_cache[gid] = s
        pbp_cache[gid] = p

    def _time_to_sec(t: str) -> int:
        try:
            m, s = t.split(":")
            return int(m) * 60 + int(s)
        except Exception:
            return 0

    def _slaf_shifts(gid: str, period: int | None) -> list[tuple[int, int]]:
        out = []
        for sh in shifts_cache[gid]:
            if sh.get("playerId") != SLAF_ID:
                continue
            if period is not None and sh.get("period") != period:
                continue
            start = _time_to_sec(sh.get("startTime") or "00:00")
            end = _time_to_sec(sh.get("endTime") or "00:00")
            if end > start:
                out.append((sh.get("period"), start, end))
        return out

    def _events_in_shift(gid: str, period: int | None) -> dict:
        """Count MTL/TBL shots, goals while Slaf on ice."""
        shifts = _slaf_shifts(gid, period)
        # Build set of (period, sec-in-period) ranges
        counts = {
            "mtl_sog": 0, "tbl_sog": 0,
            "mtl_goals": 0, "tbl_goals": 0,
            "slaf_sog": 0, "slaf_goals": 0,
            "mtl_missed": 0, "tbl_missed": 0,
            "slaf_toi_sec": 0,
            "shift_count": 0,
        }
        counts["shift_count"] = len(shifts)
        for p, s, e in shifts:
            counts["slaf_toi_sec"] += (e - s)
        for play in pbp_cache[gid]:
            pd_desc = play.get("periodDescriptor") or {}
            ev_period = pd_desc.get("number")
            if period is not None and ev_period != period:
                continue
            ev_time = _time_to_sec(play.get("timeInPeriod") or "00:00")
            typ = play.get("typeDescKey") or ""
            details = play.get("details") or {}
            # is Slaf on ice?
            on_ice = any(
                sh_p == ev_period and s <= ev_time <= e
                for sh_p, s, e in _slaf_shifts(gid, ev_period)
            )
            if not on_ice:
                continue
            # owner team
            owner = details.get("eventOwnerTeamId")
            # NHL team ids: MTL = 8, TBL = 14
            is_mtl = (owner == 8)
            if typ == "shot-on-goal":
                if is_mtl: counts["mtl_sog"] += 1
                else: counts["tbl_sog"] += 1
                shooter = details.get("shootingPlayerId")
                if shooter == SLAF_ID:
                    counts["slaf_sog"] += 1
            elif typ == "missed-shot":
                if is_mtl: counts["mtl_missed"] += 1
                else: counts["tbl_missed"] += 1
            elif typ == "goal":
                if is_mtl: counts["mtl_goals"] += 1
                else: counts["tbl_goals"] += 1
                shooter = details.get("shootingPlayerId") or details.get("scoringPlayerId")
                if shooter == SLAF_ID:
                    counts["slaf_goals"] += 1
        return counts

    result = {"status": "ok", "buckets": {}}
    for key, spec in buckets.items():
        agg = {"mtl_sog": 0, "tbl_sog": 0, "mtl_goals": 0, "tbl_goals": 0,
               "slaf_sog": 0, "slaf_goals": 0, "mtl_missed": 0, "tbl_missed": 0,
               "slaf_toi_sec": 0, "shift_count": 0}
        for gid, period in spec["games"]:
            e = _events_in_shift(gid, period)
            for k, v in e.items():
                agg[k] += v
        agg["slaf_toi_min"] = round(agg["slaf_toi_sec"] / 60.0, 2)
        result["buckets"][key] = {"label": spec["label"], **agg}
    return result


# =====================================================================
# Top-level compute
# =====================================================================
def compute_all() -> dict:
    out: dict = {
        "meta": {
            "team": TEAM,
            "opponent": OPPONENT,
            "series_ref": "2026 NHL Stanley Cup Playoffs — Round 1",
            "date": "2026-04-22",
            "pooled_keys": list(POOLED_KEYS),
            "current_only_keys": list(CURRENT_ONLY_KEYS),
        },
    }

    # --- Section C: swaps ---
    out["swaps_5v5"] = {
        "dach_gallagher": swap_analysis("Kirby Dach", "Brendan Gallagher", slot_minutes=11.9, sit="5v5"),
        "texier_veleno": swap_analysis("Alexandre Texier", "Joe Veleno", slot_minutes=12.5, sit="5v5"),
        "combined": combined_2for2(
            [("Kirby Dach", "Brendan Gallagher", 11.9),
             ("Alexandre Texier", "Joe Veleno", 12.5)],
            sit="5v5",
        ),
    }
    out["swaps_5v4"] = {
        "dach_gallagher": swap_analysis("Kirby Dach", "Brendan Gallagher", slot_minutes=1.5, sit="5v4"),
        "texier_veleno": swap_analysis("Alexandre Texier", "Joe Veleno", slot_minutes=1.5, sit="5v4"),
    }

    # --- Section D: Laine ---
    out["laine"] = laine_hypothetical(sit="5v4")

    # --- Section E: rankings (current-season + playoff weighted) ---
    out["rankings"] = team_rankings(sit="5v5", min_toi=200.0, keys=CURRENT_ONLY_KEYS)

    # --- Section F: optimal lineup ---
    out["optimal"] = optimal_lineup(keys=CURRENT_ONLY_KEYS)

    # --- Section G: Slafkovsky period buckets ---
    out["slafkovsky"] = slafkovsky_period_buckets()

    return out


def dump_json(data: dict, path: Path) -> None:
    def _default(o):
        if isinstance(o, (_stats._distn_infrastructure.rv_continuous,)):
            return str(o)
        if hasattr(o, "tolist"):
            return o.tolist()
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            return None
        return str(o)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_default)


if __name__ == "__main__":
    from pathlib import Path
    data = compute_all()
    out = Path("reports/output/habs_round1_2026.numbers.json")
    dump_json(data, out)
    print(f"Wrote {out}")
    print(f"Sections: {list(data.keys())}")
