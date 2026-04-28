"""Feature standardization, PCA, and distance primitives for the comparable engine.

Pure NumPy. No scikit-learn dependency to keep the package install lightweight.

Design:
- `FeatureMatrix` holds the raw matrix + per-column metadata + per-row identifiers.
- `standardize()` z-scores each column, returning means + stds for re-use.
- `fit_pca()` runs SVD on the standardized matrix and returns components + explained variance.
- `transform_pca()` projects new rows onto the fitted PCA basis.
- `whitened_euclidean_distance()` computes pairwise distance after PCA whitening.
  After PCA + whitening, Euclidean distance equals Mahalanobis on the original
  standardized features — same metric, computed efficiently.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FeatureMatrix:
    """Raw feature matrix with column + row metadata.

    Rows correspond to players; columns to features. NaN entries are preserved
    here and dropped/imputed at standardize time.
    """

    rows: list[str]              # player identifiers, one per row
    columns: list[str]           # feature names, one per column
    matrix: np.ndarray           # shape (n_rows, n_columns)
    row_meta: list[dict] | None = None   # optional per-row metadata (name, position, etc.)


@dataclass
class StandardizationResult:
    """Output of standardize(). Holds the means/stds so we can transform new rows later."""

    standardized: np.ndarray     # z-scored matrix; NaNs replaced with 0 (column mean)
    means: np.ndarray            # per-column mean
    stds: np.ndarray             # per-column std (zeros replaced with 1 for safety)


def standardize(matrix: np.ndarray) -> StandardizationResult:
    """Z-score each column. NaN entries imputed with column mean (becomes 0 post-std).

    Defensive against:
    - All-NaN columns: set mean=0, std=1, output column = all zeros.
    - Zero-variance columns: std=1 to avoid divide-by-zero; output column = all zeros.
    """
    matrix = np.asarray(matrix, dtype=np.float64)
    # Use np.errstate to silence "Mean of empty slice" warnings on all-NaN columns.
    with np.errstate(invalid="ignore"):
        means = np.nanmean(matrix, axis=0)
        stds = np.nanstd(matrix, axis=0, ddof=0)
    # All-NaN columns → mean=NaN, std=NaN. Replace with safe defaults.
    means = np.where(np.isnan(means), 0.0, means)
    stds = np.where(np.isnan(stds) | (stds < 1e-12), 1.0, stds)
    # Impute NaNs with column mean BEFORE standardizing.
    imputed = np.where(np.isnan(matrix), means, matrix)
    standardized = (imputed - means) / stds
    return StandardizationResult(standardized=standardized, means=means, stds=stds)


@dataclass
class PCAResult:
    """Output of fit_pca()."""

    components: np.ndarray            # shape (n_components, n_features); rows are eigenvectors
    explained_variance: np.ndarray    # length n_components; eigenvalues
    explained_variance_ratio: np.ndarray
    n_components: int


def fit_pca(standardized: np.ndarray, n_components: int) -> PCAResult:
    """Fit PCA via SVD on the standardized matrix.

    Components are returned as rows of `components`, ordered by descending
    explained variance.
    """
    n_rows, n_features = standardized.shape
    n_components = min(n_components, n_features, n_rows)
    # SVD: M = U S Vt, components = Vt rows; eigenvalues = (S^2 / (n_rows-1)).
    _, s, vt = np.linalg.svd(standardized, full_matrices=False)
    components = vt[:n_components]
    explained_variance = (s[:n_components] ** 2) / max(n_rows - 1, 1)
    total_variance = float((s ** 2).sum() / max(n_rows - 1, 1))
    explained_variance_ratio = explained_variance / total_variance if total_variance > 0 else np.zeros_like(explained_variance)
    return PCAResult(
        components=components,
        explained_variance=explained_variance,
        explained_variance_ratio=explained_variance_ratio,
        n_components=n_components,
    )


def transform_pca(standardized: np.ndarray, pca: PCAResult, whiten: bool = True) -> np.ndarray:
    """Project rows onto PCA components.

    With `whiten=True`, divide each component by sqrt(eigenvalue) so all components
    have unit variance. Distances in the whitened space equal Mahalanobis on the
    standardized input.
    """
    projected = standardized @ pca.components.T
    if whiten:
        scales = np.sqrt(np.maximum(pca.explained_variance, 1e-12))
        projected = projected / scales
    return projected


def find_nearest(query_row: np.ndarray, embedding: np.ndarray, k: int,
                 exclude_indices: list[int] | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Find indices of the k nearest rows to `query_row` in `embedding` (Euclidean).

    Returns (top_k_indices, top_k_distances). Excludes any indices in
    `exclude_indices` (typically the query itself).
    """
    diffs = embedding - query_row[np.newaxis, :]
    distances = np.linalg.norm(diffs, axis=1)
    if exclude_indices:
        for idx in exclude_indices:
            if 0 <= idx < len(distances):
                distances[idx] = np.inf
    order = np.argsort(distances)[:k]
    return order, distances[order]


def carmelo_score(distance: float, max_distance: float) -> float:
    """CARMELO-style 0-100 similarity score from a distance.

    100 = identical; 0 = at the max observed distance for the cohort.
    Non-linear: small distances should still score high.
    """
    if max_distance <= 0:
        return 100.0
    ratio = max(0.0, min(distance / max_distance, 1.0))
    # Smooth decay: similarity = 100 * (1 - ratio)^1.5, clamped to [0, 100].
    score = 100.0 * (1.0 - ratio) ** 1.5
    return round(score, 1)
