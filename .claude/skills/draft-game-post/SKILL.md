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

## Lead with outcomes, not announcements of changes

By the time a post-game report ships, the audience has already watched the game. They know who scored, they saw the lineup, they noticed if a line got reshuffled, they heard the broadcasters call out matchup changes. None of that is news. **The story is what the data reveals about play that wasn't obvious from watching** — what the new line *produced* (xGF, shot share, goals), what an isolated impact rate looks like over a multi-game window, where the chance-quality vs. shot-volume gap actually showed up.

Concretely: front the **outcome**, treat the **change** as explanatory context.

### Heuristic

Any time you're about to write a sentence whose subject is a coaching decision, a lineup move, a system tweak, or a roster change, ask: *what did it produce*? If you have a quantitative answer, lead with that. If you don't, the sentence shouldn't be in the lead — push it to a context paragraph or drop it entirely.

### Examples

| Don't lead with this | Lead with this |
|---|---|
| "MTL reshuffled two lines for Game 3." | "A trio that didn't exist before tonight scored both of MTL's 5v5 goals — here's how it was built." |
| "Slafkovský was matched against Hagel's line all night." | "Slafkovský's line gave up zero high-danger chances at 5v5; the Hagel matchup was the reason." |
| "Kapanen got 14 minutes at 3C in his first game in that role." | "MTL's third line generated +0.8 xG net in 14 minutes — Kapanen's debut at 3C." |
| "St-Louis put Hutson on PP1." | "PP1 generated 1.4 xG in 4:30 of 5v4 with Hutson at the point — his first PP1 minutes of the series." |
| "TBL's bottom six didn't see much ice time." | "TBL's bottom six was outshot 8–1 in 9 minutes of 5v5 — Cooper shortened the bench for cause." |

### When this rule does NOT apply

