"""Automated GenAI scouting corpus builder.

Iterates over players in the comparable index, does:
  1. DuckDuckGo search for "<name> hockey scouting style of play comparable"
  2. Fetch top ~2 results, extract main text via html2text
  3. Call Claude (Anthropic API) with a structured-output JSON schema for
     PlayerScoutingProfile extraction
  4. Persist via lemieux.core.scouting.upsert_profile

Idempotent + resumable: skips any player already in scouting_profiles
unless --force-refresh is passed.

Setup before running:
  1. Add ANTHROPIC_API_KEY to .env at repo root.
  2. .venv/Scripts/pip install anthropic ddgs html2text  (already done)
  3. Optional: --dry-run prints what it WOULD do without API calls.

Cost estimate (Claude Sonnet 4.6, ~5K tokens/player in/out):
   1257 players × $0.005 = ~$6 input + ~$25 output ≈ $30 max.
   Run with --max-players 100 first to validate before going wide.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_scouting_corpus.py \\
        [--max-players 100] [--min-toi 500] [--dry-run] [--force-refresh] \\
        [--position C,L,R,D] [--rate-limit-s 1.0]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

# Read .env if present (dotenv-style minimal parser)
def _load_env():
    p = REPO / ".env"
    if not p.exists(): return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "=" not in line: continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

_load_env()

DB = REPO / "legacy" / "data" / "store.sqlite"
INDEX_PATH = REPO / "legacy" / "data" / "comparable_index.json"
TODAY = date.today().isoformat()


# Lazy imports so --dry-run works without optional deps.
def _import_runtime_deps():
    global anthropic, ddgs, html2text, requests
    import anthropic as _anthropic
    from ddgs import DDGS as _DDGS
    import html2text as _html2text
    import requests as _requests
    anthropic = _anthropic
    ddgs = _DDGS
    html2text = _html2text
    requests = _requests


SYSTEM_PROMPT = """You are a hockey-analytics scouting-extraction assistant.
Given web-search snippets about an NHL player, extract a structured profile
according to the schema below. Be conservative: prefer NULL or low-confidence
over invented attributes. Quote the source text that supports each tag.

OUTPUT: a single JSON object with this exact shape, no prose around it.

{
  "attributes": [
    {"name": "<one of: skating, hands, hockey_iq, compete, size, speed, shot, vision, defense>",
     "value": <float 1.0-5.0>,
     "confidence": <float 0.0-1.0>,
     "source_count": <int, how many text passages supported this score>}
  ],
  "tags": [
    {"tag": "<one of: warrior, playmaker, sniper, two_way, shutdown, agitator, enforcer,
              power_forward, puck_mover, stay_at_home, offensive_d, fast, slow_start,
              streaky, consistent, top_six, bottom_six, bottom_pair, rover,
              specialist_pp, specialist_pk, clutch, volume_shooter>",
     "confidence": <float 0.0-1.0>,
     "source_quote": "<verbatim snippet from source text>",
     "source_url": "<URL where the snippet appears>"}
  ],
  "comp_mentions": [
    {"comp_name": "<player name being compared to>",
     "source_quote": "<verbatim 'reminds of/compares to' snippet>",
     "source_url": "<URL>",
     "polarity": "<style|trajectory|both>"}
  ]
}

Rules:
- Only include tags actually supported by quoted text. No tag should appear
  without a source_quote.
- Confidence convention:
    0.9-1.0: explicitly stated in source ("tenacious forecheck" -> warrior=0.95)
    0.7-0.85: strongly implied by multiple passages
    0.5-0.65: directionally supported, single source
