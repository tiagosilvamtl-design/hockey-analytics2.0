# Lemieux Claude skills

Skills shipped with Lemieux that extend Claude Code (or Claude Desktop) with hockey-analytics-specific workflows. All skills are bilingual (EN/FR) and compose with the `lemieux-mcp` server's tools.

## Installation

Claude Code auto-discovers skills in `.claude/skills/` when you open a project directory. You're already set.

For Claude Desktop (global skills), copy the ones you want:

```bash
# macOS / Linux
cp -r .claude/skills/* ~/.claude/skills/

# Windows (PowerShell)
Copy-Item -Recurse .claude\skills\* $env:USERPROFILE\.claude\skills\
```

## Available skills

| Skill | When to invoke |
|---|---|
| `draft-game-post` | You want a full post-game analysis with tables, CIs, and glossary links |
| `propose-swap-scenario` | You want 2-3 candidate lineup swaps evaluated head-to-head |
| `validate-analysis` | You have a draft and want a rigor check before publishing |

## Writing a new skill

Use `templates/skill-template/` as a starting point. Rules:

- Bilingual (EN + FR) instructions in the same `SKILL.md`.
- Reference glossary terms by ID, not inline definitions.
- Explicitly require outputs to show sample size and CIs.
- No predictions. No player-rating scalars.
- Prefer calling existing MCP tools over inlining logic.
