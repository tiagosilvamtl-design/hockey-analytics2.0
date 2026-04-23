"""Hand-computed fixtures verify swap-engine math and variance propagation."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from lemieux.core import PlayerImpact, build_player_impact, project_swap


def test_iso_rates_zero_when_identical_to_team():
    team = pd.Series({"toi": 1000.0, "xgf": 40.0, "xga": 35.0})
    player = pd.Series({
        "name": "Identical Joe", "team_id": "FLA",
        "toi": 500.0, "xgf": 20.0, "xga": 17.5,
    })
    imp = build_player_impact(player, team)
    assert math.isclose(imp.iso_xgf60, 0.0, abs_tol=1e-6)
    assert math.isclose(imp.iso_xga60, 0.0, abs_tol=1e-6)


def test_iso_rates_hand_computed():
    team = pd.Series({"toi": 1000.0, "xgf": 40.0, "xga": 30.0})
    player = pd.Series({
        "name": "Plus Pete", "team_id": "FLA",
        "toi": 400.0, "xgf": 20.0, "xga": 10.0,
    })
    imp = build_player_impact(player, team)
    assert math.isclose(imp.iso_xgf60, 1.0, abs_tol=1e-6)
    assert math.isclose(imp.iso_xga60, -0.5, abs_tol=1e-6)


def test_project_swap_monotonic_in_slot_minutes():
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
    p = PlayerImpact(
        player_id="ghost", name="Ghost", team_id="FLA",
        toi_on=0.0, toi_off=1000.0, xgf_on=0.0, xga_on=0.0, xgf_off=40.0, xga_off=30.0,
    )
    assert p.iso_xgf60 == pytest.approx(0.0 - 2.4, abs=1e-3)
