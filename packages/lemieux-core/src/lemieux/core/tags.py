"""Tag-query primitive — the bridge between Phase 2 (scouting corpus) and
Phase 3 (tag-cohort effect studies).

`find_players_by_tag(tag, min_confidence=0.6, position=None, ...)` returns the
cohort of players carrying a given archetype tag, joined against any other
constraints the caller cares about (position, min playoff TOI, era band, etc.).

This is what unlocks "find all players tagged 'warrior' and run a reg→playoff
split study on them" — the user's motivating Phase-3 use case.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class TaggedPlayer:
    name: str
    position: str
    tag: str
    confidence: float
    source_quote: str = ""
    source_url: str = ""


def find_players_by_tag(
    con: sqlite3.Connection,
    tag: str,
    min_confidence: float = 0.6,
    position: str | tuple[str, ...] | None = None,
    name_filter: str | None = None,
) -> list[TaggedPlayer]:
    """Return all players tagged `tag` at >= `min_confidence`.

    Optional filters:
      - position: 'C', 'L', 'R', 'D', or a tuple of any of those
      - name_filter: SQL LIKE pattern on the player name (e.g. '%Gallagher%')
    """
    sql = """
        SELECT name, position, tag, confidence, source_quote, source_url
        FROM scouting_tags
        WHERE tag = ? AND confidence >= ?
    """
    params: list = [tag, min_confidence]
    if position is not None:
        positions = (position,) if isinstance(position, str) else tuple(position)
        sql += f" AND position IN ({','.join(['?']*len(positions))})"
        params.extend(positions)
    if name_filter:
        sql += " AND name LIKE ?"
        params.append(name_filter)
    sql += " ORDER BY confidence DESC, name"
    return [
        TaggedPlayer(
            name=r[0], position=r[1], tag=r[2], confidence=r[3],
            source_quote=r[4] or "", source_url=r[5] or "",
        )
        for r in con.execute(sql, params)
    ]


def list_known_tags(con: sqlite3.Connection, min_confidence: float = 0.6,
                    min_count: int = 1) -> list[tuple[str, int]]:
    """Return [(tag, n_players_with_tag), ...] sorted by count descending.

    Useful for surfacing what's actually in the corpus before designing a
    cohort study.
    """
    rows = con.execute(
        """
        SELECT tag, COUNT(DISTINCT (name || '|' || position)) AS n
        FROM scouting_tags
        WHERE confidence >= ?
        GROUP BY tag
        HAVING n >= ?
        ORDER BY n DESC, tag
        """,
        (min_confidence, min_count),
    ).fetchall()
    return [(r[0], int(r[1])) for r in rows]


def list_player_tags(con: sqlite3.Connection, name: str, position: str = "",
                     min_confidence: float = 0.0) -> list[TaggedPlayer]:
    """All tags carried by one player, in confidence order."""
    rows = con.execute(
        """
        SELECT name, position, tag, confidence, source_quote, source_url
        FROM scouting_tags
        WHERE name = ? AND position = ? AND confidence >= ?
        ORDER BY confidence DESC, tag
        """,
        (name, position, min_confidence),
    ).fetchall()
    return [
        TaggedPlayer(name=r[0], position=r[1], tag=r[2], confidence=r[3],
                     source_quote=r[4] or "", source_url=r[5] or "")
        for r in rows
    ]
