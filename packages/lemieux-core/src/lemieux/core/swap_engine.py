"""Swap scenario engine.

Given per-player on-ice events and team totals (at any strength state), compute each
player's isolated xGF/60 and xGA/60 impact via (on-ice) minus (team-without-player)
rates. Project a swap: replace player A's slot minutes with player B's isolated
rate, propagate Poisson-approximated variance, return deltas with an 80% CI by
default.

This is NOT true RAPM. It's a transparent on/off delta with an honest noise model.
When Evolving-Hockey RAPM values or similar can be sourced, callers are encouraged
to prefer those and fall back to on/off deltas otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

# Defaults — callers can override per call.
MIN_TOI_FOR_SWAP: float = 200.0
LINE_COMBO_MIN_TOI: float = 50.0
LINE_COMBO_DIVERGENCE_PP: float = 0.10


@dataclass
class PlayerImpact:
    """Isolated on/off impact rates, per 60 minutes, at one strength state."""

    player_id: str
    name: str
    team_id: str
    toi_on: float           # minutes on-ice
    toi_off: float          # minutes team-without-player
    xgf_on: float
    xga_on: float
    xgf_off: float
    xga_off: float

    @property
    def iso_xgf60(self) -> float:
        return self._per60(self.xgf_on, self.toi_on) - self._per60(self.xgf_off, self.toi_off)

    @property
    def iso_xga60(self) -> float:
        return self._per60(self.xga_on, self.toi_on) - self._per60(self.xga_off, self.toi_off)

    @property
    def iso_xgf60_var(self) -> float:
        return self._rate_var(self.xgf_on, self.toi_on) + self._rate_var(self.xgf_off, self.toi_off)

    @property
    def iso_xga60_var(self) -> float:
        return self._rate_var(self.xga_on, self.toi_on) + self._rate_var(self.xga_off, self.toi_off)

    @staticmethod
    def _per60(events: float, toi_min: float) -> float:
        if toi_min <= 0:
            return 0.0
        return events * 60.0 / toi_min

    @staticmethod
    def _rate_var(events: float, toi_min: float) -> float:
        """Var(events/hours) ≈ events / hours² under Poisson approx."""
        if toi_min <= 0:
            return float("inf")
        hours = toi_min / 60.0
        return max(events, 1e-9) / (hours ** 2)


@dataclass
class SwapResult:
    delta_xgf60: float
    delta_xga60: float
    delta_xgf60_ci80: tuple[float, float]
    delta_xga60_ci80: tuple[float, float]
    slot_minutes: float
    strength_state: str
    sample_note: str
    line_combo_check: str | None = None


def build_player_impact(
    skater_oi_row: pd.Series,
    team_stats_row: pd.Series,
) -> PlayerImpact:
    """Derive a PlayerImpact from one on-ice skater row + team totals for same (season, stype, sit)."""
    toi_on = float(skater_oi_row.get("toi") or 0.0)
    toi_team = float(team_stats_row.get("toi") or 0.0)
    xgf_on = float(skater_oi_row.get("xgf") or 0.0)
    xga_on = float(skater_oi_row.get("xga") or 0.0)
    xgf_team = float(team_stats_row.get("xgf") or 0.0)
    xga_team = float(team_stats_row.get("xga") or 0.0)
    toi_off = max(toi_team - toi_on, 0.0)
    xgf_off = max(xgf_team - xgf_on, 0.0)
    xga_off = max(xga_team - xga_on, 0.0)
    return PlayerImpact(
        player_id=str(skater_oi_row.get("player_id") or skater_oi_row.get("name")),
        name=str(skater_oi_row.get("name") or ""),
        team_id=str(skater_oi_row.get("team_id") or skater_oi_row.get("team") or ""),
        toi_on=toi_on,
        toi_off=toi_off,
        xgf_on=xgf_on,
        xga_on=xga_on,
        xgf_off=xgf_off,
        xga_off=xga_off,
    )


def build_pooled_player_impact(
    player_rows: pd.DataFrame,
    team_rows: pd.DataFrame,
    team_id: str,
) -> PlayerImpact:
    """Pool multiple (season, stype) rows for a single player and team.

    `player_rows` = all on-ice rows for one player across whichever seasons/stypes
    the caller wants in the baseline.
    `team_rows`   = team_stats rows for the receiving team across the same keys.

    Events (xgf, xga, toi) are summed, not averaged — weighting naturally happens
    by minutes. For traded players whose team_id is composite (e.g., "MTL, STL"),
    this pools all their minutes; the caller compares against the receiving team's
    totals, which is a mild approximation.
    """
    toi_on = float(player_rows["toi"].fillna(0).sum()) if len(player_rows) else 0.0
    xgf_on = float(player_rows["xgf"].fillna(0).sum()) if len(player_rows) else 0.0
    xga_on = float(player_rows["xga"].fillna(0).sum()) if len(player_rows) else 0.0
    toi_team = float(team_rows["toi"].fillna(0).sum()) if len(team_rows) else 0.0
    xgf_team = float(team_rows["xgf"].fillna(0).sum()) if len(team_rows) else 0.0
    xga_team = float(team_rows["xga"].fillna(0).sum()) if len(team_rows) else 0.0
    toi_off = max(toi_team - toi_on, 0.0)
    xgf_off = max(xgf_team - xgf_on, 0.0)
    xga_off = max(xga_team - xga_on, 0.0)
    name = str(player_rows["name"].iloc[0]) if len(player_rows) else ""
    return PlayerImpact(
        player_id=f"{name}|pooled",
        name=name,
        team_id=team_id,
        toi_on=toi_on, toi_off=toi_off,
        xgf_on=xgf_on, xga_on=xga_on,
        xgf_off=xgf_off, xga_off=xga_off,
    )


def combine_swaps(results: list[SwapResult], confidence: float = 0.80) -> SwapResult:
    """Combine independent swap results: sum deltas, add variances (quadrature)."""
    if not results:
        raise ValueError("combine_swaps needs at least one result")
    d_xgf = sum(r.delta_xgf60 for r in results)
    d_xga = sum(r.delta_xga60 for r in results)
    z = stats.norm.ppf(0.5 + confidence / 2.0)
    v_xgf = 0.0
    v_xga = 0.0
    for r in results:
        half_f = (r.delta_xgf60_ci80[1] - r.delta_xgf60_ci80[0]) / 2.0
        half_a = (r.delta_xga60_ci80[1] - r.delta_xga60_ci80[0]) / 2.0
        v_xgf += (half_f / z) ** 2
        v_xga += (half_a / z) ** 2
    s_xgf = v_xgf ** 0.5
    s_xga = v_xga ** 0.5
    return SwapResult(
        delta_xgf60=d_xgf,
        delta_xga60=d_xga,
        delta_xgf60_ci80=(d_xgf - z * s_xgf, d_xgf + z * s_xgf),
        delta_xga60_ci80=(d_xga - z * s_xga, d_xga + z * s_xga),
        slot_minutes=sum(r.slot_minutes for r in results),
        strength_state=results[0].strength_state,
        sample_note=f"Combined {len(results)} independent swap(s); variances added in quadrature.",
    )


def project_swap(
    out_player: PlayerImpact,
    in_player: PlayerImpact,
    slot_minutes: float | None = None,
    team_total_toi: float | None = None,
    strength_state: str = "5v5",
    confidence: float = 0.80,
    min_toi: float = MIN_TOI_FOR_SWAP,
) -> SwapResult:
    """Project the swap's effect on team per-60 rates.

    Core formula:
        team_delta_xgf/60 = (iso_in.xgf60 - iso_out.xgf60) * (slot_minutes / 60)

    Result units: xG per 60 minutes of team play at the chosen strength state.
    """
    m = slot_minutes if slot_minutes is not None else max(out_player.toi_on / _games(out_player), 10.0)
    slot_share = min(max(m / 60.0, 0.0), 1.0)

    d_xgf = (in_player.iso_xgf60 - out_player.iso_xgf60) * slot_share
    d_xga = (in_player.iso_xga60 - out_player.iso_xga60) * slot_share

    d_xgf_var = (in_player.iso_xgf60_var + out_player.iso_xgf60_var) * (slot_share ** 2)
    d_xga_var = (in_player.iso_xga60_var + out_player.iso_xga60_var) * (slot_share ** 2)

    z = stats.norm.ppf(0.5 + confidence / 2.0)
    xgf_ci = (d_xgf - z * np.sqrt(d_xgf_var), d_xgf + z * np.sqrt(d_xgf_var))
    xga_ci = (d_xga - z * np.sqrt(d_xga_var), d_xga + z * np.sqrt(d_xga_var))

    notes: list[str] = []
    if out_player.toi_on < min_toi:
        notes.append(f"OUT player under {min_toi:.0f}-min threshold ({out_player.toi_on:.0f}m).")
    if in_player.toi_on < min_toi:
        notes.append(f"IN player under {min_toi:.0f}-min threshold ({in_player.toi_on:.0f}m).")
    notes.append("Score/zone context not controlled. Goalie-independent.")
    notes.append(f"{int(confidence*100)}% CI via Poisson approx on event counts.")

    return SwapResult(
        delta_xgf60=d_xgf,
        delta_xga60=d_xga,
        delta_xgf60_ci80=xgf_ci,
        delta_xga60_ci80=xga_ci,
        slot_minutes=m,
        strength_state=strength_state,
        sample_note=" ".join(notes),
    )


def line_combo_sanity(
    combo_df: pd.DataFrame,
    player_ids_after_swap: tuple[str, ...],
    predicted_xgf_pct: float,
    min_toi: float = LINE_COMBO_MIN_TOI,
    divergence_pp: float = LINE_COMBO_DIVERGENCE_PP,
) -> str | None:
    """If the proposed trio has a known line-combo row, compare observed xGF% to model."""
    if combo_df is None or combo_df.empty:
        return None
    ids_set = set(player_ids_after_swap)
    matches = combo_df[combo_df["player_ids"].apply(lambda s: set(str(s).split("|")) == ids_set)]
    if matches.empty:
        return None
    row = matches.iloc[0]
    if (row.get("toi") or 0.0) < min_toi:
        return None
    observed = row.get("xgf_pct")
    if observed is None or pd.isna(observed):
        return None
    diff = abs(float(observed) - predicted_xgf_pct)
    if diff > divergence_pp * 100:
        return (
            f"Line-combo observation disagrees with model: "
            f"observed xGF% {observed:.1f} vs. predicted {predicted_xgf_pct:.1f} "
            f"({row.get('toi'):.0f} min together)."
        )
    return (
        f"Line-combo sanity check OK: observed xGF% {observed:.1f} "
        f"(~{row.get('toi'):.0f} min)."
    )


def _games(p: PlayerImpact) -> float:
    return max(p.toi_on / 18.0, 1.0)
