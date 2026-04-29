"""Export the redistributable subset of Lemieux's data artifacts.

What this exports (safe to redistribute):
  - legacy/data/comparable_index.json         skater kNN index (PCA-whitened embeddings)
  - legacy/data/goalie_comparable_index.json  goalie kNN index (v1)
  - scouting_profiles, scouting_attributes, scouting_tags,
    scouting_comparable_mentions               LLM-extracted from public web text

What this DOES NOT export (NST + NHL.com licensing):
  - skater_stats, skater_individual_stats     raw NST per-player tables
  - goalie_stats                              raw NST goalie tables
  - team_stats / team_stats_raw               raw NST team-level tables
  - edge_player_features / edge_player_bio    NHL.com Edge endpoints
                                              (gray-area: cite-only redistribution)

The output is a `lemieux_derived_<date>.zip` with a SOURCES_NOTE.md inside.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/export_derived_artifacts.py \\
        [--out lemieux_derived_2026-04-28.zip]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "legacy" / "data" / "store.sqlite"
INDEX_SKATER = REPO / "legacy" / "data" / "comparable_index.json"
INDEX_GOALIE = REPO / "legacy" / "data" / "goalie_comparable_index.json"

SCOUTING_TABLES = (
    "scouting_profiles", "scouting_attributes",
    "scouting_tags", "scouting_comparable_mentions",
)


def dump_table_csv(con: sqlite3.Connection, table: str) -> bytes:
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for row in con.execute(f"SELECT {','.join(cols)} FROM {table}"):
        w.writerow(row)
    return buf.getvalue().encode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"lemieux_derived_{date.today().isoformat()}.zip")
    args = ap.parse_args()

    out_path = REPO / args.out
    con = sqlite3.connect(DB)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Comparable indexes
        for p in (INDEX_SKATER, INDEX_GOALIE):
            if p.exists():
                z.write(p, arcname=f"comparable/{p.name}")
                print(f"  + comparable/{p.name}  ({p.stat().st_size:,} bytes)")

        # 2. Scouting tables as CSVs
        for tbl in SCOUTING_TABLES:
            try:
                data = dump_table_csv(con, tbl)
                z.writestr(f"scouting/{tbl}.csv", data)
                count = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                print(f"  + scouting/{tbl}.csv  ({count:,} rows, {len(data):,} bytes)")
            except sqlite3.OperationalError as e:
                print(f"  ! skipped {tbl}: {e}")

        # 3. Schema dump (no data, for downstream users to recreate locally)
        schema_sql = []
        for r in con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name"
        ):
            schema_sql.append(r[0] + ";")
        z.writestr("schema/store_schema.sql", "\n".join(schema_sql))
        print(f"  + schema/store_schema.sql  ({len(schema_sql)} CREATE TABLE statements)")

        # 4. Sources note
        note = """\
# Lemieux derived artifacts — redistribution note

This zip contains the publishable subset of Lemieux's data layer. See
[SOURCES.md](https://github.com/.../SOURCES.md) and
[docs/en/data-model.md](https://github.com/.../docs/en/data-model.md) for the
full posture.

## What's in here

### `comparable/`

Fitted kNN comparable indexes — PCA-whitened embeddings + fitted parameters,
not raw counting stats. These are the model itself; redistributing them is
how Lemieux is meant to be shared.

- `comparable_index.json`         skater kNN, 1257 rows × 24 features
- `goalie_comparable_index.json`  goalie kNN (v1), 136 rows × 10 features

Loadable via `lemieux.core.comparable.ComparableIndex.load(path)`.

### `scouting/`

LLM-extracted scouting profiles. Source text is public web scouting / beat
coverage; extraction is via DDG search + Claude Sonnet 4.5 with structured
JSON output. Every tag carries its verbatim source quote and source URL —
**do not strip provenance when republishing**.

- `scouting_profiles.csv`              one row per (player, position) extracted
- `scouting_attributes.csv`            continuous 1-5 attributes with confidence
- `scouting_tags.csv`                  archetype tags with source_quote + source_url
- `scouting_comparable_mentions.csv`   "X reminds me of Y" mentions

### `schema/`

`store_schema.sql` — full SQLite schema for `legacy/data/store.sqlite`.
Use this to recreate the DB locally; populate the NST-derived tables
(`skater_stats`, `skater_individual_stats`, `goalie_stats`, `team_stats`)
yourself with your own NST access key via the refresh tools in `tools/`.

## What's NOT in here, and why

- **`skater_stats`, `skater_individual_stats`, `goalie_stats`,
  `team_stats`** — raw Natural Stat Trick tables. NST's terms prohibit
  redistribution of raw tables. Bring your own NST key (free, request via
  an NST profile); rebuild locally with `tools/refresh_skater_individual_stats.py`,
  `tools/refresh_goalie_stats.py`, etc.

- **`edge_player_bio`, `edge_player_features`** — NHL.com Edge endpoints.
  NHL.com's terms permit personal/analytic caching but redistribution is
  gray-area. Repopulate with `tools/refresh_edge_biometrics.py`.

## License

- Code: MIT
- This data: same MIT terms apply to the *extraction work* (the model fits,
  the prompt-engineered tag schema). Each tag's source_quote remains the
  property of its source publication; cite when quoting.
"""
        z.writestr("README.md", note)
        print(f"  + README.md  ({len(note)} bytes)")

    print()
    print(f"Wrote {out_path}  ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
