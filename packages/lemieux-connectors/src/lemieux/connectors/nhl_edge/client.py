"""NHL Edge HTTP client + per-player biometric feature aggregation.

Polite by default (1 req/sec, configurable). Caches via a small file-backed
JSON store in ~/.lemieux/edge_cache/ — Edge data is stable for completed seasons
so caching is safe.

The aggregation function `EdgePlayerFeatures.from_player_season(...)` returns a
flat feature row that the comparable engine can append to its Block-A vector.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

PLAYER_SEARCH = "https://search.d3.nhle.com/api/v1/search/player"
SKATING_SPEED_DETAIL = "https://api-web.nhle.com/v1/edge/skater-skating-speed-detail/{pid}/{season}/{game_type}"
SHOT_SPEED_DETAIL    = "https://api-web.nhle.com/v1/edge/skater-shot-speed-detail/{pid}/{season}/{game_type}"
PLAYER_LANDING       = "https://api-web.nhle.com/v1/player/{pid}/landing"

DEFAULT_CACHE_DIR = Path.home() / ".lemieux" / "edge_cache"
DEFAULT_RATE_LIMIT_S = 0.6   # polite default ~1.5 req/sec

# Sentinel for cache misses where the upstream returned 404 — we don't want to
# retry these on every run; cache them as empty and move on.
SENTINEL_404 = "__EDGE_404__"


@dataclass
class EdgePlayerFeatures:
    """Per-player aggregated NHL Edge biometric features."""

    player_id: int
    name: str
    season_label: str          # e.g. "20242025"
    game_type: int             # 2 regular, 3 playoffs

    max_skating_speed_mph: float | None = None
    skating_burst_count_22plus: int = 0      # bursts >= 22 mph
    skating_burst_count_20to22: int = 0      # bursts 20-22 mph
    max_shot_speed_mph: float | None = None
    hard_shot_count_90plus: int = 0
    hard_shot_count_80to90: int = 0

    @classmethod
    def from_responses(
        cls,
        player_id: int,
        name: str,
        season_label: str,
        game_type: int,
        skating: dict | None,
        shots: dict | None,
    ) -> "EdgePlayerFeatures":
        """Build from raw API JSON payloads (or None if 404)."""
        out = cls(player_id=player_id, name=name, season_label=season_label, game_type=game_type)
        if skating and (skating.get("topSkatingSpeeds")):
            speeds = [s["skatingSpeed"]["imperial"] for s in skating["topSkatingSpeeds"]
                      if s.get("skatingSpeed")]
            if speeds:
                out.max_skating_speed_mph = max(speeds)
                out.skating_burst_count_22plus = sum(1 for v in speeds if v >= 22.0)
                out.skating_burst_count_20to22 = sum(1 for v in speeds if 20.0 <= v < 22.0)
        if shots and (shots.get("hardestShots")):
            shotspeeds = [s["shotSpeed"]["imperial"] for s in shots["hardestShots"]
                          if s.get("shotSpeed")]
            if shotspeeds:
                out.max_shot_speed_mph = max(shotspeeds)
                out.hard_shot_count_90plus = sum(1 for v in shotspeeds if v >= 90.0)
                out.hard_shot_count_80to90 = sum(1 for v in shotspeeds if 80.0 <= v < 90.0)
        return out


@dataclass
class PlayerBio:
    """Static player bio from NHL.com /v1/player/{id}/landing.

    One row per player; never changes mid-career except for trade/team_abbrev
    (which we don't persist). Height/weight/birthdate/draft are stable.
    """

    player_id: int
    name: str
    height_in: int | None = None         # heightInInches
    weight_lb: int | None = None         # weightInPounds
    birth_date: str | None = None        # ISO yyyy-mm-dd
    birth_country: str | None = None     # 3-letter code (CAN/USA/SWE/...)
    shoots_catches: str | None = None    # L / R
    position: str | None = None          # C / L / R / D / G
    draft_year: int | None = None
    draft_round: int | None = None
    draft_overall: int | None = None
    is_active: int | None = None         # 1 / 0 (cast from bool)

    @classmethod
    def from_landing(cls, payload: dict, player_id: int) -> "PlayerBio":
        """Parse the /v1/player/{id}/landing response."""
        first = (payload.get("firstName") or {}).get("default") or ""
        last = (payload.get("lastName") or {}).get("default") or ""
        name = f"{first} {last}".strip()
        draft = payload.get("draftDetails") or {}
        return cls(
            player_id=player_id,
            name=name,
            height_in=payload.get("heightInInches"),
            weight_lb=payload.get("weightInPounds"),
            birth_date=payload.get("birthDate"),
            birth_country=payload.get("birthCountry"),
            shoots_catches=payload.get("shootsCatches"),
            position=payload.get("position"),
            draft_year=draft.get("year"),
            draft_round=draft.get("round"),
            draft_overall=draft.get("overallPick"),
            is_active=int(bool(payload.get("isActive"))) if "isActive" in payload else None,
        )


class NhlEdgeClient:
    """Thin HTTP wrapper with polite rate-limiting + JSON file cache."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        rate_limit_s: float = DEFAULT_RATE_LIMIT_S,
        user_agent: str = "lemieux-edge-connector/0.1",
    ):
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_s = rate_limit_s
        self._last_call = 0.0
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    # ---- low-level ----
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.rate_limit_s:
            time.sleep(self.rate_limit_s - elapsed)
        self._last_call = time.monotonic()

    def _cache_path(self, key: str) -> Path:
        # Sanitize key into a safe filename
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in key)
        return self.cache_dir / f"{safe}.json"

    def _get_json(self, url: str, cache_key: str) -> Any:
        cp = self._cache_path(cache_key)
        if cp.exists():
            try:
                cached = json.loads(cp.read_text(encoding="utf-8"))
                if cached == SENTINEL_404:
                    return None
                return cached
            except Exception:
                pass  # corrupt cache; refetch
        self._throttle()
        try:
            r = self._session.get(url, timeout=20)
        except Exception as e:
            log.warning("EDGE fetch error %s: %s", url, e)
            return None
        if r.status_code == 404:
            cp.write_text(json.dumps(SENTINEL_404), encoding="utf-8")
            return None
        if r.status_code != 200:
            log.warning("EDGE non-200 %s: %s", url, r.status_code)
            return None
        try:
            data = r.json()
        except Exception as e:
            log.warning("EDGE non-JSON %s: %s", url, e)
            return None
        cp.write_text(json.dumps(data), encoding="utf-8")
        return data

    # ---- high-level ----
    def fetch_skating_speed(self, player_id: int, season: str, game_type: int = 2) -> dict | None:
        url = SKATING_SPEED_DETAIL.format(pid=player_id, season=season, game_type=game_type)
        return self._get_json(url, f"skating_{player_id}_{season}_{game_type}")

    def fetch_shot_speed(self, player_id: int, season: str, game_type: int = 2) -> dict | None:
        url = SHOT_SPEED_DETAIL.format(pid=player_id, season=season, game_type=game_type)
        return self._get_json(url, f"shot_{player_id}_{season}_{game_type}")

    def fetch_player_landing(self, player_id: int) -> dict | None:
        """Fetch /v1/player/{id}/landing — static bio block (height, weight, draft, ...)."""
        url = PLAYER_LANDING.format(pid=player_id)
        return self._get_json(url, f"landing_{player_id}")

    def fetch_player_bio(self, player_id: int) -> PlayerBio | None:
        """Convenience: landing + parse to PlayerBio. Returns None on 404."""
        data = self.fetch_player_landing(player_id)
        if not data:
            return None
        return PlayerBio.from_landing(data, player_id=player_id)

    def fetch_player_features(
        self, player_id: int, name: str, season: str, game_type: int = 2
    ) -> EdgePlayerFeatures:
        """Fetch + aggregate Edge data for one (player, season, game_type)."""
        skating = self.fetch_skating_speed(player_id, season, game_type)
        shots = self.fetch_shot_speed(player_id, season, game_type)
        return EdgePlayerFeatures.from_responses(
            player_id=player_id, name=name, season_label=season, game_type=game_type,
            skating=skating, shots=shots,
        )


