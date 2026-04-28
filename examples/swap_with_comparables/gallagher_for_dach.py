"""Demo: Gallagher-for-Dach swap projection, with and without cohort stabilization.

Shows the form-factor described in plans/want-to-build-an-cheeky-zebra.md:
two layers stacked (raw target's pooled iso vs comp-cohort-stabilized iso),
with both projections + their 80% CIs reported side-by-side. Phase 3's
archetype-lift third layer adds on top once Phase 2 ships the tag corpus.

Run:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python examples/swap_with_comparables/gallagher_for_dach.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

import pandas as pd

from lemieux.core import (
    ComparableIndex,
    PlayerImpact,
    build_cohort_stabilized_impact,
    build_pooled_player_impact,
    project_swap,
)


SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")
DB = REPO / "legacy" / "data" / "store.sqlite"
INDEX_PATH = REPO / "legacy" / "data" / "comparable_index.json"


def fetch_player_pooled_rows(con: sqlite3.Connection, name: str, sit: str = "5v5") -> pd.DataFrame:
    """Pull all on-ice rows for one player across the 5-year window."""
    return pd.read_sql_query(
        f"""
        SELECT name, team_id, season, stype, sit, toi, xgf, xga
        FROM skater_stats
        WHERE name = ?
          AND sit = ?
          AND split = 'oi'
          AND season IN ({','.join(['?']*len(SEASONS))})
        """,
        con, params=[name, sit, *SEASONS],
    )


def fetch_team_pooled_rows(con: sqlite3.Connection, sit: str = "5v5") -> pd.DataFrame:
    """League-pooled team rows (all teams), for off-ice baseline."""
    return pd.read_sql_query(
        f"""
        SELECT team_id, season, stype, sit, toi, xgf, xga
        FROM team_stats
        WHERE sit = ?
          AND season IN ({','.join(['?']*len(SEASONS))})
        """,
        con, params=[sit, *SEASONS],
    )


def aggregate_team(team_rows: pd.DataFrame) -> pd.Series:
    return pd.Series({
        "toi": float(team_rows["toi"].sum()),
        "xgf": float(team_rows["xgf"].sum()),
        "xga": float(team_rows["xga"].sum()),
    })


def build_player_impact_pooled(con: sqlite3.Connection, name: str, sit: str = "5v5") -> PlayerImpact:
    """Pull a player's 5-year pooled iso impact at one strength state."""
    p_rows = fetch_player_pooled_rows(con, name, sit)
    team_rows = fetch_team_pooled_rows(con, sit)
    if not len(p_rows):
        raise ValueError(f"No rows for {name} in window")
    return build_pooled_player_impact(p_rows, team_rows, team_id=p_rows.iloc[0]["team_id"])


def fmt(x):
    if x is None:
        return "—"
    return f"{x:+.3f}"


