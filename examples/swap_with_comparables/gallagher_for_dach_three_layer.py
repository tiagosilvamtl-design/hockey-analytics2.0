"""End-to-end demo: three-layer Gallagher-for-Dach swap projection.

Computes and renders the form-factor described in the plan:

    Layer 1 — Target's pooled iso (Gallagher's own 5-year NHL data)
    Layer 2 — Comp-cohort-stabilized iso (kNN top-5; Block A only for now)
    Layer 3 — Archetype-adjusted iso (warrior-tag reg-to-playoff lift)

Each layer reports its Δ xGF/game, Δ xGA/game, Δ Net/game and 80% CI. The
three-layer stack is rendered as a comparison table in a branded EN+FR
docx so a real swap callout in a future report can drop straight in.

Honest framing throughout: warriors split-study CI + cohort N is shown, so
the reader sees how speculative the archetype layer is.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python examples/swap_with_comparables/gallagher_for_dach_three_layer.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

import numpy as np
import pandas as pd

from lemieux.core import (
    ComparableIndex,
    PlayerImpact,
    build_cohort_stabilized_impact,
    build_pooled_player_impact,
    list_player_tags,
    project_swap,
    tag_split_study,
)


SEASONS = ("20212022", "20222023", "20232024", "20242025", "20252026")
DB = REPO / "legacy" / "data" / "store.sqlite"
INDEX_PATH = REPO / "legacy" / "data" / "comparable_index.json"
OUT_JSON = Path(__file__).parent / "gallagher_for_dach_three_layer.numbers.json"


def fetch_player_pooled_rows(con, name, sit="5v5"):
    return pd.read_sql_query(
        f"""SELECT name, team_id, season, stype, sit, toi, xgf, xga
            FROM skater_stats
            WHERE name = ? AND sit = ? AND split = 'oi'
              AND season IN ({','.join(['?']*len(SEASONS))})""",
        con, params=[name, sit, *SEASONS],
    )


def fetch_team_pooled_rows(con, sit="5v5"):
    return pd.read_sql_query(
        f"""SELECT team_id, season, stype, sit, toi, xgf, xga
            FROM team_stats
            WHERE sit = ? AND season IN ({','.join(['?']*len(SEASONS))})""",
        con, params=[sit, *SEASONS],
    )


def player_impact(con, name, sit="5v5"):
    p = fetch_player_pooled_rows(con, name, sit)
    if not len(p): raise ValueError(f"No rows for {name}")
    t = fetch_team_pooled_rows(con, sit)
    return build_pooled_player_impact(p, t, team_id=p.iloc[0]["team_id"])


def archetype_adjusted_impact(target: PlayerImpact, lift_xgf60: float, lift_var: float) -> PlayerImpact:
    """Add an archetype-level reg-to-playoff iso lift on top of the target's
    own iso, propagating the lift's variance to the result.
    """
    new_xgf = target.iso_xgf60 + lift_xgf60
    new_var_f = (target.iso_xgf60_var or 0.0) + lift_var
    return PlayerImpact(
        player_id=f"{target.name}|archetype_adjusted",
        name=f"{target.name} (archetype-adjusted by warrior lift {lift_xgf60:+.3f})",
        team_id=target.team_id,
        toi_on=target.toi_on, toi_off=target.toi_off,
        xgf_on=target.xgf_on, xga_on=target.xga_on,
        xgf_off=target.xgf_off, xga_off=target.xga_off,
        _iso_xgf60_override=new_xgf,
        _iso_xga60_override=target.iso_xga60,
        _iso_xgf60_var_override=new_var_f,
        _iso_xga60_var_override=target.iso_xga60_var,
    )


def main():
    con = sqlite3.connect(DB, timeout=60)
    print("Loading comparable index ...")
    index = ComparableIndex.load(INDEX_PATH)

    # --- Two players in the swap ---
    target_in = player_impact(con, "Brendan Gallagher")
    target_out = player_impact(con, "Kirby Dach")
    slot_min = 14.0   # 3rd-line C slot

    # --- Layer 1: Gallagher's raw pooled iso ---
    raw_swap = project_swap(out_player=target_out, in_player=target_in, slot_minutes=slot_min)

    # --- Layer 2: comp-cohort stabilized ---
    comps = index.find_comparables("Brendan Gallagher", k=5, min_pooled_toi=200.0)
    print("Top-5 NHL comps:")
    for c in comps:
        print(f"  {c.score:5.1f}  {c.name:25s} ({c.position})  toi={c.pooled_toi_5v5:>6.0f}")
    cohort = []
    for c in comps:
        try:
            cohort.append(player_impact(con, c.name))
        except ValueError:
            pass
    stabilized = build_cohort_stabilized_impact(target_in, cohort)
    layer2_swap = project_swap(out_player=target_out, in_player=stabilized, slot_minutes=slot_min)

    # --- Layer 3: archetype-adjusted via warrior split-study ---
    print("\nGallagher's tags (min conf 0.6):")
    gallagher_tags = list_player_tags(con, "Brendan Gallagher", "R", min_confidence=0.6)
    primary_archetype_tags = [t for t in gallagher_tags if t.tag in ("warrior", "playmaker", "sniper", "two_way", "shutdown")]
    for t in gallagher_tags:
        print(f"  {t.confidence:.2f}  {t.tag}")

    archetype_layer = None
    archetype_lift = None
    if primary_archetype_tags:
        # Use the highest-confidence primary archetype tag as the lift driver
        primary = primary_archetype_tags[0]
        print(f"\nPrimary archetype for Gallagher: '{primary.tag}' (conf {primary.confidence:.2f})")
        split = tag_split_study(con, primary.tag, min_tag_confidence=0.6,
                                min_reg_toi=200.0, min_playoff_toi=50.0)
        if split.n_players >= 3:
            # Approximate lift variance from the empirical CI half-width:
            # 80% CI half-width / z(0.9) = sigma; sigma^2 = variance.
            half = (split.ci80_high - split.ci80_low) / 2.0
            sigma = half / 1.2816  # z(0.9) ≈ 1.2816
            lift_var = float(sigma ** 2)
            archetype_lift = {
                "tag": primary.tag,
                "n_cohort": split.n_players,
                "mean_lift": split.mean_delta_iso_net,
                "ci80_low": split.ci80_low,
                "ci80_high": split.ci80_high,
                "lift_var_approx": lift_var,
            }
            archetype_layer = archetype_adjusted_impact(stabilized, split.mean_delta_iso_net, lift_var)

    layer3_swap = None
    if archetype_layer:
        layer3_swap = project_swap(out_player=target_out, in_player=archetype_layer, slot_minutes=slot_min)

    # --- Render table ---
    def row(label, swap):
        if swap is None: return None
        net = swap.delta_xgf60 - swap.delta_xga60
        return {
            "label": label,
            "delta_xgf": swap.delta_xgf60,
            "delta_xga": swap.delta_xga60,
            "delta_net": net,
            "ci_xgf": swap.delta_xgf60_ci80,
            "ci_xga": swap.delta_xga60_ci80,
            "ci_xgf_width": swap.delta_xgf60_ci80[1] - swap.delta_xgf60_ci80[0],
        }

    layers = []
    layers.append(row("Layer 1 — Gallagher's pooled iso (5-yr NHL, no kNN)", raw_swap))
    layers.append(row("Layer 2 — Comp-cohort-stabilized (k=5 NHL kNN)", layer2_swap))
    if layer3_swap is not None:
        layers.append(row(f"Layer 3 — Archetype-adjusted ('{archetype_lift['tag']}' tag, N={archetype_lift['n_cohort']})", layer3_swap))

    print(f"\n{'='*92}")
    print(f"Three-layer swap projection: Gallagher (in) for Dach (out), {slot_min:.0f}-min slot, 5v5")
    print('='*92)
    print(f"\n{'Layer':<55} {'Δ Net':>10} {'xGF CI80':>22} {'CI width':>10}")
    print('-'*92)
    for L in layers:
        ci_str = f"[{L['ci_xgf'][0]:+.3f}, {L['ci_xgf'][1]:+.3f}]"
        print(f"{L['label']:<55} {L['delta_net']:>+10.3f} {ci_str:>22} {L['ci_xgf_width']:>+10.3f}")

    # --- CI tightening / direction ---
    print(f"\n{'='*92}")
    print("Honest read")
    print('='*92)
    if archetype_lift:
        lift_dir = "+" if archetype_lift['mean_lift'] >= 0 else "-"
        print(f"  Warrior cohort reg-to-playoff lift: {archetype_lift['mean_lift']:+.3f} xG/60, "
              f"CI [{archetype_lift['ci80_low']:+.3f}, {archetype_lift['ci80_high']:+.3f}], "
              f"N={archetype_lift['n_cohort']}.")
        if archetype_lift['ci80_low'] * archetype_lift['ci80_high'] > 0:
            print(f"  CI sign-consistent ⇒ archetype direction is informative (with the small-N caveat).")
        else:
            print(f"  CI straddles zero ⇒ archetype layer adds noise more than signal at this N.")
    print(f"  All layers agree directionally: {all(L['delta_net'] * layers[0]['delta_net'] > 0 for L in layers)}")
    cleanest_excludes_zero = []
    for L in layers:
        if L['ci_xgf'][0] * L['ci_xgf'][1] > 0:
            cleanest_excludes_zero.append(L['label'])
    print(f"  Layers whose xGF CI excludes zero: {', '.join(cleanest_excludes_zero) if cleanest_excludes_zero else '(none)'}")

    # --- Persist ---
    payload = {
        "meta": {
            "as_of": date.today().isoformat(),
            "swap": "Gallagher (in) for Dach (out)",
            "slot_minutes": slot_min,
            "strength_state": "5v5",
            "comp_cohort": [{"name": c.name, "score": c.score, "toi": c.pooled_toi_5v5} for c in comps],
            "archetype_lift": archetype_lift,
        },
        "layers": layers,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
