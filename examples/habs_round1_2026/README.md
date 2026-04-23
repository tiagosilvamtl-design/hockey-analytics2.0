# Example: Montreal Canadiens — 2026 Playoffs, Round 1 report

This directory is the canonical worked example for Lemieux. It shows the full pipeline:

1. **Ingest**: pull data from NST + NHL.com for the MTL vs. TBL series.
2. **Analyze**: compute swap scenarios, rank positive/negative contributors, build optimal lineup, slice Slafkovský's shifts by period.
3. **Render**: produce a publishable Word document + JSON audit trail.

## Files

- `habs_round1_2026.docx` — the final published artifact
- `habs_round1_2026.numbers.json` — every number cited in the docx, for audit
- `habs_round1_2026.md` — pandoc-converted markdown mirror of the docx

The orchestrator script that produced these artifacts is currently at `legacy/analytics/habs_round1.py` and will be migrated onto the MCP tool surface in a follow-up release. See [`legacy/README.md`](../../legacy/README.md).

## Reproducing (v0.1, using the legacy orchestrator)

```bash
# 1. Make sure your NST key is in .env at the repo root
# 2. Ingest data (hits NST politely, caches locally)
python -c "from legacy.data.nst_client import NstClient; from legacy.data.ingest import refresh_team_stats, refresh_skater_stats; c = NstClient(); [refresh_team_stats(c, s, st, sit) for s in ['20252026','20242025'] for st in [2,3] for sit in ['5v5','5v4','all']]"

# 3. Compute numbers
python -m legacy.analytics.habs_round1

# 4. Render docx (requires node + docx npm package)
node legacy/reports/build_habs_round1_2026.js
```

## Reproducing (v0.2+, via MCP)

Once the migration is complete, the same artifact will be reproducible from Claude Code with a single prompt invoking the `draft-game-post` skill, which composes `query_team_stats`, `rank_players`, `project_swap_scenario`, and `fetch_game_detail` via the MCP server.

## Why this example matters

It demonstrates that every specific claim in the Word document (e.g., "Slafkovský had 5 SOG in bucket A, 0 in bucket B") traces back to a deterministic SQL + NHL-API query. If a reader disputes a number, we can point them at the one function that produced it.
