---
name: research-game
description: Gather pre-analysis research for a specific NHL or PWHL game from a curated whitelist of trusted EN and FR sources, extract testable claims with verbatim quotes, and produce a structured `claims.yaml` ready for downstream data validation. Use this BEFORE invoking `draft-game-post` so the post has real claims to grade.
triggers:
  - "research yesterday's game"
  - "gather sources on the"
  - "pull research for"
  - "fais de la recherche sur le match"
  - "trouve les articles sur"
---

# research-game

You are gathering structured research for a specific game so a downstream analysis (typically `draft-game-post`) can grade real public claims against real data. The output is a YAML file of claims, each tied to a verbatim quote and a verifiable URL — never fabricated.

## When to invoke

- A user asks for analysis of a specific game and didn't pre-supply a research file.
- A user explicitly asks for "research" or "what are people saying about" a recent game.
- BEFORE `draft-game-post` if the post will include a "claims ledger" section (which most posts should).

## Workflow

### 1. Identify the game
- Date (YYYY-MM-DD)
- Teams (3-letter abbreviations)
- Final score, OT/SO if applicable
- For NHL playoffs: derive the NHL.com gameId (`YYYY03RRSG`) for cross-reference

### 2. Search the whitelist
Use `WebSearch` with `allowed_domains` set to one whitelist domain at a time. Run searches in **parallel** (one tool call per source, all in the same response). The English and French source lists are below — **always include FR sources**, never default to EN-only.

### 3. Fetch article bodies
For the most relevant 4-8 hits across both languages, use `WebFetch` to extract:
- Headline + byline
- Lede paragraph
- **Verbatim quotes** from coaches, players, columnists, or analysts (preserve French diacritics exactly)
- Specific player-level or team-level performance claims (testable: TOI, SOG, line assignments, special-teams performance, on-ice impact)

If a source returns 403 or is paywalled, note this and move on — never invent content.

### 4. Extract claims AND lineup changes into `claims.yaml`

**Lineup permutations are the highest-priority extract.** A research file that misses a line change but captures three columnist quotes is failing the user. Specifically search for and surface:

- Personnel changes (who's in / who's out vs. last game)
- Line reshuffles (e.g., "Kapanen moved to 3C with Demidov-Newhook")
- Defensive pair changes
- Power-play unit changes
- Healthy scratches and call-ups
- Coach's stated reasoning (quote it verbatim)

Output schema has TWO top-level sections — `lineups` and `claims`:

