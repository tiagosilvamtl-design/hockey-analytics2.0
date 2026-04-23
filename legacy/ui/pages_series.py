"""Series Overview page: all active 2026 playoff matchups at a glance."""
from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from config import CURRENT_SEASON, STORE_DB
from ui.components import caveat_banner, playoff_footer, source_row


@st.cache_data(ttl=300)
def load_team_stats(season: str, stype: int, sit: str) -> pd.DataFrame:
    with sqlite3.connect(STORE_DB) as c:
        try:
            return pd.read_sql_query(
                "SELECT * FROM team_stats WHERE season=? AND stype=? AND sit=?",
                c,
                params=(season, stype, sit),
            )
        except Exception:
            return pd.DataFrame()


def render() -> None:
    st.title("2026 Playoffs — Series Overview")
    caveat_banner()

    col1, col2 = st.columns([1, 1])
    with col1:
        sit = st.selectbox("Strength state", ["5v5", "all"], index=0)
    with col2:
        stype_label = st.selectbox("Game type", ["Playoff", "Regular season"], index=0)
    stype = 3 if stype_label == "Playoff" else 2

    df = load_team_stats(CURRENT_SEASON, stype, sit)
    if df.empty:
        st.warning(
            "No data cached yet. Run `python -m data.ingest` after the build finishes, "
            "or hit 'Refresh data' on the Team Dashboard page."
        )
        return

    display_cols = [c for c in ["team_id", "gp", "toi", "cf_pct", "xgf_pct", "hdcf_pct", "gf_pct", "pdo"] if c in df.columns]
    st.subheader(f"{stype_label} {CURRENT_SEASON[:4]}–{CURRENT_SEASON[4:]} @ {sit}")
    st.dataframe(
        df[display_cols].sort_values(display_cols[-2] if len(display_cols) >= 2 else display_cols[0], ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    source_row(["NST"])
    playoff_footer()
