"""FastMCP server exposing Lemieux analytics tools and resources.

Every tool returns structured dicts with sample-size metadata alongside point
estimates so the MCP client (typically Claude) cannot quietly omit uncertainty.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

import pandas as pd
from lemieux.core import (
    build_pooled_player_impact,
    project_swap,
)
from lemieux.glossary import list_terms, render_mcp_resource

from mcp.server.fastmcp import FastMCP

# ---------- server instance ----------
mcp = FastMCP("lemieux")

# Store path is set at CLI startup; fallback to a default.
STORE_PATH: Path = Path(
    os.environ.get("LEMIEUX_STORE", Path.home() / ".lemieux" / "store.sqlite")
)

POOLED_KEYS: tuple[tuple[str, int], ...] = (
    ("20252026", 2), ("20252026", 3),
    ("20242025", 2), ("20242025", 3),
)
CURRENT_ONLY_KEYS: tuple[tuple[str, int], ...] = (
    ("20252026", 2), ("20252026", 3),
)


# ---------- helpers ----------
def _resolve_keys(baseline: str) -> tuple[tuple[str, int], ...]:
    return {
        "pooled_2_seasons": POOLED_KEYS,
        "current_only": CURRENT_ONLY_KEYS,
    }.get(baseline, POOLED_KEYS)


def _pool_player_rows(name: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit, name]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_PATH) as c:
        return pd.read_sql_query(
            f"SELECT * FROM skater_stats WHERE sit=? AND split='oi' AND name=? AND ({clauses})",
            c, params=params,
        )


def _pool_team_rows(team_id: str, sit: str, keys: tuple[tuple[str, int], ...]) -> pd.DataFrame:
    if not keys:
        return pd.DataFrame()
    clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
    params: list = [sit, team_id]
    for s, st_ in keys:
        params.extend([s, st_])
    with sqlite3.connect(STORE_PATH) as c:
        return pd.read_sql_query(
            f"SELECT * FROM team_stats WHERE sit=? AND team_id=? AND ({clauses})",
            c, params=params,
        )


# ==================== TOOLS ====================
@mcp.tool()
def query_skater_stats(
    team_id: str,
    season: str = "20252026",
    stype: int = 2,
    sit: str = "5v5",
    split: str = "oi",
) -> list[dict]:
    """Return all skater-stat rows for a team in one (season, stype, sit, split) slice.

    Args:
        team_id: 3-letter abbrev, e.g., 'MTL', 'T.B', 'L.A'. Substring match used to catch traded players.
        season: NST format 'YYYYYYYY', e.g. '20252026'.
        stype: 2 = regular season, 3 = playoff.
        sit: strength state: '5v5', '5v4', '4v5', 'all'.
        split: 'oi' (on-ice team events) or 'bio' (individual).

    Every row includes sample-size indicators (gp, toi).
    """
    with sqlite3.connect(STORE_PATH) as c:
        df = pd.read_sql_query(
            "SELECT * FROM skater_stats "
            "WHERE season=? AND stype=? AND sit=? AND split=? "
            "AND (team_id=? OR team_id LIKE ?)",
            c, params=(season, stype, sit, split, team_id, f"%{team_id}%"),
        )
    return df.to_dict(orient="records")


@mcp.tool()
def query_team_stats(
    team_id: str,
    season: str = "20252026",
    stype: int = 2,
    sit: str = "5v5",
) -> dict | None:
    """Return team totals for one (team, season, stype, sit)."""
    with sqlite3.connect(STORE_PATH) as c:
        df = pd.read_sql_query(
            "SELECT * FROM team_stats WHERE team_id=? AND season=? AND stype=? AND sit=?",
            c, params=(team_id, season, stype, sit),
        )
    return df.iloc[0].to_dict() if not df.empty else None


@mcp.tool()
def project_swap_scenario(
    out_player_name: str,
    in_player_name: str,
    team_id: str,
    slot_minutes: float,
    sit: str = "5v5",
    baseline: str = "pooled_2_seasons",
) -> dict:
    """Project team per-60 impact of swapping out_player for in_player at a team.

    Returns point estimates + 80% CI bands + sample-size context. Directional, not predictive.

    Args:
        baseline: 'pooled_2_seasons' (24-25 + 25-26 reg + playoffs) or 'current_only' (25-26 only).
    """
    keys = _resolve_keys(baseline)
    team_rows = _pool_team_rows(team_id, sit, keys)
    out_rows = _pool_player_rows(out_player_name, sit, keys)
    in_rows = _pool_player_rows(in_player_name, sit, keys)
    if team_rows.empty or out_rows.empty or in_rows.empty:
        return {
            "error": "missing_data",
            "team_rows": len(team_rows),
            "out_rows": len(out_rows),
            "in_rows": len(in_rows),
        }
    out_imp = build_pooled_player_impact(out_rows, team_rows, team_id)
    in_imp = build_pooled_player_impact(in_rows, team_rows, team_id)
    r = project_swap(out_imp, in_imp, slot_minutes=slot_minutes, strength_state=sit)
    return {
        "sit": sit,
        "baseline": baseline,
        "slot_minutes": slot_minutes,
        "out": {"name": out_player_name, "toi_on": out_imp.toi_on,
                "iso_xgf60": out_imp.iso_xgf60, "iso_xga60": out_imp.iso_xga60},
        "in": {"name": in_player_name, "toi_on": in_imp.toi_on,
               "iso_xgf60": in_imp.iso_xgf60, "iso_xga60": in_imp.iso_xga60},
        "delta_xgf60": r.delta_xgf60,
        "delta_xga60": r.delta_xga60,
        "delta_xgf60_ci80": list(r.delta_xgf60_ci80),
        "delta_xga60_ci80": list(r.delta_xga60_ci80),
        "net_xg60": r.delta_xgf60 - r.delta_xga60,
        "sample_note": r.sample_note,
    }


@mcp.tool()
def rank_players(
    team_id: str,
    sit: str = "5v5",
    min_toi: float = 200.0,
    baseline: str = "current_only",
    top_n: int = 8,
    bottom_n: int = 5,
) -> dict:
    """Rank a team's skaters by isolated net impact (iso_xgf60 - iso_xga60).

    Returns both positive (top) and negative (bottom) contributors with sample context.
    """
    keys = _resolve_keys(baseline)
    team_rows = _pool_team_rows(team_id, sit, keys)
    with sqlite3.connect(STORE_PATH) as c:
        clauses = " OR ".join(["(season=? AND stype=?)"] * len(keys))
        params: list = [sit]
        for s, st_ in keys:
            params.extend([s, st_])
        df = pd.read_sql_query(
            f"SELECT name, position, team_id, gp, toi, xgf, xga "
            f"FROM skater_stats WHERE sit=? AND split='oi' AND ({clauses})",
            c, params=params,
        )
    df = df[df["team_id"].astype(str).str.contains(team_id, na=False)].copy()
    if df.empty or team_rows.empty:
        return {"error": "missing_data"}
    for col in ["toi", "xgf", "xga", "gp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    agg = df.groupby("name", as_index=False).agg({
        "position": "first", "gp": "sum", "toi": "sum", "xgf": "sum", "xga": "sum",
    })
    toi_team = float(team_rows["toi"].fillna(0).sum())
    xgf_team = float(team_rows["xgf"].fillna(0).sum())
    xga_team = float(team_rows["xga"].fillna(0).sum())
    rows = []
    for _, pr in agg.iterrows():
        toi_on = float(pr["toi"])
        if toi_on < min_toi:
            continue
        toi_off = max(toi_team - toi_on, 0.0)
        if toi_off <= 0:
            continue
        iso_xgf60 = (float(pr["xgf"]) * 60 / toi_on) - (max(xgf_team - float(pr["xgf"]), 0.0) * 60 / toi_off)
        iso_xga60 = (float(pr["xga"]) * 60 / toi_on) - (max(xga_team - float(pr["xga"]), 0.0) * 60 / toi_off)
        rows.append({
            "name": pr["name"], "position": pr["position"],
            "gp": int(pr["gp"]), "toi": round(toi_on, 1),
            "iso_xgf60": iso_xgf60, "iso_xga60": iso_xga60,
            "net": iso_xgf60 - iso_xga60,
        })
    ranked = sorted(rows, key=lambda r: r["net"], reverse=True)
    return {
        "team": team_id, "sit": sit, "baseline": baseline, "min_toi": min_toi,
        "positive": ranked[:top_n],
        "negative": sorted(ranked, key=lambda r: r["net"])[:bottom_n],
        "n_players_evaluated": len(ranked),
    }


@mcp.tool()
def fetch_game_detail(game_id: str) -> dict:
    """Fetch shift chart + play-by-play for one NHL game via the NHL.com public API.

    Returns a summary + structured events. Cached aggressively.
    """
    from lemieux.connectors.nhl_api import NhlApiClient
    c = NhlApiClient()
    try:
        shifts = c.shift_chart(game_id)
        pbp = c.play_by_play(game_id)
    finally:
        c.close()
    plays = pbp.get("plays") or []
    return {
        "game_id": game_id,
        "venue": pbp.get("venue", {}).get("default"),
        "home": (pbp.get("homeTeam") or {}).get("abbrev"),
        "away": (pbp.get("awayTeam") or {}).get("abbrev"),
        "shifts_count": len(shifts),
        "events_count": len(plays),
        "shifts": shifts,  # caller decides what to slice
        "plays": plays,
    }


# ==================== RESOURCES ====================
@mcp.resource("lemieux://glossary")
def list_glossary() -> str:
    """List all glossary term IDs."""
    ids = sorted(t.id for t in list_terms())
    return "\n".join(ids)


@mcp.resource("lemieux://glossary/{term_id}")
def get_glossary_term(term_id: str) -> str:
    """Get one glossary term's full definition (defaults to EN)."""
    import json
    return json.dumps(render_mcp_resource(term_id, lang="en"), ensure_ascii=False, indent=2)


