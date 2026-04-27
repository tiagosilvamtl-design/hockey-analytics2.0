"""Game 4 — Slafkovský pre/post-hit bucket analysis.

The hit: Max Crozier (TBL D, the Game-4 lineup-change-in) on Juraj Slafkovský
(MTL, #20) at P2 17:48 (2:12 remaining), neutral zone.

Pattern mirrors the Game 3 analysis after the Hagel fight: split all events
into PRE-hit and POST-hit buckets, compute Slafkovský individual stats and
on-ice 5v5 territorial / scoring stats per bucket.

  PRE-hit  : P1 entire + P2 from 0:00 to 17:48
  POST-hit : P2 from 17:48 to 20:00 + P3 entire

Output: examples/habs_round1_2026/game4_slaf_hit.numbers.json
"""

from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import truststore; truststore.inject_into_ssl()
import requests

GAME_ID = "2025030124"
SLAF_PID = 8483515
HIT_PERIOD = 2
HIT_SEC = 17 * 60 + 48   # 17:48 elapsed
HD_DISTANCE = 22.0
SHOT_TYPES = {"shot-on-goal", "missed-shot", "blocked-shot", "goal"}
OUT = Path(__file__).parent / "game4_slaf_hit.numbers.json"


def time_to_sec(t):
    if not t: return 0
    try:
        m, s = t.split(":"); return int(m) * 60 + int(s)
    except Exception:
        return 0


def shot_distance(x, y):
    if x is None or y is None: return None
    return math.sqrt((abs(x) - 89.0) ** 2 + (y or 0.0) ** 2)


def is_pre(period: int, sec: int) -> bool:
    if period == 1: return True
    if period == HIT_PERIOD and sec < HIT_SEC: return True
    return False


