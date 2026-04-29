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

Hockey coverage in 2026 still leans heavily on eye-test narrative — not because beat writers and broadcasters lack talent, but because querying advanced data takes technical chops that rarely overlap with sports journalism. Statisticians who become reporters are rare; reporters with the time to learn pandas + an xG model on a deadline are rarer still. The result is twenty years of excellent public analytics work that mostly stays inside the analytics community.

Lemieux is a **scratch-your-own-itch tool** first, a community framework second. We built it for ourselves, and we're open-sourcing it in case it helps others — fans who want to do their own analysis, beat writers and broadcasters looking for a way to fold analytical notions into their coverage without rebuilding the data pipeline from scratch, hobbyist analysts who want a pre-wired starting point. The framework does the data plumbing and rigor checks so the writing can focus on what it's meant to do.

## What you can do with Lemieux

Concrete capabilities you can drive from a Claude Code session in this repo. Every capability traces to data — no prose memory, no fabricated quotes, no series predictions.

### Ask about a player

> *"Tell me everything about Cole Caufield."*

Triggers `player-snapshot`. Returns the full 5-layer data model in one shot: bio, on-ice career arc, NHL Edge biometrics, NST individual scoring, scouting profile (with verbatim source quotes), top-7 kNN comparable cohort + per-feature drivers, indexed game-context appearances, current-series PBP-direct stats. Auto-detects skater vs goalie.

### Draft a post-game report

> *"Draft a post-game report on tonight's Habs game. Include a swap callout for the third line."*

Triggers the `research-game` → analyzer → renderer pipeline. Produces a branded EN + FR docx with claims ledger, line-reshuffle drift analysis, swap projections with 80% CIs, glossary links, and a build-time prose fact-check guard (no scoring claim about a non-scorer can ship — exit code 7 if violated). Push to Drive with one command.

### Evaluate a lineup change

> *"If Slafkovský can't play Game 5, who's the best replacement and what does it cost in xG/game?"*

Uses the swap engine + comparable engine. Each candidate gets a pooled-baseline projection with 80% CI bands; multi-leg permutations propagate uncertainty; if a tag-cohort split study supports it, an archetype-adjusted layer is layered on. The Game 5 contingency brief in `examples/habs_round1_2026/` is a worked example.

### Find similar players

> *"Find me NHL skaters most similar to Brendan Gallagher."*

The skater kNN index returns top-N comps with **per-feature drivers** (which features earned the match). 1257 skaters indexed across 24 features (NST iso 5v5/5v4, biometrics, static bio). Goalies have a separate v1 index over 10 features (perf + bio).

### Run a tag-cohort study

> *"Do players tagged `warrior` over-perform their reg-season iso in the playoffs?"*

The scouting layer surfaces 23 archetype tags with verbatim source quotes + URLs. The cohort-effects module runs reg→playoff lift studies on any tag, with bootstrap CIs. Today's worked example (Gallagher's comps): warriors lift **+0.49 xG/60** more than non-warriors, 80% CI excludes zero on n=4 — suggestive, not load-bearing. Honest framing is built in.

### Check rigor on a draft before publishing

> *"Validate this analysis before I publish."*

Triggers `validate-analysis`. Flags overclaims, missing CIs, predictions disguised as analysis, position errors, restated-pre-data narrative, fabricated scoring claims. Auto-runs on every PR via the `claude-pr-review.yml` GitHub Actions workflow.

### Translate into Québec hockey-press FR

> *"Translate this game-post draft into French."*

Triggers `translate-to-quebec-fr`. Term-mapped (50+ entries), sentence patterns matching the La Presse / RDS chroniqueur register. No literal calques. Comma decimals, thin space before %, `5 c. 5` in prose, `5v5` only in technical contexts.

## The hybrid GenAI + kNN comparable engine

This is the part of Lemieux that doesn't have an obvious public equivalent.

**The problem with existing comparable engines.** Quantitative systems like CARMELO, RAPM-distance kNN, or shot-quality embeddings will give you a top-10 list of "similar players" by stats — but they have no concept of *why* the players are similar. They can tell you that Brendan Gallagher and Troy Terry are neighbors in feature space; they can't tell you both are described as "warriors" in the scouting press, or test whether that descriptor actually predicts something about playoff behavior. Pure scouting databases have the opposite problem: rich qualitative tags, no quantitative grounding, no way to ask "do players described this way actually overperform their reg-season iso in the playoffs?"

**What Lemieux does instead.** Three layers stacked, each independently auditable, with tag-cohort effect studies on top to test whether the qualitative layer carries signal:

```
                    LAYER 3 — Cohort effect study
                    ┌──────────────────────────────────────────┐
                    │  for each archetype tag, do players       │
                    │  carrying it lift their reg-season iso    │
                    │  in the playoffs vs comparable non-tagged │
                    │  players? Bootstrap 80% CI on the Δ.      │
                    │  e.g. warrior cohort: +0.49 xG/60         │
                    │       lift, n=4 vs n=12, CI excludes zero │
                    └─────────────────┬────────────────────────┘
                                      │ uses
                ┌─────────────────────▼─────────────────────────┐
                │  LAYER 2 — GenAI scouting tags                │
                │                                                │
                │  DDG search → Sonnet 4.5 → 23 archetype tags  │
                │  per skater (warrior, sniper, playmaker,      │
                │  shutdown, two_way, etc.) with VERBATIM       │
                │  source quote + source URL per tag            │
                │                                                │
                │  1023 skaters with extracted content          │
                │  (1719 attributes + 2501 tag rows)            │
                └─────────────────────┬─────────────────────────┘
                                      │ joined on player_id
                ┌─────────────────────▼─────────────────────────┐
                │  LAYER 1 — Quantitative kNN                   │
                │                                                │
                │  PCA on 24-feature standardized embedding     │
                │  Mahalanobis-equivalent Euclidean distance    │
                │  CARMELO-style 0-100 score                    │
                │                                                │
                │  features: NST iso 5v5/5v4 (xGF/60, xGA/60,   │
                │  net), counting rates, position one-hot,      │
                │  NHL Edge biometrics, static bio              │
                │                                                │
                │  1257 skaters indexed                         │
                └────────────────────────────────────────────────┘
```

