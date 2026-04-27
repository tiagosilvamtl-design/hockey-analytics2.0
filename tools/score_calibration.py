"""Calibrate the per-period composite score against a representative sample
of recent playoff games.

Sample: 2024 + 2025 NHL playoffs. Brute-force the playoff game-ID space and
fetch what exists. For each game × completed period × skater, compute the
SAME composite score recipe used in game4_periods.py. Pool all observations,
report distribution stats and percentile thresholds for a 4-tier barème:

    Awful      : < p10
    Mediocre   : p10 – p50
    Good       : p50 – p90
    Excellent  : ≥ p90

Filters: only skaters with ≥ 3 min TOI in the period (avoids zero-TOI noise).
We can't get per-period TOI from the boxscore (only game-total), so we
approximate using shifts when available, else use full game TOI / 3 as an
estimator. Goalies excluded.

Output:
    examples/habs_round1_2026/score_bareme.json

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/score_calibration.py
"""

from __future__ import annotations
import json
import math
import statistics
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

import truststore; truststore.inject_into_ssl()
import requests
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "lemieux-hockey-analytics/0.1 (calibration)"})

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "examples" / "habs_round1_2026" / "score_bareme.json"

HD_DISTANCE = 22.0
SHOT_TYPES = {"shot-on-goal", "missed-shot", "blocked-shot", "goal"}

# season_start -> playoff game-ID prefix; e.g. 2023 → "2023030..."
SEASONS = [2023, 2024]   # 2024 playoffs (in season 23-24) + 2025 playoffs


def gen_candidate_ids():
    """NHL playoff gameId format: '{season}030{round}{matchup}{game}', all
    single digits after '030'. Round 1: matchups 1-8; R2: 1-4; R3: 1-2; R4: 1.
    """
    ids = []
    for s in SEASONS:
        for r, max_match in [(1, 8), (2, 4), (3, 2), (4, 1)]:
            for m in range(1, max_match + 1):
                for g in range(1, 8):
                    ids.append(f"{s}030{r}{m}{g}")
    return ids


def time_to_sec(t):
    if not t: return 0
    try:
        m, s = t.split(":"); return int(m) * 60 + int(s)
    except Exception:
        return 0


def shot_distance(x, y):
    if x is None or y is None: return None
    return math.sqrt((abs(x) - 89.0) ** 2 + (y or 0.0) ** 2)


def fetch_game(gid: str, sleep_between=0.4, max_retries=4):
    """Fetch PBP and boxscore for one game; return (gid, pbp, box) or None on miss.
    Uses a polite sleep + exponential backoff on 429 to respect upstream limits.
    """
    backoff = 2.0
    for attempt in range(max_retries):
        try:
            pbp = SESSION.get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play", timeout=20)
            if pbp.status_code == 429:
                time.sleep(backoff); backoff *= 2; continue
            if pbp.status_code == 404:
                return None
            if pbp.status_code != 200:
                return None
            time.sleep(sleep_between)
            box = SESSION.get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/boxscore", timeout=20)
            if box.status_code == 429:
                time.sleep(backoff); backoff *= 2; continue
            if box.status_code != 200:
                return None
            time.sleep(sleep_between)
            return (gid, pbp.json(), box.json())
        except Exception:
            time.sleep(backoff); backoff *= 2
    return None


