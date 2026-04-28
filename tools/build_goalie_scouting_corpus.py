"""GenAI scouting corpus build for NHL goalies.

Parallel to `build_scouting_corpus.py` but with goalie-specific feature
vocabulary, search query template, and SYSTEM_PROMPT. Persists to the same
`scouting_profiles` / `scouting_attributes` / `scouting_tags` tables, with
position='G' so a tag-cohort split-study still works generically.

Goalie continuous attributes (1-5):
  positioning, athleticism, glove, blocker, rebound_control, puck_handling,
  mental, size

Goalie archetype tags:
  positional, athletic, hybrid, butterfly, scrambly, calm, fiery,
  prospect, veteran, big_frame, undersized_quick, starter, backup, tandem,
  puck_mover_g, big_game, streaky, consistent

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_goalie_scouting_corpus.py
        [--min-toi 500] [--rate-limit-s 1.0] [--max-players 20]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

try:
    from anthropic import Anthropic
    from ddgs import DDGS
    import html2text as _html2text
    import requests as _requests
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"Missing dep: {e}; ensure .venv has anthropic, ddgs, html2text, python-dotenv")
    raise

DB = REPO / "legacy" / "data" / "store.sqlite"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")

SYSTEM_PROMPT = """You are a hockey-analytics scouting-extraction assistant
specialized in NHL GOALTENDERS. Given web-search snippets about a goalie,
extract a structured profile per the schema below. Be conservative: prefer
NULL or low-confidence over invented attributes. Quote source text supporting
each tag.

OUTPUT: a single JSON object, no prose around it.

{
  "attributes": [
    {"name": "<one of: positioning, athleticism, glove, blocker, rebound_control,
              puck_handling, mental, size>",
     "value": <float 1.0-5.0>,
     "confidence": <float 0.0-1.0>,
     "source_count": <int, how many passages supported this score>}
  ],
  "tags": [
    {"tag": "<one of: positional, athletic, hybrid, butterfly, scrambly, calm,
              fiery, prospect, veteran, big_frame, undersized_quick, starter,
              backup, tandem, puck_mover_g, big_game, streaky, consistent>",
     "confidence": <float 0.0-1.0>,
     "source_quote": "<verbatim snippet>",
     "source_url": "<URL>"}
  ],
  "comp_mentions": [
    {"comp_name": "<goalie name being compared to>",
     "source_quote": "<verbatim 'reminds of/compares to' snippet>",
     "source_url": "<URL>",
     "polarity": "<style|trajectory|both>"}
  ]
}

Rules:
- Tags MUST be supported by quoted text. No tag without a source_quote.
- Confidence:
    0.9-1.0: explicit ("Hellebuyck is the prototypical positional goalie")
    0.7-0.85: strongly implied across multiple passages
    0.5-0.65: directionally supported, single source
- Goalie-specific guidance:
    "positional" = relies on angles, square positioning, not flashy
    "athletic" = makes saves with reach, post-up speed, recovery
    "hybrid" = both schools — explicit in source
    "butterfly" / "scrambly" — body-style descriptors from scouting language
    "starter" = clear #1 on his team in description
    "tandem" / "backup" = explicit team-role language
    "puck_mover_g" = praised for puck-handling out of the net
    "big_game" / "clutch" = quotes about playoff performance
