# Getting started with Lemieux

> **Language**: English · [Français](../fr/getting-started.md)

## What Lemieux is

Lemieux is an open-source framework that combines Claude (or any MCP-compatible AI client) with curated hockey data connectors, analytics primitives, and workflow skills. The goal: generate analytically rigorous, caveat-aware hockey coverage without building it from scratch.

## 5-minute install

```bash
git clone https://github.com/<your-fork>/lemieux.git
cd lemieux

python -m venv .venv
source .venv/bin/activate       # Windows Git Bash: . .venv/Scripts/activate

# Install all Lemieux packages in editable mode
pip install -e packages/lemieux-core
pip install -e packages/lemieux-glossary
pip install -e packages/lemieux-connectors
pip install -e packages/lemieux-mcp
pip install -e packages/lemieux-app

# Add your NST access key (get one from your NST profile — free but approval required)
cp .env.example .env
# Edit .env, set NST_ACCESS_KEY=...
```

## Run the MCP server

```bash
lemieux-mcp --store ~/.lemieux/store.sqlite
```

Then point your Claude Desktop `mcp.json` at it. See the [lemieux-mcp README](../../packages/lemieux-mcp/README.md) for configuration.

## Use in Claude Code

Open the Lemieux repo directory in Claude Code. The `.claude/skills/` directory is auto-discovered. Ask Claude:

```
"Draft a 1000-word post about last night's Habs game. Focus on the second
power play unit. Include one swap-scenario callout. English, for a blog."
```

Claude invokes `draft-game-post`, calls the MCP tools, reads the glossary for metric definitions, runs `validate-analysis` as a rigor check, and produces a Markdown draft.

## Next steps

- Read the [glossary](../../packages/lemieux-glossary/src/lemieux/glossary/terms.yaml) to understand what Lemieux knows.
- Browse `examples/habs_round1_2026/` for a full worked analysis.
- Add a connector: see `templates/connector-template/`.

## Philosophy

Lemieux is not trying to replace Natural Stat Trick, Evolving-Hockey, or HockeyViz. It's an aggregation + orchestration layer that lets an AI client operate on their outputs honestly — with sample sizes, CIs, caveats, and glossary-linked terms always visible.

If your draft ever reads like a cliche-ridden game recap, something broke. File a bug.
