# Lemieux roadmap

## v0.1 — MVP (shipped)

- [x] `lemieux-core` — swap engine, isolated impact, pooled baselines, 80% CIs
- [x] `lemieux-connectors` — plugin base class + NHL.com public API + Natural Stat Trick
- [x] `lemieux-glossary` — 15 bilingual terms (EN + FR) with formulas, caveats, sources
- [x] `lemieux-mcp` — FastMCP server with 5 tools + 4 resources
- [x] 6 Claude skills — `research-game`, `translate-to-quebec-fr`, `draft-game-post`, `propose-swap-scenario`, `validate-analysis`, `review-pr-lemieux`
- [x] Bilingual READMEs + `docs/en` + `docs/fr`
- [x] Templates for connectors and skills
- [x] Three worked end-to-end examples in `examples/habs_round1_2026/`:
  - Round 1 standalone report (Habs vs TBL pre-G3)
  - Per-game analysis (G3 post with usage observations + line-reshuffle analysis)
  - Playoff rankings report (snapshot-style, all-MTL skaters by advanced analytics)
- [x] CI — pytest + ruff + nightly connector-health
- [x] **Auto-PR-review** via Claude Code GitHub Action (`.github/workflows/claude-pr-review.yml`)
- [x] **Build-time prose fact-check guard** — `runProseFactCheck()` aborts the docx build with exit code 7 if any roster name with 0 goals appears as a scoring subject in prose. Source of truth: `D.series_goalscorers` (PBP-derived). The "claimed X scored when X is scoreless" bug class is no longer possible to ship.
- [x] **Structural data invariants** — `<gameN>_lineups.yaml` is required input for any line-composition prose; `series_goalscorers` is required input for any scoring claim. Renderers refuse to build if these inputs are missing.
- [x] **Drive uploader** — `tools/push_to_drive.py` portable Google Drive push (BYO OAuth, 5-min one-time setup, refreshable token, `--public --folder-public` for shareable links).
- [x] **Writing rails baked into the skills**: lead with outcomes (not announcements), no meta-commentary about report structure, no restating pre-data narrative, lineup data is input not output, goalscorer claims must source from PBP.
- [x] **`CLAUDE.md`** — canonical operating guide for working in this repo as Claude Code.
- [x] **Comparable engine — Phase 1 (quantitative skater kNN)**: 1257 skaters indexed on 24 features (NST iso 5v5/5v4 + counting rates + position + biometrics + bio). PCA + Mahalanobis-equivalent kNN. CARMELO-style 0-100 score + per-feature drivers. Builder: `tools/build_comparable_index.py`. API: `lemieux.core.comparable.ComparableIndex.find_comparables()`.
- [x] **Comparable engine — v1 goalie kNN**: 136 goalies indexed on 10 features (perf + bio). Separate index file. Phase 1 plan reserved this for v4; user-pulled forward to v1. Stylistic features (positional vs scrambly, glove-side vs blocker-side) deferred to a future PBP-tracking phase. Builder: `tools/build_goalie_comparable_index.py`.
- [x] **Scouting corpus — Phase 2**: 1023 skaters + 135 goalies with LLM-extracted (Sonnet 4.5) attributes + tags + comparable mentions. Verbatim source quotes + URLs persisted; tag without quote can't ship in prose. 23 skater archetype tags, 18 goalie tags. Builders: `tools/build_scouting_corpus.py`, `tools/build_goalie_scouting_corpus.py`. Second-pass empties refresh: `tools/refresh_scouting_empties.py` (3-query rich search, ~38% recovery on first-pass empties).
- [x] **NST individual stats path** — fixed legacy `stdoi=bio` bug; new `skater_individual_stats` table with G/A/SOG/ixG/iCF/iHDCF/PIM/hits/blocks/faceoffs across 5 seasons × 3 sits × 2 stypes. Builder: `tools/refresh_skater_individual_stats.py`.
- [x] **NHL Edge biometric backfill**: 1322 player bios (height/weight/draft 100%), 1122 skaters with measured skating + shot speed data. ASCII-fold name resolver (handles Dobeš, Slafkovský, etc.) — see `_ascii_fold()` in `lemieux-connectors/nhl_edge/client.py`.
- [x] **`player-snapshot` skill + tool** — auto-detect skater vs goalie, render the full 5-layer data model dump in one shot. `tools/player_snapshot.py "<name>"`.
- [x] **`docs/en/data-model.md`** — canonical 5-layer schema documentation, replacing scattered ad-hoc info.

## v0.2 — Community-facing release

