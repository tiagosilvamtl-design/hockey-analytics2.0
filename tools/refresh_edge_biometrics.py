"""Populate NHL Edge biometric features for the comparable cohort.

Scoped for an overnight run: targets the 5 demo players' kNN cohorts (top
~10 each) plus the full Habs roster — about 50–80 players total. Pulls
their Edge skating-speed and shot-speed details across the 5-year window,
aggregates per (player, season, game_type), and persists to a small SQLite
table for the comparable index to consume.

The full 1257-player league enrichment is a separate batch job (longer
runtime) — not run automatically. This tool is the targeted-cohort
version that supports the demo + per-game reports.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/refresh_edge_biometrics.py
        [--names-from-index] [--explicit "Brendan Gallagher,Kirby Dach,..."]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-connectors" / "src"))
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

import requests

from lemieux.connectors.nhl_edge import NhlEdgeClient, resolve_player_id

DB_PATH = REPO / "legacy" / "data" / "store.sqlite"
INDEX_PATH = REPO / "legacy" / "data" / "comparable_index.json"

EDGE_SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")
EDGE_GAME_TYPES = (2, 3)  # regular, playoffs


HABS_ROSTER = [
    "Brendan Gallagher", "Kirby Dach", "Cole Caufield", "Nick Suzuki", "Juraj Slafkovský",
    "Lane Hutson", "Mike Matheson", "Kaiden Guhle", "Alexandre Carrier", "Noah Dobson",
    "Jayden Struble", "Arber Xhekaj", "Zachary Bolduc", "Alex Newhook", "Oliver Kapanen",
    "Ivan Demidov", "Phillip Danault", "Josh Anderson", "Jake Evans", "Alexandre Texier",
    "Jakub Dobeš",
]


def init_edge_table(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS edge_player_features (
            player_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            season TEXT NOT NULL,
            game_type INTEGER NOT NULL,
            max_skating_speed_mph REAL,
            skating_burst_count_22plus INTEGER DEFAULT 0,
            skating_burst_count_20to22 INTEGER DEFAULT 0,
            max_shot_speed_mph REAL,
            hard_shot_count_90plus INTEGER DEFAULT 0,
            hard_shot_count_80to90 INTEGER DEFAULT 0,
            fetched_at TEXT,
            PRIMARY KEY (player_id, season, game_type)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS edge_player_id_resolution (
            name TEXT NOT NULL,
            position TEXT NOT NULL DEFAULT '',
            player_id INTEGER,
            resolved_at TEXT,
            PRIMARY KEY (name, position)
        )
    """)
    con.commit()


def get_target_names(con: sqlite3.Connection, names_from_index: bool, explicit: list[str]) -> list[tuple[str, str]]:
    """Return list of (name, position) tuples to enrich."""
    out: dict[tuple[str, str], None] = {}
    # Always include the Habs roster (positions inferred from skater_stats)
    for name in HABS_ROSTER + explicit:
        rows = con.execute(
            "SELECT DISTINCT position FROM skater_stats WHERE name = ?", (name,)
        ).fetchall()
        if rows:
            for r in rows:
                out[(name, r[0] or "")] = None
        else:
            out[(name, "")] = None

    if names_from_index and INDEX_PATH.exists():
        idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        # Top-5 demo targets' top-10 comps each
        demo_targets = ["Brendan Gallagher", "Cole Caufield", "Nick Suzuki",
                        "Zachary Bolduc", "Lane Hutson", "Kirby Dach"]
        # Quick: for each target, find row, get euclidean nearest neighbors via the embedding
        import numpy as np
        embedding = np.asarray(idx["embedding"], dtype=np.float64)
        row_meta = idx["row_meta"]
        names_lower = [(m.get("name") or "").strip().lower() for m in row_meta]
        for target in demo_targets:
            try:
                idx_t = names_lower.index(target.strip().lower())
            except ValueError:
                continue
            target_pos = row_meta[idx_t].get("position")
            diffs = embedding - embedding[idx_t][None, :]
            dists = (diffs ** 2).sum(axis=1) ** 0.5
            order = dists.argsort()
            picked = 0
            for i in order:
                if i == idx_t:
                    continue
                m = row_meta[int(i)]
                if (m.get("position") or "") != (target_pos or ""):
                    continue
                if (m.get("pooled_toi_5v5") or 0) < 200:
                    continue
                out[(m["name"], m.get("position") or "")] = None
                picked += 1
                if picked >= 10:
                    break
    return list(out.keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names-from-index", action="store_true",
                    help="Add the kNN top-10 cohorts of the 5 demo targets to the enrichment list")
    ap.add_argument("--explicit", default="",
                    help="Comma-separated extra names to include")
    ap.add_argument("--rate-limit-s", type=float, default=0.6)
    args = ap.parse_args()

    explicit = [s.strip() for s in args.explicit.split(",") if s.strip()]
    con = sqlite3.connect(DB_PATH)
    init_edge_table(con)
    targets = get_target_names(con, args.names_from_index, explicit)
    print(f"Enriching Edge data for {len(targets)} (name, position) pairs")
    print(f"Seasons: {EDGE_SEASONS}; game types: {EDGE_GAME_TYPES}")

    edge = NhlEdgeClient(rate_limit_s=args.rate_limit_s)
    resolver_session = requests.Session()
    resolver_session.headers.update({"User-Agent": "lemieux-edge-connector/0.1"})

    n_resolved = 0; n_unresolved = 0; n_seasons_pulled = 0; n_with_data = 0

    for name, position in targets:
        # Check cache
        row = con.execute(
            "SELECT player_id FROM edge_player_id_resolution WHERE name = ? AND position = ?",
            (name, position or "")
        ).fetchone()
        if row and row[0]:
            pid = int(row[0])
        else:
            pid = resolve_player_id(name, position_hint=position or None, session=resolver_session)
            con.execute(
                "INSERT OR REPLACE INTO edge_player_id_resolution (name, position, player_id, resolved_at) VALUES (?, ?, ?, datetime('now'))",
                (name, position or "", pid),
            )
            con.commit()
            time.sleep(args.rate_limit_s)

        if not pid:
            n_unresolved += 1
            continue
        n_resolved += 1

        for season in EDGE_SEASONS:
            for gt in EDGE_GAME_TYPES:
                feats = edge.fetch_player_features(pid, name, season, gt)
                n_seasons_pulled += 1
                if feats.max_skating_speed_mph is not None or feats.max_shot_speed_mph is not None:
                    n_with_data += 1
                con.execute(
                    """
                    INSERT OR REPLACE INTO edge_player_features
                    (player_id, name, season, game_type,
                     max_skating_speed_mph, skating_burst_count_22plus, skating_burst_count_20to22,
                     max_shot_speed_mph, hard_shot_count_90plus, hard_shot_count_80to90,
                     fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (pid, name, season, gt,
                     feats.max_skating_speed_mph, feats.skating_burst_count_22plus, feats.skating_burst_count_20to22,
                     feats.max_shot_speed_mph, feats.hard_shot_count_90plus, feats.hard_shot_count_80to90),
                )
        con.commit()
        if (n_resolved % 10) == 0:
            print(f"  ... {n_resolved} resolved, {n_seasons_pulled} season-rows pulled, {n_with_data} with data")

    con.commit()
    con.close()
    print(f"\nResolved {n_resolved} of {len(targets)} target names. Unresolved: {n_unresolved}")
    print(f"Season-rows fetched: {n_seasons_pulled}. With data: {n_with_data}")
    print(f"\nNHL Edge features persisted to legacy/data/store.sqlite -> edge_player_features")


if __name__ == "__main__":
    main()
