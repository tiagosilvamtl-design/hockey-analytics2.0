"""HTTP client for Natural Stat Trick.

Uses `data.naturalstattrick.com` with the access key when available; falls back to the
public site for schema-discovery / fixture capture. Throttled at ~1 req/sec with polite
retries on 429/5xx. Results pass through a local SQLite cache.
"""
from __future__ import annotations

import threading
import time
import urllib.parse
from dataclasses import dataclass
from typing import Literal

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from config import (
    CACHE_DB,
    CACHE_TTL_COMPLETED_DAYS,
    CACHE_TTL_HISTORICAL_DAYS,
    CACHE_TTL_LIVE_HOURS,
    NST_ACCESS_KEY,
    NST_DATA_BASE,
    NST_PUBLIC_BASE,
    NST_RATE_LIMIT_PER_SEC,
    NST_USER_AGENT,
    nst_base,
)
from data.cache import HttpCache


@dataclass
class NstQuery:
    """Parameters for a Natural Stat Trick table endpoint.

    Only a subset of NST's query string is modeled — the knobs we actually use.
    Pages accept `fromseason`, `thruseason`, `stype` (2=reg, 3=playoff), `sit`
    (5v5, 5v4, 4v5, all), `score` (state), `rate` (n=counts, y=per60), `team`,
    `loc` (B=both), `gpf` / `gpfilt`, `fd`/`td` (from/to date), and `stdoi`.
    """

    endpoint: Literal[
        "teamtable.php",
        "playerteams.php",
        "lines.php",
        "pairs.php",
        "games.php",
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


class RateLimiter:
    """Minimal token-bucket limiter: at most `per_sec` calls per second."""

    def __init__(self, per_sec: float):
        self.min_interval = 1.0 / per_sec if per_sec > 0 else 0.0
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self.min_interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


class NstClient:
    def __init__(
        self,
        access_key: str | None = NST_ACCESS_KEY,
        rate_per_sec: float = NST_RATE_LIMIT_PER_SEC,
        user_agent: str = NST_USER_AGENT,
        cache_path=CACHE_DB,
    ):
        self.access_key = access_key
        self.limiter = RateLimiter(rate_per_sec)
        self.cache = HttpCache(cache_path)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        if access_key:
            # NST docs document either ?key= or an nst-key header; we use the header
            # so the key doesn't leak into URLs / cache keys / logs.
            self.session.headers["nst-key"] = access_key

    def fetch(self, query: NstQuery, *, ttl_seconds: float | None = None, force: bool = False) -> bytes:
        """Fetch the raw HTML bytes for a query. Caches by URL.

        URL always uses the canonical base (keyed subdomain if we have a key,
        public site otherwise). The key goes in a header, not the URL — so the
        cache key is stable regardless of key rotation.
        """
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
        if resp.status_code >= 500 or resp.status_code == 429:
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def _default_ttl(query: NstQuery) -> float:
        """TTL heuristic — live playoff 6h, completed 7d, historical 30d."""
        if query.stype == 3:
            return CACHE_TTL_LIVE_HOURS * 3600
        if query.fromseason == query.thruseason and query.thruseason >= "20252026":
            return CACHE_TTL_COMPLETED_DAYS * 86400
        return CACHE_TTL_HISTORICAL_DAYS * 86400

    def base(self) -> str:
        return nst_base()

    def close(self) -> None:
        self.cache.close()
        self.session.close()