def main():
    con = sqlite3.connect(DB)
    print("Loading comparable index ...")
    index = ComparableIndex.load(INDEX_PATH)
    print(f"  {index.n_rows} players, {len(index.columns)} features")

    # ---- Load the two players for the swap ----
    target_out = build_player_impact_pooled(con, "Brendan Gallagher")  # comes IN
    target_in = build_player_impact_pooled(con, "Kirby Dach")          # gets replaced

    # ---- Build Gallagher's comp cohort + stabilized impact ----
    comps = index.find_comparables("Brendan Gallagher", k=5, min_pooled_toi=200.0)
    print("\nGallagher's top-5 comps:")
    for c in comps:
        print(f"  {c.score:5.1f}  {c.name:25s} ({c.position})  toi={c.pooled_toi_5v5:>6.0f}  "
              f"iso_net={c.pooled_iso_xgf60 - c.pooled_iso_xga60:+.3f}")

    # Pull each comp's PlayerImpact for stabilization
    cohort_impacts: list[PlayerImpact] = []
    for c in comps:
        try:
            cohort_impacts.append(build_player_impact_pooled(con, c.name, "5v5"))
        except ValueError:
            pass

    stabilized = build_cohort_stabilized_impact(target_out, cohort_impacts)

    # ---- Project both swaps: raw vs stabilized ----
    slot_min = 14.0  # 3rd-line C slot, ~14 min/game
    raw_swap = project_swap(out_player=target_in, in_player=target_out, slot_minutes=slot_min)
    stabilized_swap = project_swap(out_player=target_in, in_player=stabilized, slot_minutes=slot_min)

    # ---- Render comparison ----
    print(f"\n{'='*78}")
    print("Swap projection: Gallagher (in) for Dach (out), 14-min/game slot, 5v5")
    print('='*78)
    print(f"\n{'Layer':<48} {'Δ xGF':>10} {'Δ xGA':>10} {'Δ Net':>10}")
    print("-" * 78)
    print(f"{'Target pooled iso (Gallagher 5-yr 5v5)':<48} "
          f"{raw_swap.delta_xgf60:>+10.3f} {raw_swap.delta_xga60:>+10.3f} "
          f"{raw_swap.delta_xgf60 - raw_swap.delta_xga60:>+10.3f}")
    print(f"  CI80: xGF [{raw_swap.delta_xgf60_ci80[0]:+.3f}, {raw_swap.delta_xgf60_ci80[1]:+.3f}]  "
          f"xGA [{raw_swap.delta_xga60_ci80[0]:+.3f}, {raw_swap.delta_xga60_ci80[1]:+.3f}]")
    raw_xgf_width = raw_swap.delta_xgf60_ci80[1] - raw_swap.delta_xgf60_ci80[0]
    raw_xga_width = raw_swap.delta_xga60_ci80[1] - raw_swap.delta_xga60_ci80[0]
    print(f"  CI widths: xGF {raw_xgf_width:.3f}, xGA {raw_xga_width:.3f}")

    print(f"\n{'Comp-cohort-stabilized (k=5, NHL kNN)':<48} "
          f"{stabilized_swap.delta_xgf60:>+10.3f} {stabilized_swap.delta_xga60:>+10.3f} "
          f"{stabilized_swap.delta_xgf60 - stabilized_swap.delta_xga60:>+10.3f}")
    print(f"  CI80: xGF [{stabilized_swap.delta_xgf60_ci80[0]:+.3f}, {stabilized_swap.delta_xgf60_ci80[1]:+.3f}]  "
          f"xGA [{stabilized_swap.delta_xga60_ci80[0]:+.3f}, {stabilized_swap.delta_xga60_ci80[1]:+.3f}]")
    stab_xgf_width = stabilized_swap.delta_xgf60_ci80[1] - stabilized_swap.delta_xgf60_ci80[0]
    stab_xga_width = stabilized_swap.delta_xga60_ci80[1] - stabilized_swap.delta_xga60_ci80[0]
    print(f"  CI widths: xGF {stab_xgf_width:.3f}, xGA {stab_xga_width:.3f}")

    print(f"\n{'CI tightening':<48}")
    print(f"  xGF: {raw_xgf_width:.3f} -> {stab_xgf_width:.3f}  "
          f"({(1 - stab_xgf_width / raw_xgf_width) * 100:+.1f}% width change)")
    print(f"  xGA: {raw_xga_width:.3f} -> {stab_xga_width:.3f}  "
          f"({(1 - stab_xga_width / raw_xga_width) * 100:+.1f}% width change)")

    # ---- Honest read ----
    print(f"\n{'='*78}")
    print("Honest read")
    print('='*78)
    g_toi = target_out.toi_on
    print(f"  Gallagher's pooled 5v5 TOI: {g_toi:.0f} min — {'large' if g_toi > 1500 else 'mid' if g_toi > 600 else 'small'} sample")
    print(f"  Cohort-stabilized w_target = {stabilized.name.split('=')[1].rstrip(')')}")
    print(f"  Both projections agree directionally? "
          f"{(raw_swap.delta_xgf60 - raw_swap.delta_xga60) * (stabilized_swap.delta_xgf60 - stabilized_swap.delta_xga60) > 0}")
    if abs(stabilized_swap.delta_xgf60_ci80[0]) > 0 and stabilized_swap.delta_xgf60_ci80[0] * stabilized_swap.delta_xgf60_ci80[1] > 0:
        print("  Stabilized xGF CI excludes zero ✓")
    else:
        print("  Stabilized xGF CI straddles zero (no significance)")


if __name__ == "__main__":
    main()
