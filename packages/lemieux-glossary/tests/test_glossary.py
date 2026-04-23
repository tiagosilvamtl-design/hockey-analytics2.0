"""Glossary integrity: every term has EN + FR + at least one caveat."""
from __future__ import annotations

import pytest

from lemieux.glossary import get_term, list_terms, render_for_markdown


def test_every_term_has_both_languages():
    for term in list_terms():
        assert term.en.short and term.en.long, f"{term.id} missing EN"
        assert term.fr.short and term.fr.long, f"{term.id} missing FR"


def test_every_term_has_at_least_one_caveat():
    # Pool baseline is the only allowed caveat-less entry (it's a methodology note).
    # We still enforce at least one.
    for term in list_terms():
        assert len(term.caveats) >= 1, f"{term.id} must have at least one caveat"


def test_known_term_ids_present():
    required = {
        "expected_goals", "xgf60", "xga60",
        "iso_xgf60", "iso_xga60", "iso_net",
        "confidence_interval", "pooled_baseline", "toi",
    }
    have = {t.id for t in list_terms()}
    missing = required - have
    assert not missing, f"missing required term ids: {missing}"


def test_get_term_unknown_raises():
    with pytest.raises(KeyError):
        get_term("this-is-not-a-real-term")


def test_render_markdown_en_and_fr():
    en = render_for_markdown("iso_xgf60", lang="en")
    fr = render_for_markdown("iso_xgf60", lang="fr")
    assert "Isolated xGF/60" in en
    assert "xGF/60 isolé" in fr
    assert en != fr


def test_formula_when_present_is_in_markdown():
    md = render_for_markdown("iso_xgf60", lang="en")
    assert "Formula" in md
