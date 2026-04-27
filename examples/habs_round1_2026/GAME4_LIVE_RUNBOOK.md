# Game 4 live-period reporting runbook

This is the operational playbook for producing in-game multi-period analytics
during MTL @ TBL Game 4 (game id `2025030124`, 2026-04-26).

## Pipeline overview

```
NHL.com PBP + boxscore (live)
        │
        ▼
  game4_periods.py        ← detects completed periods, computes per-period
        │                   + cumulative + delta JSONs
        ▼
  game4_periods.numbers.json
        │
        ▼
  build_game4_periods_post.js  ← multi-period docx (auto-tags filename
        │                         based on completed periods)
        ▼
  game4_periods_<tag>_2026-04-26_{EN,FR}.docx
        │
        ▼
  tools/push_to_drive.py
        │
        ▼
  shareable Drive links
```

The tag in the filename follows completed periods:

| Completed periods | Filename tag |
|---|---|
| `[1]`        | `game4_periods_p1only_*` |
| `[1, 2]`     | `game4_periods_p1p2_*` |
| `[1, 2, 3]`  | `game4_periods_p1-p3_*` |
| `[1, 2, 3, 4]` (OT) | `game4_periods_p1-p4_*` |

The standalone P1-only renderer (`build_game4_p1_post.js`, output
`game4_p1_*.docx`) is preserved so the original detailed P1 brief isn't lost.
The multi-period renderer adds the cumulative + delta views and grows naturally
period over period.

## After P2 ends — exact commands

Run all three from the repo root with the venv active:

```bash
# 1. Recompute the multi-period JSON (auto-detects P2 is now complete).
.venv/Scripts/python examples/habs_round1_2026/game4_periods.py

# 2. Render the multi-period docx (filename will become game4_periods_p1p2_*).
node examples/habs_round1_2026/build_game4_periods_post.js

# 3. Push EN + FR to Drive.
PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/push_to_drive.py \
    --public --folder "Lemieux Hockey Analytics" --overwrite \
    examples/habs_round1_2026/game4_periods_p1p2_2026-04-26_EN.docx \
    examples/habs_round1_2026/game4_periods_p1p2_2026-04-26_FR.docx
```

Repeat after P3 (filename becomes `game4_periods_p1-p3_*`) and after OT if any.

## What the multi-period docx contains

1. **TLDR** — auto-generated from the data:
   - Score and cumulative 5v5 Corsi/HDCF
   - Cumulative leader (player by composite score)
   - Biggest mover up + biggest mover down (latest period vs previous)
2. **Team totals — per period and cumulative** — one row per completed period
   plus a highlighted cumulative row.
3. **Cumulative ranking — both teams** — top 12 + bottom 5.
4. **Period-over-period movers** — green (up) / red (down) coloring, paired
   columns (P1 stat → P2 stat) for SOG, iHD, G.
5. **Per-period top performers** — top 8 per period for drilling in.
6. **MTL forward lines** — cumulative + per-period totals using the canonical
   `game4_pregame_lineups.yaml`.
7. **Method + caveats**.

## Composite ranking score

```
score = G×3 + A×2 + SOG×0.5 + ind_HD×0.75
      + (missed/blocked attempts)×0.15
      + (hits + blocks)×0.25
      − giveaways×0.5 + takeaways×0.5
```

This is intentionally a transparent linear combination — same recipe used in
the standalone P1 brief. Per-player on-ice Corsi/HDCF is NOT in any
in-game brief because NHL.com's shift chart trails the live PBP and would
mis-attribute. Those metrics belong in the post-game pass when shifts finalize
and NST publishes xG.

## Files in this repo for the live workflow

| File | Purpose |
|---|---|
| `game4_pregame_lineups.yaml`   | Canonical announced lineups |
| `game4_pregame_swap.py` / `.numbers.json` | Pre-game swap-engine projection |
| `build_game4_pregame.js` → `game4_pregame_*.docx` | Pre-game brief |
| `game4_period1_analysis.py` / `.numbers.json` | Standalone P1 analyzer (kept for parity) |
| `build_game4_p1_post.js` → `game4_p1_*.docx` | Standalone P1 brief (with pre-game contradiction analysis) |
| **`game4_periods.py` / `game4_periods.numbers.json`** | Multi-period analyzer (re-run after each period) |
| **`build_game4_periods_post.js` → `game4_periods_<tag>_*.docx`** | Multi-period brief |
