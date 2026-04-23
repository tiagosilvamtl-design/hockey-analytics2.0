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

| Package | Purpose |
|---|---|
| [`lemieux-core`](./packages/lemieux-core) | Analytics primitives: swap engine, isolated impact, pooled baselines, variance-aware projections |
| [`lemieux-connectors`](./packages/lemieux-connectors) | Plugin-style data source adapters (NHL.com public API, Natural Stat Trick, more coming) |
| [`lemieux-mcp`](./packages/lemieux-mcp) | FastMCP server exposing analytics tools + resources to any MCP client |
| [`lemieux-glossary`](./packages/lemieux-glossary) | Bilingual (EN/FR) definitions of every metric we use, with formulas and caveats |
| [`.claude/skills/`](./.claude/skills) | Opinionated Claude workflows — `draft-game-post`, `propose-swap-scenario`, `validate-analysis` |
| [`examples/`](./examples) | Worked end-to-end analyses. Start with `examples/habs_round1_2026/` |

## Quickstart

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

- **NHL.com public API** — play-by-play, shifts, rosters, standings (no key required)
- **Natural Stat Trick** — advanced stats (user-level access key required, free)
- **MoneyPuck, PWHL** — planned for v0.2 (see [ROADMAP.md](./ROADMAP.md))

## Design principles

1. **Intellectual honesty over confidence.** Every output shows sample sizes and CIs. We'd rather be boring than wrong.
2. **Directional, not predictive.** No series predictions, no "who will win", no player-rating scalars.
3. **Glossary-linked.** Every metric in any output links to a definition.
4. **Bilingual from day one.** Docs, glossary, skills all ship EN + FR. Francophone hockey analytics is essentially unoccupied territory; Lemieux changes that.
5. **Plugin-friendly.** Adding a new connector or skill is 3 files + tests. See [`templates/`](./templates).
6. **Respectful of upstream.** Cache aggressively, rate-limit politely, document every source's terms, never redistribute data we didn't generate.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) (bilingual). The easiest first PR is a connector — copy `templates/connector-template`, implement `refresh()`, write three tests. There's an issue template for each contribution type.

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
