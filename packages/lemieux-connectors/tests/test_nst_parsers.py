"""Parser tests for the NST connector using committed HTML fixtures."""
from __future__ import annotations

from pathlib import Path

from lemieux.connectors.nst import parse_skater_table, parse_team_table, parse_toi_minutes

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_team_table_columns_and_rows():
    html = (FIXTURES / "teams_5v5_sample.html").read_bytes()
    df = parse_team_table(html)
    assert len(df) == 3
    for col in ["team", "gp", "toi", "cf", "ca", "cf_pct", "xgf", "xga", "xgf_pct", "pdo"]:
        assert col in df.columns
    fla = df[df["team"] == "FLA"].iloc[0]
    assert abs(fla["cf_pct"] - 52.78) < 1e-3
    assert int(fla["gp"]) == 82


def test_parse_skater_table_oi():
    html = (FIXTURES / "skaters_oi_sample.html").read_bytes()
    df = parse_skater_table(html)
    assert len(df) == 6
    for col in ["name", "team", "position", "toi", "xgf", "xga", "xgf_pct"]:
        assert col in df.columns


def test_parse_toi_minutes_formats():
    assert parse_toi_minutes(1300.0) == 1300.0
    assert parse_toi_minutes("20:30") == 20.5
    assert parse_toi_minutes("12:00") == 12.0
    assert parse_toi_minutes(None) == 0.0