- For continuous attributes, only include those with at least one supporting
  passage. Other attributes can be omitted entirely (don't fabricate scores).
- comp_mentions are only for explicit "X reminds me of Y" / "the next Y"
  / "Y-style player" mentions. Don't synthesize these.
- Do NOT include any field other than the three above.
- Output VALID JSON only — no markdown fences, no commentary.
"""


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def gather_player_targets(con: sqlite3.Connection, *, min_toi: float, max_n: int | None,
                          position: tuple[str, ...] | None,
                          force_refresh: bool) -> list[tuple[str, str]]:
    """Return list of (name, position) tuples to process, sorted by pooled TOI desc."""
    pos_clause = ""
    params: list = ["20212022", "20222023", "20232024", "20242025", "20252026", min_toi]
    if position:
        pos_clause = f" AND s.position IN ({','.join(['?']*len(position))})"
        params.extend(position)
    sql = f"""
        SELECT s.name, s.position, SUM(s.toi) AS total_toi
        FROM skater_stats s
        WHERE s.season IN (?, ?, ?, ?, ?)
          AND s.sit = '5v5' AND s.split = 'oi' AND s.toi IS NOT NULL
        GROUP BY s.name, s.position
        HAVING total_toi >= ?
        {pos_clause}
        ORDER BY total_toi DESC
    """
    rows = con.execute(sql, params).fetchall()

    out: list[tuple[str, str]] = []
    if not force_refresh:
        existing = {(r[0], r[1] or "") for r in con.execute(
            "SELECT name, position FROM scouting_profiles"
        )}
    else:
        existing = set()
    for name, pos, _ in rows:
        if (name, pos or "") in existing:
            continue
        out.append((name, pos or ""))
        if max_n and len(out) >= max_n:
            break
    return out


def search_web(name: str, position: str, ddgs_client) -> list[dict]:
    """One web search per player. Returns up to 5 hits with title/url/body."""
    pos_word = {"C": "centre", "L": "left winger", "R": "right winger", "D": "defenseman"}.get(
        (position or "").upper(), "hockey player"
    )
    query = f"{name} NHL {pos_word} scouting style of play"
    try:
        results = list(ddgs_client.text(query, max_results=5))
    except Exception as e:
        print(f"    [search error: {e}]")
        return []
    return results


def fetch_text(url: str, requests_lib, h2t) -> str:
    """Fetch URL and convert to plain text, capped at ~10K chars."""
    try:
        r = requests_lib.get(url, timeout=20, headers={"User-Agent": "lemieux-scouting/0.1"})
        if r.status_code != 200:
            return ""
        return h2t.handle(r.text)[:10_000]
    except Exception:
        return ""


def extract_profile_via_claude(name: str, position: str, snippets: list[dict],
                               anthropic_client) -> dict | None:
    """Call Claude with the snippets, parse the structured JSON response."""
    if not snippets:
        return None
    # Build the user message with the search context
    parts = [f"Player: {name}\nPosition: {position}\n\nSearch snippets:\n"]
    for i, s in enumerate(snippets[:5], 1):
        url = s.get("href", "")
        title = s.get("title", "")
        body = s.get("body", "")
        parts.append(f"[{i}] {title} ({url})\n{body}\n")
    user_msg = "\n".join(parts)

    try:
        resp = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",   # sonnet 4.5 is the cost-balanced default
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        print(f"    [Claude API error: {e}]")
        return None
    text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    # Strip any code fences if Claude added them
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    [JSON parse error: {e}; first 200 chars: {text[:200]}]")
        return None


def persist_profile(con: sqlite3.Connection, name: str, position: str,
                    extracted: dict, source_urls: list[str]) -> None:
    """Use the existing core upsert. Imported lazily to keep --dry-run cheap."""
    from lemieux.core import (
        ComparableMention, ContinuousAttribute, PlayerScoutingProfile,
        TagAssertion, upsert_profile,
    )
    profile = PlayerScoutingProfile(
        name=name, position=position, extracted_at=TODAY,
        sources=source_urls,
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
    ap.add_argument("--max-players", type=int, default=None,
                    help="Cap on players to process this run. Useful for staging.")
    ap.add_argument("--min-toi", type=float, default=500.0,
                    help="Min pooled 5v5 TOI to be eligible (default 500 min)")
    ap.add_argument("--position", default=None,
                    help="Comma-separated positions to filter (e.g. 'C,L,R')")
    ap.add_argument("--rate-limit-s", type=float, default=1.0,
                    help="Polite delay between players")
    ap.add_argument("--dry-run", action="store_true",
                    help="Don't call APIs; just print what would happen")
    ap.add_argument("--force-refresh", action="store_true",
                    help="Re-process players already in scouting_profiles")
    args = ap.parse_args()

    positions = tuple(p.strip().upper() for p in args.position.split(",")) if args.position else None

    con = sqlite3.connect(DB, timeout=60)
    targets = gather_player_targets(
        con, min_toi=args.min_toi, max_n=args.max_players,
        position=positions, force_refresh=args.force_refresh,
    )
    print(f"Eligible players to process: {len(targets)}")
    if args.max_players:
        print(f"  (capped at --max-players={args.max_players})")
    if not targets:
        print("  Nothing to do.")
        return

    if args.dry_run:
        print("\n--dry-run: would process these players (top 20 shown):")
        for name, pos in targets[:20]:
            print(f"  {name:30s} ({pos})")
        if len(targets) > 20:
            print(f"  ...and {len(targets) - 20} more")
        # Cost estimate
        n = len(targets)
        # ~5K input tokens, ~1.5K output tokens per player on Sonnet 4.5
        # Sonnet pricing (current): $3 / M input, $15 / M output
        in_cost = n * 5000 * 3 / 1_000_000
        out_cost = n * 1500 * 15 / 1_000_000
        print(f"\nCost estimate (Sonnet 4.5): ${in_cost + out_cost:.2f} "
              f"(in {in_cost:.2f} + out {out_cost:.2f}). "
              f"Wall time at 1 player/{args.rate_limit_s+5:.0f}s ≈ {n * (args.rate_limit_s + 5) / 60:.0f} min.")
        return

    # Real-run: need API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nERROR: ANTHROPIC_API_KEY not set. Add it to .env at the repo root and re-run, "
              "or use --dry-run to preview.")
        sys.exit(1)

    _import_runtime_deps()
    h2t = html2text.HTML2Text(); h2t.ignore_links = True; h2t.ignore_images = True
    anthropic_client = anthropic.Anthropic()
    ddgs_client = ddgs()

    print(f"\nProcessing {len(targets)} players. ETA: ~{len(targets) * (args.rate_limit_s + 5) / 60:.0f} min.")
    n_ok = n_skip = n_err = 0
    for i, (name, pos) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {name} ({pos})", flush=True)
        snippets = search_web(name, pos, ddgs_client)
        if not snippets:
            print(f"    [no snippets — skipped]")
            n_skip += 1
            time.sleep(args.rate_limit_s)
            continue
        # Optionally fetch full text for the top hit (skip for now: snippets are usually enough)
        extracted = extract_profile_via_claude(name, pos, snippets, anthropic_client)
        if not extracted:
            n_err += 1
            time.sleep(args.rate_limit_s)
            continue
        urls = [s.get("href", "") for s in snippets[:5] if s.get("href")]
        try:
            persist_profile(con, name, pos, extracted, urls)
            n_ok += 1
            tags_count = len(extracted.get("tags", []))
            attrs_count = len(extracted.get("attributes", []))
            print(f"    ✓ {attrs_count} attrs, {tags_count} tags persisted")
        except Exception as e:
            print(f"    [persist error: {e}]")
            n_err += 1
        time.sleep(args.rate_limit_s)

        # Progress checkpoint every 20 players
        if i % 20 == 0:
            print(f"  --- checkpoint: {n_ok} ok, {n_skip} skipped, {n_err} errored ---")

    con.close()
    print(f"\nDone. {n_ok} persisted, {n_skip} skipped (no search results), {n_err} errored.")


if __name__ == "__main__":
    main()
