"""Base class + metadata for Lemieux connectors.

Every connector subclasses `Connector` and declares:
- a `ConnectorMetadata` at class level
- a `refresh(**params) -> pd.DataFrame` method

The base class provides: shared HTTP cache, shared rate limiter, shared user agent.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

from .cache import HttpCache
from .rate_limit import RateLimiter


@dataclass
class ConnectorMetadata:
    """Static metadata describing a connector — used by REGISTRY.yaml and docs."""
    id: str
    name_en: str
    name_fr: str
    source_url: str
    license_note: str
    rate_limit_hint: str
    key_required: bool
    key_env_var: str | None = None
    safe_to_cache: bool = True
    tags: list[str] = field(default_factory=list)


class Connector(ABC):
    """Base class for every Lemieux data connector."""

    meta: ConnectorMetadata  # each subclass must set this

    def __init__(
        self,
        cache_path: Path | None = None,
        rate_per_sec: float = 1.0,
        user_agent: str = "lemieux/0.1 (hockey analytics; https://github.com/xbeauchamp/lemieux)",
    ):
        self.cache_path = cache_path or (Path.home() / ".lemieux" / "cache.sqlite")
        self.cache = HttpCache(self.cache_path)
        self.limiter = RateLimiter(rate_per_sec)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._configure_auth()

    def _configure_auth(self) -> None:
        """Override in subclasses to attach API keys. Default = noop."""

    def _read_env_key(self) -> str | None:
        if self.meta.key_required and self.meta.key_env_var:
            return os.environ.get(self.meta.key_env_var)
        return None

    @abstractmethod
    def refresh(self, **params) -> pd.DataFrame:
        """Fetch fresh data (honoring rate limit + cache) and return a canonical DataFrame."""

    def close(self) -> None:
        self.cache.close()
        self.session.close()