- **Setup paragraphs** in long-form posts (a brief "what's at stake" framing is fine).
- **Methodology / context boxes** that exist precisely to explain how something is being measured — those are not the lead.
- **Composition tables** for reference (the BEFORE/AFTER lineup table is fine; just don't put it before the outcome).

### Why this matters

Hockey writers default to recap voice ("then this happened, then that happened"). That voice repeats what the audience already knows. The whole reason this framework exists is to surface what the *data* reveals — and that's almost always an outcome or a delta, never an announcement. If a draft reads like a play-by-play recap, it's missing the point.

## Don't restate what was known before the post-data analysis

The reader watched the game. They read the morning paper. They saw the pre-series predictions. **The post-game report is not a place to restate any of that.** Every bullet, every section intro, every sentence has to pass the test: *what does this say that the reader didn't already know without the data?*

If the answer is "this is general framing repeated from pre-series chatter" or "this is a goalscorer name from the box score," cut it or replace it with a finding only the post-data analysis can produce.

### Examples to cut

| Don't write (already known) | Write instead (analysis-only) |
|---|---|
| "Tampa drives possession, Montreal generates more high-danger chances." | "MTL holds 75% of 5v5 high-danger chances through 3 games — a level that almost always regresses but hasn't yet." |
| "Slafkovský had a hat trick in Game 1." | "Slafkovský has 8 SOG / 3 G before the Hagel fight, 2 SOG / 0 G after — but his line is still outshooting opponents 20-9 with him on after the fight." |
| "MTL won 3-2 in OT on a Hutson goal." | "Hutson scored on his first slap shot of the season per his post-game quote — the only Hutson scoring shot logged at slap-shot release type in 84 games of NST data." |
| "Vasilevskiy was the more reliable goaltender pre-series." | "Through 3 games, Dobes has a higher implied SV% than Vasilevskiy (.905 vs .893) — the pre-series claim doesn't survive contact with the data." |
| "Lineups changed for Game 3." | (cut entirely; the table goes in section 1 as context) |

### The test for every paragraph

Ask: **"Could a reader produce this sentence from the box score and yesterday's chatter alone?"** If yes, the sentence isn't earning its place. Either reframe it with the analysis-derived value-add (a specific number that contextualizes the obvious fact, an unexpected magnitude, a contradiction with the pre-series narrative), or delete it.

This is a corollary of "lead with outcomes" — outcomes are by definition NEW (they're what the data revealed), while announcements and pre-series narratives are by definition OLD. The two rules together say: **the post-game report only earns its space by adding signal the reader couldn't have gotten from watching the game.**

## No meta-commentary about the report's own structure

Don't write sentences that explain what the next paragraph will do, or that defend the editorial choices being made. Sentences like:

- "The rest of this section is about where the line came from..."
- "The composition table is below as context, not as the lead."
- "Reading order: outcome first, then context."
- "Cette section explique d'où il sort..."
- "We'll come back to that in section 4."
- "It's worth noting that..." / "What's interesting is..."

...are all having a meeting with the reader inside the report. The reader doesn't need a tour guide. They will read the next paragraph because it's there. They will see the table because it's there. **Just write the report; let the structure speak for itself.**

This is a corollary of "lead with outcomes": meta-commentary often shows up when the author is trying to justify why they put the outcome first instead of the announcement. The justification doesn't belong in the prose. Just deliver the outcome and move on.

### Examples to avoid

| Don't write | Just write |
|---|---|
| "This section explains where the line came from." | (delete the sentence; the next paragraph already does this) |
| "What the numbers say about Hutson is interesting:" | (delete; let the numbers say it) |
| "It's worth flagging that the sample is small here." | "The sample here is 3 games — wide CIs apply." (state the fact, drop the editorial frame) |
| "We'll come back to special teams below." | (delete; if the section is below, the reader will find it) |

### Self-check on the lead

- Does the first sentence of the post lead with a measured outcome (a goal differential, an iso impact, an xG share, an unexpected ranking) — or with a fact about lineups/decisions/changes?
- If the latter, restructure: pull the outcome up; push the announcement down.

---

## Lineups are inputs to this skill, not outputs

**You do not infer line composition or player positions from press prose. You read them from a structured lineups file.** The skill is allowed to refuse to draft prose about line roles if no structured lineup data is available — that's correct behavior, not a failure mode.

### The contract

Before producing any sentence about line composition, line changes between games, or who plays which position:

1. **Load the structured lineup file for this game.** Standard path: `examples/<series>/<gameN>_lineups.yaml` (or wherever the orchestrator puts it). Schema: per-team `forwards` (array of lines, each with players + their `position` field), `defense`, `goalie`, `pp1`, `pp2`, `scratches`. The file also contains the `previous_game` lineup and a `changes_vs_previous_game` block. See `examples/habs_round1_2026/game3_lineups.yaml` for the canonical example.

2. **If the file doesn't exist, stop.** Either:
   - Generate it from `research-game` output + NHL.com shift data (preferred), or
   - Tell the user the file is required and what it should contain.
   
   Do NOT improvise from press extracts. Press extracts are imprecise about positions and have produced real bugs.

3. **Write prose against the loaded data, not against narrative recall.** Every claim like "Kapanen took the center role on the Demidov line" must be a direct read of `changes_vs_previous_game.MTL.line_reshuffles[i]` — the file's `prior_center`, `new_center`, and `description` fields are the prose source. The author of those fields is the analyst who produced the lineup file (typically `research-game` + the analyzer cross-check), not you.

4. **If you find yourself wanting to say something the structured data doesn't support, the data is wrong or incomplete.** Flag it back to the user; don't paper over with prose.

## Common mistakes to avoid

- Citing a rate without TOI.
- Using "clutch", "wanted it more", "leadership", or similar unfalsifiable narrative.
- Claiming a one-game sample proves anything about a season-long trend.
- Predicting the series outcome.
- Inventing quotes. Only cite what's in the play-by-play or an explicitly sourced link.
- Using raw Corsi as a primary quality metric (it's a volume filter; xG is the quality metric).
- **Writing prose about line composition without loading the structured `*_lineups.yaml` file.** This is how the Texier-as-center bug shipped — prose was written from press recall instead of structured data. The fix is upstream (always load the file), not downstream (verify positions later).

## Self-check before delivery

Before returning output, run `validate-analysis` mentally:
- Every rate has TOI attached? ✓
- CIs shown where available? ✓
- Every cited metric appears in the glossary? ✓
- No series predictions? ✓
- Sample-size caveats in the final section? ✓
- **Structured `*_lineups.yaml` was loaded before any line-composition prose was written?** ✓
- **Every line-role sentence is a direct read of fields in that file (no narrative recall, no press-extract inference)?** ✓