@mcp.resource("lemieux://sources")
def list_sources() -> str:
    """List available data-source connectors with license notes."""
    import importlib.resources as ir
    try:
        return ir.files("lemieux.connectors").joinpath("registry.yaml").read_text(encoding="utf-8")
    except Exception as e:
        return f"# Registry not found: {e}. See SOURCES.md in the repo."


@mcp.resource("lemieux://methodology")
def get_methodology() -> str:
    """How Lemieux constructs isolated impacts, CIs, and pooled baselines."""
    return (
        "Lemieux methodology — condensed\n"
        "================================\n"
        "Isolated impact: iso_xgf60 = (xgf_on/toi_on*60) - (xgf_off/toi_off*60).\n"
        "Not true RAPM — no teammate/opponent controls.\n"
        "Minimum 200 pooled minutes to include in rankings; swap math may relax this.\n"
        "80% CI via Poisson approximation on event counts: var(rate) ≈ events / hours².\n"
        "Pooled baseline default: 2024-25 + 2025-26, regular + playoffs. Events/TOI summed.\n"
        "Traded players: on-ice events pooled across teams, subtracted against the receiving team's totals.\n"
        "No predictions. Every output should cite sample size."
    )


# ==================== CLI ENTRYPOINT ====================
def build_server(store_path: Path | None = None) -> FastMCP:
    """Construct the FastMCP server with an optional custom store path."""
    global STORE_PATH
    if store_path is not None:
        STORE_PATH = store_path
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Lemieux MCP server")
    parser.add_argument("--store", type=Path, default=None,
                        help="Path to Lemieux SQLite store. Defaults to ~/.lemieux/store.sqlite or $LEMIEUX_STORE.")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    args = parser.parse_args()
    build_server(args.store)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
