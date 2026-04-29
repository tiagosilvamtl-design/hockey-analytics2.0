# CLAUDE.md — operating guide for working in this repo

This file is read by Claude Code automatically when this directory is opened. Everything below is non-negotiable project convention. If a task seems to violate any of these rails, **stop and ask** rather than working around them.

---

## 1. What this project is

**Lemieux** is an open-source hockey analytics framework that pairs Claude (or any MCP client) with curated data connectors, analytics primitives, and workflow skills to produce analytically rigorous, journalistically honest hockey coverage. The audience is a francophone hockey-fan friend group plus the broader analytics community.

**The framework's central value claim** is that every output (game posts, rankings, swap-scenario projections, etc.) is **traceable to data**, never to narrative recall. If a sentence about hockey can't be traced to a query in `D = analyzer JSON output` or to `LINEUPS = structured lineup yaml`, that sentence does not ship.

---

## 2. The writing rails — every output must obey these

These rules are baked into the `draft-game-post`, `propose-swap-scenario`, and `validate-analysis` skills. The auto-PR-review workflow (`.github/workflows/claude-pr-review.yml`) runs `validate-analysis` against every PR, so violations get flagged at review time. But you are expected to internalize them and not produce violations in the first place.

### Hard rails (any violation = automatic CLOSE)

1. **No predictions of series outcomes.** No "MTL wins in 6", no win-probability scalars, no Cup-odds outputs. The framework grades claims; it does not forecast.
2. **No fabricated quotes.** Every quote attributed to a person must trace to a real, fetchable URL. If the URL 404s or is paywalled, the quote does not ship.
3. **No PlayerScore scalar.** Don't reduce a player to a single grade. Always show iso_xGF/60 and iso_xGA/60 separately so positive offense can't paper over negative defense (and vice versa).
4. **No secrets in repo.** API keys, tokens, OAuth credentials live in `.env` (gitignored), `~/.lemieux/`, or environment variables. Never inline.
5. **No republishing raw third-party data** beyond what `SOURCES.md` explicitly authorizes. Cite + summarize, don't re-host.

### Editorial rails (any violation = REQUEST CHANGES)

6. **Lead with outcomes, not announcements of changes.** By the time a post-game report ships, the audience has watched the game. They know lineup changes happened. The story is what those changes *produced* — not the fact that they happened. See `.claude/skills/draft-game-post/SKILL.md` for the heuristic + worked examples.
7. **Don't restate what was known before the post-data analysis.** "Tampa drives possession" was a pre-series cliché; reconfirming it post-game adds nothing. Every paragraph must answer the test: *could a reader produce this sentence from the box score and yesterday's chatter alone?* If yes, replace with an analysis-derived value-add or cut.
8. **No meta-commentary about the report's own structure.** Sentences like "The rest of this section is about...", "What's interesting here is...", "We'll come back to that...", "Reading order:" all have the author talking to themselves in front of the reader. Strip them.
9. **Lineup data is INPUT to the analysis, not output of it.** Read structured lineup files (`game{N}_lineups.yaml` in the example, generally `<scope>_lineups.yaml`); never infer line composition from press extracts. The build script must abort if the lineup file is missing.
10. **Goalscorer / assist / TOI claims source from data, never narrative recall.** Use `D.series_goalscorers` (PBP-derived) or the analyzer's `individual` output. The build-time prose fact-check guard (see §5) aborts the build if any non-scorer is claimed to have scored.

### Bilingual rails

11. **FR output is not literal-translated EN.** Pass FR drafts through the `translate-to-quebec-fr` skill before finalizing — it documents the Québec hockey-press register, term map (50+ entries), and sentence patterns. Number formatting: comma decimals (`56,1 %`), thin space before `%` and units, `5 c. 5` rather than "5v5" in prose.

---

## 3. Data flow (mental model for every output)

