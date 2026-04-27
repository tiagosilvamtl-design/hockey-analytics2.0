# `examples/habs_round1_2026/` — three worked end-to-end analyses

This directory holds the canonical worked examples that demonstrate the Lemieux data flow end-to-end. New contributors should read this before extending the framework. Anything that works here is a pattern other game series can copy.

## What's in here

### 1. Round 1 standalone report (pre-Game 3)

A snapshot of MTL vs TBL Round 1 status before Game 3 — swap-scenario analyses, claims ledger, optimal lineup, Slafkovský period analysis.

- Generator: `legacy/analytics/habs_round1.py` (orchestrator, predates the `packages/*` layout)
- Renderer: `legacy/reports/build_habs_round1_2026.js`
- Output: `habs_round1_2026.docx`, `habs_round1_2026.numbers.json`, `habs_round1_2026.md`

### 2. Per-game analysis (Game 3, 2026-04-24)

The post-game report for MTL vs TBL Game 3, with the new line-reshuffle finding leading the post and the structural-input pattern in full effect.

- Analyzer: `game3_analysis.py` — pulls NST playoff totals, NHL.com shift+PBP for the three games, computes `series_goalscorers`, `mtl_lineup_drift_g2_to_g3`, `slaf_fight_buckets`, `mtl_progression`, etc.
- Lineup input: `game3_lineups.yaml` — canonical fact base for line composition (read by the renderer; `draft-game-post` skill mandates loading this)
- Usage layer: `game3_usage_observations.yaml` — interview-derived deployment notes (Hutson 26:28, Sabourin OT cameo, etc.)
- Renderer: `build_game3_post.js` — branded EN+FR docx with `runProseFactCheck()` guard
- Audit: `game3_analysis.numbers.json`
- Reports: `game3_post_2026-04-25_{EN,FR}.docx`

### 3. Playoff rankings report (after Game 3, 2026-04-26)

A snapshot ranking of MTL skaters by advanced analytics (5v5 iso net, 5v4 iso offense, individual production, regression vs regular season, goalies).

- Analyzer: `playoff_rankings.py` — same data sources, but ranked output. Includes the **canonical goalie SV% method** (PBP-direct shot+goal counting, supersedes the buggy per_game-derived computation in `game3_analysis.py`).
- Renderer: `build_playoff_rankings_post.js` — same branded shell, prose fact-check guard active
- Audit: `playoff_rankings.numbers.json`
- Reports: `playoff_rankings_2026-04-26_{EN,FR}.docx`

## Reproducing any of these

You'll need:
- The repo cloned, Python venv set up, `pip install -e packages/lemieux-core packages/lemieux-glossary packages/lemieux-connectors`
- Your NST access key in `.env` at the repo root (`NST_ACCESS_KEY=...`)
- Node + `npm install` at the repo root (for the docx builder deps: `docx`, `yaml`)

Then for the playoff rankings:

```bash
# 1. Compute the analysis JSON
.venv/Scripts/python examples/habs_round1_2026/playoff_rankings.py

# 2. Render branded docx (runs prose fact-check guard first; aborts on violations)
node examples/habs_round1_2026/build_playoff_rankings_post.js

# 3. Optionally push to Google Drive
.venv/Scripts/python tools/push_to_drive.py --public --folder-public \
  --folder "Lemieux Hockey Analytics" \
  examples/habs_round1_2026/playoff_rankings_2026-04-26_*.docx
```

For the Game 3 post, swap `playoff_rankings` → `game3_analysis` in step 1 and `build_playoff_rankings_post` → `build_game3_post` in step 2.

## What this directory demonstrates (the patterns to copy)

1. **Analyzer → JSON → renderer → guard → docx → Drive** as the canonical pipeline.
2. **Structured input files** (`game3_lineups.yaml`, `game3_usage_observations.yaml`) as canonical fact bases that the renderer reads from. The renderer never improvises facts that the data could provide.
3. **Per-game context files** (`game1_context.yaml` … `game4_context.yaml`) as the canonical cross-game fact base. Any doc that references events from a previously analyzed game (a fight, a hit, a final score, a series state) MUST read the relevant context file first — prose memory is not a source. See [`docs/en/game-context-files.md`](../../docs/en/game-context-files.md) for the schema and `examples/habs_round1_2026/game_context_check.js` for the mechanical guard (`assertGameClaim`, `assertScore`, `assertSeriesState` — abort with exit code 8 on mismatch).
4. **Build-time prose fact-check guard** — `runProseFactCheck()` walks every prose string in the language objects and aborts the build if any roster name with 0 goals appears as the subject of a scoring verb. The pattern can (and should) be extended to validate other kinds of factual claims (ice time, assist credits, etc.) as the framework matures.
5. **Branded EN+FR docx output** — same structure both languages, FR prose run through `translate-to-quebec-fr` style.
6. **Caveats over confidence** — every section that cites a small-sample number explicitly flags it. The reader always knows when they're looking at a robust signal vs. a directional read.
7. **Live in-game pipeline** (`game4_periods.py` + `build_game4_periods_post.js`) — generic multi-period analyzer that auto-detects completed periods from PBP `period-end` events, computes per-period rankings + cumulative + period-over-period deltas, and renders a docx with the **score barème** legend (calibrated on 2024 + 2025 playoffs via `tools/score_calibration.py`) coloring each composite-score cell by tier (Awful / Mediocre / Good / Excellent). When `gameState=='FINAL'` the renderer also adds a goal-sequence narrative table, pre-game-thesis check, and player-of-the-match spotlight.

## Known caveats / data integrity notes

- `game3_analysis.py:game_level_team_stats` has a known goal-count bug in its per-game home/away counters (it produced `Dobeš 74/7/.905` when the truth was `74/8/.892`). The PBP-direct method in `playoff_rankings.py:goalie_summary` is canonical. The Game 3 docx has been corrected.
- The Slafkovský fight-bucket analysis joins NHL.com shift charts to play-by-play events — NST's game reports don't expose per-period player splits, so this layer depends on NHL.com endpoints holding their schema.
- Playoff samples are 1-3 games; every iso-impact rate has wide implicit CIs. Reports treat the directions as informative and the magnitudes as noisy.

## Sources

See [SOURCES.md](../../SOURCES.md) at the repo root for license posture and per-source notes.
