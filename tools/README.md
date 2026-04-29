# `tools/` — stand-alone scripts

Scripts that drive Lemieux's data layer or push artifacts. Grouped by what they do.

## Index

| Script | Purpose |
|---|---|
| **Data refresh — populate the SQLite store** | |
| `refresh_skater_individual_stats.py` | NST `stdoi=std` → `skater_individual_stats` (G/A/SOG/ixG/iCF/iHDCF/etc., 5 seasons × 3 sits × 2 stypes) |
| `refresh_goalie_stats.py` | NST `pos=G` → `goalie_stats` with raw counting cols (ga, sa, xga, hdga, hdca) |
| `refresh_edge_biometrics.py` | NHL Edge skating + shot speeds + bio. ASCII-fold name resolver. |
| **Comparable engine** | |
| `build_comparable_index.py` | Fit skater kNN: 1257 rows × 24 features (PCA + Mahalanobis-equivalent) |
| `build_goalie_comparable_index.py` | Fit goalie kNN v1: 136 rows × 10 features |
| `backtest_comparable_aging.py` | Held-out aging-curve backtest for the skater index |
| `score_calibration.py` | Calibrate the CARMELO-style 0-100 score curve |
| **Scouting (LLM extraction)** | |
| `build_scouting_corpus.py` | DDG search + Sonnet 4.5 → skater profiles, 1023 with content |
| `build_goalie_scouting_corpus.py` | Same shape, goalie vocab — 135 with content |
| `refresh_scouting_empties.py` | Second-pass 3-query rich search for empty profiles (~38% recovery) |
| `seed_scouting_corpus.py` | Hand-seed initial high-confidence rows for QC anchors |
| `qc_scouting_corpus.py` | Eyeball-check tag cohorts ("warriors", "snipers", etc.) |
| **Reports + briefs** | |
| `build_game_context.py` | Per-game `<gameN>_context.yaml` from NHL.com PBP + boxscore |
| `render_cohort_study.py` | Render a tag-cohort split-study to docx |
| `player_snapshot.py` | 5-layer data-model dump for any player (auto-detect skater vs goalie) |
| `dump_suzuki.py` | Legacy worked example — predates `player_snapshot.py` |
| **Distribution** | |
| `push_to_drive.py` | Portable Google Drive uploader (BYO OAuth, public-link mode) |
| `export_derived_artifacts.py` | Zip the redistributable subset (kNN indexes + scouting tables); see [SOURCES.md](../SOURCES.md) for what cannot be redistributed |

## `push_to_drive.py` — upload artifacts to Google Drive

Portable Google Drive uploader for Lemieux's docx / json / yaml outputs. Doesn't depend on Claude.ai's MCP integrations or any sandbox; you bring your own Google OAuth credentials once and the script caches a refreshable token after that.

### One-time setup (≈ 5 min)

1. Go to <https://console.cloud.google.com/>, create or pick a project.
2. **APIs & Services → Library** → search "Google Drive API" → **Enable**.
3. **APIs & Services → Credentials** → **Create Credentials → OAuth client ID**.
   - Application type: **Desktop app**.
   - Name: anything (e.g., "Lemieux uploader").
   - Click **Download JSON** when the dialog shows the new credentials.
4. Save the downloaded file as `~/.lemieux/google-credentials.json` (Windows: `%USERPROFILE%\.lemieux\google-credentials.json`).
   - Or anywhere you like, then set `LEMIEUX_GOOGLE_CREDS=/full/path/to/credentials.json` in your shell.
5. Install Python deps:
   ```bash
   pip install google-api-python-client google-auth-oauthlib
   ```

That's it. The first run opens a browser for consent. Subsequent runs are silent — the cached token at `~/.lemieux/google-token.json` is refreshed automatically.

### Usage

```bash
# Upload the Game 3 artifacts to "Lemieux Hockey Analytics"
python tools/push_to_drive.py examples/habs_round1_2026/game3_post_2026-04-25_*.docx

# Pick a different folder
python tools/push_to_drive.py --folder "Habs Round 1 2026" examples/habs_round1_2026/*.{docx,json,yaml}

# Replace existing files instead of creating duplicates
python tools/push_to_drive.py --overwrite examples/habs_round1_2026/game3_post_2026-04-25_EN_v2.docx

# Just see what would happen
python tools/push_to_drive.py --dry-run examples/habs_round1_2026/*.docx
```

Output looks like:

```
📁 Drive folder: 'Lemieux Hockey Analytics'  (id: 1ABC...XYZ)
   https://drive.google.com/drive/folders/1ABC...XYZ

   ✓ [uploaded      ] game3_post_2026-04-25_EN_v2.docx     https://drive.google.com/file/d/...
   ✓ [uploaded      ] game3_post_2026-04-25_FR_v2.docx     https://drive.google.com/file/d/...
   ↻ [updated       ] game3_analysis.numbers.json          https://drive.google.com/file/d/...
   · [exists        ] game3_usage_observations.yaml        https://drive.google.com/file/d/...
```

### What scope does this need?

`https://www.googleapis.com/auth/drive.file` — write to files this app creates.

The script can't see or modify any of your existing Drive files outside what it has uploaded itself. If you want broader access (e.g., uploading into a folder you manually created), that folder will only be discoverable to the script if it was created via this script. To work around: let the script create the folder the first time, then use it for all subsequent uploads.

### Why not use the Claude.ai Google Drive MCP?

It's also a fine option when scopes allow it, but it requires Claude.ai-side connector configuration that the local Claude Code session doesn't always have, and it depends on the MCP integration being enabled in your Claude.ai account. This script works regardless and lives in the repo so any contributor can use it.

### Troubleshooting

- **"Missing Google API client"** → `pip install google-api-python-client google-auth-oauthlib`
- **"No Google OAuth credentials at ..."** → re-run the one-time setup above; the JSON file is the missing piece.
- **`access_denied` in the browser flow** → Your account is in a Google Workspace that disallows non-verified OAuth apps. Either ask your admin to allow it, or use a personal Google account.
- **Upload appears as a Google Doc instead of a Word file** → fixed in this script (we use the docx MIME type explicitly), but if you see it on an older run, just re-upload with `--overwrite`.