```
[ raw sources ]
   │
   ├── NHL.com PBP + shifts (api-web.nhle.com / api.nhle.com/stats)
   ├── Natural Stat Trick (data.naturalstattrick.com, requires NST_ACCESS_KEY)
   ├── press coverage (research-game skill → research/<gameId>_claims.yaml)
   └── manual notes (usage observations, lineups.yaml)
   │
   ▼
[ analyzer ]  examples/<scope>/<task>.py — Python script
   │           reads SQLite store (legacy/data/store.sqlite) and PBP
   │           computes derived quantities; outputs JSON
   ▼
[ <task>.numbers.json ]  the structured fact base
   │           every number a downstream renderer / skill uses
   │           must trace to a field in here
   ▼
[ structured supporting files ]
   │           game{N}_lineups.yaml (canonical line composition)
   │           game{N}_usage_observations.yaml (interview-derived deployment notes)
   ▼
[ renderer ]  build_<task>_post.js — Node + docx-js
   │           reads JSON + YAML
   │           templates prose AGAINST the data (no narrative recall)
   │           runs `runProseFactCheck()` BEFORE writing the docx
   │           aborts with exit code 7 on prose-data mismatch
   ▼
[ branded docx ]  EN + FR variants, identical structure, FR through Québec style guide
   │
   ▼
[ Drive ]  via tools/push_to_drive.py with --public --folder-public
            anyone-with-link sharing, native docx (not Google Docs auto-convert)
```

**The invariant:** if you find yourself writing a sentence whose facts you can't point to in the JSON or YAML, the data is missing — fix it upstream, do not improvise the fact in prose. Examples of this discipline:

- Goalscorer claims read from `D.series_goalscorers.{MTL,TBL}` (built from `details.scoringPlayerId`).
- Line composition claims read from `LINEUPS.teams.{MTL,TBL}.forwards[].players[]` and `LINEUPS.changes_vs_previous_game.{TEAM}.line_reshuffles[]`.
- Slafkovský pre/post-fight claims read from `D.slaf_fight_buckets.{pre,post}`.
- Goalie SV% reads from PBP-direct shot+goal counting (see `playoff_rankings.py:goalie_summary`), NOT from per-game home/away derived counts (which have a known bug in `game3_analysis.py:game_level_team_stats` — the per_game `home_goals`/`away_goals` counters miscount in some flows).

---

## 4. Structural data invariants

These are the files / fields the framework depends on to keep prose honest. If you change their shape, every consumer breaks.

> **For the full database schema** (skater_stats, skater_individual_stats, goalie_stats, edge_player_bio, edge_player_features, scouting_*, comparable indexes), see [`docs/en/data-model.md`](docs/en/data-model.md). The 5-layer overview lives there. This section enumerates only the file-format invariants that downstream renderers depend on.

### `<gameN>_lineups.yaml`

Canonical fact base for line composition. Required by `draft-game-post`. Schema lives in `.claude/skills/research-game/SKILL.md`. Required fields:

- `teams.{MTL,TBL}.forwards[].players[].{name, position}` — `position` ∈ {`C`, `L`, `R`}
- `teams.{MTL,TBL}.defense[].players[].{name, position, side}`
- `teams.{MTL,TBL}.goalie`
- `teams.{MTL,TBL}.{pp1, pp2, scratches}`
- `previous_game.<TEAM>.forwards[]` — same shape, for drift comparison
- `changes_vs_previous_game.{TEAM}.line_reshuffles[].{description, prior_center, new_center, moved_player, position_held_throughout, line_position_g2, line_position_g3}` — read DIRECTLY into prose by `draft-game-post`. The `prior_center`, `new_center`, and `moved_player` fields are particularly load-bearing.

### `<task>.numbers.json` — analyzer output

The framework's data invariant. Every renderer reads from here. Critical fields by report type:

**Game post (`game{N}_analysis.numbers.json`)**
- `series_goalscorers.{MTL,TBL}[name] = goal_count` — source of truth for any "X scored" claim
- `mtl_g{2,3}_forward_lines[]` — actual deployed line combos by 5-man on-ice overlap (drift detection)
- `mtl_lineup_drift_g2_to_g3` — derived facts about what changed
- `slaf_fight_buckets.{pre,post}` — Slafkovský pre/post Hagel-fight on-ice events
- `mtl_progression.{movers_up, movers_down}` — reg-season vs playoff iso net deltas
- `series_5v5.{MTL,T.B}` — series-totals at 5v5 from NST
- `series_5v4.{MTL,T.B}` — same at 5v4

