"""Lemieux core analytics primitives."""
from __future__ import annotations

from .cohort_effects import (
    TagIntroductionStudyResult,
    TagSplitStudyResult,
    tag_introduction_study,
    tag_split_study,
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
from .scouting import (
    CANONICAL_TAGS,
    CONTINUOUS_ATTRIBUTES,
    ComparableMention,
    ContinuousAttribute,
    PlayerScoutingProfile,
    TagAssertion,
    init_scouting_tables,
    load_profile,
    upsert_profile,
)
from .swap_engine import (
    LINE_COMBO_DIVERGENCE_PP,
    LINE_COMBO_MIN_TOI,
    MIN_TOI_FOR_SWAP,
    PlayerImpact,
    SwapResult,
    build_player_impact,
    build_pooled_player_impact,
    combine_swaps,
    line_combo_sanity,
    project_swap,
)
from .tags import (
    TaggedPlayer,
    find_players_by_tag,
    list_known_tags,
    list_player_tags,
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
    # scouting
    "CANONICAL_TAGS",
    "CONTINUOUS_ATTRIBUTES",
    "ComparableMention",
    "ContinuousAttribute",
    "PlayerScoutingProfile",
    "TagAssertion",
    "init_scouting_tables",
    "load_profile",
    "upsert_profile",
    # tags
    "TaggedPlayer",
    "find_players_by_tag",
    "list_known_tags",
    "list_player_tags",
    # cohort effects
    "TagIntroductionStudyResult",
    "TagSplitStudyResult",
    "tag_introduction_study",
    "tag_split_study",
]

__version__ = "0.2.0"
