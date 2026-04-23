"""Quotes store: simple CRUD over the `quotes` SQLite table."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from config import STORE_DB
from data.schema import Quote, init_db


def _conn(path: Path) -> sqlite3.Connection:
    init_db(path)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def add_quote(q: Quote, path: Path = STORE_DB) -> int:
    with _conn(path) as c:
        cur = c.execute(
            """
            INSERT INTO quotes (player_id, team_id, source, url, date, author, title, lede, stance, entered_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (q.player_id, q.team_id, q.source, q.url, q.date, q.author, q.title, q.lede, q.stance, q.entered_by),
        )
        c.commit()
        return cur.lastrowid or 0


def list_quotes(
    player_id: str | None = None,
    team_id: str | None = None,
    path: Path = STORE_DB,
) -> pd.DataFrame:
    with _conn(path) as c:
        q = "SELECT * FROM quotes WHERE 1=1"
        args: list = []
        if player_id:
            q += " AND player_id = ?"
            args.append(player_id)
        if team_id:
            q += " AND team_id = ?"
            args.append(team_id)
        q += " ORDER BY date DESC, id DESC"
        return pd.read_sql_query(q, c, params=args)


def delete_quote(quote_id: int, path: Path = STORE_DB) -> None:
    with _conn(path) as c:
        c.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        c.commit()


def model_stance_from_impact(iso_xgf60: float, iso_xga60: float, ci_xgf60: tuple[float, float]) -> str:
    """Translate iso-impact signs/magnitudes + CI into a coarse stance label.

    Matches UI stance vocabulary: bullish / bearish / neutral / mixed.
    'Clears zero' means CI is entirely on one side; otherwise neutral.
    """
    ci_low, ci_high = ci_xgf60
    off_bull = ci_low > 0
    off_bear = ci_high < 0
    # defensive: negative iso_xga60 is GOOD (fewer goals against)
    def_bull = iso_xga60 < 0
    def_bear = iso_xga60 > 0

    if off_bull and def_bull:
        return "bullish"
    if off_bear and def_bear:
        return "bearish"
    if (off_bull and def_bear) or (off_bear and def_bull):
        return "mixed"
    return "neutral"


def compare_stances(model: str, quote: str) -> str:
    """Return 'agree', 'disagree', or 'ambiguous'."""
    if model == quote:
        return "agree"
    opposite = {"bullish": "bearish", "bearish": "bullish"}
    if opposite.get(model) == quote:
        return "disagree"
    return "ambiguous"
