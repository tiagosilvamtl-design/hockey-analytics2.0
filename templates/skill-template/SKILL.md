---
name: example-skill
description: REPLACE this with what the skill does. Include trigger phrases Claude should watch for in user input. Keep under ~300 chars.
triggers:
  - "REPLACE: phrase that should fire this skill"
  - "REPLACE: a French equivalent"
---

# example-skill

**REPLACE all of this.** The SKILL.md file is Claude's instruction manual for this workflow.

## What this skill does

[1-2 sentences of purpose]

## When to invoke it

[Triggers + situational cues]

## Workflow

1. [First step — often: call an MCP tool]
2. [Second step — often: transform the data]
3. [Third step — often: render output]

## Required structure of the output

[What should the final Markdown/text look like? Be specific. Include a skeleton.]

## MCP tools to call

- `query_team_stats` / `query_skater_stats` / `project_swap_scenario` / …

## Glossary terms usually referenced

- `iso_xgf60`, `confidence_interval`, `pooled_baseline`, …

## Bilingual output

If the user asked in French, produce French. Section headings in French. Pull glossary terms with `lang="fr"`.

## Common mistakes to avoid

- [Explicitly list what a good skill should NOT do in this domain]

## Self-check before delivery

- [ ] Every rate paired with sample size
- [ ] CIs shown where relevant
- [ ] No predictions
- [ ] No unfalsifiable narrative
