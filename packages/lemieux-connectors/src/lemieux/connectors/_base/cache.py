"""SQLite-backed HTTP cache (url -> payload, fetched_at, etag). Single table, single purpose."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

CACHE_DDL = """
CREATE TABLE IF NOT EXISTS http_cache (
    url TEXT PRIMARY KEY,
    fetched_at REAL NOT NULL,
    payload BLOB NOT NULL,
    etag TEXT
);
"""


class HttpCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.executescript(CACHE_DDL)

    def get(self, url: str, ttl_seconds: float) -> bytes | None:
        cur = self._conn.execute(
            "SELECT fetched_at, payload FROM http_cache WHERE url = ?", (url,)
        )
        row = cur.fetchone()
        if not row:
            return None
        fetched_at, payload = row
        if time.time() - fetched_at > ttl_seconds:
            return None
        return payload

    def put(self, url: str, payload: bytes, etag: str | None = None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO http_cache (url, fetched_at, payload, etag) VALUES (?, ?, ?, ?)",
            (url, time.time(), payload, etag),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
