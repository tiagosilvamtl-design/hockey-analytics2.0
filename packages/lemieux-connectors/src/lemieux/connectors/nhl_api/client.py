"""Connector for NHL.com's public (undocumented) endpoints.

Covers three hosts:
  - api-web.nhle.com        — gamecenter (play-by-play, rosters)
  - api.nhle.com/stats/rest — stats REST API (shift charts, standings)

No authentication. Rate limited politely; every response cached.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .._base import Connector, ConnectorMetadata

API_WEB_BASE = "https://api-web.nhle.com"
STATS_BASE = "https://api.nhle.com/stats/rest/en"

NHL_API_CONNECTOR_META = ConnectorMetadata(
    id="nhl_api",
    name_en="NHL.com public API",
    name_fr="API publique LNH.com",
    source_url="https://www.nhl.com/",
    license_note=(
        "Unofficial endpoints. Free, unauthenticated. Not for commercial redistribution. "
        "Respect rate limits; cache aggressively."
    ),
    rate_limit_hint="≤10 req/sec sustained; cache everything.",
    key_required=False,
    safe_to_cache=True,
    tags=["nhl", "play-by-play", "shifts", "rosters", "live"],
)


@dataclass
class GameId:
    """NHL playoff game IDs follow YYYY03RRSG: year, 03=playoff, R=round, S=series, G=game."""
    raw: str

    @classmethod
    def playoff(cls, season_start_year: int, round_: int, series: int, game: int) -> GameId:
        s = f"{season_start_year}03{round_}{series}{game}"
        if len(s) != 10:
            raise ValueError(f"Unexpected playoff game id length: {s}")
        return cls(raw=s)


class NhlApiClient(Connector):
    meta = NHL_API_CONNECTOR_META

    def __init__(self, rate_per_sec: float = 5.0, cache_path: Path | None = None):
        super().__init__(
            cache_path=cache_path,
            rate_per_sec=rate_per_sec,
            user_agent="lemieux-nhl-api/0.1 (hockey analytics)",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.0, max=10),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def _get_json(self, url: str, ttl_seconds: float = 6 * 3600) -> dict:
        cached = self.cache.get(url, ttl_seconds)
        if cached is not None:
            import json
            return json.loads(cached)
        self.limiter.wait()
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        self.cache.put(url, resp.content)
        return resp.json()

    def play_by_play(self, game_id: str) -> dict:
        """Full play-by-play for a game. Returns the nested JSON."""
        return self._get_json(f"{API_WEB_BASE}/v1/gamecenter/{game_id}/play-by-play")

    def shift_chart(self, game_id: str) -> list[dict]:
        """Per-player shift records for a game."""
        data = self._get_json(f"{STATS_BASE}/shiftcharts?cayenneExp=gameId={game_id}")
        return data.get("data", []) or []

    def schedule_for_date(self, date_iso: str) -> dict:
        """NHL schedule for a specific YYYY-MM-DD date."""
        return self._get_json(f"{API_WEB_BASE}/v1/schedule/{date_iso}", ttl_seconds=3600)

    def refresh(self, kind: str = "schedule", **params) -> pd.DataFrame:
        """Convenience wrapper. `kind` ∈ {schedule, shifts, pbp_events}."""
        if kind == "schedule":
            d = self.schedule_for_date(params["date"])
            rows = []
            for game_week in d.get("gameWeek", []) or []:
                for g in game_week.get("games", []) or []:
                    rows.append({
                        "game_id": str(g.get("id")),
                        "date": g.get("gameDate"),
                        "home": (g.get("homeTeam") or {}).get("abbrev"),
                        "away": (g.get("awayTeam") or {}).get("abbrev"),
                        "game_type": g.get("gameType"),
                    })
            return pd.DataFrame(rows)
        if kind == "shifts":
            shifts = self.shift_chart(params["game_id"])
            return pd.DataFrame(shifts)
        if kind == "pbp_events":
            plays = self.play_by_play(params["game_id"]).get("plays") or []
            return pd.DataFrame([{
                "event_id": p.get("eventId"),
                "period": (p.get("periodDescriptor") or {}).get("number"),
                "time_in_period": p.get("timeInPeriod"),
                "type": p.get("typeDescKey"),
                "team_id": (p.get("details") or {}).get("eventOwnerTeamId"),
                "shooter_id": (p.get("details") or {}).get("shootingPlayerId"),
                "x": (p.get("details") or {}).get("xCoord"),
                "y": (p.get("details") or {}).get("yCoord"),
            } for p in plays])
        raise ValueError(f"Unknown kind: {kind!r}")