```yaml
game_id: "2025030123"
date: "2026-04-24"
teams: { home: MTL, away: TBL }
score: { home: 3, away: 2, ot: true }

lineups:
  # One block per team. Capture personnel + line combos as reported by beat writers,
  # plus any explicit changes vs. the prior game.
  MTL:
    sources:
      - { source: "Daily Faceoff", url: "...", confidence: high }
      - { source: "Radio-Canada", url: "...", confidence: high }
    forwards:
      - { line: 1, players: ["Slafkovský", "Suzuki", "Caufield"] }
      - { line: 2, players: ["Texier", "Dach", "Bolduc"] }
      - { line: 3, players: ["Newhook", "Kapanen", "Demidov"] }
      - { line: 4, players: ["Anderson", "Evans", "Gallagher"] }
    defense:
      - { pair: 1, players: ["Matheson", "Hutson"] }
      - { pair: 2, players: ["Struble", "Carrier"] }
      - { pair: 3, players: ["Guhle", "Xhekaj"] }
    goalie: "Dobes"
    pp1: ["Suzuki", "Caufield", "Slafkovský", "Demidov", "Hutson"]
    pp2: ["Bolduc", "Danault", "Gallagher", "Texier", "Dobson"]
    scratches: ["Beck"]
    changes_vs_previous_game:
      - description: "Kapanen moved to center Demidov-Newhook (was 4C in G2)"
        type: line_reshuffle
        source_url: "https://ici.radio-canada.ca/sports/..."
        coach_quote: "..."
      - description: "Texier shifted to RW with Bolduc-Dach (was LW with Newhook)"
        type: line_reshuffle
        source_url: "..."
    coach_post_game_quote: |
      "Je n'abandonnerai jamais un joueur à moins qu'il n'abandonne sur lui-même"
    coach_post_game_source_url: "https://www.rds.ca/..."
  TBL:
    # same structure
    ...

# Usage observations: deployment / ice-time decisions that aren't in the box score.
# These enrich the pure data because a coach's intent is invisible to it.
# Examples: a star double-shifted late, a 4th-liner played 45 seconds in OT, a top
# line saw fewer minutes than usual, a player got benched mid-period, a healthy
# scratch was activated without explanation. Each entry should pair the observation
# with whatever data we can corroborate from the shift chart.
usage_observations:
  - text: "Hutson played 26:28 — most of any skater in the game."
    type: ice_time_anomaly  # one of: ice_time_anomaly, line_creation, double_shift,
                            # benched, scratch_activated, role_change, sheltered_minutes,
                            # heavy_matchup, special_teams_change, other
    player_or_team: "Hutson"
    decision_by: "St-Louis"
    source: "RDS, François Gagnon"
    source_url: "https://www.rds.ca/..."
    coach_quote: ""          # if applicable
    data_corroboration: "NHL.com shift chart confirms (26:28)."
    significance: "Heavy minutes by a 2nd-year defenseman on a winning night — both a vote of confidence and a sign the rotation tightened."

  - text: "Sabourin played 3 minutes in regulation but 45 seconds in overtime."
    type: ice_time_anomaly
    player_or_team: "Sabourin"
    decision_by: "Cooper"
    source: "Radio-Canada, Martin Leclerc"
    source_url: "https://ici.radio-canada.ca/sports/..."
    coach_quote: ""
    data_corroboration: "Confirmed via NHL.com shift chart."
    significance: "Anomalous OT deployment of an enforcer — the chronique called this a 'effronterie'. Worth tracking if Cooper repeats it."

# Cross-reference: have we VERIFIED these lineups against the actual shift data?
# Set this AFTER the analyzer has pulled NHL.com shift charts and cross-checked.
# Drift between "reported" and "actually deployed" lines is itself a finding.
lineup_verification:
  status: pending  # one of: pending, verified, drift_detected
  notes: ""

claims:
  # Quote-level claims as before. Prioritize claims that test lineup decisions
  # (e.g., "Dach's line scored 2 goals and 6 points") since those are the user's focus.
  - id: 1
    source: "La Presse"
    url: "https://www.lapresse.ca/sports/..."
    author: "Mathias Brunet"
    date: "2026-04-25"
    language: fr
    quote_verbatim: |
      Le Tricolore a dominé les chances de qualité en troisième période.
    english_paraphrase: "MTL dominated quality chances in the third period."
    claim_type: team-tactical  # team-tactical, player-perf, goalie, coaching, momentum, special-teams, lineup
    player_or_team: "MTL"
    data_testable: yes
    test_angle: "5v5 HDCF/HDCA in the 3rd period via NHL.com PBP"
    contradicts: []  # optional — list other entry IDs
```

**Why `lineups` is first-class:** the user's project is fundamentally about understanding the impact of lineup permutations. The downstream analyzer treats the lineup file as **ground-truth input** — it does not infer or guess line composition from press prose, and `draft-game-post` is not allowed to write line-role sentences without loading this file first. The lineup file is therefore not "research output to be summarized later" but the **canonical fact base** for every claim about who played where, who was promoted, who was demoted, and what changed game-over-game. Get this right or the whole downstream analysis is structurally wrong.

The lineup section must include:

- Per-team forwards (4 lines × 3 players, each with `position`: `C`, `L`, `R`)
- Per-team defense pairs (3 × 2)
- Goalie + PP1/PP2 + scratches
- A `previous_game.<TEAM>.forwards` block with the same shape so drift can be computed mechanically
- A `changes_vs_previous_game.<TEAM>.line_reshuffles` block with `prior_center`, `new_center`, `moved_player` fields populated. These fields are read directly into prose by `draft-game-post` — they are not re-interpreted.

**Why `usage_observations` is first-class:** raw shift data tells you that Hutson played 26:28; it can't tell you that doing so was a deliberate vote of confidence after a tough Game 2, or that giving Sabourin 45 seconds of OT after 3 minutes of regulation was an "effronterie". These are the *qualitative* lenses that make the *quantitative* data interpretable — and they only come from reading the press. Capture every interview-derived deployment claim here, paired with the data corroboration where available, so downstream analysis can cite both layers.

### 5. Save the file

`research/<gameId>_claims.yaml` (gitignored — never commit research notes; they may include copyrighted lede text).

If a `research/` directory doesn't exist, create it and add a one-line `README.md` noting the contents are gitignored.

### 6. Hand off to downstream

Print a one-line confirmation with the path and entry count, e.g.:

> "Saved 14 claims (8 FR, 6 EN, 2 contradictions flagged) to `research/2025030123_claims.yaml`."

## Source whitelist

**Always search at least one EN and one FR source. Default to running 6-10 searches in parallel.**

