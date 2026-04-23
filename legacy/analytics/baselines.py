"""Baseline blending: 3-yr rolling + current-season weight.

Kept simple and explicit. When we later wire Evolving-Hockey RAPM, the prefer_rapm()
hook is where that plugs in.
"""
from __future__ import annotations

import pandas as pd


def rolling_mean(df: pd.DataFrame, value_col: str, by: list[str], weight_col: str = "toi") -> pd.DataFrame:
    """Weighted mean of value_col over rows in df, weighted by weight_col, grouped by `by`."""
    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df[weight_col] = pd.to_numeric(df[weight_col], errors="coerce").fillna(0)
    grouped = df.groupby(by, dropna=False).apply(
        lambda g: (g[value_col] * g[weight_col]).sum() / g[weight_col].sum()
        if g[weight_col].sum() > 0 else float("nan")
    )
    return grouped.reset_index(name=value_col)


def blend_current_with_prior(
    current: pd.DataFrame,
    prior: pd.DataFrame,
    key: list[str],
    value_cols: list[str],
    current_weight: float = 0.6,
) -> pd.DataFrame:
    """Weighted blend: current_weight * current + (1-current_weight) * prior."""
    merged = current.merge(prior, on=key, how="left", suffixes=("_cur", "_pri"))
    for c in value_cols:
        cur = merged[f"{c}_cur"]
        pri = merged[f"{c}_pri"].fillna(cur)
        merged[c] = current_weight * cur + (1 - current_weight) * pri
    return merged[key + value_cols]


def prefer_rapm(default_df: pd.DataFrame, rapm_df: pd.DataFrame | None, key: list[str]) -> pd.DataFrame:
    """Overlay RAPM-derived values when available; fall back to default otherwise."""
    if rapm_df is None or rapm_df.empty:
        return default_df
    merged = default_df.merge(rapm_df, on=key, how="left", suffixes=("_def", "_rapm"))
    overlap = [c.removesuffix("_def") for c in merged.columns if c.endswith("_def") and c.removesuffix("_def") + "_rapm" in merged.columns]
    for col in overlap:
        merged[col] = merged[f"{col}_rapm"].fillna(merged[f"{col}_def"])
    out_cols = key + [c for c in merged.columns if not c.endswith(("_def", "_rapm"))]
    return merged[[*dict.fromkeys(out_cols)]]