**Rankings (`playoff_rankings.numbers.json`)**
- `rank_5v5[]` — sorted by net iso impact, with `iso_xgf60`, `iso_xga60`, `net`, `toi`
- `rank_5v4[]` — same at 5v4
- `individual[]` — per-player goals/assists/SOG from PBP
- `goalie` — Dobeš shots faced / GA / SV% (PBP-direct)
- `progression[]` — same shape as `mtl_progression` above

### `<gameN>_usage_observations.yaml`

The qualitative-deployment layer the box score can't tell you. Read by `draft-game-post` to populate the "Usage observations" table. Schema in `.claude/skills/research-game/SKILL.md`.

### `<gameN>_context.yaml` — canonical per-game context (REQUIRED for cross-game references)

Every game we ever analyze gets a `<gameN>_context.yaml` file. This is the canonical fact base for that game — the single source of truth a future doc must consult when it references the game by number, by event, or by score.

**The rule:** if a doc you're writing refers to events from a previously analyzed game (e.g. "the Hagel fight in Game 2", "MTL won Game 3 in OT", "Crozier hit Slafkovský in Game 4"), you MUST read the relevant `<gameN>_context.yaml` first and verify the claim against it. **Prose memory is not a source.** This rule exists because the framework already shipped a Slaf hit analysis that mis-attributed the Hagel fight to Game 3 when it was Game 2 — exactly the kind of error a context file prevents.

**Schema** (see `tools/build_game_context.py` for the data-derivable subset):

- `schema_version`, `game_id`, `date`, `season`, `game_type`
- `series`, `series_game` — index in the series (1, 2, 3, 4, ...)
- `home_team`, `away_team`, `matchup`, `final_score`, `result`
- `regulation_or_overtime` (`REG` / `OT` / `SO`)
- `goalies` — name per team
- `goalscorers` — `{team: {name: count}}`
- `goal_sequence` — list of goals in chronological order with period, time, scorer, assists, situation
- `key_events[]` — fights, marquee hits, ejections, injuries. Each has a `kind`, `period`, `time_in_period`, `significance` (manual narrative). Cross-game framework anchors should be flagged with `FRAMEWORK ANCHOR:` in the significance line.
- `series_state_after_game` — e.g. `MTL leads 2-1`, `tied 2-2`
- `file_pointers` — URLs + relative paths to PBP, boxscore, shifts, analyzer output, lineups yaml
- `related_briefs[]` — list of report files that consumed this game's data
- `notes` — free-form narrative the data alone can't capture

**Generation:** `tools/build_game_context.py` populates the data-derivable fields from NHL.com PBP + boxscore. Manual fields (`significance`, `series_state_after_game`, `notes`) are filled in by hand.

**Cross-game fact-check rule:** when extending the renderer's prose fact-check guard (see §5), **add a check that verifies any "Game N" claim resolves to a real `gameN_context.yaml` with matching attributes** (e.g., if prose says "Game 2 Hagel fight at P2 5:14", the guard should look it up in `game2_context.yaml` and confirm there's a `key_events[]` entry with `kind: fight` and `time_in_period: "05:14"`). This is the mechanical safeguard. The instinctive safeguard is: **read the context file first.**

---

## 5. The prose fact-check guard

Lives in every report's renderer (e.g., `build_game3_post.js`, `build_playoff_rankings_post.js`). Before any docx is written, the guard:

1. Walks every prose string in the language objects (EN + FR), including templated functions (e.g., `lineReshuffleBullet`, `lineupIntroProse`).
2. For every roster name with **0 goals** in `D.series_goalscorers` or `D.individual`, scans the corpus for two patterns:
   - **Direct**: `<Name> [optional modal] scored | tied it | opened the scoring | a marqué | etc.`
   - **Coordinated subject**: `<Name> ... (have|had|ont) (all|both|tous) (scored|marqué)`
