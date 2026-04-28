"""Phase 3 — tag-cohort effect studies, generic over the chosen tag.

Two study designs:
  - tag_split_study(tag, ...): for every player tagged X, compute their
    reg-season vs playoff iso impact delta. Aggregate the cohort's deltas
    with an 80% empirical CI. Answers questions of the form
    "do warriors over-deliver in playoffs?" — runnable for ANY tag X.

  - tag_introduction_study(tag, ...): scaffold for the event-study design
    (a tag-cohort player dressing for a playoff game after being scratched).
    The full implementation depends on richer game-presence flips data than
    is currently in the store; this module exposes the interface so the
    eventual analyzer slots in cleanly.

The split-study output feeds back into the swap engine via the
`with_archetype_lift(tag)` decorator on `build_cohort_stabilized_impact`
(in comparable.py) once Phase 2 ships an audited tag corpus.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np

from .tags import find_players_by_tag, TaggedPlayer


@dataclass
class TagSplitStudyResult:
    """Output of `tag_split_study()`."""
    tag: str
    n_players: int                # cohort size after filtering
    mean_delta_iso_net: float     # average (playoff_iso_net - reg_iso_net)
    median_delta_iso_net: float
    ci80_low: float
    ci80_high: float
    per_player_deltas: list[dict]  # provenance: each player's contribution


def _pooled_iso_net(con: sqlite3.Connection, name: str, position: str,
                    seasons: tuple[str, ...], stype: int, sit: str = "5v5") -> tuple[float, float]:
    """Return (iso_net60, total_toi) for a player across (seasons, stype, sit).

    Uses the framework's standard on/off iso pattern: per60(player on-ice)
    minus per60(team-without-player).
    """
    if not seasons:
        return 0.0, 0.0
    ph = ",".join(["?"] * len(seasons))
    p_rows = con.execute(
        f"""
        SELECT toi, xgf, xga FROM skater_stats
        WHERE name = ? AND position = ? AND season IN ({ph}) AND stype = ? AND sit = ? AND split = 'oi'
        """,
        (name, position, *seasons, stype, sit),
    ).fetchall()
    if not p_rows:
        return 0.0, 0.0
    p_toi = sum(r[0] or 0.0 for r in p_rows)
    p_xgf = sum(r[1] or 0.0 for r in p_rows)
    p_xga = sum(r[2] or 0.0 for r in p_rows)
    if p_toi <= 0:
        return 0.0, 0.0
    t_rows = con.execute(
        f"""
        SELECT toi, xgf, xga FROM team_stats
        WHERE season IN ({ph}) AND stype = ? AND sit = ?
        """,
        (*seasons, stype, sit),
    ).fetchall()
    t_toi = sum(r[0] or 0.0 for r in t_rows)
    t_xgf = sum(r[1] or 0.0 for r in t_rows)
    t_xga = sum(r[2] or 0.0 for r in t_rows)
    toi_off = max(t_toi - p_toi, 1.0)
    xgf_off = max(t_xgf - p_xgf, 0.0)
    xga_off = max(t_xga - p_xga, 0.0)
    iso_xgf60 = (p_xgf * 60.0 / p_toi) - (xgf_off * 60.0 / toi_off)
    iso_xga60 = (p_xga * 60.0 / p_toi) - (xga_off * 60.0 / toi_off)
    return (iso_xgf60 - iso_xga60), p_toi


def tag_split_study(
    con: sqlite3.Connection,
    tag: str,
    seasons: tuple[str, ...] = ("20212022", "20222023", "20232024", "20242025", "20252026"),
    min_tag_confidence: float = 0.6,
    min_reg_toi: float = 200.0,
    min_playoff_toi: float = 100.0,
) -> TagSplitStudyResult:
    """Reg-season vs playoff iso-net delta for the cohort tagged `tag`.

    The cohort is defined by:
      - Tagged with `tag` at confidence >= min_tag_confidence in the corpus
      - Has >= min_reg_toi in reg-season (stype=2, 5v5) across `seasons`
      - Has >= min_playoff_toi in playoffs (stype=3, 5v5) across `seasons`

    Returns a sample-mean delta + empirical 80% CI from the cohort's delta
    distribution. CI is computed via the cohort's empirical 10th and 90th
    percentiles — not bootstrapped — so it reflects observed dispersion
    rather than hypothetical resampling. Honest about cohort size.
    """
    cohort = find_players_by_tag(con, tag, min_confidence=min_tag_confidence)
    per_player: list[dict] = []
    for p in cohort:
        reg_iso_net, reg_toi = _pooled_iso_net(con, p.name, p.position, seasons, stype=2)
        play_iso_net, play_toi = _pooled_iso_net(con, p.name, p.position, seasons, stype=3)
        if reg_toi < min_reg_toi or play_toi < min_playoff_toi:
            continue
        per_player.append({
            "name": p.name, "position": p.position,
            "reg_toi": reg_toi, "playoff_toi": play_toi,
            "reg_iso_net": reg_iso_net, "playoff_iso_net": play_iso_net,
            "delta": play_iso_net - reg_iso_net,
            "tag_confidence": p.confidence,
        })
    deltas = [r["delta"] for r in per_player]
    if not deltas:
        return TagSplitStudyResult(
            tag=tag, n_players=0,
            mean_delta_iso_net=0.0, median_delta_iso_net=0.0,
            ci80_low=0.0, ci80_high=0.0,
            per_player_deltas=[],
        )
    arr = np.asarray(deltas, dtype=np.float64)
    return TagSplitStudyResult(
        tag=tag, n_players=len(per_player),
        mean_delta_iso_net=float(np.mean(arr)),
        median_delta_iso_net=float(np.median(arr)),
        ci80_low=float(np.percentile(arr, 10)),
        ci80_high=float(np.percentile(arr, 90)),
        per_player_deltas=per_player,
    )


@dataclass
class TagIntroductionStudyResult:
    """Placeholder result for the event-study design (Phase 3b)."""
    tag: str
    n_events: int
    mean_oncie_xgf_pct_delta: float | None = None
    notes: str = ""


def tag_introduction_study(con: sqlite3.Connection, tag: str) -> TagIntroductionStudyResult:
    """Stub: scaffold for the introduction-effect design.

    Real implementation requires per-game presence flips (boxscore-presence
    deltas across games) which the framework currently has via per-game
    boxscore fetches but not in a queryable table form. To be wired up once
    the boxscore-presence ingest lands.
    """
    return TagIntroductionStudyResult(
        tag=tag, n_events=0,
        notes=("Scaffold only. Awaits per-game boxscore-presence ingest. "
               "Full design: identify tag-cohort players' playoff dressing flips, "
               "compute team iso-adjusted xGF% delta in their on-ice minutes vs "
               "matched comparison games, aggregate with CI."),
    )
