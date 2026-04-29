# Lemieux data model

This is the canonical guide to what Lemieux knows about NHL players and how
that knowledge is structured. Read it once before writing analyzers, skills,
or new connectors.

The data flow has **five layers**, each adding signal the layer above can't
produce on its own:

```
[1] Counting stats        ←  NST per-player on-ice + individual splits
       ↓                       skater_stats, skater_individual_stats, goalie_stats
[2] Bio + biometrics      ←  NHL Edge skating/shot speeds, height/weight/draft
       ↓                       edge_player_bio, edge_player_features
[3] Embedded comparables  ←  PCA + Mahalanobis kNN on standardized features
       ↓                       comparable_index.json, goalie_comparable_index.json
[4] Scouting profile      ←  LLM extraction from public web scouting text
       ↓                       scouting_profiles, scouting_attributes, scouting_tags
[5] Per-game context      ←  PBP-derived facts + manual significance notes
                              examples/<scope>/gameN_context.yaml
```

The **prose-against-data invariant** (`runProseFactCheck()`, see CLAUDE.md §5)
applies at every layer: any sentence in any output must trace to a query
against one of these stores. Prose memory is not a source.

---

## Layer 1 — Counting stats (NST)

### `skater_stats` — on-ice splits
Pooled per `(player_id, season, stype, sit, split)`. `split='oi'` is the
on-ice xGF / xGA / CF / CA / HDCF etc. Driven by `tools/build_goalie_scouting_corpus.py`'s
sister script `legacy/data/ingest.py` for skaters.

- Coverage: 5 seasons (`20212022` → `20252026`), `stype` ∈ {2 (reg), 3 (playoff)},
  `sit` ∈ {`5v5`, `5v4`, `all`}
- Universe: ~1300 distinct skaters per season with ≥ 1 5v5 minute
- Source: NST `playerteams.php?stdoi=oi`

### `skater_individual_stats` — counting stats per player
Per `(player_id, season, stype, sit)`. Goals, assists (1st/2nd/total), shots,
ixG, iCF, iSCF, iHDCF, rush attempts, rebounds created, PIM, penalties drawn,
giveaways, takeaways, hits, hits taken, blocks, faceoffs.

- **Replaces the legacy `split='bio'` path** — that path was pulling
  `stdoi=bio` (biographical info: height/weight/draft) and mapping it
  through the on-ice schema, leaving every individual-stat column NULL.
  See commit `dbf467a` for the fix.
- Coverage: same 5 seasons × 3 sits as `skater_stats`. ~18,500 rows total.
- Source: NST `playerteams.php?stdoi=std`
- Refreshed via `tools/refresh_skater_individual_stats.py`

### `goalie_stats` — goalie splits
Per `(player_id, season, stype, sit)`. Includes raw counting cols (ga, sa,
xga, hdga, hdca) plus computed sv_pct, hd_sv_pct, gsax.

- Coverage: 5 seasons, `sit` ∈ {`5v5`, `all`}, ~135 distinct goalies
- Source: NST `playerteams.php?pos=G`
- Refreshed via `tools/refresh_goalie_stats.py`

### `team_stats` / `team_stats_raw`
Pooled team xG / CF / HDCF — the denominator for "isolated impact" math
(see `lemieux.core.swap_engine`).

---

## Layer 2 — Bio + biometrics (NHL Edge)

### `edge_player_bio` — static bio
Per `player_id`. Height (in), weight (lb), birth date + country, draft year /
round / overall, position, shoots/catches.

- Coverage: **1322 NHL players** (skaters + goalies), 100% height/weight,
  ~1113 with draft picks recorded
- Source: NHL.com player landing endpoint
- Resolution: `tools/refresh_edge_biometrics.py` with **ASCII-folded name
  matching** (handles Dobeš, Slafkovský, etc. — see `_ascii_fold()` in
  `packages/lemieux-connectors/.../nhl_edge/client.py`)

### `edge_player_features` — biometric tracking
Per `(player_id, season, game_type)`. Max skating speed, speed-burst counts
(20-22 mph, 22+ mph), max shot speed, hard-shot counts (80-90 mph, 90+ mph).

- Coverage: **1122 distinct skaters with populated biometric data**
- NHL Edge is **skater-only**; goalies have placeholder rows but no measured
  fields populated.

---

## Layer 3 — Embedded comparable indexes

### `legacy/data/comparable_index.json` — skater kNN
Built by `tools/build_comparable_index.py`. PCA on standardized features,
Mahalanobis-equivalent Euclidean distance in the embedding.

- 1257 skaters indexed
- 24 features: NST 5v5 + 5v4 iso (xGF/60, xGA/60, net), counting rates,
  position one-hot, biometrics, bio
- Output is a fitted PCA + the embedding for kNN queries
- Used by `lemieux.core.comparable.ComparableIndex.find_comparables()`

### `legacy/data/goalie_comparable_index.json` — goalie kNN (v1)
Built by `tools/build_goalie_comparable_index.py`. Same embedding code (it's
feature-agnostic), 10 goalie-specific features:

- Performance: sv_pct, hd_sv_pct, gsax_per60, workload_share, hd_share, gp_growth
- Bio: height, weight, age, draft_overall

- 136 goalies indexed (≥ 200 pooled regular-season TOI)
- **v1 caveat**: doesn't capture stylistic differences (positional vs scrambly,
  glove-side vs blocker-side) — those need PBP-derived rebound rate, post-up
  speed, recovery time. Captures bio + performance shape only.