3. Negative lookbehind for `-` so trio labels like `Texier-Dach-Bolduc scored` don't misattribute the goal to Bolduc individually.
4. **Aborts the build with exit code 7** if any violation is found, listing each name + the offending sentence + a pointer to the truth source.

When extending the framework, **add new structural invariants here as needed** — e.g., if you start writing claims about ice time, the guard should validate those against `D` too. The principle: **prose contradicting the data cannot produce a docx.**

---

## 6. Skills installed in this repo

All in `.claude/skills/`. Each has its own `SKILL.md` describing scope, workflow, and rails. Read them when invoked.

| Skill | Purpose |
|---|---|
| `research-game` | Pull press coverage from a curated EN+FR whitelist; output structured `claims.yaml` + `lineups` + `usage_observations`. **Always required before drafting a game post.** Schema includes the load-bearing line-reshuffle fields downstream skills read into prose. |
| `translate-to-quebec-fr` | Translate hockey-analytics writing into idiomatic Québec hockey-press French. Term map (50+ entries), sentence patterns, worked example. **Always invoked before finalizing FR copy** — never as a "tweak" pass after literal translation. |
| `draft-game-post` | Full post-game analysis with claims ledger, swap callouts, glossary links. Reads `<gameN>_lineups.yaml` as input (mandatory). Enforces all writing rails (§2). |
| `propose-swap-scenario` | Head-to-head lineup swap evaluation with 80% CI bands. Pooled-baseline default. |
| `validate-analysis` | Rigor editor — flags overclaims, missing CIs, predictions, cliches, position errors, restated-what-was-known violations, fabricated scoring claims. Used by the auto-PR-review workflow. |
| `review-pr-lemieux` | Opinionated PR review with structured verdict (MERGE / REQUEST CHANGES / CLOSE). Auto-invoked on every PR via `.github/workflows/claude-pr-review.yml`. |
| `player-snapshot` | Render the full 5-layer data-model dump for one player (auto-detects skater vs goalie). Wraps `tools/player_snapshot.py`. Triggers on "tell me about <player>", "what do we know about", "everything we have on". |

---

## 7. Common workflows

### Drafting a game post

```
1. research-game             →  produces research/<gameId>_claims.yaml +
                                lineups + usage_observations
2. analyzer (Python)         →  reads SQLite + NHL.com PBP, produces
                                <gameN>_analysis.numbers.json
3. renderer (Node + docx)    →  reads JSON + lineups.yaml, runs prose
                                fact-check guard, writes branded
                                <gameN>_post_<date>_{EN,FR}.docx
4. tools/push_to_drive.py    →  uploads with --public --folder-public,
                                native docx MIME, refreshable token cached
                                in ~/.lemieux/google-token.json
```

`examples/habs_round1_2026/` is the canonical worked example end-to-end. Look there for templates.

### Producing a rankings report

Same shape as a game post but with `rank_*` tables instead of game-specific narrative. See `examples/habs_round1_2026/playoff_rankings.py` and `build_playoff_rankings_post.js`.

### Adding a new connector

```
1. cp -r templates/connector-template
        packages/lemieux-connectors/src/lemieux/connectors/<name>
2. implement refresh() → returns DataFrame matching declared schema
3. write 3 tests (schema, refresh happy, refresh error)
4. record fixtures via VCR or saved HTML
5. update REGISTRY.yaml + SOURCES.md
6. open PR — auto-review skill grades it
```

### Adding a new skill

```
1. cp -r templates/skill-template .claude/skills/<name>
2. write EN + FR instructions in same SKILL.md
3. reference glossary terms by ID, not inline definitions
4. self-check before delivery section
```

### Adding a glossary term

Edit `packages/lemieux-glossary/src/lemieux/glossary/terms.yaml`. Both languages required, plus at least one caveat. Tests enforce both.

---

## 8. Key paths

