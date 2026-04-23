"""Anecdata Comparison: curated quotes paired with model stance."""
from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from analytics.swap_engine import build_player_impact
from anecdata.store import add_quote, compare_stances, list_quotes, model_stance_from_impact
from config import CURRENT_SEASON, STORE_DB
from data.schema import Quote
from scipy import stats as _stats
from ui.components import caveat_banner, playoff_footer, source_row


@st.cache_data(ttl=300)
def _skaters_with_team(season: str, stype: int, sit: str) -> pd.DataFrame:
    with sqlite3.connect(STORE_DB) as c:
        try:
            return pd.read_sql_query(
                "SELECT * FROM skater_stats WHERE season=? AND stype=? AND sit=? AND split='oi'",
                c,
                params=(season, stype, sit),
            )
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=300)
def _team_rows(season: str, stype: int, sit: str) -> pd.DataFrame:
    with sqlite3.connect(STORE_DB) as c:
        try:
            return pd.read_sql_query(
                "SELECT * FROM team_stats WHERE season=? AND stype=? AND sit=?",
                c,
                params=(season, stype, sit),
            )
        except Exception:
            return pd.DataFrame()


def _model_stance_for_player(row: pd.Series, team_row: pd.Series) -> tuple[str, float, float]:
    imp = build_player_impact(row, team_row)
    z = _stats.norm.ppf(0.9)
    ci = (
        imp.iso_xgf60 - z * (imp.iso_xgf60_var ** 0.5),
        imp.iso_xgf60 + z * (imp.iso_xgf60_var ** 0.5),
    )
    stance = model_stance_from_impact(imp.iso_xgf60, imp.iso_xga60, ci)
    return stance, imp.iso_xgf60, imp.iso_xga60


def render() -> None:
    st.title("Anecdata ↔ Model — do they agree?")
    st.caption(
        "Curated quotes from coaches, players, and analysts. User tags each quote's "
        "stance; the tool shows the model's stance for the same player and flags "
        "agreement or disagreement. No automated sentiment — prior NLP work on "
        "hockey interviews (Tamming 2019) showed weak signal."
    )
    caveat_banner([
        "Quote stance is user-entered. The tool does not infer sentiment from text.",
        "Model stance is coarse: bullish/bearish/mixed/neutral based on iso_xGF60 CI and iso_xGA60 sign.",
    ])

    sit = st.selectbox("Strength state for model stance", ["5v5", "all"], index=0, key="anec_sit")
    stype_label = st.selectbox("Game type", ["Playoff", "Regular season"], index=0, key="anec_stype")
    stype = 3 if stype_label == "Playoff" else 2

    skaters = _skaters_with_team(CURRENT_SEASON, stype, sit)
    teams_df = _team_rows(CURRENT_SEASON, stype, sit)

    st.subheader("Add a quote")
    with st.form("new_quote"):
        player_options = sorted(
            (skaters["name"].astype(str) + "  [" + skaters["team_id"].astype(str) + "]").tolist()
        ) if not skaters.empty else []
        player_label = st.selectbox("Player", player_options) if player_options else None
        source = st.text_input("Source (e.g., 'The Athletic', 'Sportsnet')")
        url = st.text_input("URL")
        author = st.text_input("Author / speaker")
        title = st.text_input("Title / lede (≤ 400 chars — no full quotes)", max_chars=400)
        lede = st.text_area("Short paraphrase or truncated lede (≤ 400 chars)", max_chars=400)
        date = st.date_input("Date")
        stance = st.selectbox("Stance (your read)", ["bullish", "bearish", "neutral", "mixed"], index=2)
        submitted = st.form_submit_button("Save quote")
        if submitted and player_label and source:
            prow = skaters[(skaters["name"].astype(str) + "  [" + skaters["team_id"].astype(str) + "]") == player_label].iloc[0]
            add_quote(Quote(
                player_id=str(prow.get("player_id") or prow["name"]),
                team_id=str(prow.get("team_id")),
                source=source, url=url, author=author, title=title, lede=lede,
                date=str(date), stance=stance, entered_by="Xavier",
            ))
            st.success("Quote saved.")
            st.cache_data.clear()

    st.subheader("Quotes × model")
    quotes = list_quotes()
    if quotes.empty:
        st.caption("No quotes yet. Add one above.")
        playoff_footer()
        return

    rows = []
    for _, q in quotes.iterrows():
        pid = q.get("player_id")
        tid = q.get("team_id")
        if not pid or skaters.empty:
            rows.append({**q.to_dict(), "model_stance": "n/a", "agreement": "n/a"})
            continue
        prow_match = skaters[skaters["player_id"] == pid]
        if prow_match.empty:
            rows.append({**q.to_dict(), "model_stance": "n/a", "agreement": "n/a"})
            continue
        trow_match = teams_df[teams_df["team_id"] == tid]
        if trow_match.empty:
            rows.append({**q.to_dict(), "model_stance": "n/a", "agreement": "n/a"})
            continue
        m_stance, iso_xgf, iso_xga = _model_stance_for_player(prow_match.iloc[0], trow_match.iloc[0])
        rows.append({
            **q.to_dict(),
            "model_stance": m_stance,
            "iso_xgf60": round(iso_xgf, 3),
            "iso_xga60": round(iso_xga, 3),
            "agreement": compare_stances(m_stance, q.get("stance", "neutral")),
        })
    df = pd.DataFrame(rows)
    show = [c for c in ["date", "source", "author", "title", "stance", "model_stance", "agreement", "iso_xgf60", "iso_xga60", "url"] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    source_row(["NST", "DL", "HV", "ATZ"])
    playoff_footer()
