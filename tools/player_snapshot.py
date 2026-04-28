"""Generic 'tell me everything Lemieux knows about player X' dump.

Auto-detects skater vs goalie from edge_player_bio.position and renders the
appropriate tables. Generalization of the per-player ad-hoc dump scripts.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/player_snapshot.py "Nick Suzuki"
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/player_snapshot.py "Jakub Dobeš"
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sqlite3
import sys
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core.comparable import ComparableIndex


def ascii_fold(s: str) -> str:
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def resolve(con: sqlite3.Connection, name_query: str):
    """Return (canonical_name, player_id, position, position_kind) for the closest match.

    position_kind is 'skater' or 'goalie'. Search prefers exact match, then
    LIKE, on either the raw name or the ASCII-folded form (handles unicode like Dobeš).
    """
    target_folded = ascii_fold(name_query).lower()
    # Prefer edge_player_bio (covers everyone resolved on either pipeline)
    rows = con.execute(
        "SELECT player_id, name, position FROM edge_player_bio"
    ).fetchall()
    exact_matches = [r for r in rows if (r[1] or "").lower() == name_query.lower()
                     or ascii_fold(r[1] or "").lower() == target_folded]
    like_matches = [r for r in rows if target_folded in ascii_fold(r[1] or "").lower()]
    pool = exact_matches or like_matches
    if not pool:
        return None
    pid, canonical, position = pool[0]
    kind = "goalie" if (position or "").upper() == "G" else "skater"
    return canonical, int(pid), position, kind


def section(title: str) -> None:
    print()
    print(f"[{title}]")
    print("-" * 82)


def render_bio(con: sqlite3.Connection, pid: int) -> None:
    section("STATIC BIO — table: edge_player_bio")
    for r in con.execute("SELECT * FROM edge_player_bio WHERE player_id=?", (pid,)):
        for k, v in dict(r).items():
            print(f"    {k:18s}  {v}")


def render_skater_oi(con: sqlite3.Connection, name: str) -> None:
    section("NST ON-ICE STATS — table: skater_stats")
    print(f'    {"season":<10}{"stype":<8}{"sit":<5}{"GP":>4}{"TOI":>8}{"GF":>4}{"GA":>4}{"xGF":>7}{"xGA":>7}{"CF%":>7}{"xGF%":>7}')
    for r in con.execute(
        "SELECT season, stype, sit, gp, toi, gf, ga, xgf, xga, cf, ca "
        "FROM skater_stats WHERE name=? AND split='oi' AND sit IN ('5v5','5v4','all') "
        "ORDER BY season, stype, sit",
        (name,),
    ):
        toi = r["toi"] or 0
        if toi < 1:
            continue
        cf, ca = r["cf"] or 0, r["ca"] or 0
        xgf, xga = r["xgf"] or 0, r["xga"] or 0
        cfp = 100*cf/(cf+ca) if (cf+ca) else 0
        xgfp = 100*xgf/(xgf+xga) if (xgf+xga) else 0
        stype = {2:"reg", 3:"playoff"}.get(r["stype"], str(r["stype"]))
        print(f'    {r["season"]:<10}{stype:<8}{r["sit"]:<5}{(r["gp"] or 0):>4}{toi:>8.0f}{r["gf"] or 0:>4}{r["ga"] or 0:>4}{xgf:>7.1f}{xga:>7.1f}{cfp:>6.1f}%{xgfp:>6.1f}%')


def render_skater_individual(con: sqlite3.Connection, name: str) -> None:
    section("NST INDIVIDUAL STATS — table: skater_individual_stats (G/A/SOG/ixG/hits/blocks/FO)")
    print(f'    {"season":<10}{"stype":<8}{"GP":>4}{"G":>4}{"A":>4}{"A1":>4}{"A2":>4}{"P":>4}{"SOG":>5}{"ixG":>7}{"iHDCF":>6}{"Hits":>5}{"Blks":>5}{"FOW":>5}{"FO%":>6}')
    for r in con.execute(
        "SELECT * FROM skater_individual_stats WHERE name=? AND sit='all' ORDER BY season, stype",
        (name,),
    ):
        stype = {2:"reg", 3:"playoff"}.get(r["stype"], str(r["stype"]))
        ixg = f'{r["ixg"]:.1f}' if r["ixg"] is not None else "n/a"
        fopc = f'{r["faceoffs_pct"]:.1f}' if r["faceoffs_pct"] is not None else " n/a"
        gp = r["gp"] if r["gp"] is not None else 0
        print(f'    {r["season"]:<10}{stype:<8}{gp:>4}{r["goals"] or 0:>4}{r["assists"] or 0:>4}{r["first_assists"] or 0:>4}{r["second_assists"] or 0:>4}{r["points"] or 0:>4}{r["shots"] or 0:>5}{ixg:>7}{r["ihdcf"] or 0:>6}{r["hits"] or 0:>5}{r["shots_blocked"] or 0:>5}{r["faceoffs_won"] or 0:>5}{fopc:>6}')


def render_goalie_stats(con: sqlite3.Connection, pid: int) -> None:
    section("NST GOALIE STATS — table: goalie_stats")
    print(f'    {"season":<10}{"stype":<8}{"sit":<5}{"GP":>4}{"TOI":>8}{"GA":>5}{"SA":>6}{"xGA":>7}{"HDGA":>5}{"HDCA":>5}{"SV%":>9}{"hdSV%":>9}{"GSAx":>8}')
    rows = con.execute(
        "SELECT * FROM goalie_stats WHERE player_id=? ORDER BY season, stype, sit",
        (str(pid),),
    ).fetchall()
    if not rows:
        # Try int pid
        rows = con.execute(
            "SELECT * FROM goalie_stats WHERE CAST(player_id AS INTEGER)=? ORDER BY season, stype, sit",
            (pid,),
        ).fetchall()
    for r in rows:
        stype = {2:"reg", 3:"playoff"}.get(r["stype"], str(r["stype"]))
        sv = f'{r["sv_pct"]:.3f}' if r["sv_pct"] else "n/a"
        hsv = f'{r["hd_sv_pct"]:.3f}' if r["hd_sv_pct"] is not None else "n/a"
        gsax = f'{r["gsax"]:+.2f}' if r["gsax"] is not None else "n/a"
        print(f'    {r["season"]:<10}{stype:<8}{r["sit"]:<5}{r["gp"]:>4}{r["toi"]:>8.0f}{r["ga"]:>5}{r["sa"]:>6}{r["xga"]:>7.1f}{r["hdga"]:>5}{r["hdca"]:>5}{sv:>9}{hsv:>9}{gsax:>8}')


def render_edge_features(con: sqlite3.Connection, pid: int, kind: str) -> None:
    if kind == "goalie":
        section("NHL EDGE SKATING/SHOT — table: edge_player_features")
        print("    Edge endpoints are skater-only — no biometric data populated for goalies.")
        return
    section("NHL EDGE SKATING/SHOT — table: edge_player_features")
    print(f'    {"season":<10}{"stype":<8}{"max_speed":>10}{"bursts22+":>10}{"bursts20-22":>12}{"max_shot":>9}{"hard90+":>9}{"hard80-90":>10}')
    rows = con.execute(
        "SELECT * FROM edge_player_features WHERE player_id=? ORDER BY season, game_type",
        (pid,),
    ).fetchall()
    any_data = False
    for r in rows:
        if not (r["max_skating_speed_mph"] or r["max_shot_speed_mph"]):
            continue
        any_data = True
        stype = {2:"reg", 3:"playoff"}.get(r["game_type"], str(r["game_type"]))
        speed = f'{r["max_skating_speed_mph"]:.2f}' if r["max_skating_speed_mph"] else "n/a"
        shot = f'{r["max_shot_speed_mph"]:.2f}' if r["max_shot_speed_mph"] else "n/a"
        print(f'    {r["season"]:<10}{stype:<8}{speed:>10}{r["skating_burst_count_22plus"]:>10}{r["skating_burst_count_20to22"]:>12}{shot:>9}{r["hard_shot_count_90plus"]:>9}{r["hard_shot_count_80to90"]:>10}')
    if not any_data:
        print(f"    {len(rows)} placeholder rows; no populated data (player may pre-date Edge tracking or biometrics backfill in progress)")


def render_scouting(con: sqlite3.Connection, name: str, position: str) -> None:
    section("SCOUTING PROFILE — tables: scouting_profiles, scouting_attributes, scouting_tags, scouting_comparable_mentions")
    profs = list(con.execute(
        "SELECT * FROM scouting_profiles WHERE name=? AND position=?",
        (name, position),
    ))
    if not profs:
        # Try without position filter
        profs = list(con.execute("SELECT * FROM scouting_profiles WHERE name=?", (name,)))
    if not profs:
        print("    (no scouting profile)")
        return
    for p in profs:
        print(f'    extracted_at: {p["extracted_at"]}    position recorded: {p["position"]!r}')
        sources = json.loads(p["sources_json"] or "[]")
        print(f'    sources searched ({len(sources)}):')
        for s in sources:
            print(f'      - {s}')

    print()
    print("    Continuous attributes (1-5 scale):")
    attrs = list(con.execute("SELECT * FROM scouting_attributes WHERE name=?", (name,)))
    if not attrs:
        print("      (none populated)")
    for a in sorted(attrs, key=lambda r: -r["confidence"]):
        print(f'      {a["attribute"]:18s}  value={a["value"]:.1f}/5  conf={a["confidence"]:.2f}  src_count={a["source_count"]}')

    print()
    print("    Archetype tags (sorted by confidence):")
    tags = list(con.execute("SELECT * FROM scouting_tags WHERE name=? ORDER BY confidence DESC", (name,)))
    if not tags:
        print("      (none)")
    for t in tags:
        print(f'      {t["tag"]:14s}  conf={t["confidence"]:.2f}')
        print(f'        "{t["source_quote"][:160]}"')
        print(f'        {t["source_url"]}')

    print()
    print('    Comparable mentions ("X reminds me of Y"):')
    cms = list(con.execute("SELECT * FROM scouting_comparable_mentions WHERE name=?", (name,)))
    if not cms:
        print("      (none)")
    for c in cms:
        print(f'      -> {c["comp_name"]}  ({c["polarity"]})')
        print(f'         "{c["source_quote"][:140]}"')


def render_comp_index(name: str, kind: str, k: int = 7) -> None:
    if kind == "goalie":
        section("GOALIE COMPARABLE INDEX — file: goalie_comparable_index.json")
        idx_path = REPO / "legacy" / "data" / "goalie_comparable_index.json"
    else:
        section("SKATER COMPARABLE INDEX — file: comparable_index.json")
        idx_path = REPO / "legacy" / "data" / "comparable_index.json"
    if not idx_path.exists():
        print(f"    (index file not found: {idx_path})")
        return
    idx = ComparableIndex.load(idx_path)
    target_meta = None
    for m in idx.row_meta:
        if (m.get("name") or "").lower() == name.lower():
            target_meta = m
            break
    if not target_meta:
        print(f"    Player not in index: {name!r}")
        return
    print("    Indexed row meta:")
    for k_, v in target_meta.items():
        if isinstance(v, float):
            print(f'      {k_:24s}  {v:+.4f}' if "iso" in k_ else f'      {k_:24s}  {v:.1f}')
        else:
            print(f'      {k_:24s}  {v}')
    print()
    print(f"    Top-{k} NHL kNN comps:")
    if kind == "goalie":
        print(f'    {"score":>6}  {"name":24s}  {"toi":>6}  {"GSAx/60":>8}  top drivers')
    else:
        print(f'    {"score":>6}  {"name":24s}  pos  {"toi":>6}  iso_xGF/60  iso_xGA/60   net      top drivers')
    print("    " + "-" * 116)
    try:
        comps = idx.find_comparables(name, k=k)
    except Exception as e:
        print(f"    find_comparables failed: {e}")
        return
    for c in comps:
        drivers = sorted(c.feature_contributions.items(), key=lambda x: -x[1])[:3]
        drv_str = "  ".join(f"{kk}=Δz{vv:+.2f}" for kk, vv in drivers)
        if kind == "goalie":
            gsax = next((m.get("gsax_per60") for m in idx.row_meta if m.get("name") == c.name), None)
            gsax_s = f"{gsax:+.3f}" if gsax is not None else "n/a"
            print(f'    {c.score:>6.1f}  {c.name:24s}  {c.pooled_toi_5v5:>6.0f}  {gsax_s:>8}  {drv_str}')
        else:
            net = c.pooled_iso_xgf60 - c.pooled_iso_xga60
            print(f'    {c.score:>6.1f}  {c.name:24s}  {c.position:3s}  {c.pooled_toi_5v5:>6.0f}  {c.pooled_iso_xgf60:+.3f}    {c.pooled_iso_xga60:+.3f}   {net:+.3f}  {drv_str}')


def render_game_anchors(name: str) -> None:
    section("GAME-CONTEXT ANCHORS — files: examples/habs_round1_2026/gameN_context.yaml")
    try:
        import yaml
    except ImportError:
        print("    (yaml not installed — skipping game-context lookup)")
        return
    found = False
    for path in sorted(glob.glob(str(REPO / "examples/habs_round1_2026/game*_context.yaml"))):
        try:
            with open(path, encoding="utf-8") as f:
                ctx = yaml.safe_load(f)
            gname = pathlib.Path(path).stem
            gseq = ctx.get("goal_sequence", []) or []
            goals = [g for g in gseq if name in (g.get("scorer", "") or "")]
            assists = [g for g in gseq if name in str(g.get("assists", []) or [])]
            evts = [e for e in (ctx.get("key_events", []) or []) if name in str(e)]
            if goals or assists or evts:
                found = True
                print(f'    {gname}  ({ctx.get("final_score","?")} — {ctx.get("result","?")})')
                for g in goals:
                    print(f'      goal:   P{g.get("period")} {g.get("time_in_period")}  ({g.get("situation","")})')
                for g in assists:
                    print(f'      assist: P{g.get("period")} {g.get("time_in_period")}  on goal by {g.get("scorer","")}')
                for e in evts:
                    print(f'      event:  {e.get("kind")}  P{e.get("period")} {e.get("time_in_period")}  -- {(e.get("significance","") or "")[:120]}')
        except Exception as ex:
            print(f"    {path}: error ({ex})")
    if not found:
        print("    (player not surfaced in any indexed game-context anchors)")


def render_pbp_series(name: str, kind: str) -> None:
    section("CURRENT-SERIES — examples/habs_round1_2026/playoff_rankings.numbers.json")
    pbp_path = REPO / "examples/habs_round1_2026/playoff_rankings.numbers.json"
    if not pbp_path.exists():
        print("    (no PBP-direct rankings file present)")
        return
    with open(pbp_path, encoding="utf-8") as f:
        d = json.load(f)
    if kind == "goalie":
        g = d.get("goalie", {})
        if g.get("name", "").lower() == name.lower() or name.lower() in g.get("name", "").lower():
            for k, v in g.items():
                print(f'    {k:18s}  {v}')
        else:
            print(f"    Series goalie is {g.get('name','?')}, not the target.")
        return
    ind = next((p for p in d.get("individual", []) if name in p.get("name", "")), None)
    if ind:
        print("  individual scoring:")
        for k, v in ind.items():
            print(f'    {k:18s}  {v}')
    suz_5v5 = next((p for p in d.get("rank_5v5", []) if name in p.get("name", "")), None)
    if suz_5v5:
        print()
        print("  series 5v5 isolated rank (rank_5v5):")
        for k, v in suz_5v5.items():
            print(f'    {k:18s}  {v}')
    suz_5v4 = next((p for p in d.get("rank_5v4", []) if name in p.get("name", "")), None)
    if suz_5v4:
        print()
        print("  series 5v4 isolated rank (rank_5v4):")
        for k, v in suz_5v4.items():
            print(f'    {k:18s}  {v}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="Player name (handles unicode and partial matches)")
    ap.add_argument("--k", type=int, default=7, help="Number of comp results to show")
    args = ap.parse_args()

    con = sqlite3.connect(REPO / "legacy" / "data" / "store.sqlite")
    con.row_factory = sqlite3.Row

    res = resolve(con, args.name)
    if not res:
        print(f"No player matching {args.name!r} found.")
        sys.exit(1)
    canonical, pid, position, kind = res

    print("=" * 82)
    print(f"{canonical} — full Lemieux data-model snapshot ({kind})")
    print("=" * 82)

    render_bio(con, pid)
    if kind == "skater":
        render_skater_oi(con, canonical)
        render_skater_individual(con, canonical)
    else:
        render_goalie_stats(con, pid)
    render_edge_features(con, pid, kind)
    render_scouting(con, canonical, position)
    render_comp_index(canonical, kind, k=args.k)
    render_game_anchors(canonical)
    render_pbp_series(canonical, kind)


if __name__ == "__main__":
    main()
