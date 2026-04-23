# Lemieux roadmap

## v0.1 — MVP (current)

- [x] `lemieux-core` — swap engine, isolated impact, pooled baselines, 80% CIs
- [x] `lemieux-connectors` — plugin base class + NHL.com public API + Natural Stat Trick
- [x] `lemieux-glossary` — 15 bilingual terms (EN + FR) with formulas, caveats, sources
- [x] `lemieux-mcp` — FastMCP server with 5 tools + 4 resources
- [x] 3 Claude skills — `draft-game-post`, `propose-swap-scenario`, `validate-analysis`
- [x] Bilingual READMEs + `docs/en` + `docs/fr`
- [x] Templates for connectors and skills
- [x] One worked end-to-end example (`examples/habs_round1_2026/`)
- [x] CI — pytest + ruff + nightly connector-health

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
