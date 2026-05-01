"""Tests for the Phase 2 + Phase 3 primitives: scouting profiles, tag query,
and cohort effect studies. Uses an in-memory SQLite for isolation."""
from __future__ import annotations

import sqlite3

import pytest
from lemieux.core import (
    ComparableMention,
    ContinuousAttribute,
    PlayerScoutingProfile,
    TagAssertion,
    find_players_by_tag,
    list_known_tags,
    list_player_tags,
    load_profile,
    upsert_profile,
)


@pytest.fixture
def in_memory_db():
    con = sqlite3.connect(":memory:")
    yield con
    con.close()


@pytest.fixture
def populated_db(in_memory_db):
    con = in_memory_db
    # Create empty skater_stats / team_stats so cohort-effect studies can run
    # cleanly with zero rows rather than blowing up on missing tables.
    con.executescript("""
        CREATE TABLE skater_stats (
            name TEXT, position TEXT, season TEXT, stype INTEGER,
            sit TEXT, split TEXT, toi REAL, xgf REAL, xga REAL
        );
        CREATE TABLE team_stats (
            season TEXT, stype INTEGER, sit TEXT,
            toi REAL, xgf REAL, xga REAL
        );
    """)
    profiles = [
        PlayerScoutingProfile(
            name="Alpha One", position="C", extracted_at="2026-04-28",
            attributes=[ContinuousAttribute(name="skating", value=4.0, confidence=0.9)],
            tags=[
                TagAssertion(tag="warrior", confidence=0.9, source_quote="grit", source_url="http://x"),
                TagAssertion(tag="top_six", confidence=0.85, source_quote="1C", source_url="http://x"),
            ],
            comp_mentions=[ComparableMention(comp_name="Bravo Two", source_quote="reminds me of",
                                             source_url="http://y", polarity="style")],
        ),
        PlayerScoutingProfile(
            name="Bravo Two", position="R", extracted_at="2026-04-28",
            attributes=[ContinuousAttribute(name="skating", value=3.0, confidence=0.8)],
            tags=[TagAssertion(tag="warrior", confidence=0.65, source_quote="hard", source_url="http://x")],
        ),
        PlayerScoutingProfile(
            name="Charlie Three", position="D", extracted_at="2026-04-28",
            attributes=[ContinuousAttribute(name="skating", value=5.0, confidence=0.95)],
            tags=[
                TagAssertion(tag="offensive_d", confidence=0.95, source_quote="mobile", source_url="http://x"),
                TagAssertion(tag="puck_mover", confidence=0.9, source_quote="passing", source_url="http://x"),
            ],
        ),
    ]
    for p in profiles:
        upsert_profile(con, p)
    return con


# ----- scouting (persistence + roundtrip) -----

def test_upsert_and_load_roundtrip(in_memory_db):
    con = in_memory_db
    profile = PlayerScoutingProfile(
        name="Test Player", position="C", extracted_at="2026-04-28",
        attributes=[
            ContinuousAttribute(name="skating", value=4.0, confidence=0.9, source_count=2),
        ],
        tags=[
            TagAssertion(tag="warrior", confidence=0.85, source_quote="grit", source_url="http://example.com"),
        ],
        comp_mentions=[
            ComparableMention(comp_name="Comp One", source_quote="reminds me of", source_url="http://y"),
        ],
        sources=["http://example.com"],
    )
    upsert_profile(con, profile)
    loaded = load_profile(con, "Test Player", "C")
    assert loaded is not None
    assert loaded.name == "Test Player"
    assert loaded.position == "C"
    assert len(loaded.attributes) == 1
    assert loaded.attributes[0].name == "skating"
    assert loaded.attributes[0].value == 4.0
    assert len(loaded.tags) == 1
    assert loaded.tags[0].tag == "warrior"
    assert loaded.has_tag("warrior", min_confidence=0.6)
    assert not loaded.has_tag("warrior", min_confidence=0.9)
    assert len(loaded.comp_mentions) == 1
    assert loaded.comp_mentions[0].comp_name == "Comp One"


def test_upsert_replaces_child_rows(in_memory_db):
    con = in_memory_db
    p1 = PlayerScoutingProfile(
        name="X", position="C", extracted_at="2026-04-28",
        tags=[TagAssertion(tag="sniper", confidence=0.9, source_quote="", source_url="")],
    )
    upsert_profile(con, p1)
    # Re-extract with different tags — old tags should be wiped, not unioned.
    p2 = PlayerScoutingProfile(
        name="X", position="C", extracted_at="2026-04-29",
        tags=[TagAssertion(tag="playmaker", confidence=0.85, source_quote="", source_url="")],
    )
    upsert_profile(con, p2)
    loaded = load_profile(con, "X", "C")
    assert len(loaded.tags) == 1
    assert loaded.tags[0].tag == "playmaker"


# ----- tag query -----

def test_find_players_by_tag_min_confidence(populated_db):
    con = populated_db
    # warrior at min_conf 0.7 → only Alpha (0.9), not Bravo (0.65)
    high = find_players_by_tag(con, "warrior", min_confidence=0.7)
    assert [p.name for p in high] == ["Alpha One"]
    # warrior at min_conf 0.6 → both
    low = find_players_by_tag(con, "warrior", min_confidence=0.6)
    assert sorted(p.name for p in low) == ["Alpha One", "Bravo Two"]


def test_find_players_by_tag_position_filter(populated_db):
    con = populated_db
    # warrior cohort filtered to D — empty (Alpha is C, Bravo is R)
    d_only = find_players_by_tag(con, "warrior", min_confidence=0.6, position="D")
    assert d_only == []
    # warrior, position in (C, R) — both
    cr = find_players_by_tag(con, "warrior", min_confidence=0.6, position=("C", "R"))
    assert sorted(p.name for p in cr) == ["Alpha One", "Bravo Two"]


def test_list_known_tags(populated_db):
    con = populated_db
    tags = dict(list_known_tags(con, min_confidence=0.6))
    assert tags["warrior"] == 2
    assert tags["top_six"] == 1
    assert tags["offensive_d"] == 1
    # At min_confidence 0.7, Bravo's warrior (0.65) drops out
    tags_high = dict(list_known_tags(con, min_confidence=0.7))
    assert tags_high["warrior"] == 1


def test_list_player_tags_ordered_by_confidence(populated_db):
    con = populated_db
    tags = list_player_tags(con, "Alpha One", "C", min_confidence=0.0)
    # Order: warrior (0.9), top_six (0.85)
    assert [t.tag for t in tags] == ["warrior", "top_six"]
    assert [t.confidence for t in tags] == [0.9, 0.85]


# ----- cohort split study (functional with tiny synthetic data) -----

def test_tag_split_study_returns_zero_n_when_no_iso_data(populated_db):
    """Tag exists in scouting but skater_stats has zero rows for those players →
    cohort filters drop them and the study returns n=0 cleanly."""
    from lemieux.core import tag_split_study
    con = populated_db
    # skater_stats table is empty, so reg_toi and playoff_toi are 0 for every
    # tagged player; default thresholds (200 / 100) drop them all.
    result = tag_split_study(con, "warrior")
    assert result.tag == "warrior"
    assert result.n_players == 0
    assert result.mean_delta_iso_net == 0.0


def test_tag_introduction_study_scaffold(populated_db):
    from lemieux.core import tag_introduction_study
    con = populated_db
    res = tag_introduction_study(con, "warrior")
    assert res.tag == "warrior"
    assert res.n_events == 0
    assert "Awaits per-game boxscore-presence ingest" in res.notes
