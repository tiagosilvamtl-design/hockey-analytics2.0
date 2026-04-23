"""Swap Scenario page — the core feature. Supports N-for-N swaps with pooled baseline."""
from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from analytics.swap_engine import (
    build_pooled_player_impact,
    combine_swaps,
    project_swap,
)
from config import CURRENT_SEASON, MIN_TOI_FOR_SWAP, STORE_DB
from ui.components import caveat_banner, ci_bar_plot, playoff_footer, source_row

BASELINE_PRESETS: dict[str, list[tuple[str, int]]] = {
    "Pooled: 2 seasons + playoffs (recommended)": [
        ("20252026", 2), ("20252026", 3),
        ("20242025", 2), ("20242025", 3),
    ],
    "Pooled: 25-26 regular + playoffs": [
        ("20252026", 2), ("20252026", 3),
    ],
    "Current season regular only": [
        ("20252026", 2),
    ],
    "24-25 regular only": [
        ("20242025", 2),
    ],
}


@st.cache_data(ttl=300)
def _pool_player_rows(name: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    """All (season, stype) on-ice 5v5 rows for a player, matched by name only
    (handles traded players whose team_id is 'MTL, STL' etc.)."""
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit, name]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        return pd.read_sql_query(
            f"SELECT * FROM skater_stats WHERE sit=? AND split='oi' AND name=? AND ({clauses})",
            c, params=params,
        )


@st.cache_data(ttl=300)
def _pool_team_rows(team_id: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit, team_id]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        return pd.read_sql_query(
            f"SELECT * FROM team_stats WHERE sit=? AND team_id=? AND ({clauses})",
            c, params=params,
        )


@st.cache_data(ttl=300)
def _eligible_players(sit: str, keys: tuple[tuple[str, int], ...], min_toi: float) -> pd.DataFrame:
    """One row per player (by name) with pooled TOI, for the player dropdowns.

    Keeps the 'best' team_id: prefers a current-season single-team row; otherwise
    uses the most-recent-team substring. This affects display only; the actual
    math pools all rows for that name.
    """
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_DB) as c:
        df = pd.read_sql_query(
            f"SELECT season, stype, team_id, name, position, toi FROM skater_stats "
            f"WHERE sit=? AND split='oi' AND ({clauses})",
            c, params=params,
        )
    if df.empty:
        return df
    df["toi"] = pd.to_numeric(df["toi"], errors="coerce").fillna(0.0)
    # primary team_id: most-recent season, simplest (non-composite) team
    df_sorted = df.sort_values(["season", "stype"], ascending=[False, False])
    df_sorted["is_single_team"] = ~df_sorted["team_id"].astype(str).str.contains(",", na=False)
    df_sorted = df_sorted.sort_values(["name", "is_single_team", "season", "stype"], ascending=[True, False, False, False])
    primary = df_sorted.drop_duplicates(subset=["name"], keep="first")[["name", "team_id", "position"]]
    pooled_toi = df.groupby("name", as_index=False)["toi"].sum()
    out = primary.merge(pooled_toi, on="name", how="left")
    out = out[out["toi"].fillna(0) >= min_toi]
    return out.sort_values("name").reset_index(drop=True)


@st.cache_data(ttl=300)
def _playoff_teams(season: str, sit: str) -> list[str]:
    with sqlite3.connect(STORE_DB) as c:
        try:
            df = pd.read_sql_query(
                "SELECT DISTINCT team_id FROM team_stats WHERE season=? AND stype=3 AND sit=?",
                c, params=(season, sit),
            )
            return sorted([t for t in df["team_id"].dropna().unique()])
        except Exception:
            return []


def _default_slot_minutes(name: str, team_id: str, sit: str, is_playoff_ctx: bool) -> float:
    """Best guess for the player's per-game minutes in the chosen context."""
    with sqlite3.connect(STORE_DB) as c:
        if is_playoff_ctx:
            df = pd.read_sql_query(
                "SELECT toi, gp FROM skater_stats WHERE season=? AND stype=3 AND sit=? AND split='oi' AND name=? AND team_id=?",
                c, params=(CURRENT_SEASON, sit, name, team_id),
            )
            if not df.empty and float(df["toi"].iloc[0] or 0) > 0 and int(df["gp"].iloc[0] or 0) > 0:
                return max(4.0, min(28.0, float(df["toi"].iloc[0]) / int(df["gp"].iloc[0])))
        df2 = pd.read_sql_query(
            "SELECT toi, gp FROM skater_stats WHERE season=? AND stype=2 AND sit=? AND split='oi' AND name=? "
            "AND (team_id=? OR team_id LIKE ?)",
            c, params=(CURRENT_SEASON, sit, name, team_id, f"%{team_id}%"),
        )
    if df2.empty:
        return 16.0
    toi = float(df2["toi"].iloc[0] or 0.0)
    gp = int(df2["gp"].iloc[0] or 0)
    if gp <= 0 or toi <= 0:
        return 16.0
    return max(4.0, min(28.0, toi / gp))