```
CLAUDE.md                                    ← this file (rules of the road)
README.md / README_FR.md                     ← public landing pages
ROADMAP.md                                   ← shipped + planned
SOURCES.md                                   ← per-source license posture

.claude/skills/                              ← Claude Code skills (auto-discovered)
.github/workflows/claude-pr-review.yml       ← auto-PR-review pipeline
.github/workflows/tests.yml                  ← pytest + ruff CI
.github/workflows/connector-health.yml       ← nightly upstream-API drift detection

packages/lemieux-core/                       ← swap engine, comparable engine, scouting
  src/lemieux/core/swap_engine.py            ← isolated impact, swap projections, CIs
  src/lemieux/core/comparable.py             ← Comparable, ComparableIndex, build_cohort_stabilized_impact
  src/lemieux/core/embedding.py              ← standardize, PCA, Mahalanobis kNN
  src/lemieux/core/scouting.py               ← PlayerScoutingProfile, ContinuousAttribute, TagAssertion
  src/lemieux/core/tags.py                   ← find_players_by_tag, list_known_tags
  src/lemieux/core/cohort_effects.py         ← tag_split_study (any tag), tag_introduction_study (scaffold)
packages/lemieux-connectors/                 ← NHL API, NST, NHL Edge, plugin base
  src/lemieux/connectors/nhl_edge/           ← biometric features (skating speed, shot speed)
packages/lemieux-mcp/                        ← FastMCP server (5 tools, 4 resources)
packages/lemieux-glossary/                   ← bilingual metric definitions (15+)
packages/lemieux-app/                        ← (Streamlit companion, pending migration)

tools/                                       ← stand-alone scripts (not packaged)
  push_to_drive.py                           ← Drive uploader (BYO Google OAuth)
  player_snapshot.py                         ← 5-layer player data-model dump (any name)
  build_comparable_index.py                  ← (re)fit skater kNN index from store.sqlite
  build_goalie_comparable_index.py           ← (re)fit goalie kNN index (v1)
  build_scouting_corpus.py                   ← LLM-extract skater scouting profiles via DDG + Sonnet
  build_goalie_scouting_corpus.py            ← same shape, goalie vocab
  refresh_scouting_empties.py                ← second-pass 3-query rich search for empty profiles
  refresh_skater_individual_stats.py         ← NST stdoi=std → skater_individual_stats
  refresh_goalie_stats.py                    ← NST pos=G → goalie_stats with raw counting cols
  refresh_edge_biometrics.py                 ← NHL Edge skating + shot + bio backfill
  build_game_context.py                      ← per-game context yaml (PBP-derived fields)
  qc_scouting_corpus.py / score_calibration.py / backtest_comparable_aging.py
                                             ← QC + calibration + held-out backtest tooling
  export_derived_artifacts.py                ← export the publishable subset (no raw NST tables)

examples/habs_round1_2026/                   ← worked example end-to-end
  game3_analysis.py                          ← analyzer
  build_game3_post.js                        ← renderer with prose fact-check guard
  game3_lineups.yaml                         ← canonical lineup fact base
  game3_usage_observations.yaml              ← interview-derived deployment layer
  game3_analysis.numbers.json                ← analyzer output (audit trail)
  game3_post_2026-04-25_{EN,FR}.docx         ← rendered reports
  playoff_rankings.py                        ← rankings analyzer (canonical goalie SV% method)
  build_playoff_rankings_post.js             ← rankings renderer
  playoff_rankings.numbers.json              ← rankings audit trail
  playoff_rankings_2026-04-26_{EN,FR}.docx   ← rendered reports

legacy/                                      ← original prototype (claudehockey)
  data/store.sqlite                          ← cached NST team + skater stats
  data/cache.sqlite                          ← HTTP cache (NST + NHL.com)
  analytics/habs_round1.py                   ← original orchestrator (predates packages/)

reports/output/                              ← legacy report output
.lemieux/                                    ← Drive credentials + token (gitignored)
research/, reearch/                          ← input research notes (gitignored)
```

---

## 9. What NOT to do

