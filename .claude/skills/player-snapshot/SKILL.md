---
name: player-snapshot
description: Render a complete data-model snapshot for any NHL player Lemieux knows about. Auto-detects skater vs goalie and renders bio, on-ice stats, biometrics, scouting profile, kNN cohort, game-context anchors, and current-series PBP-direct stats.
triggers:
  - "tell me everything about"
  - "tell me about <player>"
  - "what do we know about"
  - "snapshot of"
  - "show me <player>'s data"
  - "everything we have on"
---

# player-snapshot

You're rendering a complete picture of what Lemieux's data model knows about
a single player. The user wants every section the framework has data for, in
a consistent format they can scan quickly.

## Workflow

1. Run `tools/player_snapshot.py <name>` — it auto-detects skater vs goalie
   and pulls everything in one shot. Partial-match and unicode-aware (e.g.
   `"Dobes"` resolves `Jakub Dobeš` correctly).
2. Reformat the script's plain-text output into the markdown structure
   below. The script's order is the right order; you're just polishing.
3. Surface non-obvious findings in a closing paragraph — the same way
   `propose-swap-scenario` doesn't just dump tables, it tells the reader
   what's notable.

## Sections (in order)

1. **Static bio** — height, weight, birth date, draft, shoots/catches
2. **On-ice stats** (skater) OR **Goalie stats** (goalie) — career arc by
   (season, stype, sit). For skaters always show 5v5 + 5v4 + all. For
   goalies always show 5v5 + all.
3. **NHL Edge biometrics** — skating/shot speeds, burst counts. For goalies,
   note explicitly that Edge endpoints are skater-only.
4. **GenAI scouting profile** — sources searched, continuous attributes
   (1-5), archetype tags with cited quotes + URLs, comparable mentions.
5. **Comparable engine kNN cohort** — top 5-7 NHL comps with similarity
   score + per-feature drivers. Skaters use `comparable_index.json`,
   goalies use `goalie_comparable_index.json`.
6. **Game-context anchors** — any indexed `gameN_context.yaml` files where
   the player appears in `goal_sequence` or `key_events`. (Currently only
   the Habs Round 1 2026 series is indexed.)
7. **Current-series PBP-direct stats** — from
   `examples/habs_round1_2026/playoff_rankings.numbers.json`. Skaters get
   individual scoring + 5v5 iso ranking + 5v4 iso ranking. Goalies get
   shots-faced / GA / SV%.

## Closing paragraph (required)

End with a 2-4 sentence "What the framework can tell you about this player
right now" synthesis. Include:
- The most striking finding from the data (the career year, the iso
  collapse, the playoff slump, etc.).
- Where the data is thin or missing (low scouting source-count, no Edge
  data, comparable cohort N is small, etc.).
- One falsifiable claim the data supports if any (e.g. "Suzuki's playoff
  5v5 iso has cratered to -0.73 vs his pooled career -0.17").

## Output rules

- Always show every section, even when "no data" — the absence is
  informative.
- Quote source URLs verbatim for scouting-tag evidence so the reader can
  click through.
- For comparable mentions, the kNN cohort's per-feature drivers are
  load-bearing (they explain *why* a comp matched). Always include the
  top-3 driver columns.
- Don't editorialize about the player's character or trajectory beyond
  what the data says. The framework grades claims, doesn't speculate.
- If the player has bilingual coverage, FR output requires running the
  closing-paragraph synthesis through `translate-to-quebec-fr` first.

## Common mistakes to avoid

- Computing individual scoring from skater_stats. Lemieux currently doesn't
  pre-aggregate G/A/SOG per season — those come from PBP analyzers
  (`playoff_rankings.numbers.json` etc.) only. Don't claim "Suzuki has 73
  goals in 25-26" from the data unless the source is the analyzer.
- Treating goalie kNN comps as a stylistic match. The v1 goalie comp
  engine is built on bio + performance + workload-share — it captures
  trajectory and shape, not stylistic differences (positional vs scrambly,
  glove-side vs blocker-side). Surface that caveat when the user asks
  "who plays like X."
- Quoting scouting tags out of context. Each tag has a source quote and
  source URL — both must travel together. A tag without its quote is
  framework-internal and shouldn't be presented as a fact.
- Inferring playoff performance from regular-season pooled stats. The
  pool window includes both reg + playoff but downstream callers (swap
  engine etc.) often want only reg-season-as-prior. Be specific about
  which slice you're showing.
