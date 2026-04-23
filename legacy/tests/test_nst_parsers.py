"""Tests for NST HTML table parsing using committed fixtures."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from data.nst_parsers import parse_skater_table, parse_team_table, parse_toi_minutes

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_team_table_columns_and_rows():
    html = (FIXTURES / "teams_5v5_sample.html").read_bytes()
    df = parse_team_table(html)
    assert len(df) == 3
    # Renamed columns present
    for col in ["team", "gp", "toi", "cf", "ca", "cf_pct", "xgf", "xga", "xgf_pct", "pdo"]:
        assert col in df.columns, f"missing {col}"
    fla = df[df["team"] == "FLA"].iloc[0]
    assert pytest_approx(fla["cf_pct"], 52.78)
    assert pytest_approx(fla["xgf_pct"], 54.17)
    assert int(fla["gp"]) == 82


def test_parse_skater_table_oi():
    html = (FIXTURES / "skaters_oi_sample.html").read_bytes()
    df = parse_skater_table(html)
    # six sample skaters
    assert len(df) == 6
    for col in ["name", "team", "position", "toi", "xgf", "xga", "xgf_pct"]:
        assert col in df.columns
    barkov = df[df["name"] == "Aleksander Barkov"].iloc[0]
    assert pytest_approx(barkov["toi"], 1300.0)
    assert pytest_approx(barkov["xgf"], 92.5)


def test_parse_toi_minutes_formats():
    assert parse_toi_minutes(1300.0) == 1300.0
    assert parse_toi_minutes("20:30") == 20.5
    assert parse_toi_minutes("12:00") == 12.0
    assert parse_toi_minutes(None) == 0.0


def pytest_approx(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(float(a) - float(b)) < tol
