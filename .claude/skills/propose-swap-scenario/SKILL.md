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
4. **For low-sample IN candidates (pooled TOI < 600 min) or when comp-stabilization adds value:**
   - Load the persisted `ComparableIndex` (`legacy/data/comparable_index.json`).
   - Call `find_comparables(target=IN_player_name, k=5)` to retrieve their kNN cohort.
   - Call `build_cohort_stabilized_impact(target_impact, cohort)` to get a Layer-2 projection that blends the target's iso with the cohort's pooled iso (variance propagated). Tighter CI on small-sample targets.
5. **For targets with strong archetype tags (any tag at confidence ≥ 0.6 in `scouting_tags`):**
   - Pull the target's primary archetype tag via `list_player_tags(name, position)`.
   - Run `tag_split_study(tag)` for that archetype; if the cohort has N ≥ 10 AND its CI is sign-consistent (doesn't straddle zero), apply the lift as a Layer-3 archetype adjustment. Otherwise show the layer with explicit "CI straddles zero" framing.
6. Sort by net projected impact across all available layers, present top candidates with the layered CI breakdown.

## Output rules

- Always show all candidates, not just the "best" — the spread matters.
- If all candidates have CIs straddling zero, lead with **"the data does not confidently distinguish these options."**
- Never present a single recommended swap without its CI.

## Template — basic (Layer 1 only)

```markdown
## Swap scenarios for [TEAM] at 5v5

Baseline: pooled 2 seasons + playoffs. Slot minutes match OUT player's typical usage.

| OUT → IN | Slot min | Δ xGF/60 | Δ xGA/60 | Net | 80% CI (net) |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

**Read**: [plain-language summary. If CIs straddle zero, say "indistinguishable in this sample."]
```

## Template — three-layer (with comp engine + scouting tags)

When the IN candidate has a populated comp-cohort + at least one strong archetype tag, render the layered breakdown. Worked example in `examples/swap_with_comparables/build_three_layer_swap_post.js`.

```markdown
## Swap projection: [IN] for [OUT] at [SLOT_MIN]-min/game [STRENGTH] slot

| Layer | Δ Net xG/game | xGF 80% CI | CI width |
|---|---|---|---|
| L1 — Target's pooled iso (5-yr NHL) | ... | [..., ...] | ... |
| L2 — Comp-cohort-stabilized (k=5 NHL kNN) | ... | [..., ...] | ... |
| L3 — Archetype-adjusted ('[TAG]', N=...) | ... | [..., ...] | ... |

**Read**: [Are layers directionally aligned? Which layers' CIs exclude zero? If L3's CI straddles zero, the archetype lift is too noisy at this cohort size — note that explicitly.]
```

## Common mistakes to avoid

- Proposing a swap using a tiny-sample recent call-up as the IN player — flag sample size, and use Layer 2 (comp-cohort stabilization) to regularize.
- Suggesting swaps across strength states without re-calling the tool with the right `sit`.
- Claiming a swap "will" improve the team — they're projections, not predictions.
- Applying Layer 3 (archetype lift) when the cohort N < 10 OR its CI straddles zero — that adds noise rather than signal. Show the layer with the straddles-zero caveat or omit it.
- Pretending Layer 3 is statistically robust for any tag whose corpus N is small. Tag noise + sample-size noise compound; the framework's discipline is to grade the claim, not manufacture lift.