- Continuous attributes only when at least one supporting passage exists.
- comp_mentions only for explicit "X reminds me of Y" / "next Y" mentions.
- Output VALID JSON only — no markdown fences, no commentary.
"""


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def gather_goalie_targets(con: sqlite3.Connection, *, min_toi: float, max_n: int | None,
                          force_refresh: bool) -> list[tuple[str, str]]:
    """Return list of (name, 'G') for goalies with at least min_toi pooled across the window."""
    rows = con.execute(
        """
        SELECT name, SUM(toi) AS total_toi
        FROM goalie_stats
        WHERE sit = 'all' AND stype = 2
        GROUP BY name HAVING total_toi >= ?
        ORDER BY total_toi DESC
        """,
        (min_toi,),
    ).fetchall()

    if not force_refresh:
        existing = {(r[0], r[1] or "") for r in con.execute(
            "SELECT name, position FROM scouting_profiles WHERE position='G'"
        )}
    else:
        existing = set()

    out: list[tuple[str, str]] = []
    for name, _ in rows:
        if (name, "G") in existing:
            continue
        out.append((name, "G"))
        if max_n and len(out) >= max_n:
            break
    return out


def search_web(name: str, ddgs_client) -> list[dict]:
    query = f"{name} NHL goalie scouting style of play"
    try:
        results = list(ddgs_client.text(query, max_results=5))
    except Exception as e:
        print(f"    [search error: {e}]")
        return []
    return results


def extract_profile_via_claude(name: str, snippets: list[dict],
                               anthropic_client) -> dict | None:
    if not snippets:
        return None
    parts = [f"Goalie: {name}\n\nSearch snippets:\n"]
    for i, s in enumerate(snippets[:5], 1):
        parts.append(f"[{i}] {s.get('title','')} ({s.get('href','')})\n{s.get('body','')}\n")
    user_msg = "\n".join(parts)

    try:
        resp = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        print(f"    [Claude API error: {e}]")
        return None
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    [JSON parse error: {e}; first 200 chars: {text[:200]}]")
        return None


def persist_profile(con: sqlite3.Connection, name: str, extracted: dict,
                    source_urls: list[str]) -> None:
    from lemieux.core import (
        ComparableMention, ContinuousAttribute, PlayerScoutingProfile,
        TagAssertion, upsert_profile,
    )
    profile = PlayerScoutingProfile(
        name=name, position="G", extracted_at=TODAY, sources=source_urls,
        attributes=[
            ContinuousAttribute(
                name=a.get("name", ""),
                value=float(a.get("value", 0)),
                confidence=float(a.get("confidence", 0)),
                source_count=int(a.get("source_count", 1)),
            )
            for a in extracted.get("attributes", [])
            if a.get("name")
        ],
        tags=[
            TagAssertion(
                tag=t.get("tag", ""),
                confidence=float(t.get("confidence", 0)),
                source_quote=t.get("source_quote", "")[:1000],
                source_url=t.get("source_url", "")[:500],
            )
            for t in extracted.get("tags", [])
            if t.get("tag")
        ],
        comp_mentions=[
            ComparableMention(
                comp_name=m.get("comp_name", ""),
                source_quote=m.get("source_quote", "")[:1000],
                source_url=m.get("source_url", "")[:500],
                polarity=m.get("polarity", "style"),
            )
            for m in extracted.get("comp_mentions", [])
            if m.get("comp_name")
        ],
    )
    upsert_profile(con, profile)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-players", type=int, default=None)
    ap.add_argument("--min-toi", type=float, default=500.0,
                    help="Min pooled regular-season TOI to be eligible")
    ap.add_argument("--rate-limit-s", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-refresh", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(DB, timeout=60)
    targets = gather_goalie_targets(
        con, min_toi=args.min_toi, max_n=args.max_players,
        force_refresh=args.force_refresh,
    )
    print(f"Eligible goalies to process: {len(targets)}")
    if args.dry_run:
        print("Dry-run: would process the above; estimated cost ~$0.04/goalie")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in .env")
        return
    anthropic_client = Anthropic(api_key=api_key)
    ddgs_client = DDGS()

    n_ok = n_skip = n_err = 0
    for i, (name, _) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {name} (G)")
        snippets = search_web(name, ddgs_client)
        if not snippets:
            print("    skipped (no search results)")
            n_skip += 1
            continue
        extracted = extract_profile_via_claude(name, snippets, anthropic_client)
        if not extracted:
            n_err += 1
            continue
        urls = [s.get("href", "") for s in snippets if s.get("href")]
        persist_profile(con, name, extracted, urls)
        n_attrs = len(extracted.get("attributes", []))
        n_tags = len(extracted.get("tags", []))
        print(f"    OK  {n_attrs} attrs, {n_tags} tags persisted")
        n_ok += 1
        if i % 10 == 0:
            con.commit()
            print(f"  --- checkpoint: {n_ok} ok, {n_skip} skipped, {n_err} errored ---")
        time.sleep(args.rate_limit_s)

    con.commit()
    con.close()
    print(f"\nDone. {n_ok} goalies persisted, {n_skip} skipped (no search results), {n_err} errored.")


if __name__ == "__main__":
    main()
