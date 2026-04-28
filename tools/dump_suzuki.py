"""One-shot script: dump everything Lemieux's data model has on Nick Suzuki."""
import sys, sqlite3, json, pathlib, glob
sys.path.insert(0, 'packages/lemieux-core/src')
from lemieux.core.comparable import ComparableIndex
import yaml

con = sqlite3.connect('legacy/data/store.sqlite')
con.row_factory = sqlite3.Row

print('=' * 82)
print('NICK SUZUKI — full data model snapshot')
print('=' * 82)

# 1. Bio
print()
print('[1] STATIC BIO — table: edge_player_bio')
print('-' * 82)
pid = None
for r in con.execute("SELECT * FROM edge_player_bio WHERE name='Nick Suzuki'"):
    pid = r['player_id']
    for k, v in dict(r).items():
        print(f'    {k:18s}  {v}')

# 2. NST on-ice stats
print()
print('[2] NST ON-ICE STATS — table: skater_stats (5v5 + 5v4 + all)')
print('-' * 82)
print(f'    {"season":<10}{"stype":<8}{"sit":<5}{"GP":>4}{"TOI":>8}{"GF":>4}{"GA":>4}{"xGF":>7}{"xGA":>7}{"CF%":>7}{"xGF%":>7}')
for r in con.execute(
    "SELECT season, stype, sit, gp, toi, gf, ga, xgf, xga, cf, ca "
    "FROM skater_stats WHERE name='Nick Suzuki' AND split='oi' AND sit IN ('5v5','5v4','all') "
    "ORDER BY season, stype, sit"
):
    toi = r['toi'] or 0
    if toi < 1:
        continue
    cf = r['cf'] or 0; ca = r['ca'] or 0
    xgf = r['xgf'] or 0; xga = r['xga'] or 0
    cfp = 100*cf/(cf+ca) if (cf+ca) else 0
    xgfp = 100*xgf/(xgf+xga) if (xgf+xga) else 0
    stype = {2:'reg',3:'playoff'}.get(r['stype'], str(r['stype']))
    print(f'    {r["season"]:<10}{stype:<8}{r["sit"]:<5}{(r["gp"] or 0):>4}{toi:>8.0f}{r["gf"] or 0:>4}{r["ga"] or 0:>4}{xgf:>7.1f}{xga:>7.1f}{cfp:>6.1f}%{xgfp:>6.1f}%')

# 3. Edge biometric
print()
print('[3] NHL EDGE SKATING/SHOT — table: edge_player_features')
print('-' * 82)
print(f'    {"season":<10}{"stype":<8}{"max_speed":>10}{"bursts22+":>10}{"bursts20-22":>12}{"max_shot":>9}{"hard90+":>9}{"hard80-90":>10}')
edge_rows = list(con.execute(
    'SELECT season, game_type, max_skating_speed_mph, skating_burst_count_22plus, '
    'skating_burst_count_20to22, max_shot_speed_mph, hard_shot_count_90plus, hard_shot_count_80to90 '
    'FROM edge_player_features WHERE player_id=? ORDER BY season, game_type', (pid,)
))
any_data = False
for r in edge_rows:
    if not (r['max_skating_speed_mph'] or r['max_shot_speed_mph']):
        continue
    any_data = True
    stype = {2:'reg',3:'playoff'}.get(r['game_type'], str(r['game_type']))
    speed = f'{r["max_skating_speed_mph"]:.2f}' if r['max_skating_speed_mph'] else 'n/a'
    shot = f'{r["max_shot_speed_mph"]:.2f}' if r['max_shot_speed_mph'] else 'n/a'
    print(f'    {r["season"]:<10}{stype:<8}{speed:>10}{r["skating_burst_count_22plus"]:>10}{r["skating_burst_count_20to22"]:>12}{shot:>9}{r["hard_shot_count_90plus"]:>9}{r["hard_shot_count_80to90"]:>10}')
if not any_data:
    print(f'    {len(edge_rows)} placeholder rows; no populated data yet (background biometrics job ~40%)')

# 4. NST individual stats
print()
print('[4] NST INDIVIDUAL — table: skater_stats split=bio')
print('-' * 82)
cols_all = [r[1] for r in con.execute('PRAGMA table_info(skater_stats)')]
indiv_cols = [c for c in cols_all if c not in ('player_id','team_id','season','stype','sit','split','name','position','gp','toi')]
sql_cols = 'season, stype, sit, gp, toi, ' + ', '.join(indiv_cols) if indiv_cols else 'season, stype, sit, toi'
for r in con.execute(
    f"SELECT {sql_cols} FROM skater_stats WHERE name='Nick Suzuki' AND split='bio' AND sit='all' ORDER BY season, stype"
):
    stype = {2:'reg',3:'playoff'}.get(r['stype'], str(r['stype']))
    gp = r["gp"] if r["gp"] is not None else "?"
    toi = r["toi"] or 0
    print(f'    {r["season"]:<10}{stype:<8}{r["sit"]:<5}GP={gp!s:>3}  TOI={toi:.0f}')
    nonnull = [(c, r[c]) for c in indiv_cols if r[c] not in (None, 0)]
    for chunk in [nonnull[i:i+5] for i in range(0, len(nonnull), 5)]:
        print('         ' + '  '.join(f'{c}={v}' for c, v in chunk))

