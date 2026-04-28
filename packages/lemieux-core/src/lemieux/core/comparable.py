"""Player comparable engine — sample-size enhancer for the swap engine.

Phase 1 (this file) is the kNN-on-embedding core. It consumes already-pooled
per-player feature rows (Block A: NST iso + rate stats), fits a PCA, and lets
callers query for top-k comparables of a target.

Block B (NHL Edge biometrics) and Block C (cross-league via NHLe) plug in by
adding columns to the feature matrix; the kNN logic is the same.

The output `Comparable` dataclass surfaces per-block contributions when the
embedding is fitted on multi-block features, so reports can show *why* the
match happened.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

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
from .swap_engine import PlayerImpact


# Position one-hot dimensions used in the feature matrix.
POSITION_TOKENS = ("C", "L", "R", "D")


@dataclass
class Comparable:
    """One nearest-neighbor match with its similarity score and meta."""

    name: str
    position: str
    score: float                   # 0-100 CARMELO-style
    distance: float                # raw Euclidean distance in PCA-whitened space
    pooled_toi_5v5: float          # sample size for the comp's pooled 5v5 (used for cohort weighting)
    pooled_iso_xgf60: float
    pooled_iso_xga60: float
    feature_contributions: dict[str, float] = field(default_factory=dict)


@dataclass
class ComparableIndex:
    """Persisted comparable index — the kNN search structure.

    Self-contained: holds the player table, the standardized feature matrix,
    the PCA, and the embedded matrix used for distance queries.
    """

    rows: list[str]                # row identifiers (player_id strings)
    row_meta: list[dict]           # per-row metadata (name, position, pooled_toi, pooled_iso, ...)
    columns: list[str]             # feature names
    matrix_raw: np.ndarray         # shape (n_rows, n_columns)
    means: np.ndarray
    stds: np.ndarray
    pca_components: np.ndarray
    pca_explained_variance: np.ndarray
    embedding: np.ndarray          # shape (n_rows, n_pca_components); whitened
    metadata: dict = field(default_factory=dict)  # build provenance

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    def find_by_name(self, name: str) -> int | None:
        """Return row index of player by display name (case-insensitive substring)."""
        target = name.strip().lower()
        for i, m in enumerate(self.row_meta):
            if (m.get("name") or "").strip().lower() == target:
                return i
        # fallback: substring
        for i, m in enumerate(self.row_meta):
            if target in (m.get("name") or "").strip().lower():
                return i
        return None

    def find_comparables(
        self,
        target_name: str,
        k: int = 5,
        position_filter: str | tuple[str, ...] | None = None,
        min_pooled_toi: float = 200.0,
    ) -> list[Comparable]:
        """Return the k nearest neighbors of `target_name`.

        - position_filter: only compare against players of these positions.
            By default, restricts to same position as the target.
        - min_pooled_toi: excludes comps with too little sample (default 200 min 5v5).
        """
        idx = self.find_by_name(target_name)
        if idx is None:
            raise ValueError(f"Player not found in index: {target_name!r}")
        target_meta = self.row_meta[idx]
        target_position = target_meta.get("position") or ""

        # Build position filter
        if position_filter is None:
            allowed_positions = (target_position,)
        elif isinstance(position_filter, str):
            allowed_positions = (position_filter,)
        else:
            allowed_positions = tuple(position_filter)

        # Build exclusion list: target itself + ineligible by position/toi
        exclude: list[int] = [idx]
        for i, m in enumerate(self.row_meta):
            if i == idx:
                continue
            pos = m.get("position") or ""
            if pos not in allowed_positions:
                exclude.append(i)
                continue
            if (m.get("pooled_toi_5v5") or 0.0) < min_pooled_toi:
                exclude.append(i)

        order, distances = find_nearest(self.embedding[idx], self.embedding, k, exclude_indices=exclude)
        max_d = float(np.max(distances)) if len(distances) else 1.0
        comps: list[Comparable] = []
        for nbr_idx, dist in zip(order, distances):
            if not np.isfinite(dist):
                continue
            m = self.row_meta[int(nbr_idx)]
            comps.append(Comparable(
                name=m.get("name") or "",
                position=m.get("position") or "",
                score=carmelo_score(float(dist), max_d),
                distance=float(dist),
                pooled_toi_5v5=float(m.get("pooled_toi_5v5") or 0.0),
                pooled_iso_xgf60=float(m.get("pooled_iso_xgf60") or 0.0),
                pooled_iso_xga60=float(m.get("pooled_iso_xga60") or 0.0),
                feature_contributions=self._feature_contributions(idx, int(nbr_idx)),
            ))
        return comps

    def _feature_contributions(self, target_idx: int, nbr_idx: int) -> dict[str, float]:
        """How each original column contributed to the distance.

        Computed as the absolute z-score difference per column. Reports use
        this to say "the match is driven by 5v5 iso impact and shot generation,
        not by power-play involvement", etc.
        """
        # Standardize on the fly using stored means/stds
        z_target = (self.matrix_raw[target_idx] - self.means) / self.stds
        z_nbr = (self.matrix_raw[nbr_idx] - self.means) / self.stds
        # Replace NaNs (target had missing) with 0 (mean) before differencing.
        z_target = np.where(np.isnan(z_target), 0.0, z_target)
        z_nbr = np.where(np.isnan(z_nbr), 0.0, z_nbr)
        contribs = np.abs(z_target - z_nbr)
        return {col: float(c) for col, c in zip(self.columns, contribs)}

    # ----- persistence -----
    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "row_meta": self.row_meta,
            "columns": self.columns,
            "matrix_raw": self.matrix_raw.tolist(),
            "means": self.means.tolist(),
            "stds": self.stds.tolist(),
            "pca_components": self.pca_components.tolist(),
            "pca_explained_variance": self.pca_explained_variance.tolist(),
            "embedding": self.embedding.tolist(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComparableIndex":
        return cls(
            rows=d["rows"],
            row_meta=d["row_meta"],
            columns=d["columns"],
            matrix_raw=np.asarray(d["matrix_raw"], dtype=np.float64),
            means=np.asarray(d["means"], dtype=np.float64),
            stds=np.asarray(d["stds"], dtype=np.float64),
            pca_components=np.asarray(d["pca_components"], dtype=np.float64),
            pca_explained_variance=np.asarray(d["pca_explained_variance"], dtype=np.float64),
            embedding=np.asarray(d["embedding"], dtype=np.float64),
            metadata=d.get("metadata", {}),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ComparableIndex":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def build_index_from_features(
    feature_matrix: FeatureMatrix,
    row_meta: list[dict],
    n_components: int = 8,
    metadata: dict | None = None,
) -> ComparableIndex:
    """Fit standardize + PCA + whitening on the matrix and return a ComparableIndex."""
    std = standardize(feature_matrix.matrix)
    n_components = min(n_components, feature_matrix.matrix.shape[1], feature_matrix.matrix.shape[0])
    pca = fit_pca(std.standardized, n_components=n_components)
    embedding = transform_pca(std.standardized, pca, whiten=True)
    return ComparableIndex(
        rows=feature_matrix.rows,
        row_meta=row_meta,
        columns=feature_matrix.columns,
        matrix_raw=feature_matrix.matrix,
        means=std.means,
        stds=std.stds,
        pca_components=pca.components,
        pca_explained_variance=pca.explained_variance,
        embedding=embedding,
        metadata=metadata or {},
    )


def build_cohort_stabilized_impact(
    target: PlayerImpact,
    cohort: list[PlayerImpact],
    target_weight_floor: float = 0.20,
    target_weight_ceiling: float = 0.80,
    pivot_toi_min: float = 600.0,
) -> PlayerImpact:
    """Blend the target's pooled iso impact with a cohort's pooled iso impact.

    Blend ratio is a sigmoid-shaped function of the target's pooled TOI:
    - Below `pivot_toi_min`, the cohort dominates (weight_target → `target_weight_floor`).
    - Above `pivot_toi_min`, the target dominates (weight_target → `target_weight_ceiling`).

    Returns a new PlayerImpact whose iso properties (rate AND variance) are set
    via overrides on the dataclass — so `project_swap()` consumes the BLENDED
    rate AND the BLENDED variance, producing a tighter CI when the cohort
    contributes meaningful sample. Math:

        blend_rate = w_t * target_rate + w_c * cohort_rate
        blend_var  = w_t² * target_var + w_c² * cohort_var

    The cohort's variance is small (lots of pooled minutes), so the second term
    is typically much smaller than the first; the net effect is variance ≈
    w_t² × target_var, i.e. a CI that contracts as the target's relative weight
    falls (i.e. as the target's sample shrinks).
    """
    if not cohort:
        return target

    # Sigmoid blend on log10(toi) around the pivot. Weight on target.
    if target.toi_on <= 0:
        w_t = target_weight_floor
    else:
        rel = (np.log10(max(target.toi_on, 1.0)) - np.log10(pivot_toi_min)) * 1.5
        sigmoid = 1.0 / (1.0 + np.exp(-rel))
        w_t = target_weight_floor + (target_weight_ceiling - target_weight_floor) * float(sigmoid)
    w_c = 1.0 - w_t

    # Pool cohort: sum events, sum minutes.
    coh_xgf_on = sum(c.xgf_on for c in cohort)
    coh_xga_on = sum(c.xga_on for c in cohort)
    coh_xgf_off = sum(c.xgf_off for c in cohort)
    coh_xga_off = sum(c.xga_off for c in cohort)
    coh_toi_on = sum(c.toi_on for c in cohort)
    coh_toi_off = sum(c.toi_off for c in cohort)

    def per60(ev, toi):
        return ev * 60.0 / toi if toi > 0 else 0.0

    def rate_var(ev, toi):
        if toi <= 0:
            return float("inf")
        hours = toi / 60.0
        return max(ev, 1e-9) / (hours ** 2)

    coh_iso_xgf60 = per60(coh_xgf_on, coh_toi_on) - per60(coh_xgf_off, coh_toi_off)
    coh_iso_xga60 = per60(coh_xga_on, coh_toi_on) - per60(coh_xga_off, coh_toi_off)
    coh_iso_xgf60_var = rate_var(coh_xgf_on, coh_toi_on) + rate_var(coh_xgf_off, coh_toi_off)
    coh_iso_xga60_var = rate_var(coh_xga_on, coh_toi_on) + rate_var(coh_xga_off, coh_toi_off)

    t_iso_xgf60 = target.iso_xgf60
    t_iso_xga60 = target.iso_xga60
    t_iso_xgf60_var = target.iso_xgf60_var
    t_iso_xga60_var = target.iso_xga60_var

    blended_iso_xgf60 = w_t * t_iso_xgf60 + w_c * coh_iso_xgf60
    blended_iso_xga60 = w_t * t_iso_xga60 + w_c * coh_iso_xga60
    blended_iso_xgf60_var = (w_t ** 2) * t_iso_xgf60_var + (w_c ** 2) * coh_iso_xgf60_var
    blended_iso_xga60_var = (w_t ** 2) * t_iso_xga60_var + (w_c ** 2) * coh_iso_xga60_var

    # Build the result via override fields so iso properties return the blended
    # rate AND the blended variance directly. Carries the original toi/events
    # values for downstream auditability.
    return PlayerImpact(
        player_id=f"{target.name}|cohort_stabilized",
        name=f"{target.name} (cohort-stabilized; w_target={w_t:.2f})",
        team_id=target.team_id,
        toi_on=target.toi_on,
        toi_off=target.toi_off,
        xgf_on=target.xgf_on,
        xga_on=target.xga_on,
        xgf_off=target.xgf_off,
        xga_off=target.xga_off,
        _iso_xgf60_override=blended_iso_xgf60,
        _iso_xga60_override=blended_iso_xga60,
        _iso_xgf60_var_override=blended_iso_xgf60_var,
        _iso_xga60_var_override=blended_iso_xga60_var,
    )