def _ensure_state() -> None:
    if "swap_pairs" not in st.session_state:
        st.session_state.swap_pairs = [{"id": 0}]
        st.session_state._next_swap_id = 1


def render() -> None:
    st.title("Swap Scenario — Δ in projected possession/xG")
    st.caption(
        "Pick one or more OUT→IN pairs and the tool projects the combined team-level "
        "per-60 deltas with 80% CI bands. Directional, not predictive."
    )

    _ensure_state()

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        sit = st.selectbox("Strength state", ["5v5", "all"], index=0, key="swap_sit")
    with c2:
        ctx_label = st.selectbox("Context", ["2026 Playoffs", "Regular season 2025-26"], index=0, key="swap_stype")
        is_playoff_ctx = ctx_label == "2026 Playoffs"
    with c3:
        baseline_label = st.selectbox(
            "Baseline sample for isolated impact",
            list(BASELINE_PRESETS.keys()),
            index=0,
            key="swap_baseline",
            help="Pooling across seasons gives a bigger, more stable sample — matters for low-GP "
                 "players like Dach (37 GP) or traded players like Texier. The default pools "
                 "2024-25 reg + playoffs with 2025-26 reg + playoffs.",
        )
    baseline_keys = tuple(BASELINE_PRESETS[baseline_label])

    eligible = _eligible_players(sit, baseline_keys, MIN_TOI_FOR_SWAP)
    if eligible.empty:
        st.warning(
            f"No players meet the {MIN_TOI_FOR_SWAP:.0f}-min pooled minimum in "
            f"`{baseline_label}`. Pick a broader baseline or refresh data."
        )
        playoff_footer()
        return

    teams_in_data = sorted(eligible["team_id"].dropna().unique())
    if is_playoff_ctx:
        playoff_teams = _playoff_teams(CURRENT_SEASON, sit)
        out_team_options = [t for t in teams_in_data if t in playoff_teams] or teams_in_data
    else:
        out_team_options = teams_in_data

    st.divider()
    st.subheader("Swap pairs")
    st.caption(
        "Add as many OUT→IN pairs as you want. Each pair's isolated impact is computed "
        f"against the receiving team's pooled totals over the chosen baseline."
    )

    # Render swap pair rows
    swap_results = []
    pair_rows = []
    to_remove: int | None = None

    for idx, pair in enumerate(st.session_state.swap_pairs):
        pid = pair["id"]
        with st.container(border=True):
            pcol_hdr, pcol_rm = st.columns([5, 1])
            with pcol_hdr:
                st.markdown(f"**Pair #{idx + 1}**")
            with pcol_rm:
                if len(st.session_state.swap_pairs) > 1:
                    if st.button("Remove", key=f"rm_{pid}"):
                        to_remove = idx

            c4, c5 = st.columns(2)
            with c4:
                out_team = st.selectbox(
                    "OUT — team", out_team_options,
                    key=f"out_team_{pid}",
                    index=0,
                )
                out_pool = eligible[eligible["team_id"] == out_team]
                out_label = st.selectbox(
                    "OUT — player", out_pool["name"].tolist(),
                    key=f"out_p_{pid}",
                )
            with c5:
                in_team_choice = st.selectbox(
                    "IN — team", ["(any team)"] + teams_in_data,
                    key=f"in_team_{pid}",
                )
                in_pool = eligible if in_team_choice == "(any team)" else eligible[eligible["team_id"] == in_team_choice]
                in_default = min(idx, max(0, len(in_pool) - 1))
                in_label = st.selectbox(
                    "IN — player", in_pool["name"].tolist(),
                    key=f"in_p_{pid}",
                    index=in_default,
                )

            if not out_label or not in_label:
                continue

            default_slot = _default_slot_minutes(out_label, out_team, sit, is_playoff_ctx)
            slot_minutes = st.slider(
                f"Slot minutes/game ({out_label}'s usual role)",
                min_value=4.0, max_value=28.0,
                value=float(round(default_slot, 1)),
                step=0.5, key=f"slot_{pid}",
            )

            # pool rows for each player and the receiving team
            out_rows = _pool_player_rows(out_label, sit, baseline_keys)
            in_rows = _pool_player_rows(in_label, sit, baseline_keys)
            team_rows = _pool_team_rows(out_team, sit, baseline_keys)
            if team_rows.empty:
                st.error(f"No team_stats rows for {out_team} in this baseline.")
                continue

            out_imp = build_pooled_player_impact(out_rows, team_rows, out_team)
            in_imp = build_pooled_player_impact(in_rows, team_rows, out_team)
            res = project_swap(out_imp, in_imp, slot_minutes=slot_minutes, strength_state=sit)
            swap_results.append(res)

            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric(f"Δ xGF/60", f"{res.delta_xgf60:+.3f}",
                         help=f"80% CI: ({res.delta_xgf60_ci80[0]:+.3f}, {res.delta_xgf60_ci80[1]:+.3f})")
            mcol2.metric(f"Δ xGA/60", f"{res.delta_xga60:+.3f}",
                         help=f"80% CI: ({res.delta_xga60_ci80[0]:+.3f}, {res.delta_xga60_ci80[1]:+.3f})")
            mcol3.metric(f"Net/60 (xGF−xGA)", f"{res.delta_xgf60 - res.delta_xga60:+.3f}")

            pair_rows.append({
                "pair": idx + 1,
                "OUT": f"{out_label} [{out_team}]",
                "OUT TOI (pooled)": f"{out_imp.toi_on:.0f}m",
                "IN": f"{in_label} [{in_imp.team_id if in_team_choice == '(any team)' else in_team_choice}]",
                "IN TOI (pooled)": f"{in_imp.toi_on:.0f}m",
                "slot min": f"{slot_minutes:.1f}",
                "Δ xGF/60": round(res.delta_xgf60, 3),
                "Δ xGA/60": round(res.delta_xga60, 3),
                "iso_xgf60 OUT→IN": f"{out_imp.iso_xgf60:+.3f}  →  {in_imp.iso_xgf60:+.3f}",
                "iso_xga60 OUT→IN": f"{out_imp.iso_xga60:+.3f}  →  {in_imp.iso_xga60:+.3f}",
            })

    if to_remove is not None:
        st.session_state.swap_pairs.pop(to_remove)
        st.rerun()

    bcol1, _ = st.columns([1, 4])
    with bcol1:
        if st.button("＋ Add swap pair"):
            nid = st.session_state._next_swap_id
            st.session_state._next_swap_id = nid + 1
            st.session_state.swap_pairs.append({"id": nid})
            st.rerun()

    st.divider()

    if not swap_results:
        st.info("Configure at least one swap pair above.")
        playoff_footer()
        return

    st.subheader("Combined impact on team per-60 rates")
    combined = combine_swaps(swap_results)

    fig = ci_bar_plot(
        title=f"Combined swap Δ ({len(swap_results)} pair{'s' if len(swap_results) != 1 else ''}, {sit})",
        y_labels=["xGF/60", "xGA/60"],
        point=[combined.delta_xgf60, combined.delta_xga60],
        ci_low=[combined.delta_xgf60_ci80[0], combined.delta_xga60_ci80[0]],
        ci_high=[combined.delta_xgf60_ci80[1], combined.delta_xga60_ci80[1]],
    )
    st.plotly_chart(fig, use_container_width=True)

    net = combined.delta_xgf60 - combined.delta_xga60
    st.metric("Combined net per-60 shift (xGF − xGA)", f"{net:+.3f}")

    extra_notes = [
        f"Baseline: **{baseline_label}**. Impacts pool all rows where the player's "
        f"name appears in that window — captures traded-player minutes (e.g., 'MTL, STL').",
    ]
    if is_playoff_ctx:
        extra_notes.append("Slot minutes reflect 2026 playoff usage where available; else 25-26 regular.")
    caveat_banner(extra_notes + [combined.sample_note])

    with st.expander("Per-pair breakdown"):
        st.dataframe(pd.DataFrame(pair_rows), use_container_width=True, hide_index=True)

    source_row(["NST", "EH", "HV"])
    playoff_footer()