- [ ] PyPI publishing for all 5 packages (Trusted Publishers via GitHub Actions)
- [ ] Register `lemieux-mcp` in Anthropic's MCP catalog once stable
- [ ] `lemieux-connectors/moneypuck` — CSV downloader, independent xG model for cross-validation
- [ ] `lemieux-connectors/pwhl` — women's league (zero public analytics tooling currently)
- [ ] Migrate `legacy/ui/` Streamlit app into `packages/lemieux-app`
- [ ] Second French skill translation pass
- [ ] GitHub Pages docs site (Docusaurus i18n)

## v0.3 — Depth

- [ ] `lemieux-connectors/all_three_zones` — opt-in, user-supplied Patreon data
- [ ] `lemieux-connectors/hockey_reference` — historical & roster data
- [ ] `lemieux-connectors/big_data_cup` — Stathletes annual public datasets
- [ ] `lemieux-connectors/eliteprospects` — cross-league career stats for prospect comps (KHL/AHL/SHL/Liiga/CHL/USHL/NCAA)
- [ ] **Comparable engine — Phase 3 (tag-cohort split studies)**: scaffold exists in `lemieux.core.cohort_effects.tag_split_study(tag)`. Wiring `with_archetype_lift(tag)` decorator on the swap engine + integrating into the propose-swap-scenario renderer is the next visible-to-user capability.
- [ ] **NHLe translation factors** with CIs (`lemieux.core.nhle`) — needed before prospect kNN can ship.
- [ ] Additional skills: `draft-trend-brief`, `draft-player-profile`, `compare-teams`
- [ ] Glossary expansion (target: 40+ terms)

## Future data sources

Sources we'd like to integrate eventually but haven't yet. Each has a different access posture; the notes below are what we know going in. (Sources we *do* connect to today are documented in [SOURCES.md](./SOURCES.md).)

| Source | What it adds | Access | Status |
|---|---|---|---|
| **MoneyPuck** ([moneypuck.com/data.htm](https://moneypuck.com/data.htm)) | CSV dumps with an independent xG model — useful for cross-validating NST. | Free; nightly updates. Document source, don't republish raw. | v0.2 |
| **PWHL** ([thepwhl.com/en/stats](https://www.thepwhl.com/en/stats), pwhl.hockey-statistics.com) | Women's league team + player stats. Almost no public analytics tooling covers PWHL — a deliberate differentiator. | Free, public. Cite source. | v0.2 |
| **EliteProspects** ([eliteprospects.com](https://www.eliteprospects.com/)) | Cross-league career stats (KHL / AHL / SHL / Liiga / CHL / USHL / NCAA). Prerequisite for prospect comps via NHLe translation. | Free scraping with polite rate; respect their bot policy. | v0.3 |
| **Hockey-Reference** ([hockey-reference.com](https://www.hockey-reference.com/)) | Historical stats, rosters, season summaries, records. | Free scraping; bot policy at [sports-reference.com/bot-traffic.html](https://www.sports-reference.com/bot-traffic.html) enforces 20 req/min. Sports-Reference doesn't love redistribution — cite, link, cache locally. | v0.3 |
| **All Three Zones** (Corey Sznajder, Patreon) | Hand-tracked microstats — zone entries/exits, scoring chances, passing. Unique depth, no equivalent public source. | Patreon subscription (~$5–20/month). Each user brings their own subscription. Connector reads files from a user-supplied local path; we never hit Patreon's API nor redistribute a single row. | v0.3 (opt-in) |
| **Big Data Cup** (Stathletes — [stathletes.com/big-data-cup](https://www.stathletes.com/big-data-cup/)) | Annual public research datasets with detailed event tracking. | Free downloads via [bigdatacup repos](https://github.com/bigdatacup). Flat-file loader, not a live connector. | v0.3 |
| **Sportlogiq, PuckPedia, CapFriendly** | Tracking, contracts, salary-cap data. | Paywalled / partnership-gated. Documented here so users know why they're absent. | Not currently planned |

We also reference but don't connect to:

- **Evolving-Hockey** ([evolving-hockey.com](https://evolving-hockey.com/)) — dashboard-only as of 2026; no CSV export, no public API. Their RAPM model is widely cited; the glossary references their methodology where relevant.
- **HockeyViz** ([hockeyviz.com](https://hockeyviz.com/)) — subscription visualizations; not integrable. Cited in docs when contextualizing our isolated-impact approach.

## Explicit non-goals

- Real-time / live-game streaming (post-game analysis is the sweet spot)
- Prediction markets or betting tooling
- Replacing Natural Stat Trick, Evolving-Hockey, or HockeyViz (we aggregate their outputs)
- NHL Edge endpoint reverse-engineering beyond what's stable
- Video / computer-vision analysis

## How to propose additions

Open an issue using the `new-connector` or `new-skill` template. Or jump straight to a PR via `templates/connector-template` or `templates/skill-template`.
