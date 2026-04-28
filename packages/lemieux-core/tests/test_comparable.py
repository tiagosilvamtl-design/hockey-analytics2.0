"""Sanity tests for the comparable engine primitives."""
from __future__ import annotations

import math

import numpy as np
import pytest

from lemieux.core import (
    Comparable,
    ComparableIndex,
    FeatureMatrix,
    PlayerImpact,
    build_cohort_stabilized_impact,
    build_index_from_features,
    carmelo_score,
    fit_pca,
    standardize,
)


def test_standardize_zero_var_columns_safe():
    """Columns with no variance should not produce NaN/inf in the standardized output."""
    matrix = np.array([
        [1.0, 5.0, 100.0],
        [2.0, 5.0, 100.0],
        [3.0, 5.0, 100.0],
    ])
    out = standardize(matrix)
    assert np.all(np.isfinite(out.standardized))
    # Constant columns should standardize to zero (mean-centered, std=1 by safety).
    assert np.allclose(out.standardized[:, 1], 0.0)
    assert np.allclose(out.standardized[:, 2], 0.0)


def test_standardize_nan_imputed_to_mean():
    matrix = np.array([
        [1.0, 10.0],
        [2.0, np.nan],
        [3.0, 30.0],
    ])
    out = standardize(matrix)
    # NaN at (1,1) is replaced with column mean (20.0). After standardize, mean=0.
    assert np.all(np.isfinite(out.standardized))
    assert math.isclose(out.standardized[1, 1], 0.0, abs_tol=1e-9)


def test_pca_orthogonal_components():
    rng = np.random.default_rng(42)
    matrix = rng.standard_normal((50, 6))
    std = standardize(matrix)
    pca = fit_pca(std.standardized, n_components=4)
    # Components should be unit vectors and orthogonal.
    norms = np.linalg.norm(pca.components, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-6)
    gram = pca.components @ pca.components.T
    assert np.allclose(gram, np.eye(4), atol=1e-6)


def test_carmelo_score_bounds():
    assert carmelo_score(0.0, 1.0) == 100.0
    assert carmelo_score(1.0, 1.0) == 0.0
    # Negative dist (shouldn't happen but) clamps at 100.
    assert carmelo_score(-0.1, 1.0) == 100.0
    # Distance beyond max clamps at 0.
    assert carmelo_score(2.0, 1.0) == 0.0


def test_index_find_returns_self_excluded():
    """The target itself must NEVER appear in its own top-k."""
    rows = ["a|C", "b|C", "c|C", "d|C"]
    columns = ["x", "y"]
    matrix = np.array([
        [1.0, 1.0],
        [1.1, 1.1],   # closest to a
        [5.0, 5.0],
        [10.0, 10.0],
    ])
    fm = FeatureMatrix(rows=rows, columns=columns, matrix=matrix)
    row_meta = [
        {"name": "Alpha", "position": "C", "pooled_toi_5v5": 500.0,
         "pooled_iso_xgf60": 0.0, "pooled_iso_xga60": 0.0},
        {"name": "Bravo", "position": "C", "pooled_toi_5v5": 500.0,
         "pooled_iso_xgf60": 0.0, "pooled_iso_xga60": 0.0},
        {"name": "Charlie", "position": "C", "pooled_toi_5v5": 500.0,
         "pooled_iso_xgf60": 0.0, "pooled_iso_xga60": 0.0},
        {"name": "Delta", "position": "C", "pooled_toi_5v5": 500.0,
         "pooled_iso_xgf60": 0.0, "pooled_iso_xga60": 0.0},
    ]
    idx = build_index_from_features(fm, row_meta=row_meta, n_components=2)
    comps = idx.find_comparables("Alpha", k=3, min_pooled_toi=0.0)
    names = [c.name for c in comps]
    assert "Alpha" not in names
    assert names[0] == "Bravo"   # closest neighbor


def test_index_position_filter_default_same_position():
    """By default, comps are filtered to the target's own position."""
    rows = ["c|C", "f|L", "g|R"]
    columns = ["x"]
    matrix = np.array([[1.0], [1.05], [1.1]])
    fm = FeatureMatrix(rows=rows, columns=columns, matrix=matrix)
    row_meta = [
        {"name": "Center", "position": "C", "pooled_toi_5v5": 500,
         "pooled_iso_xgf60": 0, "pooled_iso_xga60": 0},
        {"name": "LeftWing", "position": "L", "pooled_toi_5v5": 500,
         "pooled_iso_xgf60": 0, "pooled_iso_xga60": 0},
        {"name": "RightWing", "position": "R", "pooled_toi_5v5": 500,
         "pooled_iso_xgf60": 0, "pooled_iso_xga60": 0},
    ]
    idx = build_index_from_features(fm, row_meta=row_meta, n_components=1)
    comps = idx.find_comparables("Center", k=5, min_pooled_toi=0.0)
    assert all(c.position == "C" for c in comps)


def test_cohort_stabilized_impact_blends_toward_cohort_for_small_sample():
    """A target with tiny TOI should pull strongly toward the cohort."""
    target = PlayerImpact(
        player_id="t|R", name="Target", team_id="MTL",
        toi_on=50.0, toi_off=950.0, xgf_on=2.0, xga_on=1.0, xgf_off=40.0, xga_off=35.0,
    )
    # Cohort with a clearly different iso profile.
    cohort = [
        PlayerImpact(player_id=f"c{i}|R", name=f"Comp{i}", team_id="X",
                     toi_on=600.0, toi_off=400.0,
                     xgf_on=30.0, xga_on=15.0, xgf_off=15.0, xga_off=20.0)
        for i in range(5)
    ]
    blended = build_cohort_stabilized_impact(target, cohort)
    # Target has very small TOI, so blended should be closer to cohort than to target.
    target_iso_net = target.iso_xgf60 - target.iso_xga60
    cohort_iso_net_first = cohort[0].iso_xgf60 - cohort[0].iso_xga60
    blended_iso_net = blended.iso_xgf60 - blended.iso_xga60
    # Verify the blended sits between target and cohort, closer to cohort.
    assert (cohort_iso_net_first - blended_iso_net) ** 2 < (target_iso_net - blended_iso_net) ** 2


def test_cohort_stabilized_impact_returns_target_when_cohort_empty():
    target = PlayerImpact(
        player_id="t|R", name="Target", team_id="MTL",
        toi_on=500.0, toi_off=500.0, xgf_on=20.0, xga_on=15.0, xgf_off=20.0, xga_off=20.0,
    )
    blended = build_cohort_stabilized_impact(target, [])
    assert blended is target
