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
| `research-game` | Pull press coverage (EN + FR whitelist) for a specific game; output structured `claims.yaml` + `usage_observations.yaml` ready for downstream analysis |
| `translate-to-quebec-fr` | Translate hockey-analytics writing into idiomatic Québec hockey-press French — never call after literal translation, always before finalizing FR copy |
| `draft-game-post` | Full post-game analysis with tables, CIs, glossary links, claims ledger graded against data |
| `propose-swap-scenario` | 2–3 candidate lineup swaps evaluated head-to-head with 80% CI bands |
| `validate-analysis` | Rigor check on a draft before publishing — flags overclaims, missing CIs, predictions, cliches |
| `review-pr-lemieux` | Opinionated PR review with structured verdict (MERGE / REQUEST CHANGES / CLOSE). Auto-invoked by `.github/workflows/claude-pr-review.yml` |

## Writing a new skill

Use `templates/skill-template/` as a starting point. Rules:

- Bilingual (EN + FR) instructions in the same `SKILL.md`.
- Reference glossary terms by ID, not inline definitions.
- Explicitly require outputs to show sample size and CIs.
- No predictions. No player-rating scalars.
- Prefer calling existing MCP tools over inlining logic.
