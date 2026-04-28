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
from .comparable import (
    POSITION_TOKENS,
    Comparable,
    ComparableIndex,
    build_cohort_stabilized_impact,
    build_index_from_features,
)
from .embedding import (
    FeatureMatrix,
    PCAResult,
    StandardizationResult,
    carmelo_score,
    find_nearest,
    fit_pca,
    standardize,
    transform_pca,
)

__all__ = [
    # swap engine
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
    # comparable engine
    "POSITION_TOKENS",
    "Comparable",
    "ComparableIndex",
    "build_cohort_stabilized_impact",
    "build_index_from_features",
    "FeatureMatrix",
    "PCAResult",
    "StandardizationResult",
    "carmelo_score",
    "find_nearest",
    "fit_pca",
    "standardize",
    "transform_pca",
]

__version__ = "0.2.0"