def main() -> int:
    pbp = requests.get(f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play", timeout=30).json()
    shifts = requests.get(f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={GAME_ID}",
                          timeout=30).json().get("data", [])

    home_id = pbp["homeTeam"]["id"]
    away_id = pbp["awayTeam"]["id"]
    home_abbr = pbp["homeTeam"]["abbrev"]
    away_abbr = pbp["awayTeam"]["abbrev"]
    mtl_id = home_id if home_abbr == "MTL" else away_id
    tbl_id = away_id if home_abbr == "MTL" else home_id

    # Build Slafkovský shift intervals per period.
    slaf_shifts = [s for s in shifts if s.get("playerId") == SLAF_PID]
    by_period = {1: [], 2: [], 3: []}
    for s in slaf_shifts:
        p = s.get("period")
        if p not in by_period: continue
        st = time_to_sec(s.get("startTime"))
        en = time_to_sec(s.get("endTime"))
        if en > st:
            by_period[p].append((st, en))

    def slaf_on_ice(period: int, sec: int) -> bool:
        for st, en in by_period.get(period, []):
            if st <= sec <= en:
                return True
        return False

    def empty_bucket(label: str) -> dict:
        return {
            "label": label,
            "period_range": "",
            # Slafkovský individual
            "slaf_sog": 0, "slaf_missed": 0, "slaf_blocked": 0, "slaf_goals": 0,
            "slaf_hits_for": 0, "slaf_hits_against": 0,
            "slaf_blocks_made": 0,
            "slaf_giveaways": 0, "slaf_takeaways": 0,
            # On-ice 5v5
            "mtl_cf_5v5": 0, "tbl_cf_5v5": 0,
            "mtl_hdcf_5v5": 0, "tbl_hdcf_5v5": 0,
            "mtl_sog_oi": 0, "tbl_sog_oi": 0,
            "mtl_goals_oi": 0, "tbl_goals_oi": 0,
            # TOI
            "slaf_toi_sec": 0,
            "shifts_count": 0,
        }

    pre = empty_bucket("PRE-hit: P1 + P2 up to 17:48")
    pre["period_range"] = "P1 (0:00-20:00) + P2 (0:00-17:48)"
    post = empty_bucket("POST-hit: P2 17:48 onward + P3")
    post["period_range"] = "P2 (17:48-20:00) + P3 (full)"

    # TOI calculation
    for p in (1, 2, 3):
        for st, en in by_period.get(p, []):
            if p == 1:
                pre["slaf_toi_sec"] += en - st
            elif p == 3:
                post["slaf_toi_sec"] += en - st
            else:  # p == 2: split at HIT_SEC
                if en <= HIT_SEC:
                    pre["slaf_toi_sec"] += en - st
                elif st >= HIT_SEC:
                    post["slaf_toi_sec"] += en - st
                else:
                    pre["slaf_toi_sec"] += HIT_SEC - st
                    post["slaf_toi_sec"] += en - HIT_SEC

    pre["shifts_count"] = sum(
        1 for p in (1, 2)
        for st, en in by_period.get(p, [])
        if (p == 1) or (en <= HIT_SEC) or (st < HIT_SEC and en > HIT_SEC)
    )
    post["shifts_count"] = sum(
        1 for p in (2, 3)
        for st, en in by_period.get(p, [])
        if (p == 3) or (st >= HIT_SEC) or (st < HIT_SEC and en > HIT_SEC)
    )

    # Walk the play-by-play
    for play in pbp.get("plays", []):
        pn = (play.get("periodDescriptor") or {}).get("number")
        if pn not in (1, 2, 3): continue
        sec = time_to_sec(play.get("timeInPeriod"))
        bucket = pre if is_pre(pn, sec) else post
        typ = play.get("typeDescKey") or ""
        d = play.get("details") or {}
        owner = d.get("eventOwnerTeamId")
        is_5v5 = (play.get("situationCode") or "") == "1551"

        # Slafkovský individual events
        if typ in SHOT_TYPES:
            shooter = d.get("shootingPlayerId") or d.get("scoringPlayerId")
            if shooter == SLAF_PID:
                if typ == "shot-on-goal": bucket["slaf_sog"] += 1
                elif typ == "missed-shot": bucket["slaf_missed"] += 1
                elif typ == "blocked-shot": bucket["slaf_blocked"] += 1
                elif typ == "goal":
                    bucket["slaf_goals"] += 1
                    bucket["slaf_sog"] += 1
            blocker = d.get("blockingPlayerId")
            if typ == "blocked-shot" and blocker == SLAF_PID:
                bucket["slaf_blocks_made"] += 1
        if typ == "hit":
            if d.get("hittingPlayerId") == SLAF_PID: bucket["slaf_hits_for"] += 1
            if d.get("hitteePlayerId") == SLAF_PID: bucket["slaf_hits_against"] += 1
        if typ == "giveaway" and d.get("playerId") == SLAF_PID: bucket["slaf_giveaways"] += 1
        if typ == "takeaway" and d.get("playerId") == SLAF_PID: bucket["slaf_takeaways"] += 1

        # On-ice 5v5 events while Slaf is on
        if typ in SHOT_TYPES and slaf_on_ice(pn, sec):
            x = d.get("xCoord"); y = d.get("yCoord")
            dist = shot_distance(x, y)
            is_hd = dist is not None and dist <= HD_DISTANCE
            if is_5v5:
                if owner == mtl_id:
                    bucket["mtl_cf_5v5"] += 1
                    if is_hd: bucket["mtl_hdcf_5v5"] += 1
                elif owner == tbl_id:
                    bucket["tbl_cf_5v5"] += 1
                    if is_hd: bucket["tbl_hdcf_5v5"] += 1
            # SOG/goals all-strength while on-ice
            if typ in ("shot-on-goal", "goal"):
                if owner == mtl_id: bucket["mtl_sog_oi"] += 1
                elif owner == tbl_id: bucket["tbl_sog_oi"] += 1
            if typ == "goal":
                if owner == mtl_id: bucket["mtl_goals_oi"] += 1
                elif owner == tbl_id: bucket["tbl_goals_oi"] += 1

    # Derived rates
    def pct(a, b): return None if (a + b) == 0 else round(100 * a / (a + b), 1)
    for bk in (pre, post):
        bk["mtl_cf_pct_5v5"] = pct(bk["mtl_cf_5v5"], bk["tbl_cf_5v5"])
        bk["mtl_hdcf_pct_5v5"] = pct(bk["mtl_hdcf_5v5"], bk["tbl_hdcf_5v5"])
        bk["slaf_toi_min"] = round(bk["slaf_toi_sec"] / 60.0, 2)
        bk["mtl_xg_share_5v5"] = bk["mtl_cf_pct_5v5"]   # approximation; xG model unavailable

    payload = {
        "meta": {
            "game_id": GAME_ID,
            "matchup": f"{away_abbr} @ {home_abbr}",
            "hit_event": {
                "period": HIT_PERIOD,
                "time_elapsed": f"{HIT_SEC // 60:02d}:{HIT_SEC % 60:02d}",
                "time_remaining_in_period": f"{(20*60 - HIT_SEC) // 60:02d}:{(20*60 - HIT_SEC) % 60:02d}",
                "hitter": "Max Crozier (TBL D)",
                "hittee": "Juraj Slafkovský (MTL L)",
                "zone": "Neutral",
                "story_hook": (
                    "Crozier was the very defenseman Tampa inserted for Game 4 — the "
                    "Carlile-out / Crozier-in swap projected at +0.11 net xG/game pre-game."
                ),
            },
            "method_note": (
                "5v5 events use NHL.com situationCode='1551'. HDCF proxy: shot from "
                "<= 22 ft of net. Slafkovský on-ice attribution uses NHL.com shift "
                "chart (post-game; complete for P1, P2, P3). Sample is one game; read "
                "as descriptive, not predictive."
            ),
        },
        "pre": pre,
        "post": post,
        "deltas": {
            "slaf_sog": post["slaf_sog"] - pre["slaf_sog"],
            "slaf_hits_against": post["slaf_hits_against"] - pre["slaf_hits_against"],
            "slaf_toi_min": round(post["slaf_toi_min"] - pre["slaf_toi_min"], 2),
            "mtl_cf_pct_5v5_pp": (
                round((post.get("mtl_cf_pct_5v5") or 0) - (pre.get("mtl_cf_pct_5v5") or 0), 1)
                if pre.get("mtl_cf_pct_5v5") is not None and post.get("mtl_cf_pct_5v5") is not None else None
            ),
            "mtl_hdcf_pct_5v5_pp": (
                round((post.get("mtl_hdcf_pct_5v5") or 0) - (pre.get("mtl_hdcf_pct_5v5") or 0), 1)
                if pre.get("mtl_hdcf_pct_5v5") is not None and post.get("mtl_hdcf_pct_5v5") is not None else None
            ),
        },
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}\n")
    print(f"PRE-hit  ({pre['period_range']}):")
    print(f"  Slaf TOI: {pre['slaf_toi_min']:.2f} min, shifts={pre['shifts_count']}")
    print(f"  Slaf individual: G {pre['slaf_goals']}  SOG {pre['slaf_sog']}  missed {pre['slaf_missed']}  blocked-shots-by-Slaf {pre['slaf_blocks_made']}  hits-for {pre['slaf_hits_for']}  hits-against {pre['slaf_hits_against']}")
    print(f"  On-ice 5v5: MTL Corsi {pre['mtl_cf_5v5']}-{pre['tbl_cf_5v5']} ({pre['mtl_cf_pct_5v5']}%)  HDCF {pre['mtl_hdcf_5v5']}-{pre['tbl_hdcf_5v5']} ({pre['mtl_hdcf_pct_5v5']}%)")
    print(f"  Goals on-ice: MTL {pre['mtl_goals_oi']}  TBL {pre['tbl_goals_oi']}")
    print()
    print(f"POST-hit ({post['period_range']}):")
    print(f"  Slaf TOI: {post['slaf_toi_min']:.2f} min, shifts={post['shifts_count']}")
    print(f"  Slaf individual: G {post['slaf_goals']}  SOG {post['slaf_sog']}  missed {post['slaf_missed']}  blocked-shots-by-Slaf {post['slaf_blocks_made']}  hits-for {post['slaf_hits_for']}  hits-against {post['slaf_hits_against']}")
    print(f"  On-ice 5v5: MTL Corsi {post['mtl_cf_5v5']}-{post['tbl_cf_5v5']} ({post['mtl_cf_pct_5v5']}%)  HDCF {post['mtl_hdcf_5v5']}-{post['tbl_hdcf_5v5']} ({post['mtl_hdcf_pct_5v5']}%)")
    print(f"  Goals on-ice: MTL {post['mtl_goals_oi']}  TBL {post['tbl_goals_oi']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
