"""Team Dashboard: selected team's skater tables + refresh controls."""
from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from config import CURRENT_SEASON, STORE_DB
from data.ingest import refresh_skater_stats, refresh_team_stats
from data.nst_client import NstClient
from ui.components import caveat_banner, playoff_footer, source_row


@st.cache_data(ttl=300)
def _skater_rows(season: str, stype: int, sit: str, split: str, team_id: str | None) -> pd.DataFrame:
    with sqlite3.connect(STORE_DB) as c:
        q = "SELECT * FROM skater_stats WHERE season=? AND stype=? AND sit=? AND split=?"
        args: list = [season, stype, sit, split]
        if team_id:
            q += " AND team_id = ?"
            args.append(team_id)
        return pd.read_sql_query(q, c, params=args)


@st.cache_data(ttl=300)
def _teams(season: str, stype: int, sit: str) -> list[str]:
    with sqlite3.connect(STORE_DB) as c:
        try:
            df = pd.read_sql_query(
                "SELECT DISTINCT team_id FROM team_stats WHERE season=? AND stype=? AND sit=?",
                c,
                params=(season, stype, sit),
            )
            return sorted([t for t in df["team_id"].dropna().unique()])
        except Exception:
            return []


def render() -> None:
    st.title("Team Dashboard")
    caveat_banner()

    c1, c2, c3 = st.columns(3)
    with c1:
        sit = st.selectbox("Strength state", ["5v5", "all"], index=0, key="team_sit")
    with c2:
        stype_label = st.selectbox("Game type", ["Playoff", "Regular season"], index=0, key="team_stype")
    stype = 3 if stype_label == "Playoff" else 2
    with c3:
        teams = _teams(CURRENT_SEASON, stype, sit)
        team = st.selectbox("Team", teams, index=0) if teams else None

    with st.expander("Refresh data from NST", expanded=not teams):
        st.caption("One click = up to 3 polite requests to data.naturalstattrick.com.")
        if st.button("Refresh this (season, stype, sit)"):
            client = NstClient()
            with st.spinner("Fetching NST..."):
                refresh_team_stats(client, CURRENT_SEASON, stype, sit)
                refresh_skater_stats(client, CURRENT_SEASON, stype, sit, split="oi")
                refresh_skater_stats(client, CURRENT_SEASON, stype, sit, split="bio")
            st.cache_data.clear()
            st.success("Refreshed. Reload to see the new data.")

    if not team:
        st.info("Pick a team above once data is cached.")
        playoff_footer()
        return

    st.subheader(f"{team} — on-ice @ {sit}, {stype_label.lower()}")
    oi = _skater_rows(CURRENT_SEASON, stype, sit, "oi", team)
    show = [c for c in ["name", "position", "gp", "toi", "cf_pct", "xgf_pct", "hdcf_pct", "gf_pct"] if c in oi.columns]
    if not oi.empty:
        st.dataframe(
            oi[show].sort_values("toi" if "toi" in show else show[0], ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No on-ice rows for this selection.")

    st.subheader("Individual (bio)")
    bio = _skater_rows(CURRENT_SEASON, stype, sit, "bio", team)
    bio_show = [c for c in ["name", "position", "gp", "toi", "gf", "xgf"] if c in bio.columns]
    if not bio.empty:
        st.dataframe(
            bio[bio_show].sort_values("xgf" if "xgf" in bio_show else bio_show[0], ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No individual rows for this selection.")

    source_row(["NST"])
    playoff_footer()
