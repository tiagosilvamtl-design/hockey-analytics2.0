"""Natural Stat Trick connector."""
from __future__ import annotations

from .client import NstClient, NstQuery, NST_CONNECTOR_META
from .parsers import parse_skater_table, parse_team_table, parse_toi_minutes
from .team_map import NAME_TO_ABBREV, to_abbrev

__all__ = [
    "NstClient",
    "NstQuery",
    "NST_CONNECTOR_META",
    "parse_skater_table",
    "parse_team_table",
    "parse_toi_minutes",
    "NAME_TO_ABBREV",
    "to_abbrev",
]
