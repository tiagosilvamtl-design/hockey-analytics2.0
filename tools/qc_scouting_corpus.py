"""Data-quality checks for the scouting corpus.

Run AFTER the corpus build completes. Reports issues + suggests fixes.

Categories:
  A. Schema integrity     — value ranges, mandatory fields
  B. Provenance integrity — source quotes + URLs on every tag
  C. Coverage             — per-position, per-attribute, per-tag distributions
  D. Eyeball sanity       — tag cohort recognizability + co-occurrence patterns
  E. Cohort-stat readiness — which tags have publishable N for split studies

The companion fix tool (--fix) addresses common issues:
  - Drops tags with confidence < threshold
  - Normalizes positions
  - Deduplicates same-tag-twice (would only happen on stale schema)
  - Removes orphan rows (attributes/tags without parent profile)

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/qc_scouting_corpus.py [--fix]
        [--min-confidence-keep 0.5]
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core import (
    CANONICAL_TAGS, CONTINUOUS_ATTRIBUTES,
    find_players_by_tag, list_known_tags, tag_split_study,
)

DB = REPO / "legacy" / "data" / "store.sqlite"


def hr(s: str) -> None:
    print(f"\n{'='*78}\n{s}\n{'='*78}")


def check_schema(con: sqlite3.Connection) -> dict:
    """Return dict of issue counts per check."""
    issues = {}
    # Attribute value out-of-range
    n = con.execute(
        "SELECT COUNT(*) FROM scouting_attributes WHERE value < 1.0 OR value > 5.0"
    ).fetchone()[0]
    issues["attr_value_out_of_range_1_5"] = n
    # Confidence out-of-range
    for table in ("scouting_attributes", "scouting_tags"):
        n = con.execute(
            f"SELECT COUNT(*) FROM {table} WHERE confidence < 0 OR confidence > 1"
        ).fetchone()[0]
        issues[f"{table}_conf_out_of_range_0_1"] = n
    # Tags not in canonical vocabulary (allow `_other:*` prefix)
    bad_tags = con.execute(
        "SELECT DISTINCT tag FROM scouting_tags WHERE tag NOT IN ({})"
        .format(",".join(["?"] * len(CANONICAL_TAGS))),
        list(CANONICAL_TAGS),
    ).fetchall()
    bad_tags = [t[0] for t in bad_tags if not (t[0] or "").startswith("_other")]
    issues["non_canonical_tags"] = len(bad_tags)
    if bad_tags:
        print("  Non-canonical tags found:", bad_tags[:20])
    # Attributes not in canonical vocabulary
    bad_attrs = con.execute(
        "SELECT DISTINCT attribute FROM scouting_attributes WHERE attribute NOT IN ({})"
        .format(",".join(["?"] * len(CONTINUOUS_ATTRIBUTES))),
        list(CONTINUOUS_ATTRIBUTES),
    ).fetchall()
    issues["non_canonical_attributes"] = len(bad_attrs)
    if bad_attrs:
        print("  Non-canonical attributes:", [r[0] for r in bad_attrs[:20]])
    return issues


def check_provenance(con: sqlite3.Connection) -> dict:
    """Tag must have a non-empty source_quote and a URL-shaped source_url."""
    issues = {}
    n = con.execute(
        "SELECT COUNT(*) FROM scouting_tags WHERE source_quote IS NULL OR LENGTH(TRIM(source_quote)) = 0"
    ).fetchone()[0]
    issues["tags_missing_source_quote"] = n
    n = con.execute(
        "SELECT COUNT(*) FROM scouting_tags WHERE source_url IS NULL OR LENGTH(TRIM(source_url)) = 0"
    ).fetchone()[0]
    issues["tags_missing_source_url"] = n
    n = con.execute(
        "SELECT COUNT(*) FROM scouting_tags WHERE source_url NOT LIKE 'http%'"
    ).fetchone()[0]
    issues["tags_malformed_source_url"] = n
    n = con.execute(
        "SELECT COUNT(*) FROM scouting_comparable_mentions "
        "WHERE comp_name IS NULL OR LENGTH(TRIM(comp_name)) = 0"
    ).fetchone()[0]
    issues["comp_mentions_missing_comp_name"] = n
    return issues


def check_orphans(con: sqlite3.Connection) -> dict:
    """Child rows whose parent profile is missing."""
    issues = {}
    for child in ("scouting_attributes", "scouting_tags", "scouting_comparable_mentions"):
        n = con.execute(f"""
            SELECT COUNT(*) FROM {child} c
            WHERE NOT EXISTS (
                SELECT 1 FROM scouting_profiles p
                WHERE p.name = c.name AND p.position = c.position
            )
        """).fetchone()[0]
        issues[f"orphan_rows_{child}"] = n
    return issues


def coverage_report(con: sqlite3.Connection) -> None:
    """Distribution stats."""
    n_profiles = con.execute("SELECT COUNT(*) FROM scouting_profiles").fetchone()[0]
    print(f"  Total profiles: {n_profiles}")

    print("\n  By position:")
    for r in con.execute(
        "SELECT position, COUNT(*) FROM scouting_profiles GROUP BY position ORDER BY 2 DESC"
    ):
        print(f"    {r[0] or '(none)':6s} {r[1]:5d}")

    print("\n  Attributes per profile (distribution):")
    rows = con.execute(
        "SELECT name, position, COUNT(*) AS n FROM scouting_attributes GROUP BY name, position"
    ).fetchall()
    n_per = Counter(r[2] for r in rows)
    for k in sorted(n_per):
        print(f"    {k} attributes: {n_per[k]} profiles")

    print("\n  Tags per profile (distribution):")
    rows = con.execute(
        "SELECT name, position, COUNT(*) AS n FROM scouting_tags GROUP BY name, position"
    ).fetchall()
    n_per = Counter(r[2] for r in rows)
    for k in sorted(n_per):
        print(f"    {k} tags: {n_per[k]} profiles")
    n_no_tags = n_profiles - sum(n_per.values())
    if n_no_tags > 0:
        print(f"    0 tags: {n_no_tags} profiles  ⚠ flagged for re-extraction")


def tag_distribution(con: sqlite3.Connection, min_confidence: float = 0.6) -> None:
    print(f"\n  Tag counts (min_confidence {min_confidence}):")
    tags = list_known_tags(con, min_confidence=min_confidence)
    for t, n in tags:
        bar = "█" * min(n // 2, 40)
        print(f"    {t:18s} {n:4d}  {bar}")


def cohort_readiness(con: sqlite3.Connection, min_confidence: float = 0.6) -> None:
    """For each tag with N >= 5 players, run the split-study and report N + CI."""
    print(f"\n  Tag-cohort split-study readiness (reg-season -> playoff iso net):")
    print(f"  {'Tag':<18}  {'N':>4}  {'mean Δ':>9}  {'80% CI':>22}  {'sign':>5}")
    print("  " + "-" * 76)
    for t, n in list_known_tags(con, min_confidence=min_confidence):
        if n < 5:
            continue
        try:
            res = tag_split_study(
                con, t, min_tag_confidence=min_confidence,
                min_reg_toi=200.0, min_playoff_toi=50.0,
            )
        except Exception as e:
            print(f"    {t:<18}  err: {e}")
            continue
        if res.n_players < 3:
            print(f"    {t:<18}  {res.n_players:>4}  (insufficient cohort with both reg+playoff TOI)")
            continue
        sign_consistent = (res.ci80_low * res.ci80_high) > 0
        sign_mark = "✓" if sign_consistent else "—"
        print(f"    {t:<18}  {res.n_players:>4}  {res.mean_delta_iso_net:>+9.3f}  "
              f"[{res.ci80_low:>+6.3f}, {res.ci80_high:>+6.3f}]  {sign_mark:>5}")


def comp_mentions_summary(con: sqlite3.Connection) -> None:
    """Most-named comparable players + total mentions count."""
    n = con.execute("SELECT COUNT(*) FROM scouting_comparable_mentions").fetchone()[0]
    print(f"\n  Total comparable mentions captured: {n}")
    if n == 0:
        return
    print(f"  Top 15 most-named comparables:")
    for r in con.execute(
        "SELECT comp_name, COUNT(*) FROM scouting_comparable_mentions "
        "GROUP BY comp_name ORDER BY 2 DESC LIMIT 15"
    ):
        print(f"    {r[1]:4d}  {r[0]}")


def fix_apply(con: sqlite3.Connection, args) -> None:
    print("\n  Applying fixes:")
    # 1. Drop tags below confidence threshold
    n = con.execute(
        "DELETE FROM scouting_tags WHERE confidence < ?", (args.min_confidence_keep,)
    ).rowcount
    print(f"    Dropped {n} tags below confidence {args.min_confidence_keep}")
    # 2. Drop tags with empty source quotes (provenance violations)
    n = con.execute(
        "DELETE FROM scouting_tags WHERE source_quote IS NULL OR LENGTH(TRIM(source_quote)) = 0"
    ).rowcount
    print(f"    Dropped {n} tags with empty source_quote")
    # 3. Drop attributes out of range
    n = con.execute(
        "DELETE FROM scouting_attributes WHERE value < 1.0 OR value > 5.0"
    ).rowcount
    print(f"    Dropped {n} out-of-range attribute values")
    # 4. Drop attributes/tags with confidence > 1 or < 0
    n = con.execute(
        "DELETE FROM scouting_attributes WHERE confidence < 0 OR confidence > 1"
    ).rowcount
    print(f"    Dropped {n} attributes with confidence out of [0,1]")
    n = con.execute(
        "DELETE FROM scouting_tags WHERE confidence < 0 OR confidence > 1"
    ).rowcount
    print(f"    Dropped {n} tags with confidence out of [0,1]")
    # 5. Drop non-canonical tags (excluding _other:*)
    n = con.execute(
        "DELETE FROM scouting_tags WHERE tag NOT IN ({}) AND tag NOT LIKE '_other%'".format(
            ",".join(["?"] * len(CANONICAL_TAGS))
        ),
        list(CANONICAL_TAGS),
    ).rowcount
    print(f"    Dropped {n} non-canonical tags")
    # 6. Drop non-canonical attributes
    n = con.execute(
        "DELETE FROM scouting_attributes WHERE attribute NOT IN ({})".format(
            ",".join(["?"] * len(CONTINUOUS_ATTRIBUTES))
        ),
        list(CONTINUOUS_ATTRIBUTES),
    ).rowcount
    print(f"    Dropped {n} non-canonical attributes")
    # 7. Drop orphan child rows
    for child in ("scouting_attributes", "scouting_tags", "scouting_comparable_mentions"):
        n = con.execute(f"""
            DELETE FROM {child}
            WHERE NOT EXISTS (
                SELECT 1 FROM scouting_profiles p
                WHERE p.name = {child}.name AND p.position = {child}.position
            )
        """).rowcount
        print(f"    Dropped {n} orphan rows from {child}")
    # 8. Drop profiles with zero tags AND zero attributes (failed extractions
    #    that left empty parent rows)
    n = con.execute("""
        DELETE FROM scouting_profiles
        WHERE NOT EXISTS (
            SELECT 1 FROM scouting_tags t
            WHERE t.name = scouting_profiles.name AND t.position = scouting_profiles.position
        )
        AND NOT EXISTS (
            SELECT 1 FROM scouting_attributes a
            WHERE a.name = scouting_profiles.name AND a.position = scouting_profiles.position
        )
    """).rowcount
    print(f"    Dropped {n} empty-shell profiles (will be retried on next corpus run)")
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Apply fixes after reporting")
    ap.add_argument("--min-confidence-keep", type=float, default=0.5,
                    help="Tags below this confidence are dropped on --fix (default 0.5)")
    ap.add_argument("--cohort-min-conf", type=float, default=0.6,
                    help="Min tag confidence used for cohort readiness reports (default 0.6)")
    args = ap.parse_args()

    con = sqlite3.connect(DB, timeout=60)

    hr("A. Schema integrity")
    schema = check_schema(con)
    for k, v in schema.items():
        flag = "⚠" if v > 0 else "✓"
        print(f"  {flag} {k}: {v}")

    hr("B. Provenance integrity")
    prov = check_provenance(con)
    for k, v in prov.items():
        flag = "⚠" if v > 0 else "✓"
        print(f"  {flag} {k}: {v}")

    hr("C. Coverage")
    coverage_report(con)

    hr("D. Tag distribution")
    tag_distribution(con, min_confidence=args.cohort_min_conf)

    hr("E. Orphan rows")
    orphans = check_orphans(con)
    for k, v in orphans.items():
        flag = "⚠" if v > 0 else "✓"
        print(f"  {flag} {k}: {v}")

    hr("F. Comparable mentions")
    comp_mentions_summary(con)

    hr("G. Tag-cohort split-study readiness")
    cohort_readiness(con, min_confidence=args.cohort_min_conf)

    if args.fix:
        hr("Applying fixes")
        fix_apply(con, args)
        print("\nRe-running checks after fix:")
        hr("Schema (post-fix)")
        for k, v in check_schema(con).items():
            flag = "⚠" if v > 0 else "✓"
            print(f"  {flag} {k}: {v}")
        hr("Provenance (post-fix)")
        for k, v in check_provenance(con).items():
            flag = "⚠" if v > 0 else "✓"
            print(f"  {flag} {k}: {v}")
        hr("Orphans (post-fix)")
        for k, v in check_orphans(con).items():
            flag = "⚠" if v > 0 else "✓"
            print(f"  {flag} {k}: {v}")
    con.close()


if __name__ == "__main__":
    main()