def resolve_player_id(name: str, position_hint: str | None = None,
                      session: requests.Session | None = None,
                      rate_limit_s: float = DEFAULT_RATE_LIMIT_S) -> int | None:
    """Resolve a display name to NHL.com playerId via the public search endpoint.

    If position_hint is provided (e.g. 'R', 'D'), filter to matching position
    when multiple players share the name (Brendan Gallagher vs Ty Gallagher).
    """
    if not name:
        return None
    s = session or requests.Session()
    s.headers.setdefault("User-Agent", "lemieux-edge-connector/0.1")
    try:
        r = s.get(PLAYER_SEARCH, params={"culture": "en-us", "limit": 20, "q": name}, timeout=15)
        if r.status_code != 200:
            return None
        candidates = r.json()
    except Exception as e:
        log.warning("Player resolve failed for %r: %s", name, e)
        return None
    # Filter to exact-name match (case-insensitive)
    target = name.strip().lower()
    exact = [c for c in candidates if (c.get("name") or "").strip().lower() == target]
    pool = exact if exact else candidates
    if position_hint:
        pos = position_hint.strip().upper()
        ph = [c for c in pool if (c.get("positionCode") or "").upper() == pos]
        if ph:
            pool = ph
    # Tiebreak: most recently active (lastTeamAbbrev present)
    pool.sort(key=lambda c: 0 if c.get("lastTeamAbbrev") else 1)
    if pool:
        try:
            return int(pool[0]["playerId"])
        except Exception:
            return None
    return None