---

## Layer 4 — Scouting (GenAI extraction)

Four tables, all keyed on player `name`. Built by Claude Sonnet 4.5 extracting
structured JSON from DDG-search snippets of public scouting text.

### `scouting_profiles`
Per player: `extracted_at`, list of source URLs searched.

- **1393 profiles total** (1257 skater + 136 goalie)
- **1023 skaters and 135 goalies have meaningful content** (any attributes
  or tags); the remainder were searched but produced thin results.

### `scouting_attributes`
Continuous attributes on a 1-5 scale with confidence. **1719 rows**.
- Skater vocab: skating, hands, hockey_iq, compete, size, speed, shot,
  vision, defense
- Goalie vocab: positioning, athleticism, glove, blocker, rebound_control,
  puck_handling, mental, size

### `scouting_tags` — controlled-vocabulary archetype tags
**2501 rows.** Each tag carries `confidence`, `source_quote` (verbatim from
source text), and `source_url`.

Skater tags: `warrior`, `playmaker`, `sniper`, `two_way`, `shutdown`,
`agitator`, `enforcer`, `power_forward`, `puck_mover`, `stay_at_home`,
`offensive_d`, `fast`, `slow_start`, `streaky`, `consistent`, `top_six`,
`bottom_six`, `bottom_pair`, `rover`, `specialist_pp`, `specialist_pk`,
`clutch`, `volume_shooter`.

Goalie tags: `positional`, `athletic`, `hybrid`, `butterfly`, `scrambly`,
`calm`, `fiery`, `prospect`, `veteran`, `big_frame`, `undersized_quick`,
`starter`, `backup`, `tandem`, `puck_mover_g`, `big_game`, `streaky`,
`consistent`.

**The provenance rule:** A tag without its `source_quote` and `source_url`
is framework-internal and cannot ship in reader-facing prose. If a docx
quotes the tag, it must quote the source text alongside it.

### `scouting_comparable_mentions`
Explicit "X reminds me of Y" / "the next Y" mentions, with quote + URL.
**125 rows.** Used as weak supervision for v3 contrastive embedding (not yet
shipped) and for narrative comp captions.

### Refresh tooling
- `tools/build_scouting_corpus.py` — full skater corpus, single-query DDG
  search per player, idempotent (skips already-profiled players)
- `tools/build_goalie_scouting_corpus.py` — same shape, goalie vocab
- `tools/refresh_scouting_empties.py` — second-pass with **3-query rich
  search** for profiles that came back empty on the first pass
  (recovers ~38% of empties)

---

## Layer 5 — Per-game context

`examples/<scope>/<gameN>_context.yaml` — canonical fact base for every
analyzed game. **Required reading before any cross-game prose claim.**

Schema documented in CLAUDE.md §4. Generated by `tools/build_game_context.py`
(data-derivable fields) plus manual `significance` and `notes` for marquee
events.

---

## How to query: the snapshot tool

`tools/player_snapshot.py <name>` (also exposed as the `player-snapshot`
Claude skill) renders all five layers for one player in a fixed format:

```
$ python tools/player_snapshot.py "Cole Caufield"

[1] STATIC BIO              — height/weight/birth/draft
[2] NST ON-ICE              — career arc by (season, stype, sit)
[3] EDGE BIOMETRIC          — skating + shot speeds, burst counts
[4] NST INDIVIDUAL          — G/A/SOG/ixG/iCF/iHDCF/etc.
[5] SCOUTING                — attributes + tags + comparable mentions
[6] kNN COMPARABLES         — top 5-7 NHL comps with per-feature drivers
[7] GAME-CONTEXT ANCHORS    — appearances in indexed game contexts
[8] CURRENT-SERIES PBP      — series-direct stats from analyzer JSON
```

Auto-detects skater vs goalie. ASCII-fold partial-match on the name.

---

## Coverage snapshot (as of 2026-04-28)

| Layer | Coverage |
|---|---|
| Skater on-ice (NST) | 5 seasons × 3 sits × 2 stypes |
| Skater individual (NST) | 5 seasons × 3 sits × 2 stypes, 18,500 rows |
| Goalie stats (NST) | 5 seasons × 2 sits × 2 stypes, ~135 goalies |
| Player bios | **1322** (height/weight 100%) |
| Skater biometrics | **1122** distinct skaters with measured data |
| Skater scouting | **1023** with meaningful content (out of 1257 profiles) |
| Goalie scouting | **135** with meaningful content (out of 136 profiles) |
| Skater kNN index | **1257** rows, 24 features |
| Goalie kNN index | **136** rows, 10 features |

---

## What can be redistributed

**Cannot push** the SQLite DB itself: `skater_stats`, `skater_individual_stats`,
`goalie_stats`, `team_stats` contain raw Natural Stat Trick tables.
Per [SOURCES.md](../../SOURCES.md): *"Do NOT redistribute raw tables."*

**Can push** (these are derived artifacts Lemieux owns):

- `legacy/data/comparable_index.json` — PCA-whitened embeddings (not raw
  NST stats, fitted parameters of our model)
- `legacy/data/goalie_comparable_index.json` — same shape
- LLM-extracted scouting tables (`scouting_*`) — these are extractions of
  *public web text* via our own prompts and code
- `edge_player_bio` and `edge_player_features` — NHL.com permits "personal
  / analytic" caching; redistribution is gray-area (cite source)

Use `tools/export_derived_artifacts.py` to dump the publishable subset to a
zip alongside a README pointer for downstream users.