**Why each layer matters.**

- **Layer 1 alone** lets you ask "find me NHL skaters most similar to player X." You get a ranked list with per-feature drivers (which features earned the match — e.g. *Lane Hutson's top comp Samuel Girard matched on max_shot_speed_mph: Δz +1.64, pp_share: Δz +1.43*). This part is the standard quant comparable engine.
- **Layer 2 alone** is a queryable scouting profile per player. It's structured (controlled vocab, confidence-scored), it's provenance-bound (every tag carries the verbatim source quote and URL — the framework rail is *no tag ships in prose without its quote*), and it's queryable as a cohort: `find_players_by_tag('warrior')` returns a recognizable set (Gallagher, Tom Wilson, Sam Bennett, Bertuzzi…) rather than noise. This part replaces hand-curated scouting databases.
- **Layer 3 — the cohort effect study — is the novel piece.** Take the kNN cohort for a target player, partition by an archetype tag, compute the playoff-vs-reg-season iso lift for each subset, bootstrap a CI on the difference. *That* is a falsifiable test of whether the qualitative tag predicts something the quant features don't already capture. If the CI excludes zero, the archetype layer earns the right to enter a swap projection. If it straddles zero, the framework says so honestly and the projection runs without it.

**Worked example shipping in this repo.** [Game 5 contingency brief](./examples/habs_round1_2026/) (Slafkovský out, who replaces him?). The swap engine projects each replacement candidate with a pooled-baseline CI band. Then for the lead candidate (Gallagher), the cohort-effect study asks: *of the 30 nearest comparables, do those carrying the `warrior` tag lift their playoff iso more than those that don't?* Result: warrior cohort (n=4) mean lift +0.69 xG/60, non-warrior cohort (n=12) mean lift +0.19, bootstrap Δ = +0.49 with 80% CI [+0.05, +0.93]. **The CI excludes zero — but n=4 is small and bootstrap on 4 datapoints recycles the same values.** The brief explicitly flags this as suggestive, not load-bearing, and shows the projection both with and without the archetype layer so the reader can disagree with the addend.

**What's open about this.** The model fits ship as redistributable artifacts. The skater kNN index (`comparable_index.json`), the goalie kNN index (`goalie_comparable_index.json`), and the four scouting tables are all bundled into a single zip via [`tools/export_derived_artifacts.py`](./tools/export_derived_artifacts.py). The raw NST counting stats stay out (per their terms) — bring your own NST key, run the refresh tools, and your local DB matches ours. Every tag in the scouting tables carries its verbatim source quote and source URL; downstream republishers must keep that provenance attached.

**What this is not.** It's not a replacement for stylistic tracking (positional vs scrambly goaltending, glove-side vs blocker-side; right-wall vs left-wall puck retrievals). Those features need PBP-derived microstats we don't yet ingest. It's not RAPM. It's not a single-number player rating. It's a hybrid quantitative + qualitative comparable engine with falsifiable tag-cohort tests on top — the kind of thing that, today, you could only build by stitching three different paid tools together and writing the integration yourself.

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

## Data coverage (as of 2026-04-29)

The figures below describe **our local instance** of Lemieux. After you clone, the database is empty — you'll populate it yourself with the refresh tools in `tools/` and a free Natural Stat Trick access key (request via an NST profile, see [SOURCES.md](./SOURCES.md)). What ships in the repo is the **code** to rebuild every layer; what doesn't ship is the raw NST data (per their terms — see "Can the database itself be redistributed?" below).

| Layer | Our coverage | How to populate it |
|---|---|---|
| **NST counting stats** (skater + goalie) | 5 seasons × {5v5, 5v4, all} × {reg, playoff}, ~18,500 individual-stat rows | NST key + `tools/refresh_skater_individual_stats.py`, `tools/refresh_goalie_stats.py` |
| **Player bio** (height/weight/draft) | **1322** players, 100% on height + weight | `tools/refresh_edge_biometrics.py --bio-only` (no key needed) |
| **NHL Edge biometrics** (skating, shot, bursts) | **1122** distinct skaters with measured data | `tools/refresh_edge_biometrics.py --all-skaters` (no key) |
| **GenAI scouting tags + attributes** | **1023 skaters + 135 goalies** with extracted content (1393 total profiles) | `ANTHROPIC_API_KEY` + `tools/build_scouting_corpus.py` (~$30 in API calls for the full corpus) |
| **kNN comparable indexes** | **1257 skaters** (24-feature embedding) + **136 goalies** (10-feature v1) | `tools/build_comparable_index.py` + `tools/build_goalie_comparable_index.py` (run AFTER the NST + Edge layers are populated) |
| **Per-game context yamls** | Habs Round 1 2026 series (Games 1-4 indexed) | `tools/build_game_context.py <game_id>` per game; manual `significance` notes for marquee events |

**Don't want to rebuild the whole stack?** The redistributable subset (kNN indexes + LLM-extracted scouting tables, but not the raw NST counting stats) ships as a separately downloadable zip — see [`tools/export_derived_artifacts.py`](./tools/export_derived_artifacts.py) and the answer below.

Once your DB is populated, run `python tools/player_snapshot.py "<name>"` (or use the `player-snapshot` Claude skill) to dump all five layers for any player in one shot.

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
