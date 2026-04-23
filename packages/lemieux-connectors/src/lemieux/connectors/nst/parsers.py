"""Parse NST HTML tables into normalized DataFrames."""
from __future__ import annotations

import io

import pandas as pd

TEAM_COL_RENAMES = {
    "Team": "team", "GP": "gp", "TOI": "toi",
    "W": "wins", "L": "losses", "OTL": "otl", "ROW": "row",
    "Points": "points", "Point %": "point_pct",
    "CF": "cf", "CA": "ca", "CF%": "cf_pct",
    "FF": "ff", "FA": "fa", "FF%": "ff_pct",
    "SF": "sf", "SA": "sa", "SF%": "sf_pct",
    "GF": "gf", "GA": "ga", "GF%": "gf_pct",
    "xGF": "xgf", "xGA": "xga", "xGF%": "xgf_pct",
    "SCF": "scf", "SCA": "sca", "SCF%": "scf_pct",
    "HDCF": "hdcf", "HDCA": "hdca", "HDCF%": "hdcf_pct",
    "PDO": "pdo",
}

SKATER_COL_RENAMES = {
    "Player": "name", "Team": "team", "Position": "position",
    "GP": "gp", "TOI": "toi",
    "CF": "cf", "CA": "ca", "CF%": "cf_pct",
    "FF": "ff", "FA": "fa", "FF%": "ff_pct",
    "SF": "sf", "SA": "sa", "SF%": "sf_pct",
    "GF": "gf", "GA": "ga", "GF%": "gf_pct",
    "xGF": "xgf", "xGA": "xga", "xGF%": "xgf_pct",
    "SCF": "scf", "SCA": "sca", "SCF%": "scf_pct",
    "HDCF": "hdcf", "HDCA": "hdca", "HDCF%": "hdcf_pct",
    "Shots": "shots", "Goals": "goals",
    "First Assists": "a1", "Second Assists": "a2",
    "Total Assists": "assists", "Total Points": "points",
    "IPP": "ipp", "SH%": "sh_pct",
}


def _normalize(df: pd.DataFrame, renames: dict[str, str]) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    unnamed = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed:
        df = df.drop(columns=unnamed)
    df = df.rename(columns=renames)
    return df


def _read_first_table(html: bytes | str) -> pd.DataFrame:
    buf = io.BytesIO(html) if isinstance(html, (bytes, bytearray)) else io.StringIO(html)
    tables = pd.read_html(buf, flavor="lxml")
    if not tables:
        raise ValueError("No HTML table found in NST page")
    return max(tables, key=len)


def parse_team_table(html: bytes | str) -> pd.DataFrame:
    df = _read_first_table(html)
    df = _normalize(df, TEAM_COL_RENAMES)
    if "toi" in df.columns:
        df["toi"] = df["toi"].apply(parse_toi_minutes)
    numeric_cols = [c for c in df.columns if c not in {"team", "toi"}]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def parse_skater_table(html: bytes | str) -> pd.DataFrame:
    df = _read_first_table(html)
    df = _normalize(df, SKATER_COL_RENAMES)
    if "toi" in df.columns:
        df["toi"] = df["toi"].apply(parse_toi_minutes)
    non_numeric = {"name", "team", "position", "toi"}
    for c in df.columns:
        if c in non_numeric:
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def parse_toi_minutes(val) -> float:
    """NST TOI is 'mm:ss' on some tables; totals are plain floats."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if ":" in s:
        m, sec = s.split(":")
        return float(m) + float(sec) / 60.0
    try:
        return float(s)
    except ValueError:
        return 0.0
