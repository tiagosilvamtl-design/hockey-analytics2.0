# Lemieux — AI Hockey Analytics Framework

[![tests](https://github.com/lemieuxAI/framework/actions/workflows/tests.yml/badge.svg)](https://github.com/lemieuxAI/framework/actions/workflows/tests.yml)
[![license](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](./pyproject.toml)
[![mcp](https://img.shields.io/badge/MCP-server-8A2BE2)](./packages/lemieux-mcp)
[![docs](https://img.shields.io/badge/docs-EN%20%7C%20FR-green)](./docs)

🇬🇧 **English** · [🇫🇷 Français](./README_FR.md)

> *Draft the analytics post you wish you'd read.*

**Lemieux** is an open-source framework that lets you combine Claude (or any MCP-compatible AI client) with curated hockey data connectors, analytics primitives, and workflow skills to generate analytically rigorous, caveat-aware hockey coverage — the kind most outlets don't produce.

The primary workflow isn't a standalone app — it's a repo you clone and a Claude session you open in it:

```
clone repo  →  open Claude Code  →  ask about last night's game
           →  Claude uses MCP tools + skills + connectors
           →  draft with tables, 80% CIs, sources, glossary links
```

## Why this exists

Most hockey coverage in 2026 remains innumerate: deep conclusions from single-game eye tests, narratives recycled from the 1990s, zero engagement with twenty years of public advanced stats. Lemieux is a **scratch-your-own-itch tool** first, a community framework second. It's what one of us wanted yesterday; it's open-sourced because others almost certainly want the same.

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code / Claude Desktop / any MCP client                  │
│        ▲                                   ▲                    │
│        │ skills (workflows)                │ MCP tools           │
│        │                                   │ + resources         │
└────────┼───────────────────────────────────┼────────────────────┘
         │                                   │
    .claude/skills/                   packages/lemieux-mcp
    ├── draft-game-post                      │
    ├── propose-swap-scenario                ▼
    └── validate-analysis           ┌──────────────────┐
                                    │  lemieux-core    │  swap engine, CIs,
                                    │                  │  pooled baselines
                                    └─────────┬────────┘
                                              │
                                    ┌─────────▼────────┐
                                    │ lemieux-glossary │  bilingual metric defs
                                    │                  │  (EN + FR)
                                    └──────────────────┘
                                              │
                                    ┌─────────▼────────────┐
                                    │  lemieux-connectors  │  plugin-style data sources
                                    │                      │  (NHL API, NST, ...)
                                    └──────────────────────┘
```

## What's in the box

| Package / dir | Purpose |
|---|---|
| [`lemieux-core`](./packages/lemieux-core) | Analytics primitives: **swap engine** (pooled baselines + 80% CIs), **comparable engine** (kNN over PCA-whitened standardized features), **scouting** + **tags** + **cohort_effects** (tag-split studies) |
| [`lemieux-connectors`](./packages/lemieux-connectors) | Plugin-style data source adapters: NHL.com public API, Natural Stat Trick, NHL Edge (biometrics) |
| [`lemieux-mcp`](./packages/lemieux-mcp) | FastMCP server exposing analytics tools + resources to any MCP client |
| [`lemieux-glossary`](./packages/lemieux-glossary) | Bilingual (EN/FR) definitions of every metric we use, with formulas and caveats |
| [`.claude/skills/`](./.claude/skills) | Opinionated Claude workflows — `research-game`, `translate-to-quebec-fr`, `draft-game-post`, `propose-swap-scenario`, `validate-analysis`, `review-pr-lemieux`, `player-snapshot` |
| [`tools/`](./tools) | Stand-alone scripts: scouting-corpus builder, kNN index builder, biometrics refresher, player snapshot, Drive uploader, derived-artifacts exporter |
| [`examples/habs_round1_2026/`](./examples/habs_round1_2026) | Multiple worked end-to-end reports: pre-game brief, Game 3 / Game 4 post-game analyses, playoff rankings, **Game 5 contingency brief**, fight-bucket per-period analysis |
| [`docs/en/data-model.md`](./docs/en/data-model.md) | Canonical guide to the 5-layer data model (counting → bio → kNN → scouting → game context) |
| [`CLAUDE.md`](./CLAUDE.md) | Canonical operating guide for working in this repo with Claude Code — writing rails, data flow invariants, structural conventions |

## Data coverage (as of 2026-04-28)

Lemieux's database knows the following about every NHL player:

| Layer | Coverage |
|---|---|
| **NST counting stats** (skater + goalie) | 5 seasons × {5v5, 5v4, all} × {reg, playoff}, ~18,500 individual-stat rows |
| **Player bio** (height/weight/draft) | **1322** players, 100% on height + weight |
| **NHL Edge biometrics** (skating, shot, bursts) | **1122** distinct skaters with measured data |
| **GenAI scouting tags + attributes** | **1023 skaters + 135 goalies** with extracted content (1393 total profiles) |
| **kNN comparable indexes** | **1257 skaters** (24-feature embedding) + **136 goalies** (10-feature v1) |
| **Per-game context yamls** | Habs Round 1 2026 series (Games 1-4 indexed) |

Run `python tools/player_snapshot.py "<name>"` (or use the `player-snapshot`
Claude skill) to dump all five layers for any player in one shot.

## Quickstart

> **Non-technical?** See [INSTALLATION_FACILE.md](./INSTALLATION_FACILE.md) (FR) — a friend-of-the-project install guide that walks you through Claude Code + Lemieux setup with zero prior tooling assumed.

```bash
git clone https://github.com/lemieuxAI/framework.git lemieux
cd lemieux

python -m venv .venv
source .venv/bin/activate     # Windows Git Bash: . .venv/Scripts/activate

pip install -e packages/lemieux-core
pip install -e packages/lemieux-glossary
pip install -e packages/lemieux-connectors
pip install -e packages/lemieux-mcp

cp .env.example .env          # add your NST access key (see SOURCES.md for how)
```

### Use from Claude Code

Open the repo in Claude Code. The `.claude/skills/` directory is auto-discovered. Ask:

> *"Draft a 1000-word post about last night's Habs game. Focus on 5v5 defensive structure. Include one swap-scenario callout. In French please."*

Claude invokes `draft-game-post`, calls the MCP tools, reads the glossary for term definitions, runs `validate-analysis` as a rigor check, and produces a Markdown draft.

### Use from Claude Desktop

Add to your `mcp.json`:

```json
{
  "mcpServers": {
    "lemieux": {
      "command": "lemieux-mcp",
      "args": ["--store", "/path/to/.lemieux/store.sqlite"],
      "env": { "NST_ACCESS_KEY": "your-key-here" }
    }
  }
}
```

## Data sources

See [SOURCES.md](./SOURCES.md) for the full list with license terms. Connectors shipping in v0.1:

- **NHL.com public API** — play-by-play, shifts, rosters, standings, NHL Edge biometrics (no key required)
- **Natural Stat Trick** — on-ice + individual + goalie advanced stats (user-level access key required, free)
- **DDG + Sonnet 4.5 extraction** — public scouting text → structured tags + attributes with verbatim source-quote provenance
- **MoneyPuck, PWHL, EliteProspects** — planned for v0.2 (see [ROADMAP.md](./ROADMAP.md))

### Can the database itself be redistributed?

**No.** `legacy/data/store.sqlite` contains raw Natural Stat Trick tables, and
SOURCES.md is unambiguous: *"Do NOT redistribute raw tables."* You bring your
own NST access key (free, requested via an NST profile), and the refresh
scripts in `tools/` rebuild the DB locally.

**But the derived artifacts can be:**

- Comparable indexes (`comparable_index.json`, `goalie_comparable_index.json`) — these are PCA-whitened embeddings + fitted parameters of our model, not raw stats.
- Scouting tables (`scouting_*`) — LLM-extracted from public web text via our own prompts; we own the extraction work.

Run `python tools/export_derived_artifacts.py` to produce a redistributable
zip with these alongside a README pointer.

## Design principles

1. **Intellectual honesty over confidence.** Every output shows sample sizes and CIs. We'd rather be boring than wrong.
2. **Directional, not predictive.** No series predictions, no "who will win", no player-rating scalars.
3. **Glossary-linked.** Every metric in any output links to a definition.
4. **Bilingual from day one.** Docs, glossary, skills all ship EN + FR. Francophone hockey analytics is essentially unoccupied territory; Lemieux changes that.
5. **Plugin-friendly.** Adding a new connector or skill is 3 files + tests. See [`templates/`](./templates).
6. **Respectful of upstream.** Cache aggressively, rate-limit politely, document every source's terms, never redistribute data we didn't generate.
7. **Data is the source; prose is templated against it.** Structured input files (`<gameN>_lineups.yaml`, `<task>.numbers.json`) are the canonical fact base. The build invariant guarantees no prose can contradict the data — `runProseFactCheck()` aborts the docx build (exit code 7) if any roster name with 0 goals appears as a scoring subject in prose. Same pattern applies to lineup composition, ice time, assists, etc. Lineup composition data is INPUT to the analysis, never inferred from press extracts.
8. **Lead with outcomes, not announcements.** The audience watched the game — the post-game report's job is to surface what only the data reveals (unexpected magnitudes, paradoxes the eye test misses, contradictions with pre-series narrative). The auto-PR-review pipeline catches violations.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) (bilingual). The easiest first PR is a connector — copy `templates/connector-template`, implement `refresh()`, write three tests. There's an issue template for each contribution type.

**Auto-review on every PR.** When you open a PR, a GitHub Action runs Claude Code with the [`review-pr-lemieux`](./.claude/skills/review-pr-lemieux) skill and posts a structured review comment within minutes — verdict (MERGE / REQUEST CHANGES / CLOSE), what the PR does, what's good, what worries me, a project-rules checklist, and a recommended next step. The maintainer reads the review and accepts or rejects; Claude never auto-merges or auto-closes. See [CONTRIBUTING.md](./CONTRIBUTING.md#auto-review) for what triggers each verdict.

## Roadmap

See [ROADMAP.md](./ROADMAP.md). v0.2 focus: MoneyPuck connector, PWHL connector (a genuine under-served community), PyPI publishing, Streamlit companion migration.

## License

- **Code**: MIT. See [LICENSE](./LICENSE).
- **Docs**: CC BY 4.0.
- **Data**: varies by source. See [SOURCES.md](./SOURCES.md) for per-source license notes. We do not relicense data we don't own.

## Acknowledgements

Assembled on top of the analytics community that made this thinkable: [Natural Stat Trick](https://www.naturalstattrick.com/), [MoneyPuck](https://moneypuck.com/), NHL.com public APIs, [Evolving-Hockey](https://evolving-hockey.com/), [HockeyViz](https://hockeyviz.com/), [All Three Zones](https://www.allthreezones.com/) (Corey Sznajder), and the long list of hockey-stats bloggers, R package maintainers, and Substack writers linked throughout the glossary and docs.

## The name

*Lemieux* is an homage to **Claude Lemieux** — the Québécois winger who made a Stanley Cup–decorated career out of long, ugly playoff series — and therefore an implicit wink at a certain favourite coding assistant and the models that power it. We don't dwell on it.