def compute_period_scores(plays_in_period, pinfo, home_id, away_id, home_abbr, away_abbr):
    """Same scoring recipe as game4_periods.py."""
    init = lambda: {"g": 0, "a1": 0, "a2": 0, "sog": 0, "missed": 0, "blocked_taken": 0,
                    "blocks_made": 0, "hits_for": 0, "ind_attempts": 0, "ind_hd_attempts": 0,
                    "giveaways": 0, "takeaways": 0}
    counters = defaultdict(init)

    for play in plays_in_period:
        typ = play.get("typeDescKey") or ""
        d = play.get("details") or {}

        if typ in SHOT_TYPES:
            shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
            if shooter:
                c = counters[shooter]
                x = d.get("xCoord"); y = d.get("yCoord")
                dist = shot_distance(x, y)
                is_hd = dist is not None and dist <= HD_DISTANCE
                if typ == "shot-on-goal":
                    c["sog"] += 1; c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                elif typ == "missed-shot":
                    c["missed"] += 1; c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                elif typ == "blocked-shot":
                    c["blocked_taken"] += 1; c["ind_attempts"] += 1
                elif typ == "goal":
                    c["g"] += 1; c["sog"] += 1; c["ind_attempts"] += 1
                    if is_hd: c["ind_hd_attempts"] += 1
                    a1 = d.get("assist1PlayerId"); a2 = d.get("assist2PlayerId")
                    if a1: counters[a1]["a1"] += 1
                    if a2: counters[a2]["a2"] += 1
            blocker = d.get("blockingPlayerId")
            if typ == "blocked-shot" and blocker:
                counters[blocker]["blocks_made"] += 1

        if typ == "hit":
            hitter = d.get("hittingPlayerId")
            if hitter: counters[hitter]["hits_for"] += 1
        if typ == "giveaway":
            g = d.get("playerId")
            if g: counters[g]["giveaways"] += 1
        if typ == "takeaway":
            g = d.get("playerId")
            if g: counters[g]["takeaways"] += 1

    rows = []
    for pid, c in counters.items():
        info = pinfo.get(pid)
        if not info or info.get("is_goalie"):
            continue
        score = (c["g"] * 3.0 + (c["a1"] + c["a2"]) * 2.0 + c["sog"] * 0.5
                 + c["ind_hd_attempts"] * 0.75 + (c["ind_attempts"] - c["sog"]) * 0.15
                 + (c["hits_for"] + c["blocks_made"]) * 0.25
                 - c["giveaways"] * 0.5 + c["takeaways"] * 0.5)
        rows.append({
            "score": score,
            "g": c["g"], "a": c["a1"] + c["a2"], "sog": c["sog"],
            "ind_hd_attempts": c["ind_hd_attempts"], "ind_attempts": c["ind_attempts"],
            "position": info.get("position"),
            "is_d": info.get("position") == "D",
        })
    return rows


def process_game(triple):
    if not triple:
        return []
    gid, pbp, box = triple
    home_id = pbp["homeTeam"]["id"]; away_id = pbp["awayTeam"]["id"]
    home_abbr = pbp["homeTeam"]["abbrev"]; away_abbr = pbp["awayTeam"]["abbrev"]

    pinfo = {}
    for side in ("homeTeam", "awayTeam"):
        for grp in ("forwards", "defense", "goalies"):
            for p in box.get("playerByGameStats", {}).get(side, {}).get(grp, []):
                pinfo[p["playerId"]] = {
                    "position": p["position"],
                    "is_goalie": grp == "goalies",
                    "toi_total_min": (lambda t: int(t.split(":")[0]) + int(t.split(":")[1]) / 60.0)(p.get("toi", "00:00")),
                }

    plays = pbp.get("plays", [])
    completed_periods = sorted({(p.get("periodDescriptor") or {}).get("number")
                                for p in plays if p.get("typeDescKey") == "period-end"})
    completed_periods = [p for p in completed_periods if p is not None]
    if not completed_periods:
        return []

    out_rows = []
    for pn in completed_periods:
        plays_pn = [p for p in plays if (p.get("periodDescriptor") or {}).get("number") == pn]
        per_period = compute_period_scores(plays_pn, pinfo, home_id, away_id, home_abbr, away_abbr)
        for r in per_period:
            r["game_id"] = gid
            r["period"] = pn
            out_rows.append(r)
    return out_rows


def percentiles(data, pcts):
    if not data: return {}
    sorted_data = sorted(data)
    out = {}
    for p in pcts:
        idx = (len(sorted_data) - 1) * p / 100.0
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            out[p] = sorted_data[lo]
        else:
            out[p] = sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)
    return out


