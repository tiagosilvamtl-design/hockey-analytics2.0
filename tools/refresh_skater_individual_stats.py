"""Pull NST individual (per-player counting) stats and persist to skater_individual_stats.

Hits the same playerteams.php endpoint Lemieux already uses for on-ice stats,
but with stdoi=std — NST's individual table: Goals, Assists, First/Second
Assists, Points, Shots, ixG, iCF, iSCF, iHDCF, Rush Attempts, Rebounds
Created, PIM, Penalties Drawn, Giveaways, Takeaways, Hits, Hits Taken,
Shots Blocked, Faceoffs W/L/%.

(The legacy refresh_all in legacy/data/ingest.py was pulling stdoi=bio,
which returns biographical info — height/weight/draft — and stored it as
empty rows in skater_stats with split='bio'. Those rows are useless; this
tool replaces that path.)

Persists to a new `skater_individual_stats` table keyed by
(player_id, season, stype, sit). Same key shape as skater_stats so joining
on-ice + individual stats is trivial.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/refresh_skater_individual_stats.py
        [--seasons 20212022,20222023,20232024,20242025,20252026]
        [--stypes 2,3] [--sits 5v5,5v4,all]
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

import pandas as pd
import requests
from dotenv import load_dotenv

DB_PATH = REPO / "legacy" / "data" / "store.sqlite"
NST_URL = "https://data.naturalstattrick.com/playerteams.php"
PLAYER_ID_RE = re.compile(r"playerid=(\d+)")


def init_table(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS skater_individual_stats (
            player_id INTEGER NOT NULL,
            season TEXT NOT NULL,
            stype INTEGER NOT NULL,
            sit TEXT NOT NULL,
            name TEXT,
            team_id TEXT,
            position TEXT,
            gp INTEGER,
            toi REAL,
            goals INTEGER,
            assists INTEGER,
            first_assists INTEGER,
            second_assists INTEGER,
            points INTEGER,
            ipp REAL,
            shots INTEGER,
            sh_pct REAL,
            ixg REAL,
            icf INTEGER,
            iff INTEGER,
            iscf INTEGER,
            ihdcf INTEGER,
            rush_attempts INTEGER,
            rebounds_created INTEGER,
            pim INTEGER,
            penalties INTEGER,
            penalties_drawn INTEGER,
            giveaways INTEGER,
            takeaways INTEGER,
            hits INTEGER,
            hits_taken INTEGER,
            shots_blocked INTEGER,
            faceoffs_won INTEGER,
            faceoffs_lost INTEGER,
            faceoffs_pct REAL,
            PRIMARY KEY (player_id, season, stype, sit)
        )
    """)
    con.commit()


def fetch_html(session, season, stype, sit) -> bytes:
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
        "pos": "S",
        "stdoi": "std",
    }
    r = session.get(NST_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.content


def parse_table(html: bytes) -> pd.DataFrame:
    tables = pd.read_html(io.BytesIO(html), flavor="lxml")
    if not tables:
        raise ValueError("no table on NST page")
    df = max(tables, key=len)
    text = html.decode("utf-8", errors="ignore")
    pids = PLAYER_ID_RE.findall(text)
    if len(pids) >= len(df):
        df = df.copy()
        df["player_id"] = [int(p) for p in pids[: len(df)]]
    else:
        df["player_id"] = None
    return df


def to_int(v, default=None):
    if v is None or pd.isna(v):
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def to_float(v, default=None):
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


def parse_toi(v) -> float | None:
    if v is None or pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if ":" in s:
        m, sec = s.split(":")
        try:
            return float(m) + float(sec) / 60.0
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def upsert(con, df, season, stype, sit) -> int:
    n = 0
    for _, r in df.iterrows():
        pid = r.get("player_id")
        if pid is None or pd.isna(pid):
            continue
        con.execute(
            """
            INSERT OR REPLACE INTO skater_individual_stats
            (player_id, season, stype, sit, name, team_id, position,
             gp, toi, goals, assists, first_assists, second_assists, points, ipp,
             shots, sh_pct, ixg, icf, iff, iscf, ihdcf,
             rush_attempts, rebounds_created, pim, penalties, penalties_drawn,
             giveaways, takeaways, hits, hits_taken, shots_blocked,
             faceoffs_won, faceoffs_lost, faceoffs_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(pid), season, stype, sit,
                r.get("Player"), r.get("Team"), r.get("Position"),
                to_int(r.get("GP")), parse_toi(r.get("TOI")),
                to_int(r.get("Goals")), to_int(r.get("Total Assists")),
                to_int(r.get("First Assists")), to_int(r.get("Second Assists")),
                to_int(r.get("Total Points")), to_float(r.get("IPP")),
                to_int(r.get("Shots")), to_float(r.get("SH%")),
                to_float(r.get("ixG")), to_int(r.get("iCF")), to_int(r.get("iFF")),
                to_int(r.get("iSCF")), to_int(r.get("iHDCF")),
                to_int(r.get("Rush Attempts")), to_int(r.get("Rebounds Created")),
                to_int(r.get("PIM")), to_int(r.get("Total Penalties")),
                to_int(r.get("Penalties Drawn")),
                to_int(r.get("Giveaways")), to_int(r.get("Takeaways")),
                to_int(r.get("Hits")), to_int(r.get("Hits Taken")),
                to_int(r.get("Shots Blocked")),
                to_int(r.get("Faceoffs Won")), to_int(r.get("Faceoffs Lost")),
                to_float(r.get("Faceoffs %")),
            ),
        )
        n += 1
    con.commit()
    return n


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default="20212022,20222023,20232024,20242025,20252026")
    ap.add_argument("--stypes", default="2,3")
    ap.add_argument("--sits", default="5v5,5v4,all")
    ap.add_argument("--rate-limit-s", type=float, default=1.0)
    args = ap.parse_args()

    seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
    stypes = [int(s) for s in args.stypes.split(",")]
    sits = [s.strip() for s in args.sits.split(",")]

    nst_key = os.environ.get("NST_ACCESS_KEY", "")
    sess = requests.Session()
    sess.headers.update({"User-Agent": "lemieux-skater-individual/0.1", "nst-key": nst_key})

    con = sqlite3.connect(DB_PATH, timeout=60)
    init_table(con)

    total = 0
    for season in seasons:
        for stype in stypes:
            for sit in sits:
                try:
                    html = fetch_html(sess, season, stype, sit)
                    df = parse_table(html)
                    n = upsert(con, df, season, stype, sit)
                    total += n
                    print(f"  {season} stype={stype} sit={sit:5s} -> {n} skaters")
                    time.sleep(args.rate_limit_s)
                except Exception as e:
                    print(f"  {season} stype={stype} sit={sit}: {e}")

    con.close()
    print(f"\nDone. {total} skater-rows persisted to skater_individual_stats.")


if __name__ == "__main__":
    main()
