"""Orchestrate: fetch NST pages, parse, upsert into SQLite.

Exposes one callable per refresh task. Streamlit calls these with st.cache_data wrappers.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from config import CURRENT_SEASON, PRIOR_SEASONS, STORE_DB
from data.nst_client import NstClient, NstQuery
from data.nst_parsers import parse_skater_table, parse_team_table
from data.schema import init_db
from data.team_map import to_abbrev


def refresh_team_stats(
    client: NstClient, season: str, stype: int, sit: str = "5v5", store_path: Path = STORE_DB
) -> pd.DataFrame:
    init_db(store_path)
    q = NstQuery(
        endpoint="teamtable.php",
        fromseason=season,
        thruseason=season,
        stype=stype,
        sit=sit,
    )
    html = client.fetch(q)
    df = parse_team_table(html)
    df["season"] = season
    df["stype"] = stype
    df["sit"] = sit
    with sqlite3.connect(store_path) as conn:
        _upsert_team_stats(conn, df)
    return df


def refresh_skater_stats(
    client: NstClient,
    season: str,
    stype: int,
    sit: str = "5v5",
    split: str = "oi",  # 'oi' = on-ice; 'bio' = individual; 'std' = both combined
    store_path: Path = STORE_DB,
) -> pd.DataFrame:
    init_db(store_path)
    q = NstQuery(
        endpoint="playerteams.php",
        fromseason=season,
        thruseason=season,
        stype=stype,
        sit=sit,
        stdoi=split,
    )
    html = client.fetch(q)
    df = parse_skater_table(html)
    df["season"] = season
    df["stype"] = stype
    df["sit"] = sit
    df["split"] = split
    with sqlite3.connect(store_path) as conn:
        _upsert_skater_stats(conn, df)
    return df


def refresh_all(
    client: NstClient,
    seasons: list[str] | None = None,
    stypes: tuple[int, ...] = (2, 3),
    sits: tuple[str, ...] = ("5v5", "all"),
) -> dict:
    """Convenience: refresh team + skater (on-ice + individual) for the requested scope."""
    seasons = seasons or [CURRENT_SEASON, *PRIOR_SEASONS[:1]]
    counts: dict = {"team": 0, "skater_oi": 0, "skater_bio": 0}
    for s in seasons:
        for st in stypes:
            for sit in sits:
                try:
                    df_t = refresh_team_stats(client, s, st, sit)
                    counts["team"] += len(df_t)
                except Exception as e:  # noqa: BLE001
                    print(f"[warn] team {s} stype={st} sit={sit}: {e}")
                try:
                    df_oi = refresh_skater_stats(client, s, st, sit, split="oi")
                    counts["skater_oi"] += len(df_oi)
                except Exception as e:  # noqa: BLE001
                    print(f"[warn] skater/oi {s} stype={st} sit={sit}: {e}")
                try:
                    df_bio = refresh_skater_stats(client, s, st, sit, split="bio")
                    counts["skater_bio"] += len(df_bio)
                except Exception as e:  # noqa: BLE001
                    print(f"[warn] skater/bio {s} stype={st} sit={sit}: {e}")
    return counts


def _upsert_team_stats(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    cols = [
        "team", "season", "stype", "sit", "toi", "gp",
        "cf", "ca", "cf_pct", "ff", "fa", "ff_pct",
        "sf", "sa", "sf_pct", "gf", "ga", "gf_pct",
        "xgf", "xga", "xgf_pct",
        "scf", "sca", "scf_pct",
        "hdcf", "hdca", "hdcf_pct", "pdo",
    ]
    present = [c for c in cols if c in df.columns]
    rows = df[present].where(pd.notna(df[present]), None).to_dict(orient="records")
    if not rows:
        return
    # teamtable returns full names; normalize to abbreviations so team_id joins to skater_stats.
    for r in rows:
        r["team_id"] = to_abbrev(r.pop("team", None) or "")
    placeholders = ", ".join(["?"] * (len(present) + 0))
    col_sql = ", ".join(["team_id"] + [c for c in present if c != "team"])
    vals_sql = ", ".join(["?"] * (1 + len([c for c in present if c != "team"])))
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS team_stats_raw (season TEXT, stype INTEGER, sit TEXT, team_id TEXT, raw_json TEXT)"
    )
    # Simplest path: replace-all for (season, stype, sit).
    if rows:
        first = rows[0]
        conn.execute(
            "DELETE FROM team_stats WHERE season=? AND stype=? AND sit=?",
            (first.get("season"), first.get("stype"), first.get("sit")),
        )
    for r in rows:
        fields = ["team_id"] + [c for c in present if c != "team"]
        vals = [r.get(f) for f in fields]
        q = f"INSERT INTO team_stats ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})"
        conn.execute(q, vals)
    conn.commit()


def _upsert_skater_stats(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    df = df.copy()
    # NST skater tables use player name as identity; until we add roster IDs,
    # use name|team|position (NHL has had multiple same-name players on same team;
    # e.g., Elias Pettersson C + Elias Pettersson D on VAN in 2024-25).
    pos = df.get("position")
    if pos is None:
        pos = pd.Series([""] * len(df))
    df["player_id"] = (
        df["name"].astype(str) + "|" + df.get("team", "").astype(str) + "|" + pos.astype(str)
    ).str.lower()
    df["team_id"] = df.get("team")
    df = df.drop_duplicates(subset=["player_id"], keep="first")
    cols_present = [
        c for c in [
            "player_id", "team_id", "season", "stype", "sit", "split",
            "name", "position", "gp", "toi",
            "cf", "ca", "cf_pct", "ff", "fa", "ff_pct",
            "xgf", "xga", "xgf_pct",
            "scf", "sca", "scf_pct",
            "hdcf", "hdca", "hdcf_pct",
            "gf", "ga",
        ] if c in df.columns
    ]
    rows = df[cols_present].where(pd.notna(df[cols_present]), None).to_dict(orient="records")
    if not rows:
        return
    first = rows[0]
    conn.execute(
        "DELETE FROM skater_stats WHERE season=? AND stype=? AND sit=? AND split=?",
        (first.get("season"), first.get("stype"), first.get("sit"), first.get("split")),
    )
    for r in rows:
        fields = list(r.keys())
        q = f"INSERT OR REPLACE INTO skater_stats ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})"
        conn.execute(q, [r[f] for f in fields])
    conn.commit()
