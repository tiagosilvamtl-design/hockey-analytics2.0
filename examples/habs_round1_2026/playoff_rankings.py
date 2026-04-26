"""Habs playoff player rankings — analytics through Game N.

Produces a structured JSON of:
  - 5v5 iso-impact rankings (forwards + defense)
  - 5v4 iso-impact rankings (PP)
  - Individual goal production (from NHL.com PBP scoringPlayerId)
  - Goal-involvement counts (assists from PBP)
  - Comparison vs 2025-26 regular-season iso net
  - Goalies summary (Dobeš)

Data source: SQLite store (NST 5v5 / 5v4 playoff totals) + NHL.com PBP for
goalscorers and assist credits. Any prose in the rendered post must be
sourced from this JSON.
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

import truststore; truststore.inject_into_ssl()  # noqa: E702
import pandas as pd
import requests

sys.path.insert(0, "legacy")

STORE = Path("legacy/data/store.sqlite")
OUT_JSON = Path("examples/habs_round1_2026/playoff_rankings.numbers.json")
SEASON_CURRENT = "20252026"
TEAM = "MTL"
TEAM_ID_NHL = 8
NHL_GAMES = ["2025030121", "2025030122", "2025030123"]


# ---------- DB helpers ----------
def team_totals(sit: str, stype: int, season: str = SEASON_CURRENT) -> dict | None:
    with sqlite3.connect(STORE) as c:
        df = pd.read_sql_query(
            "SELECT * FROM team_stats WHERE season=? AND stype=? AND sit=? AND team_id=?",
            c, params=(season, stype, sit, TEAM),
        )
    return df.iloc[0].to_dict() if not df.empty else None


def skaters(sit: str, stype: int, split: str = "oi", season: str = SEASON_CURRENT) -> pd.DataFrame:
    with sqlite3.connect(STORE) as c:
        df = pd.read_sql_query(
            "SELECT * FROM skater_stats WHERE season=? AND stype=? AND sit=? AND split=? "
            "AND team_id LIKE ?",
            c, params=(season, stype, sit, split, f"%{TEAM}%"),
        )
    for col in ("toi", "xgf", "xga", "cf", "ca", "gf", "ga", "gp",
                "cf_pct", "xgf_pct", "hdcf", "hdca", "hdcf_pct"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def iso(toi_on: float, ev_on: float, toi_team: float, ev_team: float):
    toi_off = max(toi_team - toi_on, 0.0)
    if toi_on <= 0 or toi_off <= 0:
        return None
    ev_off = max(ev_team - ev_on, 0.0)
    return (ev_on * 60.0 / toi_on) - (ev_off * 60.0 / toi_off)


# ---------- Per-strength rankings ----------
def rank_at(sit: str, min_toi: float = 15.0) -> list[dict]:
    team = team_totals(sit, 3)
    if not team:
        return []
    sk = skaters(sit, 3, "oi")
    out = []
    for _, r in sk.iterrows():
        toi = float(r["toi"])
        if toi < min_toi:
            continue
        ix = iso(toi, float(r["xgf"]), float(team["toi"]), float(team["xgf"]))
        ig = iso(toi, float(r["xga"]), float(team["toi"]), float(team["xga"]))
        if ix is None or ig is None:
            continue
        out.append({
            "name": r["name"], "position": r["position"],
            "gp": int(r["gp"]), "toi": round(toi, 1),
            "iso_xgf60": ix, "iso_xga60": ig, "net": ix - ig,
            "cf_pct": float(r.get("cf_pct") or 0),
            "xgf_pct": float(r.get("xgf_pct") or 0),
            "hdcf_pct": float(r.get("hdcf_pct") or 0) if "hdcf_pct" in r else None,
        })
    return sorted(out, key=lambda x: x["net"], reverse=True)


# ---------- Individual production from PBP ----------
def fetch_pbp(game_id: str) -> dict:
    return requests.get(
        f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play", timeout=30
    ).json()


def individual_production() -> dict:
    """Per-MTL-player goals / primary assists / secondary assists / SOG across the playoff series."""
    counts: dict[str, dict] = {}
    rosters: dict[int, str] = {}
    for gid in NHL_GAMES:
        pbp = fetch_pbp(gid)
        for sp in pbp.get("rosterSpots") or []:
            pid = sp.get("playerId")
            if pid:
                first = (sp.get("firstName") or {}).get("default") or ""
                last = (sp.get("lastName") or {}).get("default") or ""
                rosters[pid] = f"{first} {last}".strip()
        for play in pbp.get("plays") or []:
            d = play.get("details") or {}
            owner = d.get("eventOwnerTeamId")
            if owner != TEAM_ID_NHL:
                continue
            typ = play.get("typeDescKey") or ""
            if typ == "goal":
                scorer = d.get("scoringPlayerId")
                a1 = d.get("assist1PlayerId")
                a2 = d.get("assist2PlayerId")
                if scorer:
                    name = rosters.get(scorer, str(scorer))
                    counts.setdefault(name, _zero())["g"] += 1
                if a1:
                    name = rosters.get(a1, str(a1))
                    counts.setdefault(name, _zero())["a1"] += 1
                if a2:
                    name = rosters.get(a2, str(a2))
                    counts.setdefault(name, _zero())["a2"] += 1
            elif typ == "shot-on-goal":
                sh = d.get("shootingPlayerId")
                if sh:
                    name = rosters.get(sh, str(sh))
                    counts.setdefault(name, _zero())["sog"] += 1
    rows = []
    for name, c in counts.items():
        c["points"] = c["g"] + c["a1"] + c["a2"]
        c["a"] = c["a1"] + c["a2"]
        c["name"] = name
        rows.append(c)
    return sorted(rows, key=lambda r: (-r["points"], -r["g"]))


def _zero() -> dict:
    return {"g": 0, "a1": 0, "a2": 0, "sog": 0}


# ---------- Goalie ----------
def goalie_summary() -> dict:
    """Compute Dobeš shots faced / GA / SV% across MTL playoff games."""
    shots_faced = 0
    goals_against = 0
    for gid in NHL_GAMES:
        pbp = fetch_pbp(gid)
        home_id = (pbp.get("homeTeam") or {}).get("id")
        away_id = (pbp.get("awayTeam") or {}).get("id")
        for play in pbp.get("plays") or []:
            d = play.get("details") or {}
            typ = play.get("typeDescKey") or ""
            owner = d.get("eventOwnerTeamId")
            # Shots / goals against MTL = events owned by the OPPOSING team
            if owner == TEAM_ID_NHL:
                continue
            if typ == "shot-on-goal":
                shots_faced += 1
            elif typ == "goal":
                shots_faced += 1
                goals_against += 1
    sv = (1 - goals_against / shots_faced) if shots_faced > 0 else 0
    return {
        "name": "Jakub Dobeš",
        "shots_faced": shots_faced,
        "goals_against": goals_against,
        "sv_pct": round(sv, 3),
        "games": len(NHL_GAMES),
    }


# ---------- Reg-season comparison ----------
def progression() -> list[dict]:
    """Compare each player's reg-season iso net to playoff iso net."""
    team_p = team_totals("5v5", 3)
    team_r = team_totals("5v5", 2)
    if not team_p or not team_r:
        return []
    sk_p = skaters("5v5", 3, "oi")
    sk_r = skaters("5v5", 2, "oi")
    rows = []
    for _, p in sk_p.iterrows():
        if float(p["toi"]) < 15.0:
            continue
        r_match = sk_r[sk_r["name"] == p["name"]]
        if r_match.empty or float(r_match.iloc[0]["toi"]) < 200.0:
            continue
        r = r_match.iloc[0]
        ixp = iso(float(p["toi"]), float(p["xgf"]), float(team_p["toi"]), float(team_p["xgf"]))
        igp = iso(float(p["toi"]), float(p["xga"]), float(team_p["toi"]), float(team_p["xga"]))
        ixr = iso(float(r["toi"]), float(r["xgf"]), float(team_r["toi"]), float(team_r["xgf"]))
        igr = iso(float(r["toi"]), float(r["xga"]), float(team_r["toi"]), float(team_r["xga"]))
        if None in (ixp, igp, ixr, igr):
            continue
        net_p, net_r = ixp - igp, ixr - igr
        rows.append({
            "name": p["name"], "position": p["position"],
            "toi_p": round(float(p["toi"]), 1), "toi_r": round(float(r["toi"]), 1),
            "net_r": net_r, "net_p": net_p, "delta": net_p - net_r,
        })
    return sorted(rows, key=lambda x: x["delta"], reverse=True)