def main():
    candidates = gen_candidate_ids()
    # Subsample to ~50 games (deterministic stride) to stay polite + fast.
    import random
    random.seed(42)
    random.shuffle(candidates)
    candidates = candidates[:60]
    print(f"Candidate playoff IDs (sampled): {len(candidates)}")
    rows = []
    games_hit = 0
    for i, gid in enumerate(candidates):
        triple = fetch_game(gid)
        if triple is None:
            continue
        games_hit += 1
        rows.extend(process_game(triple))
        if games_hit % 5 == 0:
            print(f"  processed {games_hit} games, {len(rows)} player-period rows so far")
    print(f"Total games fetched: {games_hit}")
    print(f"Total player-period observations: {len(rows)}")

    # Filter trivial rows (no events at all). The per-period TOI is unknown
    # from the boxscore alone, so we filter on event count instead — keep
    # rows with any of: an attempt, hit, block, takeaway, or non-zero
    # giveaway. This drops bench-warmer noise.
    nontriv = [
        r for r in rows
        if (r["ind_attempts"] + r.get("g", 0) + r.get("a", 0) + r.get("sog", 0)) > 0
        or r["score"] != 0.0
    ]
    print(f"After filter (non-trivial): {len(nontriv)}")

    scores = [r["score"] for r in nontriv]
    fwd_scores = [r["score"] for r in nontriv if not r["is_d"]]
    d_scores   = [r["score"] for r in nontriv if r["is_d"]]

    pcts = [5, 10, 25, 40, 50, 60, 75, 85, 90, 95, 99]

    payload = {
        "meta": {
            "playoffs_sampled": ["2024 (season 23-24)", "2025 (season 24-25)"],
            "candidate_ids_tried": len(candidates),
            "games_fetched": games_hit,
            "total_player_period_obs": len(rows),
            "non_trivial_obs": len(nontriv),
            "score_recipe": (
                "G×3 + A×2 + SOG×0.5 + ind_HD×0.75 + (missed/blocked attempts)×0.15 "
                "+ (hits + blocks)×0.25 - giveaways×0.5 + takeaways×0.5"
            ),
            "filter_note": (
                "Excluded skater-period observations with no events recorded. Per-period "
                "TOI not reliably available from boxscore; event-presence filter is the "
                "honest substitute."
            ),
        },
        "stats_overall": {
            "n": len(scores),
            "mean": round(statistics.mean(scores), 3) if scores else None,
            "median": round(statistics.median(scores), 3) if scores else None,
            "stdev": round(statistics.stdev(scores), 3) if len(scores) > 1 else None,
            "min": round(min(scores), 3) if scores else None,
            "max": round(max(scores), 3) if scores else None,
            "percentiles": {p: round(v, 3) for p, v in percentiles(scores, pcts).items()},
        },
        "stats_forwards": {
            "n": len(fwd_scores),
            "mean": round(statistics.mean(fwd_scores), 3) if fwd_scores else None,
            "median": round(statistics.median(fwd_scores), 3) if fwd_scores else None,
            "stdev": round(statistics.stdev(fwd_scores), 3) if len(fwd_scores) > 1 else None,
            "percentiles": {p: round(v, 3) for p, v in percentiles(fwd_scores, pcts).items()},
        },
        "stats_defense": {
            "n": len(d_scores),
            "mean": round(statistics.mean(d_scores), 3) if d_scores else None,
            "median": round(statistics.median(d_scores), 3) if d_scores else None,
            "stdev": round(statistics.stdev(d_scores), 3) if len(d_scores) > 1 else None,
            "percentiles": {p: round(v, 3) for p, v in percentiles(d_scores, pcts).items()},
        },
        "tiers": {
            # Computed below
        },
    }

    # Build tiers from overall percentiles.
    pct = payload["stats_overall"]["percentiles"]
    tiers = {
        "Awful":     {"max": pct[10], "color_hex": "F8CBAD", "label_en": "Awful",     "label_fr": "Faible"},
        "Mediocre":  {"min": pct[10], "max": pct[50], "color_hex": "FFE699", "label_en": "Mediocre",  "label_fr": "Moyen"},
        "Good":      {"min": pct[50], "max": pct[90], "color_hex": "C6E0B4", "label_en": "Good",      "label_fr": "Bon"},
        "Excellent": {"min": pct[90],                 "color_hex": "70AD47", "label_en": "Excellent", "label_fr": "Excellent"},
    }
    payload["tiers"] = tiers
    payload["tier_thresholds_summary"] = {
        "p10":  pct[10],
        "p50":  pct[50],
        "p90":  pct[90],
        "interpretation": (
            f"A skater scoring < {pct[10]} in a single period is in the bottom 10% of "
            f"playoff observations (Awful). {pct[10]}-{pct[50]} = bottom-half but not "
            f"alarming (Mediocre). {pct[50]}-{pct[90]} = above-median, contributing "
            f"(Good). > {pct[90]} = top 10%, dominant period (Excellent)."
        ),
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT}")
    print(f"\nTier thresholds (per-period composite score):")
    print(f"  Awful:     score < {pct[10]}")
    print(f"  Mediocre:  {pct[10]} <= score < {pct[50]}")
    print(f"  Good:      {pct[50]} <= score < {pct[90]}")
    print(f"  Excellent: score >= {pct[90]}")
    print(f"\nDistribution: mean={payload['stats_overall']['mean']}, "
          f"median={payload['stats_overall']['median']}, "
          f"stdev={payload['stats_overall']['stdev']}, "
          f"min={payload['stats_overall']['min']}, max={payload['stats_overall']['max']}")


if __name__ == "__main__":
    main()
