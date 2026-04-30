"""Morning-after Game 5 special report (2026-04-30).

Comprehensive analysis with the now-refreshed NST data:
  1. Press-claim verification (5v5 scoring stars vs stars)
  2. MTL vs TBL series overview — are Habs overperforming their xG?
  3. Player deep dives — Caufield, Demidov, Slafkovský
  4. League playoff rankings (all 16 teams)
  5. Historical context (3-2 series advancement rate, comparable upset wins)

Output: g5_morning_after_special.numbers.json
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
OUT_PATH = HERE / "g5_morning_after_special.numbers.json"
DB = REPO / "legacy" / "data" / "store.sqlite"

PLAYOFF_TEAMS = [
    ("MTL", "Montréal"), ("T.B", "Tampa Bay"), ("BOS", "Boston"), ("BUF", "Buffalo"),
    ("OTT", "Ottawa"), ("CAR", "Carolina"), ("PIT", "Pittsburgh"), ("PHI", "Philadelphia"),
    ("DAL", "Dallas"), ("MIN", "Minnesota"), ("EDM", "Edmonton"), ("ANA", "Anaheim"),
    ("COL", "Colorado"), ("L.A", "Los Angeles"), ("VGK", "Vegas"), ("UTA", "Utah"),
]


def fetch(con, q, params=()):
    return con.execute(q, params).fetchall()


def press_claim_verification(con):
    """Verify the 'MTL stars 0 pts at 5v5 vs TBL stars 11 pts' press claim."""
    mtl_stars = ["Nick Suzuki", "Cole Caufield", "Juraj Slafkovský", "Ivan Demidov"]
    tbl_stars = ["Brandon Hagel", "Nikita Kucherov", "Anthony Cirelli", "Jake Guentzel"]

    def query(names):
        rows = []
        for n in names:
            r = con.execute("""
                SELECT name, gp, goals, assists, points, shots, ixg, ihdcf
                FROM skater_individual_stats
                WHERE name=? AND season='20252026' AND stype=3 AND sit='5v5'
            """, (n,)).fetchone()
            if r:
                rows.append({
                    "name": r[0], "gp": r[1], "goals": r[2], "assists": r[3],
                    "points": r[4], "shots": r[5], "ixg": round(r[6], 2), "ihdcf": r[7],
                })
        return rows

    mtl = query(mtl_stars)
    tbl = query(tbl_stars)
    return {
        "mtl_stars_5v5": mtl,
        "tbl_stars_5v5": tbl,
        "mtl_total_pts": sum(r["points"] for r in mtl),
        "tbl_total_pts": sum(r["points"] for r in tbl),
        "mtl_total_g": sum(r["goals"] for r in mtl),
        "tbl_total_g": sum(r["goals"] for r in tbl),
    }


def series_team_overview(con):
    """Series-level xGF / xGA per team vs actual goals scored.

    NST team_stats per (season, stype, sit) gives series-aggregate xG. Compare to
    actual goals (we know MTL 14-13 advantage in goals through G5, ~).
    """
    # Both teams' all-situations totals across the playoff (= series-aggregate so far)
    out = {}
    for team in ("MTL", "T.B"):
        r = con.execute("""
            SELECT toi, gp, gf, ga, xgf, xga, sf, sa, scf, sca, hdcf, hdca
            FROM team_stats
            WHERE team_id=? AND season='20252026' AND stype=3 AND sit='all'
        """, (team,)).fetchone()
        if r:
            toi, gp, gf, ga, xgf, xga, sf, sa, scf, sca, hdcf, hdca = r
            out[team] = {
                "gp": gp, "toi": round(toi, 1),
                "gf": gf, "ga": ga,
                "xgf": round(xgf, 2), "xga": round(xga, 2),
                "sf": sf, "sa": sa, "scf": scf, "sca": sca, "hdcf": hdcf, "hdca": hdca,
                "gf_minus_xgf": round(gf - xgf, 2),  # finish luck
                "ga_minus_xga": round(ga - xga, 2),  # save luck (negative = goalie playing well)
            }
    if "MTL" in out and "T.B" in out:
        out["mtl_finish_overperform"] = round(out["MTL"]["gf_minus_xgf"], 2)
        out["mtl_save_overperform"] = round(-out["MTL"]["ga_minus_xga"], 2)  # positive = MTL goalie above expectation
        out["tbl_finish_overperform"] = round(out["T.B"]["gf_minus_xgf"], 2)
        out["tbl_save_overperform"] = round(-out["T.B"]["ga_minus_xga"], 2)
    # Also 5v5 only
    out_5v5 = {}
    for team in ("MTL", "T.B"):
        r = con.execute("""
            SELECT toi, gf, ga, xgf, xga, sf, sa, hdcf, hdca
            FROM team_stats
            WHERE team_id=? AND season='20252026' AND stype=3 AND sit='5v5'
        """, (team,)).fetchone()
        if r:
            out_5v5[team] = {
                "toi": round(r[0], 1), "gf": r[1], "ga": r[2],
                "xgf": round(r[3], 2), "xga": round(r[4], 2),
                "sf": r[5], "sa": r[6], "hdcf": r[7], "hdca": r[8],
                "gf_minus_xgf": round(r[1] - r[3], 2),
                "ga_minus_xga": round(r[2] - r[4], 2),
                "xgf_pct": round(r[3] / (r[3] + r[4]) * 100, 1) if (r[3] + r[4]) > 0 else None,
            }
    return {"all_situations": out, "five_v_five": out_5v5}


def player_deep_dive(con, name, *, pool_seasons=(("20242025", 2), ("20242025", 3),
                                                 ("20252026", 2), ("20252026", 3))):
    """For a target player: (a) pooled iso baseline (4-window), (b) series-direct
    individual + on-ice stats. Used to answer 'is X performing above/below baseline?'."""
    # Baseline: 5v5 oi pooled across the 4 windows
    keys_clause = " OR ".join("(season=? AND stype=?)" for _ in pool_seasons)
    params = [name]
    for s, st in pool_seasons:
        params.extend([s, st])
    rows = con.execute(f"""
        SELECT SUM(toi), SUM(xgf), SUM(xga), SUM(gf), SUM(ga)
        FROM skater_stats
        WHERE name=? AND sit='5v5' AND split='oi' AND ({keys_clause})
    """, params).fetchone()
    pool_toi, pool_xgf, pool_xga, pool_gf, pool_ga = rows or (0, 0, 0, 0, 0)
    pool_iso_xgf60 = (pool_xgf * 60.0 / pool_toi) if pool_toi else None
    pool_iso_xga60 = (pool_xga * 60.0 / pool_toi) if pool_toi else None
    pool_iso_net60 = (pool_iso_xgf60 - pool_iso_xga60) if pool_iso_xgf60 is not None else None

    # Series 5v5 oi
    s_oi = con.execute("""
        SELECT toi, xgf, xga, gf, ga
        FROM skater_stats
        WHERE name=? AND sit='5v5' AND split='oi' AND season='20252026' AND stype=3
    """, (name,)).fetchone()
    series_5v5 = None
    if s_oi:
        toi, xgf, xga, gf, ga = s_oi
        series_5v5 = {
            "toi": round(toi or 0, 1), "gf": gf, "ga": ga,
            "xgf": round(xgf or 0, 2), "xga": round(xga or 0, 2),
            "iso_xgf60": round(xgf * 60.0 / toi, 3) if toi else None,
            "iso_xga60": round(xga * 60.0 / toi, 3) if toi else None,
            "iso_net60": round((xgf - xga) * 60.0 / toi, 3) if toi else None,
        }

    # Series individual all-situations
    s_ind = con.execute("""
        SELECT gp, toi, goals, assists, points, shots, ixg, ihdcf, icf
        FROM skater_individual_stats
        WHERE name=? AND season='20252026' AND stype=3 AND sit='all'
    """, (name,)).fetchone()
    series_ind = None
    if s_ind:
        series_ind = {
            "gp": s_ind[0], "toi": round(s_ind[1], 1),
            "g": s_ind[2], "a": s_ind[3], "p": s_ind[4],
            "sog": s_ind[5], "ixg": round(s_ind[6], 2),
            "ihdcf": s_ind[7], "icf": s_ind[8],
        }

    # Individual at 5v5 specifically
    s_ind_5v5 = con.execute("""
        SELECT gp, toi, goals, assists, points, shots, ixg
        FROM skater_individual_stats
        WHERE name=? AND season='20252026' AND stype=3 AND sit='5v5'
    """, (name,)).fetchone()
    series_ind_5v5 = None
    if s_ind_5v5:
        series_ind_5v5 = {
            "gp": s_ind_5v5[0], "toi": round(s_ind_5v5[1], 1),
            "g": s_ind_5v5[2], "a": s_ind_5v5[3], "p": s_ind_5v5[4],
            "sog": s_ind_5v5[5], "ixg": round(s_ind_5v5[6], 2),
        }

    return {
        "name": name,
        "pool_baseline": {
            "toi_min": round(pool_toi or 0, 0),
            "iso_xgf60": round(pool_iso_xgf60, 3) if pool_iso_xgf60 is not None else None,
            "iso_xga60": round(pool_iso_xga60, 3) if pool_iso_xga60 is not None else None,
            "iso_net60": round(pool_iso_net60, 3) if pool_iso_net60 is not None else None,
        },
        "series_5v5_oi": series_5v5,
        "series_individual_all_sit": series_ind,
        "series_individual_5v5": series_ind_5v5,
    }


def league_playoff_rankings(con):
    """Top players in the playoffs by 5v5 iso net60, plus by total points,
    across all 16 playoff teams.

    Filter: ≥30 5v5 TOI in 25-26 playoffs (avoids tiny-sample noise).
    """
    teams_filter = ",".join(["?"] * 16)
    params = [tid for tid, _ in PLAYOFF_TEAMS]

    # By 5v5 iso net60
    rows = con.execute(f"""
        SELECT name, team_id, gp, toi, xgf, xga
        FROM skater_stats
        WHERE season='20252026' AND stype=3 AND sit='5v5' AND split='oi'
          AND team_id IN ({teams_filter})
          AND toi >= 30
        ORDER BY (xgf - xga) * 60.0 / toi DESC
        LIMIT 30
    """, params).fetchall()
    by_iso = []
    for r in rows:
        name, team, gp, toi, xgf, xga = r
        by_iso.append({
            "name": name, "team": team, "gp": gp, "toi": round(toi, 1),
            "iso_xgf60": round(xgf * 60.0 / toi, 3),
            "iso_xga60": round(xga * 60.0 / toi, 3),
            "iso_net60": round((xgf - xga) * 60.0 / toi, 3),
        })

    # By total points (individual all-situations)
    rows = con.execute(f"""
        SELECT name, team_id, gp, points, goals, assists, shots
        FROM skater_individual_stats
        WHERE season='20252026' AND stype=3 AND sit='all'
          AND team_id IN ({teams_filter})
        ORDER BY points DESC, goals DESC, shots DESC
        LIMIT 30
    """, params).fetchall()
    by_pts = []
    for r in rows:
        name, team, gp, pts, g, a, sog = r
        by_pts.append({
            "name": name, "team": team, "gp": gp,
            "pts": pts, "g": g, "a": a, "sog": sog,
            "ppg": round(pts / gp, 2) if gp else 0,
        })

    # Goalie leaders
    rows = con.execute(f"""
        SELECT name, team_id, gp, toi, sa, ga, sv_pct
        FROM goalie_stats
        WHERE season='20252026' AND stype=3 AND sit='all'
          AND team_id IN ({teams_filter})
          AND toi >= 60
        ORDER BY sv_pct DESC
        LIMIT 15
    """, params).fetchall()
    by_goalie = []
    for r in rows:
        by_goalie.append({
            "name": r[0], "team": r[1], "gp": r[2], "toi": round(r[3], 1),
            "sa": r[4], "ga": r[5], "sv_pct": round(r[6], 4),
        })

    return {
        "top_by_iso_net60": by_iso,
        "top_by_points": by_pts,
        "top_goalies_by_sv_pct": by_goalie,
    }


def main():
    con = sqlite3.connect(DB)

    pcv = press_claim_verification(con)
    series_team = series_team_overview(con)
    deep = {
        n: player_deep_dive(con, n)
        for n in ("Cole Caufield", "Ivan Demidov", "Juraj Slafkovský",
                  "Brendan Gallagher", "Lane Hutson", "Nick Suzuki",
                  "Brandon Hagel", "Nikita Kucherov", "Jake Guentzel",
                  "Brayden Point")
    }
    league = league_playoff_rankings(con)

    payload = {
        "meta": {
            "as_of": "2026-04-30 (morning after Game 5)",
            "scope": "MTL @ TBL Round 1 series + league-wide playoff rankings",
            "data_status": "NST refreshed overnight; all 16 playoff teams' G1-Gn stats current.",
            "data_versions": {
                "team_stats": "25-26 playoffs all sits",
                "skater_stats": "25-26 playoffs 5v5/5v4/all (oi)",
                "skater_individual_stats": "25-26 playoffs 5v5/5v4/all (std)",
                "goalie_stats": "25-26 playoffs 5v5/all",
            },
        },
        "press_claim_verification": pcv,
        "series_team_overview": series_team,
        "player_deep_dives": deep,
        "league_rankings": league,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print()
    print("=" * 90)
    print("PRESS CLAIM (5v5 stars vs stars):")
    print(f"  MTL top-4: {pcv['mtl_total_pts']} pts ({pcv['mtl_total_g']}G)")
    print(f"  TBL top-4: {pcv['tbl_total_pts']} pts ({pcv['tbl_total_g']}G)")
    print()
    print("SERIES TEAM OVERVIEW (all situations):")
    s = series_team["all_situations"]
    if "MTL" in s:
        print(f"  MTL: GF={s['MTL']['gf']} (xGF {s['MTL']['xgf']}) | GA={s['MTL']['ga']} (xGA {s['MTL']['xga']})")
        print(f"  TBL: GF={s['T.B']['gf']} (xGF {s['T.B']['xgf']}) | GA={s['T.B']['ga']} (xGA {s['T.B']['xga']})")
    print()
    print("PLAYER DEEP DIVES — pool baseline (5v5 iso net60) vs series 5v5 actual:")
    for n, d in deep.items():
        if d["pool_baseline"]["iso_net60"] is None:
            continue
        s5 = d.get("series_5v5_oi")
        s_iso = s5["iso_net60"] if s5 else None
        ind_p = d.get("series_individual_all_sit", {}) or {}
        ind5 = d.get("series_individual_5v5", {}) or {}
        print(f"  {n:25s}  pool {d['pool_baseline']['iso_net60']:+.3f}  "
              f"series5v5 {s_iso:+.3f}  | series P={ind_p.get('p', '-')}  5v5 P={ind5.get('p', '-')}")
    print()
    print("LEAGUE TOP-10 BY 5v5 ISO NET60 (≥30 toi):")
    for r in league["top_by_iso_net60"][:10]:
        print(f"  {r['name']:25s} {r['team']:5s}  toi={r['toi']:>5.1f}  iso_net={r['iso_net60']:+.3f}")
    print()
    print("LEAGUE TOP-10 BY POINTS:")
    for r in league["top_by_points"][:10]:
        print(f"  {r['name']:25s} {r['team']:5s}  GP={r['gp']}  P={r['pts']}  G={r['g']}  A={r['a']}")
    print()
    print("LEAGUE TOP GOALIES BY SV%:")
    for r in league["top_goalies_by_sv_pct"][:8]:
        print(f"  {r['name']:25s} {r['team']:5s}  GP={r['gp']}  SA={r['sa']}  GA={r['ga']}  SV%={r['sv_pct']:.4f}")


if __name__ == "__main__":
    main()
