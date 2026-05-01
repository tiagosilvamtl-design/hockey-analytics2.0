"""NHL.com public API connector — shifts + play-by-play + schedules."""
from __future__ import annotations

from .client import NHL_API_CONNECTOR_META, NhlApiClient

__all__ = ["NhlApiClient", "NHL_API_CONNECTOR_META"]
