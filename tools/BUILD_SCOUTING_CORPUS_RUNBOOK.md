# Running the full scouting-corpus build

This is the step-by-step for kicking off the full GenAI scouting corpus
build over the 1 257-player NHL cohort. The tool that does the work is
`tools/build_scouting_corpus.py`.

## Pre-flight (one-time)

1. **Get an Anthropic API key.** https://console.anthropic.com → API Keys → Create.
2. **Add it to `.env` at the repo root**:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. **(Already done in the spike)**: required Python deps installed
   (`anthropic`, `ddgs`, `html2text`).
4. **Optional sanity check**: dry-run shows what would happen + cost estimate
   without calling any APIs:
   ```bash
   PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_scouting_corpus.py --dry-run
   ```

## Recommended staged run

Don't kick off all 1 257 at once. Stage:

### Stage 1 — top 50 players, sanity check (~$2, ~5 min)

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_scouting_corpus.py \
    --max-players 50 --rate-limit-s 1.0
```

Inspect a few of the persisted profiles:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
import sys; sys.path.insert(0, 'packages/lemieux-core/src')
import sqlite3
from lemieux.core import list_player_tags, list_known_tags
con = sqlite3.connect('legacy/data/store.sqlite')
print('Top tags after stage-1:')
for tag, n in list_known_tags(con, min_confidence=0.6)[:15]:
    print(f'  {n:3d}  {tag}')
"
```

If the tags look reasonable and the warriors / playmakers / snipers are
sensibly identified, continue to stage 2. If extraction quality is poor,
inspect a profile and adjust the `SYSTEM_PROMPT` in the tool before
scaling.

### Stage 2 — top 250 (forwards + top D), ~$10, ~25 min

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_scouting_corpus.py \
    --max-players 250 --min-toi 800 --rate-limit-s 1.0
```

This brings the corpus to a publishable cohort size for most archetype tags
(warrior, playmaker, sniper, two_way will each have 20-50 players).

### Stage 3 — full league, ~$30, ~2 hours

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_scouting_corpus.py \
    --min-toi 200 --rate-limit-s 1.0
```

The tool is idempotent + resumable — already-extracted players are skipped.
If you stop and restart, it picks up where it left off.

## Cost / time reference

Cost is dominated by Claude Sonnet 4.5 output tokens. Rough budget:

| Players | Input tokens | Output tokens | Est. cost | Wall time |
|---|---|---|---|---|
| 50  | 250K  | 75K  | $1.90  | 5 min |
| 250 | 1.25M | 375K | $9.40  | 25 min |
| 500 | 2.5M  | 750K | $19    | 50 min |
| 1257 (full) | 6.3M | 1.9M | $40    | 2 hours |

The cost grows with the corpus, but tag-cohort N grows with it too — and
N is what makes the Phase 3 split-studies publishable. There's a real
ROI inflection around ~250-500 players.

## What the tool persists

For each player processed:
- One row in `scouting_profiles` (name, position, extracted_at, sources)
- 0-9 rows in `scouting_attributes` (continuous attributes 1-5 with
  confidence and source_count)
- 0-many rows in `scouting_tags` (archetype tags with quote + URL provenance)
- 0-many rows in `scouting_comparable_mentions` ("X reminds me of Y" extractions)

Re-running with `--force-refresh` wipes + re-extracts the targeted players.

## After running: what to do

1. **Re-run the warrior split-study** — it should now have N=20-50 instead
   of N=8, with a much tighter CI.
2. **Re-run the Gallagher demo** — Layer 3's CI will now reflect the larger
   warrior cohort.
3. **Audit a sample of profiles** (e.g. 20 random) — check that the LLM
   extraction is producing tags consistent with the source quotes.
4. **Wire `build_cohort_stabilized_impact()` into `propose-swap-scenario`** —
   the engine is now ready to feed real game-post swap callouts.

## Troubleshooting

- **Search returns 0 hits for some players**: skipped, no harm done. They
  may be obscure depth players whose name is ambiguous; can be retried
  with a more specific query in a follow-up pass.
- **JSON parse errors**: Claude occasionally wraps the JSON in prose
  despite the strict prompt. The tool strips code fences but doesn't
  retry — those players show up as `errored` in the run summary and can
  be re-processed with `--force-refresh` after a prompt tweak.
- **Rate-limit hits**: bump `--rate-limit-s` to 2.0 or higher.
- **Cost overrun**: cap with `--max-players` and inspect spend before
  going further.
