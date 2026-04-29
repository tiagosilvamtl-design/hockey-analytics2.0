"""Second-pass refresh for scouting profiles that came back empty.

The main `build_scouting_corpus.py` does ONE DDG query per player. Some
recognizable NHLers (Heiskanen, Orlov, Gavrikov) come back with 0 attrs +
0 tags because the single-query budget produced thin results. This tool
re-runs JUST those empties using THREE query variants:

  1. "<name> NHL <position> scouting style of play"   (the original)
  2. "<name> NHL player profile breakdown"
  3. "<name> hockey reminds me of OR similar to OR comparable"

Hits are merged + deduped by URL, then handed to the same Claude
extraction + persistence path. The replacement profile overwrites the
empty one via existing `upsert_profile`.

Idempotent: a profile that comes back empty AGAIN stays empty (same row
overwritten). Safe to run multiple times.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/refresh_scouting_empties.py
        [--max-players N] [--rate-limit-s 1.0] [--dry-run]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

# Reuse everything from the main builder.
from tools.build_scouting_corpus import (  # type: ignore
    DB, _import_runtime_deps, _load_env,
    extract_profile_via_claude, persist_profile,
)

_load_env()


def find_empty_profiles(con: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return [(name, position), ...] for skater profiles with no signal."""
    rows = con.execute("""
        SELECT p.name, p.position
        FROM scouting_profiles p
        LEFT JOIN scouting_attributes a ON a.name = p.name
        LEFT JOIN scouting_tags t ON t.name = p.name
        WHERE (p.position IS NULL OR p.position != 'G')
        GROUP BY p.name, p.position
        HAVING COUNT(DISTINCT a.attribute) = 0
           AND COUNT(DISTINCT t.tag) = 0
        ORDER BY p.name
    """).fetchall()
    return [(r[0], r[1] or "") for r in rows]


def rich_search(name: str, position: str, ddgs_client) -> list[dict]:
    """Three query variants, deduped by URL, capped at 7 hits."""
    pos_word = {"C": "centre", "L": "left winger", "R": "right winger",
                "D": "defenseman"}.get((position or "").upper(), "hockey player")
    queries = [
        f"{name} NHL {pos_word} scouting style of play",
        f"{name} NHL player profile breakdown",
        f"{name} hockey reminds me of OR similar to OR comparable",
    ]
    seen_urls: set[str] = set()
    merged: list[dict] = []
    for q in queries:
        try:
            results = list(ddgs_client.text(q, max_results=4))
        except Exception as e:
            print(f"    [search error on '{q[:40]}...': {e}]")
            continue
        for r in results:
            url = r.get("href", "") or r.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(r)
        if len(merged) >= 7:
            break
    return merged[:7]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-players", type=int, default=None)
    ap.add_argument("--rate-limit-s", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(DB, timeout=60)
    targets = find_empty_profiles(con)
    print(f"Empty skater profiles: {len(targets)}")
    if args.max_players:
        targets = targets[: args.max_players]
        print(f"  capped to --max-players={args.max_players}")
    if not targets:
        print("Nothing to do.")
        return

    if args.dry_run:
        print("\n--dry-run: would re-search these players (top 20 shown):")
        for name, pos in targets[:20]:
            print(f"  {name:30s} ({pos})")
        if len(targets) > 20:
            print(f"  ...and {len(targets) - 20} more")
        return

    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    _import_runtime_deps()
    from tools.build_scouting_corpus import anthropic, ddgs, html2text  # populated by import
    h2t = html2text.HTML2Text(); h2t.ignore_links = True; h2t.ignore_images = True
    anthropic_client = anthropic.Anthropic()
    ddgs_client = ddgs()

    print(f"\nRe-processing {len(targets)} empties. ETA: ~{len(targets) * (args.rate_limit_s + 6) / 60:.0f} min.")
    n_ok = n_still_empty = n_err = 0
    for i, (name, pos) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {name} ({pos})", flush=True)
        snippets = rich_search(name, pos, ddgs_client)
        if not snippets:
            print(f"    [no snippets across 3 queries]")
            n_still_empty += 1
            time.sleep(args.rate_limit_s)
            continue
        extracted = extract_profile_via_claude(name, pos, snippets, anthropic_client)
        if not extracted:
            n_err += 1
            time.sleep(args.rate_limit_s)
            continue
        urls = [s.get("href", "") for s in snippets if s.get("href")]
        try:
            persist_profile(con, name, pos, extracted, urls)
            tags_count = len(extracted.get("tags", []))
            attrs_count = len(extracted.get("attributes", []))
            if attrs_count == 0 and tags_count == 0:
                n_still_empty += 1
                marker = "still empty"
            else:
                n_ok += 1
                marker = "RECOVERED"
            print(f"    ✓ {attrs_count} attrs, {tags_count} tags  [{marker}]")
        except Exception as e:
            print(f"    [persist error: {e}]")
            n_err += 1
        time.sleep(args.rate_limit_s)

        if i % 20 == 0:
            print(f"  --- checkpoint: {n_ok} recovered, {n_still_empty} still empty, {n_err} errored ---")

    con.close()
    print(f"\nDone. {n_ok} recovered, {n_still_empty} still empty, {n_err} errored.")


if __name__ == "__main__":
    main()
