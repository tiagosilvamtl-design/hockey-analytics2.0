# Lemieux roadmap

## v0.1 — MVP (shipped)

- [x] `lemieux-core` — swap engine, isolated impact, pooled baselines, 80% CIs
- [x] `lemieux-connectors` — plugin base class + NHL.com public API + Natural Stat Trick
- [x] `lemieux-glossary` — 15 bilingual terms (EN + FR) with formulas, caveats, sources
- [x] `lemieux-mcp` — FastMCP server with 5 tools + 4 resources
- [x] 6 Claude skills — `research-game`, `translate-to-quebec-fr`, `draft-game-post`, `propose-swap-scenario`, `validate-analysis`, `review-pr-lemieux`
- [x] Bilingual READMEs + `docs/en` + `docs/fr` + `INSTALLATION_FACILE.md` (FR non-technical install)
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
- [ ] Additional skills: `draft-trend-brief`, `draft-player-profile`, `compare-teams`
- [ ] Glossary expansion (target: 40+ terms)

## Explicit non-goals

- Real-time / live-game streaming (post-game analysis is the sweet spot)
- Prediction markets or betting tooling
- Replacing Natural Stat Trick, Evolving-Hockey, or HockeyViz (we aggregate their outputs)
- NHL EDGE endpoint reverse-engineering beyond what's stable
- Video / computer-vision analysis

## How to propose additions

Open an issue using the `new-connector` or `new-skill` template. Or jump straight to a PR via `templates/connector-template` or `templates/skill-template`.
