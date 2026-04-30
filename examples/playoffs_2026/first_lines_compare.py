"""Special report: compare each playoff team's "most typical first line" by iso impact.

The 16 teams in the 25-26 NHL playoffs (Round 1 in flight as of 2026-04-29):
  East: TBL, MTL, BOS, BUF, OTT, CAR, PIT, PHI
  West: DAL, MIN, EDM, ANA, COL, L.A, VGK, UTA

"Most typical first line" heuristic
-----------------------------------
For each team, pick the top-1 C + top-1 L + top-1 R by 25-26 5v5 TOI (regular
season + playoff combined). This approximates the "canonical L1 by deployment"
without needing PBP shift-overlap data (line_combos table is unpopulated in
our DB). It will mismatch slightly when a team's TOI leader isn't actually
deployed with the other position-leaders — flagged honestly in the brief.

For each team we then compute:
  - Pooled trio iso net60 (mean of per-player iso, as in the swap engine)
  - Total trio 5v5 TOI (deployment intensity)
  - Top scouting tags per player (with provenance lookup elsewhere)

Output: examples/playoffs_2026/first_lines_compare.numbers.json
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "legacy"))

from analytics.swap_engine import build_pooled_player_impact, PlayerImpact

DB = REPO / "legacy" / "data" / "store.sqlite"
OUT_PATH = Path(__file__).parent / "first_lines_compare.numbers.json"

# Pool windows for iso baselines
POOL_KEYS = [
    ("20242025", 2), ("20242025", 3),
    ("20252026", 2), ("20252026", 3),
]

PLAYOFF_TEAMS = [
    # East
    ("MTL", "Montreal"), ("T.B", "Tampa Bay"),
    ("BOS", "Boston"), ("BUF", "Buffalo"),
    ("OTT", "Ottawa"), ("CAR", "Carolina"),
    ("PIT", "Pittsburgh"), ("PHI", "Philadelphia"),
    # West
    ("DAL", "Dallas"), ("MIN", "Minnesota"),
    ("EDM", "Edmonton"), ("ANA", "Anaheim"),
    ("COL", "Colorado"), ("L.A", "Los Angeles"),
    ("VGK", "Vegas"), ("UTA", "Utah"),
]

# Press-confirmed overrides where the top-by-TOI heuristic diverges from
# the actual deployed L1 trio. Each override is web-search-verified
# (sources cited in the brief).
LINE_OVERRIDES = {
    # Heuristic gave Joona Koppanen LW; press confirms Rakell on Crosby's wing.
    "PIT": {"L": "Rickard Rakell", "C": "Sidney Crosby", "R": "Bryan Rust",
            "source": "Pensburgh / Daily Faceoff (2026 playoff preview)"},
    # Heuristic gave Trenin C + Hartman R; press confirms the Kaprizov line is
    # Kaprizov LW – Hartman C – Zuccarello RW.
    "MIN": {"L": "Kirill Kaprizov", "C": "Ryan Hartman", "R": "Mats Zuccarello",
            "source": "Hockey Wilderness / NHL.com Wild playoff coverage"},
    # Heuristic gave Gourde C (he led TBL Cs in TOI because Point was injured
    # for chunks of the reg season); press confirms Point returned as the L1
    # C in the playoffs.
    "T.B": {"L": "Brandon Hagel", "C": "Brayden Point", "R": "Nikita Kucherov",
            "source": "Daily Faceoff / NHL.com Lightning playoff preview"},
}


def fetch_top_by_position(con, team_id: str) -> dict:
    """Top forward by 5v5 TOI in 25-26 (reg+playoff combined) per position."""
    out = {}
    for pos in ("C", "L", "R"):
        r = con.execute("""
            SELECT name, SUM(toi) as toi
            FROM skater_stats
            WHERE team_id=? AND season='20252026' AND sit='5v5' AND split='oi'
              AND position=?
            GROUP BY name
            ORDER BY toi DESC LIMIT 1
        """, (team_id, pos)).fetchone()
        if r:
            out[pos] = {"name": r[0], "team_toi_2526_5v5": round(r[1] or 0, 0)}
    return out


def fetch_player_rows(con, name):
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in POOL_KEYS)
    params = []
    for s, st in POOL_KEYS:
        params.extend([s, st])
    q = f"""
        SELECT name, team_id, season, stype, sit, split, toi, xgf, xga
        FROM skater_stats
        WHERE name=? AND sit='5v5' AND split='oi' AND ({keys_clause})
    """
    return pd.read_sql_query(q, con, params=[name] + params)


def fetch_team_rows(con, team_id):
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in POOL_KEYS)
    params = []
    for s, st in POOL_KEYS:
        params.extend([s, st])
    q = f"""
        SELECT team_id, season, stype, sit, toi, xgf, xga
        FROM team_stats
        WHERE team_id=? AND sit='5v5' AND ({keys_clause})
    """
    return pd.read_sql_query(q, con, params=[team_id] + params)


def player_tags(con, name, *, top_n=3, min_conf=0.5):
    rows = con.execute("""
        SELECT tag, confidence FROM scouting_tags
        WHERE name=? ORDER BY confidence DESC LIMIT ?
    """, (name, top_n * 3)).fetchall()
    return [{"tag": r[0], "confidence": round(r[1], 2)}
            for r in rows if r[1] >= min_conf][:top_n]


def main():
    con = sqlite3.connect(DB)

    teams_data = []
    for team_id, team_name in PLAYOFF_TEAMS:
        team_rows = fetch_team_rows(con, team_id)
        if team_rows.empty:
            print(f"WARN: no team rows for {team_id}")
            continue

        positions = fetch_top_by_position(con, team_id)
        if not all(p in positions for p in ("C", "L", "R")):
            print(f"WARN: {team_id} missing a position leader")
            continue

        line = {pos: positions[pos] for pos in ("C", "L", "R")}

        # Apply press-confirmed L1 override if present
        override = LINE_OVERRIDES.get(team_id)
        if override:
            for pos in ("C", "L", "R"):
                # Look up the override player's TOI; keep heuristic value as fallback
                override_name = override[pos]
                r = con.execute("""
                    SELECT SUM(toi) FROM skater_stats
                    WHERE name=? AND team_id=? AND season='20252026'
                      AND sit='5v5' AND split='oi'
                """, (override_name, team_id)).fetchone()
                line[pos] = {
                    "name": override_name,
                    "team_toi_2526_5v5": round(r[0] or 0, 0) if r else 0,
                    "_overridden_from": positions[pos]["name"],
                }
            line["_override_source"] = override.get("source")
        line_iso = []
        line_xgf = []
        line_xga = []
        line_toi_pool = []  # pooled iso baseline TOI per player
        for pos in ("C", "L", "R"):
            info = line[pos]
            rows = fetch_player_rows(con, info["name"])
            if rows.empty:
                continue
            imp = build_pooled_player_impact(rows, team_rows, team_id=team_id)
            line[pos]["iso_xgf60"] = round(imp.iso_xgf60, 3)
            line[pos]["iso_xga60"] = round(imp.iso_xga60, 3)
            line[pos]["iso_net60"] = round(imp.iso_xgf60 - imp.iso_xga60, 3)
            line[pos]["pool_toi"] = round(imp.toi_on, 0)
            line[pos]["tags"] = player_tags(con, info["name"])
            line_iso.append(imp.iso_xgf60 - imp.iso_xga60)
            line_xgf.append(imp.iso_xgf60)
            line_xga.append(imp.iso_xga60)
            line_toi_pool.append(imp.toi_on)

        if len(line_iso) < 3:
            continue

        trio_combined_2526_toi = sum(line[p]["team_toi_2526_5v5"] for p in ("C", "L", "R")) / 3
        avg_iso_net60 = sum(line_iso) / 3
        avg_xgf60 = sum(line_xgf) / 3
        avg_xga60 = sum(line_xga) / 3

        # Series-direct PBP context: try playoff_rankings + analyzer outputs
        # For now, just package the heuristic line.
        teams_data.append({
            "team_id": team_id, "team_name": team_name,
            "line": line,
            "trio_avg_iso_xgf60": round(avg_xgf60, 3),
            "trio_avg_iso_xga60": round(avg_xga60, 3),
            "trio_avg_iso_net60": round(avg_iso_net60, 3),
            "trio_avg_2526_5v5_toi": round(trio_combined_2526_toi, 0),
            "min_pool_toi": round(min(line_toi_pool), 0),
        })

    teams_data.sort(key=lambda t: -t["trio_avg_iso_net60"])

    # ---- League aggregate stats ----
    isos = [t["trio_avg_iso_net60"] for t in teams_data]
    league_avg = sum(isos) / len(isos)
    best = teams_data[0]
    worst = teams_data[-1]

    # Tag-frequency view: which archetypes show up across the 48 forwards?
    tag_counts = {}
    for t in teams_data:
        for pos in ("C", "L", "R"):
            for tg in t["line"][pos].get("tags", []):
                tag_counts[tg["tag"]] = tag_counts.get(tg["tag"], 0) + 1
    tag_summary = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]

    payload = {
        "meta": {
            "as_of": "2026-04-29",
            "scope": "16 teams in 25-26 NHL Round 1 playoffs",
            "method": (
                "'Most typical first line' = top-1 C + top-1 L + top-1 R by 25-26 "
                "5v5 TOI (reg + playoff combined). Approximates canonical L1 by "
                "deployment without PBP shift-overlap data. Pooled iso baseline "
                "uses 24-25 + 25-26 reg+playoff windows."
            ),
            "data_source": "Natural Stat Trick on-ice (oi) splits, pooled.",
            "swap_engine": "lemieux pooled-baseline (lemieux-core)",
        },
        "teams": teams_data,
        "league_summary": {
            "n_teams": len(teams_data),
            "avg_trio_iso_net60": round(league_avg, 3),
            "best_team": best["team_name"],
            "best_trio_iso_net60": best["trio_avg_iso_net60"],
            "worst_team": worst["team_name"],
            "worst_trio_iso_net60": worst["trio_avg_iso_net60"],
            "spread": round(best["trio_avg_iso_net60"] - worst["trio_avg_iso_net60"], 3),
        },
        "tag_summary_top10": [{"tag": k, "count": v} for k, v in tag_summary],
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print()
    print("=" * 110)
    print("RANKED FIRST-LINE TRIO ISO IMPACT (16 playoff teams, pooled 24-25 + 25-26 reg+playoff)")
    print("=" * 110)
    print(f"{'Rank':<5} {'Team':<14} {'Line (C-L-R)':<60} {'iso_xgf60':>10} {'iso_xga60':>10} {'net60':>8}")
    for i, t in enumerate(teams_data, 1):
        c = t["line"]["C"]["name"]
        l = t["line"]["L"]["name"]
        r = t["line"]["R"]["name"]
        line_str = f"{l} - {c} - {r}"[:60]
        print(f"{i:<5} {t['team_name']:<14} {line_str:<60} "
              f"{t['trio_avg_iso_xgf60']:>+10.3f} {t['trio_avg_iso_xga60']:>+10.3f} {t['trio_avg_iso_net60']:>+8.3f}")
    print()
    print(f"League avg trio iso net60: {league_avg:+.3f}")
    print(f"Spread (best minus worst): {best['trio_avg_iso_net60'] - worst['trio_avg_iso_net60']:.3f}")
    print()
    print("Top archetype tags across the 48 forwards:")
    for tg, n in tag_summary:
        print(f"  {tg:18s}  {n}")


if __name__ == "__main__":
    main()
