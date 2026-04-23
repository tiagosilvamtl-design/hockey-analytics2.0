"""Hand-computed fixtures verify swap-engine math and variance propagation."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from analytics.swap_engine import PlayerImpact, build_player_impact, project_swap


def test_iso_rates_zero_when_identical_to_team():
    """If the player's on-ice rates match team totals, isolated impact should be 0."""
    # Team plays 1000 min with 40 xGF and 35 xGA. Player plays 500 min with 20/17.5.
    team = pd.Series({"toi": 1000.0, "xgf": 40.0, "xga": 35.0})
    player = pd.Series({
        "name": "Identical Joe",
        "team_id": "FLA",
        "toi": 500.0,
        "xgf": 20.0,
        "xga": 17.5,
    })
    imp = build_player_impact(player, team)
    assert math.isclose(imp.iso_xgf60, 0.0, abs_tol=1e-6)
    assert math.isclose(imp.iso_xga60, 0.0, abs_tol=1e-6)


def test_iso_rates_hand_computed():
    team = pd.Series({"toi": 1000.0, "xgf": 40.0, "xga": 30.0})
    player = pd.Series({
        "name": "Plus Pete",
        "team_id": "FLA",
        "toi": 400.0,
        "xgf": 20.0,   # 20/400 min * 60 = 3.0 xGF/60 on-ice
        "xga": 10.0,   # 10/400 * 60 = 1.5 xGA/60 on-ice
    })
    imp = build_player_impact(player, team)
    # off-ice: 600 min, 20 xGF, 20 xGA → 2.0 xGF/60, 2.0 xGA/60
    assert math.isclose(imp.iso_xgf60, 3.0 - 2.0, abs_tol=1e-6)
    assert math.isclose(imp.iso_xga60, 1.5 - 2.0, abs_tol=1e-6)  # negative = good defensively


def test_project_swap_monotonic_in_slot_minutes():
    # OUT: neutral player (0 iso). IN: strong offensive player (+1 iso_xgf60).
    team = pd.Series({"toi": 1000.0, "xgf": 40.0, "xga": 30.0})
    out_row = pd.Series({"name": "Flat", "team_id": "FLA", "toi": 400.0, "xgf": 16.0, "xga": 12.0})
    in_row = pd.Series({"name": "Spark", "team_id": "FLA", "toi": 400.0, "xgf": 20.0, "xga": 12.0})
    out_imp = build_player_impact(out_row, team)
    in_imp = build_player_impact(in_row, team)
    r_low = project_swap(out_imp, in_imp, slot_minutes=6.0)
    r_high = project_swap(out_imp, in_imp, slot_minutes=18.0)
    assert r_high.delta_xgf60 > r_low.delta_xgf60 > 0


def test_project_swap_ci_contains_point_estimate():
    team = pd.Series({"toi": 1000.0, "xgf": 40.0, "xga": 30.0})
    out_row = pd.Series({"name": "A", "team_id": "FLA", "toi": 400.0, "xgf": 16.0, "xga": 12.0})
    in_row = pd.Series({"name": "B", "team_id": "FLA", "toi": 400.0, "xgf": 20.0, "xga": 12.0})
    out_imp = build_player_impact(out_row, team)
    in_imp = build_player_impact(in_row, team)
    r = project_swap(out_imp, in_imp, slot_minutes=18.0)
    lo, hi = r.delta_xgf60_ci80
    assert lo <= r.delta_xgf60 <= hi
    assert hi - lo > 0


def test_zero_toi_player_returns_safe_rates():
    """Defensive: don't divide by zero when a player had no on-ice time."""
    p = PlayerImpact(
        player_id="ghost", name="Ghost", team_id="FLA",
        toi_on=0.0, toi_off=1000.0, xgf_on=0.0, xga_on=0.0, xgf_off=40.0, xga_off=30.0,
    )
    # per60 on 0 TOI should be 0 (handled by _per60)
    assert p.iso_xgf60 == pytest.approx(0.0 - 2.4, abs=1e-3)
