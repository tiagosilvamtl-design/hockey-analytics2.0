"""HTTP client for Natural Stat Trick.

Uses `data.naturalstattrick.com` with the user's access key when available;
falls back to the public site for schema-discovery / fixture capture only.
Throttled at ~1 req/sec with polite retries on 429/5xx. Results pass
through a local SQLite cache.
"""
from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .._base import Connector, ConnectorMetadata, HttpCache, RateLimiter

NST_DATA_BASE = "https://data.naturalstattrick.com"
NST_PUBLIC_BASE = "https://www.naturalstattrick.com"

NST_CONNECTOR_META = ConnectorMetadata(
    id="nst",
    name_en="Natural Stat Trick",
    name_fr="Natural Stat Trick",
    source_url="https://www.naturalstattrick.com/",
    license_note=(
        "Per https://www.naturalstattrick.com/scraping.php, automated traffic permitted on "
        "data.naturalstattrick.com with an approved access key. Do not redistribute raw tables."
    ),
    rate_limit_hint="~1 req/sec with polite backoff.",
    key_required=True,
    key_env_var="NST_ACCESS_KEY",
    safe_to_cache=True,
    tags=["nhl", "advanced-stats", "team", "skater", "line-combos"],
)


@dataclass
class NstQuery:
    """Parameters for a Natural Stat Trick table endpoint."""
    endpoint: Literal[
        "teamtable.php", "playerteams.php", "lines.php", "pairs.php", "games.php"
    ]
    fromseason: str
    thruseason: str
    stype: int = 2
    sit: str = "5v5"
    score: str = "all"
    rate: str = "n"
    team: str = "all"
    loc: str = "B"
    gpf: int = 410
    fd: str = ""
    td: str = ""
    stdoi: str | None = None
    pos: str = "S"

    def querystring(self) -> str:
        params: dict[str, str] = {
            "fromseason": self.fromseason,
            "thruseason": self.thruseason,
            "stype": str(self.stype),
            "sit": self.sit,
            "score": self.score,
            "rate": self.rate,
            "team": self.team,
            "loc": self.loc,
            "gpf": str(self.gpf),
            "fd": self.fd,
            "td": self.td,
            "pos": self.pos,
        }
        if self.stdoi is not None:
            params["stdoi"] = self.stdoi
        return urllib.parse.urlencode(params)


DEFAULT_TTLS = {
    "live_hours": 6,
    "completed_days": 7,
    "historical_days": 30,
}


class NstClient(Connector):
    """Low-level HTTP client. For full Connector.refresh(), callers use the higher
    level pull functions in `ingest.py` (which know how to upsert to a SQLite store).
    This class only provides fetch() + parse helpers."""

    meta = NST_CONNECTOR_META

    def __init__(
        self,
        access_key: str | None = None,
        rate_per_sec: float = 1.0,
        user_agent: str | None = None,
        cache_path: Path | None = None,
    ):
        super().__init__(
            cache_path=cache_path,
            rate_per_sec=rate_per_sec,
            user_agent=user_agent or "lemieux-nst/0.1 (hockey analytics)",
        )
        self.access_key = access_key or self._read_env_key()
        if self.access_key:
            # Header form so the key doesn't end up in URL-keyed caches.
            self.session.headers["nst-key"] = self.access_key

    def fetch(self, query: NstQuery, *, ttl_seconds: float | None = None, force: bool = False) -> bytes:
        base = NST_DATA_BASE if self.access_key else NST_PUBLIC_BASE
        url = f"{base}/{query.endpoint}?{query.querystring()}"
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl(query)
        if not force:
            cached = self.cache.get(url, ttl)
            if cached is not None:
                return cached
        payload = self._get(url)
        self.cache.put(url, payload)
        return payload

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.5, max=20),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def _get(self, url: str) -> bytes:
        self.limiter.wait()
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def _default_ttl(query: NstQuery) -> float:
        if query.stype == 3:
            return DEFAULT_TTLS["live_hours"] * 3600
        if query.fromseason == query.thruseason and query.thruseason >= "20252026":
            return DEFAULT_TTLS["completed_days"] * 86400
        return DEFAULT_TTLS["historical_days"] * 86400

    def refresh(self, **params) -> "pd.DataFrame":
        """Generic refresh entry point: accepts NstQuery kwargs, parses based on endpoint."""
        from .parsers import parse_skater_table, parse_team_table
        import pandas as pd  # noqa: F401

        q = NstQuery(**params)
        html = self.fetch(q)
        if q.endpoint == "teamtable.php":
            return parse_team_table(html)
        if q.endpoint == "playerteams.php":
            return parse_skater_table(html)
        raise NotImplementedError(f"No canonical parser for {q.endpoint!r} yet")
