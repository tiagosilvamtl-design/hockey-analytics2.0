"""Lemieux core analytics primitives."""
from __future__ import annotations

from .swap_engine import (
    MIN_TOI_FOR_SWAP,
    LINE_COMBO_MIN_TOI,
    LINE_COMBO_DIVERGENCE_PP,
    PlayerImpact,
    SwapResult,
    build_player_impact,
    build_pooled_player_impact,
    combine_swaps,
    line_combo_sanity,
    project_swap,
)

__all__ = [
    "MIN_TOI_FOR_SWAP",
    "LINE_COMBO_MIN_TOI",
    "LINE_COMBO_DIVERGENCE_PP",
    "PlayerImpact",
    "SwapResult",
    "build_player_impact",
    "build_pooled_player_impact",
    "combine_swaps",
    "line_combo_sanity",
    "project_swap",
]

__version__ = "0.1.0"