# ---------- Top-level ----------
def compute_all() -> dict:
    out = {
        "meta": {
            "as_of": "2026-04-26",
            "team": TEAM,
            "games_played": 3,
            "series": "Round 1 vs TBL (MTL leads 2-1)",
            "min_toi_5v5": 15.0,
            "min_toi_5v4": 5.0,
        },
        "rank_5v5": rank_at("5v5", min_toi=15.0),
        "rank_5v4": rank_at("5v4", min_toi=5.0),
        "individual": individual_production(),
        "goalie": goalie_summary(),
        "progression": progression(),
    }
    return out


def sanitize(o):
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, dict):
        return {k: sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(x) for x in o]
    return o


if __name__ == "__main__":
    data = sanitize(compute_all())
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"wrote {OUT_JSON}")
    print(f"5v5 ranking: {len(data['rank_5v5'])} skaters (≥{data['meta']['min_toi_5v5']} min)")
    print(f"5v4 ranking: {len(data['rank_5v4'])} skaters (≥{data['meta']['min_toi_5v4']} min)")
    print(f"Top 3 net 5v5: {[r['name'] for r in data['rank_5v5'][:3]]}")
    print(f"Bottom 3 net 5v5: {[r['name'] for r in data['rank_5v5'][-3:]]}")
    print(f"Top scorer: {data['individual'][0]['name'] if data['individual'] else '—'} ({data['individual'][0]['g'] if data['individual'] else 0}G)")
