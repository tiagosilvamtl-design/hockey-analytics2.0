"""Shared Streamlit UI bits: caveat banner, source badges, CI bars."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

SOURCE_BADGES = {
    "NST": ("Natural Stat Trick", "https://www.naturalstattrick.com/"),
    "EH": ("Evolving-Hockey", "https://evolving-hockey.com/"),
    "MP": ("MoneyPuck", "https://moneypuck.com/"),
    "HV": ("HockeyViz (McCurdy)", "https://hockeyviz.com/"),
    "JF": ("JFresh", "https://jfresh.substack.com/"),
    "ATZ": ("All Three Zones (Sznajder)", "https://www.allthreezones.com/"),
    "DL": ("Luszczyszyn / The Athletic", "https://x.com/domluszczyszyn"),
}


def caveat_banner(extra_notes: list[str] | None = None) -> None:
    notes = extra_notes or []
    st.info(
        "**Interpret with care.** Playoff samples are 16–28 games; confidence "
        "intervals are wide and goalie variance dominates short series. "
        "Projections assume usage held constant and do not control for score "
        "state, zone starts, or quality of competition.\n\n"
        + ("\n\n".join(f"- {n}" for n in notes) if notes else ""),
        icon="ℹ️",
    )


def source_row(keys: list[str]) -> None:
    chips = []
    for k in keys:
        if k not in SOURCE_BADGES:
            continue
        label, url = SOURCE_BADGES[k]
        chips.append(f"[{label}]({url})")
    if chips:
        st.caption("Sources: " + " · ".join(chips))


def ci_bar_plot(
    title: str,
    y_labels: list[str],
    point: list[float],
    ci_low: list[float],
    ci_high: list[float],
    x_title: str = "Δ per 60 minutes",
) -> go.Figure:
    fig = go.Figure()
    for i, label in enumerate(y_labels):
        fig.add_trace(
            go.Scatter(
                x=[ci_low[i], ci_high[i]],
                y=[label, label],
                mode="lines",
                line=dict(width=6),
                name=f"{label} 80% CI",
                hovertemplate=f"CI: %{{x:.3f}}<extra>{label}</extra>",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[point[i]],
                y=[label],
                mode="markers",
                marker=dict(size=12, symbol="diamond"),
                name=label,
                hovertemplate=f"Δ = %{{x:.3f}}<extra>{label}</extra>",
                showlegend=False,
            )
        )
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="",
        height=220 + 40 * len(y_labels),
        margin=dict(l=20, r=20, t=60, b=40),
    )
    return fig


def playoff_footer() -> None:
    st.caption(
        "Projections use current-season + 3-yr rolling baselines. Playoff "
        "samples are 16–28 games; goalie variance dominates. **Do not bet on this.**"
    )
