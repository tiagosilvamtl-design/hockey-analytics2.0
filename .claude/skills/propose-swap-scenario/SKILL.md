---
name: propose-swap-scenario
description: Given a team and an optional constraint, propose 1-3 interesting lineup swaps and evaluate each via project_swap_scenario with 80% CIs. Honestly flags when the data doesn't distinguish the options.
triggers:
  - "propose a swap"
  - "what if we swap"
  - "suggest lineup changes"
  - "propose un échange"
---

# propose-swap-scenario

You're helping a user think through lineup changes for a specific team. You generate **2-3 candidate swaps**, run `project_swap_scenario` for each, and present a ranked comparison. You are honest about when CIs straddle zero — that's the common case.

## Workflow

1. Call `rank_players(team_id, sit='5v5', min_toi=200, baseline='current_only')` to identify the lowest iso-net bottom-six players (candidates to swap OUT) and the healthy scratches / call-ups with positive pooled-baseline impact (candidates to swap IN).
2. Use `query_skater_stats(team_id)` to find the OUT player's usual slot minutes.
3. For each candidate pair, call `project_swap_scenario` with:
   - `baseline='pooled_2_seasons'` (bigger sample, more stable)
   - `slot_minutes` = OUT player's typical usage
   - `sit='5v5'` (and optionally also `'5v4'` if PP relevance is clear)
4. Sort by net projected impact, present top candidates with CI.

## Output rules

- Always show all candidates, not just the "best" — the spread matters.
- If all candidates have CIs straddling zero, lead with **"the data does not confidently distinguish these options."**
- Never present a single recommended swap without its CI.

## Template

```markdown
## Swap scenarios for [TEAM] at 5v5

Baseline: pooled 2 seasons + playoffs. Slot minutes match OUT player's typical usage.

| OUT → IN | Slot min | Δ xGF/60 | Δ xGA/60 | Net | 80% CI (net) |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

**Read**: [plain-language summary. If CIs straddle zero, say "indistinguishable in this sample."]
```

## Common mistakes to avoid

- Proposing a swap using a tiny-sample recent call-up as the IN player — flag sample size.
- Suggesting swaps across strength states without re-calling the tool with the right `sit`.
- Claiming a swap "will" improve the team — they're projections, not predictions.