### Francophone (Quebec / Canada)
- **La Presse** (`lapresse.ca`) — Mathias Brunet, Simon-Olivier Lorange, Guillaume Lefrançois, Jean-François Tremblay, Richard Labbé. Strongest analysis register.
- **RDS** (`rds.ca`) — François Gagnon (chronique), Luc Gélinas, Marc Denis. Game recaps + chroniques.
- **Radio-Canada Sports** (`ici.radio-canada.ca`) — Martin Leclerc (chronique), Marc-Antoine Godin, Alexandre Pratt. Recaps + opinion.
- **Le Devoir** (`ledevoir.com`) — limited hockey coverage but occasional analytical pieces.
- ⚠ **Journal de Montréal** (`journaldemontreal.com`) and **TVA Sports** (`tvasports.ca`) are currently blocked from automated retrieval. Note the source if a user references them directly; don't try to scrape them.

### Anglophone
- **NHL.com** (`nhl.com`) — official recaps, coach press conferences (transcribed).
- **The Athletic** (`theathletic.com`) — Marc Antoine Godin (FR-Canadian context, writes in EN), Arpon Basu (Canadiens beat). Paywalled but lede + headline often visible.
- **Sportsnet** (`sportsnet.ca`) — Eric Engels (Canadiens), Luke Fox.
- **TSN** (`tsn.ca`) — Frank Seravalli, Pierre LeBrun.
- **Habs Eyes On The Prize** (`habseyesontheprize.com`) — community analytics-leaning blog.
- **Daily Faceoff** (`dailyfaceoff.com`) — line combinations, lineup confirmations.
- **HockeyDB** (`hockeydb.com`) — boxscore-only structured recap.
- **CityNews Montreal** (`montreal.citynews.ca`) — local angle.

### Anti-whitelist (avoid these)
- Pure betting/odds outlets (NY Post betting, Covers.com, etc.) — claims are speculative pre-game, not data-grounded.
- YouTube/recap aggregators with no editorial process.
- Wire-service rewrites that just rephrase the boxscore — they add no testable claim.

## Hard rules

- **Lineups before opinions.** If you only have time for one extraction pass, capture the line combinations and any changes vs. the previous game. The analytical layer downstream depends on this.
- **Cross-check lineup sources.** Daily Faceoff is the canonical lineup source pre-game; Radio-Canada and beat reporters confirm post-game. If they disagree, prefer the post-game beat-reporter version (reported = aspirational; actual = what was deployed) and flag the disagreement.
- **Never fabricate.** If a source is paywalled or returns 403, log the URL with `paywalled: true` and skip the body. Do not invent quotes.
- **Always include FR sources.** A claims file with zero FR entries is incomplete for any Quebec-team-related analysis. For non-Quebec teams, FR sources are still encouraged when relevant (Senators get good FR coverage too).
- **Prefer specific claims over narrative.** "Hutson played 26:28 with 4 blocked shots" is data-testable; "Hutson played his heart out" is not — drop it.
- **Flag contradictions.** If RDS calls a player "transformé" and NY Post calls him "diminué," that contradiction is gold for the data piece — surface it via the `contradicts` field.
- **Quote diacritics exactly.** Preserve é, è, ç, à, etc. Don't strip them.
- **Cite real URLs.** If you can't find a real URL, drop the claim.

## Output for the user

After the YAML is saved, provide a 5-7 sentence executive summary:

1. **Lineup changes** for both teams (most important — lead with this).
2. How many claims by language.
3. 1-2 surprising / contradictory findings worth surfacing in the post.
4. Any sources that were unreachable.
5. A pointer to the next step: "Run the analyzer to cross-check reported lineups against actual shift deployment, then `draft-game-post` to grade the claims."

That summary feeds straight into the `draft-game-post` skill's Claims Ledger and into the swap-scenario analytics, which need the line combinations as input.

## Verifying reported vs. deployed lineups

Reported lineups (Daily Faceoff, beat reporters) are pre-game. Actual lineups are what got deployed. They often differ — coaches double-shift stars, juggle on the fly, or rotate after a bad period.

**After the YAML is written**, the downstream analyzer should:
1. Pull NHL.com shift charts via `lemieux.connectors.nhl_api`.
2. For each reported line, sum the seconds where exactly those 3 forwards (or 2 D) were on ice together.
3. Compare to total team TOI per line — if reported "Line 1" only saw 4 minutes together but reported "Line 4" saw 12, the reported lines are wrong (or got abandoned mid-game).
4. Update `lineup_verification.status` to `verified` or `drift_detected`, with notes.

This drift detection is a **first-class finding** for any post about a game — the user's central interest is what coaches actually do with their lineups, not what they tell reporters they'll do.

## French variant

If the user asked in French, the SKILL.md instructions still apply but your final summary is delivered in French. Section headings inside the saved YAML stay in English (it's a structured machine-readable file).

## Self-check before delivery

- [ ] At least one FR source represented
- [ ] Every quote has a real, fetchable URL
- [ ] No fabricated content — paywalled entries explicitly flagged
- [ ] Claims tagged with testable angles (the analytics layer needs to know what to compute)
- [ ] Contradictions surfaced when present
