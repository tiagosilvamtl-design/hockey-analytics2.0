"""Analyze Slafkovsky-replacement candidates for the Habs.

Two questions:
  1. Which Habs forward best replaces Slaf on L1 LW?
  2. For Gallagher specifically: do his kNN comps with the `warrior` tag
     show a stronger reg-to-playoff iso lift than his non-warrior comps?

Both use only data already in the store + the kNN index + the scouting tags.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core.comparable import ComparableIndex

DB = REPO / "legacy" / "data" / "store.sqlite"
INDEX = REPO / "legacy" / "data" / "comparable_index.json"
SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def pooled_iso_net60(name: str, *, stype: int) -> tuple[float | None, float, int]:
    """Return (iso_net60, total_toi, n_seasons) pooled across the 5-yr window
    for the given regular(2)/playoff(3) split, sit='5v5'."""
    rows = con.execute(
        """SELECT toi, xgf, xga FROM skater_stats
           WHERE name = ? AND split='oi' AND sit='5v5' AND stype=?
             AND season IN (?,?,?,?,?)""",
        (name, stype, *SEASONS),
    ).fetchall()
    toi = sum((r["toi"] or 0) for r in rows)
    xgf = sum((r["xgf"] or 0) for r in rows)
    xga = sum((r["xga"] or 0) for r in rows)
    n = sum(1 for r in rows if (r["toi"] or 0) > 0)
    if toi <= 0:
        return (None, 0.0, 0)
    iso_net = (xgf - xga) * 60.0 / toi
    return (iso_net, toi, n)


def has_tag(name: str, tag: str, *, min_conf: float = 0.5) -> tuple[bool, float | None]:
    r = con.execute(
        "SELECT confidence FROM scouting_tags WHERE name=? AND tag=? ORDER BY confidence DESC LIMIT 1",
        (name, tag),
    ).fetchone()
    if not r or r["confidence"] < min_conf:
        return (False, r["confidence"] if r else None)
    return (True, r["confidence"])


def player_tags(name: str) -> list[tuple[str, float]]:
    return [(r["tag"], r["confidence"]) for r in con.execute(
        "SELECT tag, confidence FROM scouting_tags WHERE name=? ORDER BY confidence DESC", (name,)
    )]


# ============================================================
# QUESTION 1 — replacement candidates for Slafkovsky on L1 LW
# ============================================================
print("=" * 90)
print("Q1: Best replacement for Slafkovský on the Habs first line LW")
print("=" * 90)
print()

# Slaf's pooled performance (the bar)
slaf_reg = pooled_iso_net60("Juraj Slafkovský", stype=2)
slaf_play = pooled_iso_net60("Juraj Slafkovský", stype=3)
print(f"Slafkovský pooled (5-yr window, 5v5 oi):")
print(f"  reg-season  iso_net60 = {slaf_reg[0]:+.3f}   toi={slaf_reg[1]:.0f}   ({slaf_reg[2]} seasons)")
print(f"  playoff     iso_net60 = {slaf_play[0]:+.3f}   toi={slaf_play[1]:.0f}   ({slaf_play[2]} seasons)")
print(f"  Slaf tags: {player_tags('Juraj Slafkovský')}")
print()

candidates = [
    "Brendan Gallagher",       # RW; would slot LW or shift Caufield
    "Patrik Laine",            # natural L, only 5 GP this season
    "Florian Xhekaj",          # depth L
    "Joshua Roy",              # young RW, could pinch-shift
    "Joe Veleno",              # C, but versatile
]

print(f"{'Candidate':24s} {'reg iso60':>10} {'reg TOI':>8} {'play iso60':>11} {'play TOI':>9}  tags")
print("-" * 100)
for name in candidates:
    reg = pooled_iso_net60(name, stype=2)
    play = pooled_iso_net60(name, stype=3)
    tags = ", ".join(f"{t}({c:.2f})" for t, c in player_tags(name)[:5])
    reg_str = f"{reg[0]:+.3f}" if reg[0] is not None else "n/a"
    play_str = f"{play[0]:+.3f}" if play[0] is not None else "n/a"
    play_toi = f"{play[1]:.0f}" if play[1] else "0"
    print(f"{name:24s} {reg_str:>10} {reg[1]:>8.0f} {play_str:>11} {play_toi:>9}  {tags}")

print()
print("Note: replacement choice is also constrained by handedness + line role.")
print("      Gallagher = RW; slotting him on LW means flipping him or shifting Caufield.")
print("      Laine = natural L but only 49 toi this season (post-injury).")
print()


# ============================================================
# QUESTION 2 — Gallagher's kNN comps split by warrior tag
# ============================================================
print("=" * 90)
print("Q2: Do Gallagher's kNN comps with `warrior` tag show stronger reg→playoff lift?")
print("=" * 90)
print()

idx = ComparableIndex.load(INDEX)
gallagher_comps = idx.find_comparables("Brendan Gallagher", k=30, min_pooled_toi=200.0)
print(f"Gallagher's top-30 kNN comps (filtered to >=200 5v5 toi):")
print()

rows = []
for c in gallagher_comps:
    if c.name.lower() == "brendan gallagher":
        continue
    is_warrior, conf = has_tag(c.name, "warrior")
    reg = pooled_iso_net60(c.name, stype=2)
    play = pooled_iso_net60(c.name, stype=3)
    if reg[0] is None or play[0] is None or play[1] < 50:
        continue  # need both reg + playoff samples
    lift = play[0] - reg[0]
    rows.append({
        "name": c.name, "score": c.score, "warrior": is_warrior, "warrior_conf": conf,
        "reg_iso": reg[0], "play_iso": play[0], "lift": lift,
        "reg_toi": reg[1], "play_toi": play[1],
    })

# Print rows
print(f"{'rank':>4} {'name':24s} {'comp':>5} {'war':>4} {'reg':>8} {'play':>8} {'lift':>8}  {'reg toi':>8} {'play toi':>8}")
print("-" * 100)
for i, r in enumerate(rows, 1):
    war = "Y" if r["warrior"] else "."
    print(f"{i:>4} {r['name']:24s} {r['score']:>5.1f} {war:>4} {r['reg_iso']:>+8.3f} {r['play_iso']:>+8.3f} {r['lift']:>+8.3f}  {r['reg_toi']:>8.0f} {r['play_toi']:>8.0f}")

# Split-study comparison
warriors = [r for r in rows if r["warrior"]]
non_warriors = [r for r in rows if not r["warrior"]]
print()
print(f"=== Split summary ===")
print(f"  warrior comps      n={len(warriors):>2}   mean lift = {np.mean([r['lift'] for r in warriors]):+.3f}   "
      f"median = {np.median([r['lift'] for r in warriors]):+.3f}")
print(f"  non-warrior comps  n={len(non_warriors):>2}   mean lift = {np.mean([r['lift'] for r in non_warriors]):+.3f}   "
      f"median = {np.median([r['lift'] for r in non_warriors]):+.3f}")
print(f"  Δ (warrior − non) = {np.mean([r['lift'] for r in warriors]) - np.mean([r['lift'] for r in non_warriors]):+.3f}")

# Bootstrap 80% CI on the difference
def bootstrap_diff(a: list[float], b: list[float], n: int = 2000, ci: float = 0.80) -> tuple[float, float, float]:
    rng = np.random.default_rng(42)
    diffs = []
    a_arr = np.array(a); b_arr = np.array(b)
    for _ in range(n):
        a_s = rng.choice(a_arr, size=len(a_arr), replace=True)
        b_s = rng.choice(b_arr, size=len(b_arr), replace=True)
        diffs.append(a_s.mean() - b_s.mean())
    diffs = np.array(diffs)
    lo, hi = np.quantile(diffs, [(1-ci)/2, 1-(1-ci)/2])
    return (diffs.mean(), lo, hi)

if warriors and non_warriors:
    mean_d, lo, hi = bootstrap_diff([r["lift"] for r in warriors], [r["lift"] for r in non_warriors])
    print(f"  Bootstrap mean Δ = {mean_d:+.3f}   80% CI [{lo:+.3f}, {hi:+.3f}]")
    if lo > 0:
        print("  -> CI excludes 0: warrior comps DO show a stronger lift on this small sample.")
    elif hi < 0:
        print("  -> CI excludes 0: warrior comps show a WEAKER lift.")
    else:
        print("  -> CI straddles 0: small sample doesn't support either direction.")
else:
    print("  Not enough data on one side to compute CI.")

print()
print("Caveats:")
print("  - kNN cohorts of size <10 produce wide CIs even with bootstrap.")
print("  - 'lift' here is unweighted by playoff TOI; small playoff samples can")
print("    dominate the cohort mean.")
print("  - reg + playoff iso are pooled across the 5-yr window — a player whose")
print("    'warrior identity' emerged late or after a trade gets averaged out.")
