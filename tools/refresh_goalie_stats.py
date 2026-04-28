"""Populate goalie_stats by scraping NST's pos=G playerteams page.

NST exposes goalie data via the same `playerteams.php` endpoint that drives
skater_stats, but with `pos=G`. The table layout is the same on-ice format
(Corsi/Fenwick/xGF/xGA over the goalie's TOI). From those columns we
derive:

    sv_pct       — NST exposes "On-Ice SV%" directly (per-100 scale -> /100)
    gsax         — xGA - GA (positive = goals saved above expected)
    hd_sv_pct    — 1 - HDGA / HDCA (high-danger goal-rate-against proxy;
                   HDCA is chances-against so this approximates hdSV%)

The Player column in NST is rendered as an HTML link with the playerId in
the href; we parse that out so we never have to do a fuzzy name lookup.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/refresh_goalie_stats.py
        [--seasons 20212022,20222023,20232024,20242025,20252026]
        [--stypes 2,3]
        [--sits 5v5,all]
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "legacy"))

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

import io
import pandas as pd
import requests
from dotenv import load_dotenv

DB_PATH = REPO / "legacy" / "data" / "store.sqlite"

NST_URL = "https://data.naturalstattrick.com/playerteams.php"
PLAYER_ID_RE = re.compile(r"playerid=(\d+)")


def init_goalie_table(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS goalie_stats (
            player_id INTEGER NOT NULL,
            team_id TEXT,
            season TEXT NOT NULL,
            stype INTEGER NOT NULL,
            sit TEXT NOT NULL,
            name TEXT,
            gp INTEGER,
            toi REAL,
            sv_pct REAL,
            hd_sv_pct REAL,
            gsax REAL,
            PRIMARY KEY (player_id, season, stype, sit)
        )
        """
    )
    # Idempotently add the raw-counting columns so re-runs don't error if the
    # table already existed without them.
    existing_cols = {r[1] for r in con.execute("PRAGMA table_info(goalie_stats)")}
    for col, ddl in [
        ("ga", "INTEGER"), ("sa", "INTEGER"), ("xga", "REAL"),
        ("hdga", "INTEGER"), ("hdca", "INTEGER"),
    ]:
        if col not in existing_cols:
            con.execute(f"ALTER TABLE goalie_stats ADD COLUMN {col} {ddl}")
    con.commit()


def fetch_goalie_html(session: requests.Session, season: str, stype: int, sit: str) -> bytes:
    params = {
        "fromseason": season,
        "thruseason": season,
        "stype": str(stype),
        "sit": sit,
        "score": "all",
        "rate": "n",
        "team": "all",
        "loc": "B",
        "gpf": "410",
        "pos": "G",
    }
    r = session.get(NST_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.content


def parse_goalie_table(html: bytes) -> pd.DataFrame:
    """Parse NST goalie HTML; carry player_id out from the Player href."""
    tables = pd.read_html(io.BytesIO(html), flavor="lxml")
    if not tables:
        raise ValueError("no table on NST goalie page")
    df = max(tables, key=len)
    # Pull player_ids from the raw HTML — pd.read_html drops the link.
    text = html.decode("utf-8", errors="ignore")
    pids = PLAYER_ID_RE.findall(text)
    # The order matches the order players appear in the table.
    if len(pids) >= len(df):
        df = df.copy()
        df["player_id"] = [int(p) for p in pids[: len(df)]]
    else:
        df["player_id"] = None
    return df


def parse_toi_minutes(val) -> float:
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if ":" in s:
        m, sec = s.split(":")
        return float(m) + float(sec) / 60.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def upsert_goalie_rows(con: sqlite3.Connection, df: pd.DataFrame, season: str,
                       stype: int, sit: str) -> int:
    """Compute derived metrics + upsert. Returns row count."""
    def to_float(v, default=0.0):
        if v is None or pd.isna(v):
            return default
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s or s == "-":
            return default
        try:
            return float(s)
        except ValueError:
            return default

    n = 0
    for _, r in df.iterrows():
        pid = r.get("player_id")
        if pid is None or pd.isna(pid):
            continue
        ga = to_float(r.get("GA"))
        sa = to_float(r.get("SA"))
        xga = to_float(r.get("xGA"))
        hdga = to_float(r.get("HDGA"))
        hdca = to_float(r.get("HDCA"))
        # sv_pct: NST's "On-Ice SV%" is reported as 88.31 -> /100
        sv_raw = r.get("On-Ice SV%")
        sv_pct = None
        if sv_raw is not None and not pd.isna(sv_raw):
            try:
                sv_pct = float(sv_raw) / 100.0
            except (ValueError, TypeError):
                sv_pct = None
        # GSAx = xGA - GA (positive = goalie saved more than expected)
        gsax = xga - ga
        # hd_sv_pct ≈ 1 - HDGA / HDCA  (HDCA is chances against, not shots,
        # but it's the closest proxy NST surfaces; documented in glossary)
        hd_sv_pct = (1.0 - hdga / hdca) if hdca > 0 else None
        toi = parse_toi_minutes(r.get("TOI"))
        gp = int(r.get("GP") or 0)
        team = r.get("Team")
        name = r.get("Player")

        con.execute(
            """
            INSERT OR REPLACE INTO goalie_stats
            (player_id, team_id, season, stype, sit, name, gp, toi,
             sv_pct, hd_sv_pct, gsax, ga, sa, xga, hdga, hdca)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (int(pid), team, season, stype, sit, name, gp, toi,
             sv_pct, hd_sv_pct, gsax, int(ga), int(sa), xga, int(hdga), int(hdca)),
        )
        n += 1
    con.commit()
    return n


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default="20212022,20222023,20232024,20242025,20252026")
    ap.add_argument("--stypes", default="2,3", help="2=regular, 3=playoff")
    ap.add_argument("--sits", default="all,5v5", help="NST 'sit' values")
    ap.add_argument("--rate-limit-s", type=float, default=1.0)
    args = ap.parse_args()

    seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
    stypes = [int(s) for s in args.stypes.split(",")]
    sits = [s.strip() for s in args.sits.split(",")]

    nst_key = os.environ.get("NST_ACCESS_KEY", "")
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "lemieux-goalie-ingest/0.1",
        "nst-key": nst_key,
    })

    con = sqlite3.connect(DB_PATH, timeout=60)
    init_goalie_table(con)

    total = 0
    for season in seasons:
        for stype in stypes:
            for sit in sits:
                try:
                    html = fetch_goalie_html(sess, season, stype, sit)
                    df = parse_goalie_table(html)
                    n = upsert_goalie_rows(con, df, season, stype, sit)
                    total += n
                    print(f"  {season} stype={stype} sit={sit:5s} -> {n} goalies")
                    time.sleep(args.rate_limit_s)
                except Exception as e:
                    print(f"  {season} stype={stype} sit={sit}: {e}")

    con.close()
    print(f"\nDone. {total} goalie-rows persisted to goalie_stats.")


if __name__ == "__main__":
    main()
