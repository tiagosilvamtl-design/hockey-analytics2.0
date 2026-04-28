"""NHL Edge stats connector — biometric features for the comparable engine.

Exposes per-player skating-speed + shot-speed data via:
  - https://api-web.nhle.com/v1/edge/skater-skating-speed-detail/{pid}/{season}/{game-type}
  - https://api-web.nhle.com/v1/edge/skater-shot-speed-detail/{pid}/{season}/{game-type}

Player ID resolution via:
  - https://search.d3.nhle.com/api/v1/search/player?q=...

Aggregates per-player into a feature row:
  - max_skating_speed_mph (top observed, across all sampled games)
  - skating_burst_count_22 (count of bursts >= 22 mph)
  - max_shot_speed_mph (top observed)
  - hard_shot_count_90 (count of shots >= 90 mph)
  - hard_shot_count_80 (count of shots in 80-90 mph)

License: NHL.com public stats. Source notes documented in SOURCES.md.
"""
from .client import NhlEdgeClient, EdgePlayerFeatures, resolve_player_id

__all__ = ["NhlEdgeClient", "EdgePlayerFeatures", "resolve_player_id"]
