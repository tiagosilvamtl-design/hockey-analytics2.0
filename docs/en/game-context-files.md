# Per-game context files

Every game we ever analyze gets a `gameN_context.yaml` file. It is the
**canonical fact base** for that game — the single source of truth a future
report consults whenever it references the game by number, by event, or by
score.

Without this convention, prose memory drifts. The framework already shipped
one report that mis-attributed the Hagel-Slafkovský fight to Game 3 when it
was Game 2. Per-game context files prevent that class of error
*structurally*, not by hoping a human catches it.

## The rule

If a doc you're writing refers to events from a previously analyzed game:

- "the Hagel fight in Game 2"
- "MTL won Game 1 in OT"
- "Crozier hit Slafkovský in Game 4"

…then you **must read the relevant `gameN_context.yaml` first** and verify
the claim against it. **Prose memory is not a source.**

## Schema

A context file has these sections:

```yaml
schema_version: 1
game_id: "2025030122"          # NHL.com 10-digit gameId
date: "2026-04-21"
season: "20252026"
game_type: 3                    # 2 = regular, 3 = playoffs
series: "Round 1, MTL vs TBL"
series_game: 2                  # this is the 2nd game of the series

home_team: "TBL"
away_team: "MTL"
matchup: "MTL @ TBL"
final_score: { TBL: 3, MTL: 2 }
result: "TBL 3 - MTL 2 (OT)"
regulation_or_overtime: "OT"     # REG | OT | SO
completed_periods: [1, 2, 3, 4]

goalies:
  TBL: "A. Vasilevskiy"
  MTL: "J. Dobes"

goalscorers:
  TBL: { "B. Hagel": 1, "N. Kucherov": 1, "J. Moser": 1 }
  MTL: { "L. Hutson": 1, "J. Anderson": 1 }

goal_sequence:
  - period: 1
    time: "08:40"
    team: TBL
    scorer: "B. Hagel"
    assist1: "J. Guentzel"
    assist2: "E. Cernak"
    situation: "5v5"
  # ...

key_events:
  - kind: fight
    period: 2
    time_in_period: "05:14"
    elapsed_sec_in_period: 314
    primary_player: "J. Slafkovský"
    team: MTL
    details: "5-min fighting major; drawn by B. Hagel"
    significance: |
      FRAMEWORK ANCHOR: ...
      (the narrative significance — when the event recurs across reports)
  - kind: hit
    period: 3
    time_in_period: "04:44"
    hittee: "J. Slafkovský"
    hitter: "D. Raddysh"
    zone: D
    significance: "..."

series_state_after_game: "tied 1-1"

file_pointers:
  pbp_url: "https://api-web.nhle.com/v1/gamecenter/<gameId>/play-by-play"
  boxscore_url: "https://api-web.nhle.com/v1/gamecenter/<gameId>/boxscore"
  shifts_url: "https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=<gameId>"
  analyzer_output: "examples/.../<gameN>_analysis.numbers.json"
  lineups_yaml: "examples/.../<gameN>_lineups.yaml"

related_briefs:
  - "examples/.../<gameN>_post_<date>_EN.docx"
  - "examples/.../<gameN>_post_<date>_FR.docx"

notes: |
  Free-form narrative the data alone can't capture: deployment context,
  line-blender pivots, injury rumours, beat-reporter color, etc.
```

## Two types of fields

**Data-derivable** — populated by `tools/build_game_context.py` from NHL.com
PBP + boxscore: `final_score`, `result`, `goalies`, `goalscorers`,
`goal_sequence`, raw `key_events` (penalties / fights / Slafkovský
hits-against), `file_pointers` (URLs).

**Manual** — filled in by a human after game analysis: `series` label,
`series_game` index, the `significance` line on each `key_event`,
`series_state_after_game`, `related_briefs`, `notes`. The generator marks
these `TODO_MANUAL` so you know what to fill.

## Generating a starter file

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_game_context.py \
    2025030121 2025030122 2025030123 2025030124 \
    --series "Round 1, MTL vs TBL" \
    --series-start-game 1 \
    --output-dir examples/habs_round1_2026/
```

The first id becomes `series_game = --series-start-game` (default 1), the
second `+1`, etc. Files are written as `game<n>_context.yaml`.

## Mechanical fact-check (use it in renderers)

`examples/habs_round1_2026/game_context_check.js` exposes:

```javascript
const ctxCheck = require('./game_context_check');

ctxCheck.assertGameClaim({
  game: 2, kind: 'fight', period: 2, time: '05:14',
  contextDir: __dirname,
});

ctxCheck.assertScore({
  game: 4, expected: 'TBL 3 - MTL 2',
  contextDir: __dirname,
});

ctxCheck.assertSeriesState({
  afterGame: 4, expected: 'tied 2-2',
  contextDir: __dirname,
});
```

Each assertion **aborts the build with exit code 8** if the claim
contradicts the context file or the file is missing. Add these calls at
the top of any renderer that references prior games — the build itself
becomes the verifier.

## When to add / update

- **A new game gets analyzed**: generate its context file before writing
  any analytical artifact.
- **A previously analyzed game is referenced**: load that game's context
  file *first*; then write the prose; then add an `assertGameClaim` /
  `assertScore` call to the renderer.
- **A new framework-anchor event is identified**: update the
  `significance` line on the relevant `key_event` to flag it
  (`FRAMEWORK ANCHOR: ...`) so future writers recognize the cross-game
  importance.

## What this *isn't*

- It's not a per-game analyzer output (that's `<gameN>_analysis.numbers.json`).
- It's not a lineup file (that's `<gameN>_lineups.yaml`).
- It's not a usage-observation file (that's `<gameN>_usage_observations.yaml`).

The context file is the **cross-game lookup layer** — the quick
fact-check sheet you reach for whenever a doc mentions another game by
name. It coexists with the deeper artifacts above, doesn't replace them.

## See also

- `CLAUDE.md` §4 — schema as part of the data-flow invariant
- `CLAUDE.md` §9 — "don't reference a previously analyzed game from prose memory"
- `tools/build_game_context.py` — generator
- `examples/habs_round1_2026/game{1,2,3,4}_context.yaml` — worked examples
