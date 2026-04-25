---
name: draft-game-post
description: Draft an analytically rigorous post-game hockey analysis in markdown, with tables, 80% CIs, sample-size disclosures, glossary links, and cited sources. Works for any NHL game or the PWHL if the PWHL connector is enabled. Supports EN and FR output.
triggers:
  - "draft a post about"
  - "write up last night's game"
  - "analyze the game between"
  - "rédige un billet sur"
  - "résume le match de"
---

# draft-game-post

You are drafting a **journalistically honest, analytically rigorous** post about a single NHL game, for a reader who wants the actual numbers and won't tolerate cliches ("compete level", "wanted it more", "clutch gene"). Output is Markdown suitable for Substack, a blog, or a thread.

## Core rules

1. **Cite sample sizes.** Every rate you quote is paired with TOI (minutes) and GP (games), or the pooled window used.
2. **Use 80% CIs.** When the data supports it, show point estimate + 80% CI. If CI straddles zero, say so in plain language.
3. **Every metric links to the glossary.** Use MCP resource `lemieux://glossary/{term_id}` to get the short label + long definition. Put an HTML-style link or footnote to its short definition the first time it appears.
4. **No predictions.** This skill never predicts future series outcomes.
5. **No "player rating" scalars.** Don't reduce to a single grade — show iso_xgf60 and iso_xga60 separately.
6. **Language match.** If user asked in French, produce French; else English. Glossary loader accepts `lang="fr"` or `"en"`.

## Required structure

1. **Dek / one-line takeaway** — the headline sentence a reader could repeat.
2. **What happened (30-60 words)** — final score + key plays with event timestamps from the play-by-play.
3. **What the numbers say (200-350 words)** — the analytical core:
   - Team-level 5v5 xG and CF% (pulled via `query_team_stats`)
   - One-to-three notable players with iso impacts (pulled via `query_skater_stats` or `rank_players`)
   - One surprise vs. prior (a player unexpectedly positive/negative)
4. **One swap-scenario callout** — *if* the user asked for it or it's clearly warranted: call `project_swap_scenario` with a defensible pair (e.g., a struggling 3C → a healthy scratch) and present the Δ with CI. Label it "directional, not predictive."
5. **What the data can't tell us** — 2-3 sentences on limits: matchups the model doesn't see, goalie variance, small playoff sample.
6. **Footer** — sources (NHL.com, NST, others used), pooled window used, timestamp.

## MCP tools to call (in order)

1. `query_team_stats(team_id, season, stype='3' if playoff else '2', sit='5v5')` for both teams.
2. `rank_players(team_id, sit='5v5', min_toi=200, baseline='current_only', top_n=5, bottom_n=3)` for the team you're focusing on.
3. `fetch_game_detail(game_id)` to get the plays/shifts for narrative accuracy.
4. `project_swap_scenario(...)` if a swap callout is appropriate.
5. Read `lemieux://glossary/{term_id}` for each metric you cite.

## Glossary terms you'll almost always reference

- `expected_goals`, `xgf60`, `xga60`, `iso_xgf60`, `iso_xga60`, `confidence_interval`, `toi`, `pooled_baseline`

## Output format

Markdown. Tables for anything multi-column. Callout boxes (blockquotes with a bold header) for caveats. Links for sources.

### Example skeleton (English)

```markdown
# [Headline]: [one-line takeaway]

*[Date] · [AWAY] at [HOME] · Final: [score]*

## What happened

[30-60 words of factual recap with time stamps from play-by-play]

## What the numbers say

At 5v5, [TEAM] outshot [OPP] by [CF%] and outchanced [CF/xGF pct]. [Link: [xGF%][1]]
...

| Player | Position | TOI | iso xGF/60 | iso xGA/60 | Net |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

[2-3 paragraphs analyzing why — never moralizing about effort, always grounded in the table]

## Swap scenario callout (optional)

**If [TEAM] ran [X] in [Y]'s slot at 5v5:**
- Δ xGF/60: +0.XX (80% CI: −0.YY, +0.ZZ)
- Net per-60: ±0.XX

*Directional, not predictive. See methodology.*

## What the data can't tell us

[2-3 sentences of honest limitations]

---

[1]: *xGF%: team's share of expected goals. See glossary: https://github.com/.../glossary#xgf60*

**Sources**: [NHL.com play-by-play], [Natural Stat Trick], [MoneyPuck (if used)].
**Pooled window**: [what was used].
```

## French variant

Same structure. French versions of term names come from `lemieux://glossary/{term_id}` with `lang="fr"`. Keep section headings in French: « Ce qui s'est passé », « Ce que disent les chiffres », « Ce que les données ne disent pas », etc.

## Common mistakes to avoid

- Citing a rate without TOI.
- Using "clutch", "wanted it more", "leadership", or similar unfalsifiable narrative.
- Claiming a one-game sample proves anything about a season-long trend.
- Predicting the series outcome.
- Inventing quotes. Only cite what's in the play-by-play or an explicitly sourced link.
- Using raw Corsi as a primary quality metric (it's a volume filter; xG is the quality metric).
- **Misstating a player's position when describing line roles.** Always cross-check the position before writing prose like "X took Y's center role" or "Z moved to wing." Skater roster positions live in `skater_stats.position` (`C`, `L`, `R`, `D`). If your prose claims a player took on or vacated a role, run the verification step below.

## Position-verification step (mandatory before submitting prose about line roles)

This catches a real bug that almost shipped: I once described Texier as a center on a line where Newhook was actually the center, because the press extract said "Kapanen took Texier's former line" and I conflated "left that line" with "was the center of that line". Don't do this.

**Before writing any sentence of the form "X took Y's role as <position>" or "X moved from <position> to <position>", do this:**

1. Pull `skater_stats.position` for every player named in the sentence (one SQL query, or call `query_skater_stats` via MCP).
2. For each player, confirm what position the press / data attributes to them in BOTH the prior game and the current game.
3. Check whether the previous-game line had a different center than the new-game version of that line. If the center changed, name the previous center explicitly.
4. If a player you claim "took the center role" is not listed as `C` in the data, restructure the sentence to describe the line composition without inferring positional roles. Example: "Texier joined Dach and Bolduc" is safer than "Texier moved to Dach's wing" if you haven't verified Dach plays center (he does, but the principle holds).

The verification is one query and 30 seconds. Skipping it is how the wrong-name-as-center error gets into a published draft.

## Self-check before delivery

Before returning output, run `validate-analysis` mentally:
- Every rate has TOI attached? ✓
- CIs shown where available? ✓
- Every cited metric appears in the glossary? ✓
- No series predictions? ✓
- Sample-size caveats in the final section? ✓
- **Every player position claim verified against `skater_stats.position`?** ✓
- **Every line-role assertion ("X took Y's role at C") names the right prior and new center?** ✓