# 5. Scouting profile
print()
print('[5] SCOUTING PROFILE')
print('-' * 82)
for r in con.execute("SELECT * FROM scouting_profiles WHERE name='Nick Suzuki'"):
    print(f'    extracted_at: {r["extracted_at"]}')
    print(f'    position recorded: {r["position"]!r}')
    sources = json.loads(r['sources_json'] or '[]')
    print(f'    sources searched ({len(sources)}):')
    for s in sources:
        print(f'      - {s}')

print()
print('    Continuous attributes (1-5 scale):')
attrs = list(con.execute("SELECT * FROM scouting_attributes WHERE name='Nick Suzuki'"))
if not attrs:
    print('      (none populated)')
for a in attrs:
    print(f'      {a["attribute"]:18s}  value={a["value"]:.1f}/5  conf={a["confidence"]:.2f}  src_count={a["source_count"]}')

print()
print('    Archetype tags (sorted by conf):')
tags = list(con.execute("SELECT * FROM scouting_tags WHERE name='Nick Suzuki' ORDER BY confidence DESC"))
if not tags:
    print('      (none)')
for t in tags:
    print(f'      {t["tag"]:14s}  conf={t["confidence"]:.2f}')
    print(f'        "{t["source_quote"][:160]}"')
    print(f'        {t["source_url"]}')

print()
print('    Comparable mentions:')
cms = list(con.execute("SELECT * FROM scouting_comparable_mentions WHERE name='Nick Suzuki'"))
if not cms:
    print('      (none)')
for c in cms:
    print(f'      -> {c["comp_name"]}  ({c["polarity"]})')
    print(f'         "{c["source_quote"][:140]}"')

# 6. Skater kNN cohort
print()
print('[6] SKATER COMPARABLE INDEX — file: comparable_index.json')
print('-' * 82)
idx = ComparableIndex.load(pathlib.Path('legacy/data/comparable_index.json'))
target_meta = None
for m in idx.row_meta:
    if (m.get('name') or '').lower() == 'nick suzuki':
        target_meta = m
        break
if target_meta:
    print('    Indexed row meta:')
    for k, v in target_meta.items():
        if isinstance(v, float):
            print(f'      {k:24s}  {v:+.4f}' if 'iso' in k else f'      {k:24s}  {v:.1f}')
        else:
            print(f'      {k:24s}  {v}')
    print()
    print('    Top-7 NHL kNN comps:')
    print(f'    {"score":>6}  {"name":24s}  pos  {"toi":>6}  iso_xGF/60  iso_xGA/60   net      top drivers')
    print('    ' + '-' * 120)
    comps = idx.find_comparables('Nick Suzuki', k=7)
    for c in comps:
        net = c.pooled_iso_xgf60 - c.pooled_iso_xga60
        drivers = sorted(c.feature_contributions.items(), key=lambda x: -x[1])[:3]
        drv_str = '  '.join(f'{k}=Δz{v:+.2f}' for k, v in drivers)
        print(f'    {c.score:>6.1f}  {c.name:24s}  {c.position:3s}  {c.pooled_toi_5v5:>6.0f}  {c.pooled_iso_xgf60:+.3f}    {c.pooled_iso_xga60:+.3f}   {net:+.3f}  {drv_str}')

# 7. Game-context anchors
print()
print('[7] GAME-CONTEXT ANCHORS — files: examples/habs_round1_2026/gameN_context.yaml')
print('-' * 82)
for path in sorted(glob.glob('examples/habs_round1_2026/game*_context.yaml')):
    try:
        with open(path, encoding='utf-8') as f:
            ctx = yaml.safe_load(f)
        gname = pathlib.Path(path).stem
        gseq = ctx.get('goal_sequence', []) or []
        suz_goals = [g for g in gseq if 'Suzuki' in (g.get('scorer', '') or '')]
        suz_assists = [g for g in gseq if 'Suzuki' in str(g.get('assists', []) or [])]
        evts = [e for e in (ctx.get('key_events', []) or []) if 'Suzuki' in str(e)]
        if suz_goals or suz_assists or evts:
            print(f'    {gname}  ({ctx.get("final_score","?")} — {ctx.get("result","?")})')
            for g in suz_goals:
                print(f'      goal:   P{g.get("period")} {g.get("time_in_period")} ({g.get("situation","")})')
            for g in suz_assists:
                print(f'      assist: P{g.get("period")} {g.get("time_in_period")} on goal by {g.get("scorer","")}')
            for e in evts:
                print(f'      event:  {e.get("kind")}  P{e.get("period")} {e.get("time_in_period")}  -- {(e.get("significance","") or "")[:120]}')
    except Exception as ex:
        print(f'    {path}: error ({ex})')

# 8. PBP-direct
print()
print('[8] CURRENT-SERIES — playoff_rankings.numbers.json')
print('-' * 82)
with open('examples/habs_round1_2026/playoff_rankings.numbers.json', encoding='utf-8') as f:
    d = json.load(f)
ind = d.get('individual', [])
suz = next((p for p in ind if 'Suzuki' in p.get('name', '')), None)
if suz:
    for k, v in suz.items():
        print(f'    individual.{k:14s}  {v}')
suz_5v5 = next((p for p in d.get('rank_5v5', []) if 'Suzuki' in p.get('name', '')), None)
if suz_5v5:
    print()
    print('  series 5v5 isolated rank (rank_5v5):')
    for k, v in suz_5v5.items():
        print(f'    {k:18s}  {v}')
suz_5v4 = next((p for p in d.get('rank_5v4', []) if 'Suzuki' in p.get('name', '')), None)
if suz_5v4:
    print()
    print('  series 5v4 isolated rank (rank_5v4):')
    for k, v in suz_5v4.items():
        print(f'    {k:18s}  {v}')
