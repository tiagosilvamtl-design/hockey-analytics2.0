"""Arber Xhekaj special — what does the +2.01 actually mean?

Conversational deep dive: small-sample iso, career baseline, comp cohort,
and the absurd extrapolation question (if he sustained +2 net60 over 82 GP,
who would he be?). Output for a renderer that goes chum-au-bar register.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
OUT = HERE / "arber_special.numbers.json"
DB = REPO / "legacy" / "data" / "store.sqlite"

sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))
from lemieux.core.comparable import ComparableIndex


def main():
    con = sqlite3.connect(DB)

    # 1. Bio
    bio = dict(zip(
        [c[1] for c in con.execute("PRAGMA table_info(edge_player_bio)").fetchall()],
        con.execute("SELECT * FROM edge_player_bio WHERE name='Arber Xhekaj'").fetchone() or []
    ))

    # 2. Pooled iso (24-25 + 25-26 reg+playoff)
    r = con.execute("""
        SELECT SUM(toi), SUM(xgf), SUM(xga)
        FROM skater_stats
        WHERE name='Arber Xhekaj' AND sit='5v5' AND split='oi'
          AND ((season='20242025' AND stype IN (2,3))
            OR (season='20252026' AND stype IN (2,3)))
    """).fetchone()
    pool_toi, pool_xgf, pool_xga = r
    pool = {
        "toi": round(pool_toi, 0),
        "xgf": round(pool_xgf, 2),
        "xga": round(pool_xga, 2),
        "iso_xgf60": round(pool_xgf * 60 / pool_toi, 3),
        "iso_xga60": round(pool_xga * 60 / pool_toi, 3),
        "iso_net60": round((pool_xgf - pool_xga) * 60 / pool_toi, 3),
    }

    # 3. Career history (5v5)
    history = []
    for r in con.execute("""
        SELECT season, stype, gp, toi, xgf, xga
        FROM skater_stats
        WHERE name='Arber Xhekaj' AND sit='5v5' AND split='oi' AND toi > 0
        ORDER BY season, stype
    """):
        s, st, gp, toi, xgf, xga = r
        history.append({
            "season": s, "stype": st, "gp": gp, "toi": round(toi, 1),
            "iso_net60": round((xgf - xga) * 60 / toi, 3),
            "label": f"{s[:4]}-{s[4:6]} {('reg' if st == 2 else 'playoff')}",
        })

    # 4. Series individual all sit + hits/pim
    s = con.execute("""
        SELECT gp, toi, goals, assists, points, shots, hits, pim, ihdcf, takeaways, giveaways
        FROM skater_individual_stats
        WHERE name='Arber Xhekaj' AND season='20252026' AND stype=3 AND sit='all'
    """).fetchone()
    series_individual = None
    if s:
        series_individual = {
            "gp": s[0], "toi": round(s[1], 0),
            "g": s[2], "a": s[3], "p": s[4],
            "sog": s[5], "hits": s[6], "pim": s[7], "ihdcf": s[8],
            "takeaways": s[9], "giveaways": s[10],
        }

    # 5. Series 5v5 oi
    s5 = con.execute("""
        SELECT toi, xgf, xga, gf, ga
        FROM skater_stats
        WHERE name='Arber Xhekaj' AND sit='5v5' AND split='oi'
          AND season='20252026' AND stype=3
    """).fetchone()
    series_5v5 = None
    if s5:
        toi, xgf, xga, gf, ga = s5
        series_5v5 = {
            "toi": round(toi, 1), "gf": gf, "ga": ga,
            "xgf": round(xgf, 2), "xga": round(xga, 2),
            "iso_xgf60": round(xgf * 60 / toi, 3),
            "iso_xga60": round(xga * 60 / toi, 3),
            "iso_net60": round((xgf - xga) * 60 / toi, 3),
        }

    # 6. Tags (with verbatim source quotes)
    tags = [
        {"tag": r[0], "confidence": round(r[1], 2),
         "source_quote": (r[2] or "")[:300], "source_url": r[3] or ""}
        for r in con.execute("""
            SELECT tag, confidence, source_quote, source_url
            FROM scouting_tags
            WHERE name='Arber Xhekaj' ORDER BY confidence DESC
        """).fetchall()
    ]

    # 7. kNN comps
    idx = ComparableIndex.load(REPO / "legacy" / "data" / "comparable_index.json")
    comps = []
    try:
        for c in idx.find_comparables("Arber Xhekaj", k=8, min_pooled_toi=200.0):
            comps.append({
                "name": c.name, "position": c.position, "score": round(c.score, 1),
                "pooled_toi_5v5": round(c.pooled_toi_5v5, 0),
                "iso_xgf60": round(c.pooled_iso_xgf60, 3),
                "iso_xga60": round(c.pooled_iso_xga60, 3),
                "iso_net60": round(c.pooled_iso_xgf60 - c.pooled_iso_xga60, 3),
            })
    except Exception as e:
        print(f"comp lookup err: {e}")

    # 8. Top defensemen for the extrapolation context
    top_d = []
    for r in con.execute("""
        SELECT name, SUM(toi) as toi,
               (SUM(xgf)-SUM(xga))*60.0/SUM(toi) as iso_net
        FROM skater_stats
        WHERE position='D' AND sit='5v5' AND split='oi'
          AND ((season='20242025' AND stype IN (2,3))
            OR (season='20252026' AND stype IN (2,3)))
        GROUP BY name
        HAVING toi >= 1500
        ORDER BY iso_net DESC LIMIT 8
    """):
        top_d.append({
            "name": r[0], "toi": round(r[1], 0),
            "iso_net60": round(r[2], 3),
        })

    # 9. The fun extrapolation
    series_iso_net = series_5v5["iso_net60"] if series_5v5 else None
    typical_3rd_pair_5v5_per_game = 12.0  # min/game at 5v5 for a 3rd-pair D
    minutes_in_82 = 82 * typical_3rd_pair_5v5_per_game
    if series_iso_net is not None:
        season_xg_net = series_iso_net * minutes_in_82 / 60.0
    else:
        season_xg_net = None
    league_top = top_d[0]["iso_net60"] if top_d else None
    multiple_of_top_d = (
        round(series_iso_net / league_top, 1) if (league_top and league_top > 0) else None
    )

    extrapolation = {
        "playoff_iso_net60": series_iso_net,
        "assumed_5v5_min_per_game_82gp": typical_3rd_pair_5v5_per_game,
        "total_5v5_min_82gp": minutes_in_82,
        "extrapolated_season_xg_net": round(season_xg_net, 1) if season_xg_net else None,
        "league_top_d_iso_net60_pooled": league_top,
        "league_top_d_name": top_d[0]["name"] if top_d else None,
        "multiple_of_league_top_d": multiple_of_top_d,
        "honest_caveat": (
            f"Sample = {round(s5[0] if s5 else 0, 1)} 5v5 minutes across 5 playoff games. "
            f"At ~10 min/game, a single shift moving the puck the right way swings the per-60 "
            f"rate by ±0.5. The extrapolation is mathematically clean and physically meaningless."
        ),
    }

    # 10. Habs L1 comparison just to show what +2 looks like in real life
    hutson = con.execute("""
        SELECT SUM(toi), (SUM(xgf)-SUM(xga))*60.0/SUM(toi)
        FROM skater_stats
        WHERE name='Lane Hutson' AND sit='5v5' AND split='oi'
          AND ((season='20242025' AND stype IN (2,3))
            OR (season='20252026' AND stype IN (2,3)))
    """).fetchone()
    hutson_baseline = {"toi": round(hutson[0], 0), "iso_net60": round(hutson[1], 3)} if hutson and hutson[0] else None

    payload = {
        "meta": {
            "as_of": "2026-04-30",
            "scope": "Arber Xhekaj — what does the +2.01 series iso actually mean?",
        },
        "bio": bio,
        "pooled_baseline_24_25_25_26": pool,
        "career_history": history,
        "series_individual_all_sit": series_individual,
        "series_5v5_oi": series_5v5,
        "tags": tags,
        "knn_comps": comps,
        "league_top_d_pooled": top_d,
        "hutson_baseline_for_context": hutson_baseline,
        "fun_extrapolation": extrapolation,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"wrote {OUT}")
    print()
    print(f"Xhekaj career pooled (24-25 + 25-26): iso_net60 = {pool['iso_net60']:+.3f}")
    print(f"Xhekaj 25-26 PLAYOFF (49 min, 5 GP):   iso_net60 = {series_5v5['iso_net60']:+.3f}")
    print(f"League top D pooled (Adam Fox):        iso_net60 = {league_top:+.3f}")
    print(f"Xhekaj's playoff = {multiple_of_top_d}× the league's best D over a full sample.")
    print()
    print(f"Extrapolation: {round(extrapolation['extrapolated_season_xg_net'], 1)} expected GF net per 82 GP at his playoff pace.")
    print()
    print("Top kNN comps (career baseline):")
    for c in comps[:6]:
        print(f"  {c['name']:25s}  iso_net={c['iso_net60']:+.3f}  ({c['pooled_toi_5v5']} toi)")


if __name__ == "__main__":
    main()