- **Don't reference a previously analyzed game from prose memory.** If you write "the Hagel fight in Game 3" or "MTL won Game 1 in OT", load the relevant `<gameN>_context.yaml` first and confirm the claim against it. The framework already shipped one report with the Hagel fight mis-attributed to Game 3 (it was Game 2). The fix is upstream — context-file lookup, not downstream verification.
- **Don't leak framework-internal feedback or corrections into published prose.** If a prior version of the report had a fact wrong, the rewrite must read like the wrong version never existed. Phrases like "this is not the second straight game", "(corrected)", "the framework anchors are X and Y", "earlier we said Z, but actually Y" all leak the editorial process to the reader, who has no idea what was wrong before and shouldn't. Just write the story correctly. The fact-check guards exist precisely so the reader never needs to know what was caught — they only ever see the right version.
- **Don't reference framework-internal vocabulary in reader-facing prose.** Words like "framework anchor", "bucket-cut", "structural invariant", "non-trivial observation" are pipeline-internal. The reader sees "the hit", "before/after the hit", "the moment that flipped the period". Translate framework jargon to reader-language before it ships.
- **Don't write prose about line roles without loading `<gameN>_lineups.yaml` first.** It will be wrong eventually; the structural fix is upstream loading, not downstream verification.
- **Don't claim a player scored without checking `D.series_goalscorers`.** The prose fact-check guard will abort the build, but you're expected to not produce the violation in the first place.
- **Don't restate pre-series narrative ("Tampa drives possession") as if it's a finding.** The reader knew that yesterday. Either reframe with the analysis-derived value-add or cut.
- **Don't write meta-commentary** ("This section explains...", "We'll come back to...", "What's interesting is..."). The reader doesn't need a tour guide.
- **Don't translate FR literally from EN strings.** Run through `translate-to-quebec-fr` skill — Québec sportswriting register, not formal European French, not literal calques.
- **Don't add a feature, refactor, or abstraction beyond what the task requires.** The framework is small on purpose. Three similar lines is better than a premature abstraction.
- **Don't bypass the prose fact-check guard.** Adding `--no-verify`-style escape hatches is a CLOSE-tier violation. The whole point of the invariant is that it can't be opted out of.

---

## 10. Known gaps / things to watch

- **Goalie SV% data discrepancy** between `game3_analysis.py:game_level_team_stats` (per-game home/away counter) and `playoff_rankings.py:goalie_summary` (PBP-direct count). The PBP-direct method is canonical; the per_game method has a known goal-count bug. The Game 3 docx originally cited Dobes 74/7/.905; the corrected number is 74/8/.892. Future game posts should use the PBP-direct method (refactor `game3_analysis.py` accordingly when convenient).
- **Streamlit companion (`packages/lemieux-app`) is a placeholder.** The `legacy/ui/` Streamlit code still runs and is the working UI; migration is roadmapped for v0.2.
- **Goalie GSAx is not yet ingested.** Optimal-lineup section in old reports lists goalie placeholder. To be wired when needed.
- **Per-period player-level data** (the Slafkovský fight bucket analysis) comes from NHL.com shift charts + PBP correlation, not NST (NST game reports don't expose per-period player splits). This works but adds a dependency on NHL.com endpoints holding their schema.
- **Drive uploader** depends on a user-side Google OAuth credentials JSON. Setup is documented in `tools/README.md`. The MCP-based path (Claude.ai's Google Drive integration) was tried and ran into scope-locked-to-readonly limitations as of the time of writing.

---

## 11. When in doubt

- Read the relevant skill's `SKILL.md` first.
- For data flow questions, trace through `examples/habs_round1_2026/`.
- For writing-rule questions, look up the worked-example tables in `draft-game-post/SKILL.md` and `validate-analysis/SKILL.md`.
- If you're about to make a change that violates one of the rails in §2, **stop and ask the user**. They have a track record of catching errors that would have shipped, and the rails exist precisely because of those catches.

The framework is built on the principle that **the data is the source, the prose is templated against it, and the build invariant guarantees no contradiction.** Everything else flows from that.
