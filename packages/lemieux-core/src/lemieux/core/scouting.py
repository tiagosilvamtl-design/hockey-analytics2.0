"""GenAI scouting layer — continuous attributes + categorical archetype tags
extracted from per-player scouting/beat-coverage text.

This module defines the schemas the corpus builder writes and the engine
consumes. The builder itself (web search + LLM extraction) lives in
`tools/build_scouting_corpus.py`.

Two layers per player:
  - Continuous attributes: 1-5 scale + per-attribute confidence
        skating, hands, hockey_iq, compete, size, speed, shot, vision, defense
  - Categorical tags: multi-label boolean with provenance + confidence
        e.g. {warrior, playmaker, sniper, two-way, agitator, shutdown,
              power-forward, puck-mover, rover, clutch, streaky, ...}
        Each tag carries the source quote that triggered it for auditability.

Plus a "reminds me of" extraction layer:
  - List of explicit comparable mentions from beat coverage
  - Each item: comp_name, source URL, quote, polarity (style|trajectory|both)
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

# Canonical attribute IDs; numeric values 1-5; confidence 0-1.
# Skater attributes + goalie attributes are unioned because they live in the
# same scouting_attributes table (position field disambiguates).
CONTINUOUS_ATTRIBUTES = (
    # Skater
    "skating", "hands", "hockey_iq", "compete", "size", "speed",
    "shot", "vision", "defense",
    # Goalie
    "positioning", "athleticism", "glove", "blocker", "rebound_control",
    "puck_handling", "mental",
)

# Canonical tag vocabulary. The corpus builder is told to classify against
# this set; novel descriptors get rounded to the nearest, or filed under
# `_other` with the source quote preserved for later schema review.
CANONICAL_TAGS = (
    # ==== Skater ====
    # Offensive archetypes
    "playmaker", "sniper", "volume_shooter", "power_forward", "two_way",
    # Defensive archetypes
    "shutdown", "puck_mover", "stay_at_home", "offensive_d",
    # Style descriptors
    "warrior", "agitator", "enforcer", "clutch",
    "fast", "slow_start", "streaky", "consistent",
    # Role descriptors
    "top_six", "bottom_six", "bottom_pair", "rover", "specialist_pp", "specialist_pk",
    # ==== Goalie ====
    # Style schools
    "positional", "athletic", "hybrid", "butterfly", "scrambly",
    # Temperament
    "calm", "fiery",
    # Role/career-stage
    "prospect", "veteran", "starter", "backup", "tandem",
    # Build/specialty
    "big_frame", "undersized_quick", "puck_mover_g", "big_game",
)


@dataclass
class ContinuousAttribute:
    name: str                    # one of CONTINUOUS_ATTRIBUTES
    value: float                 # 1.0 to 5.0
    confidence: float            # 0.0 to 1.0
    source_count: int = 0        # how many sources contributed to the score


@dataclass
class TagAssertion:
    tag: str                     # one of CANONICAL_TAGS (or '_other:<text>' for novel)
    confidence: float            # 0.0 to 1.0
    source_quote: str            # the snippet that triggered the tag
    source_url: str              # provenance URL


@dataclass
class ComparableMention:
    """An explicit 'X reminds me of Y' style mention in published text."""
    comp_name: str               # the comp player named in the quote
    source_quote: str
    source_url: str
    polarity: str = "style"      # 'style' | 'trajectory' | 'both'


@dataclass
class PlayerScoutingProfile:
    """The complete extracted profile for one player."""
    name: str
    position: str
    extracted_at: str            # ISO date
    attributes: list[ContinuousAttribute] = field(default_factory=list)
    tags: list[TagAssertion] = field(default_factory=list)
    comp_mentions: list[ComparableMention] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)   # all source URLs consulted

    def attr(self, name: str) -> ContinuousAttribute | None:
        for a in self.attributes:
            if a.name == name:
                return a
        return None

    def has_tag(self, tag: str, min_confidence: float = 0.0) -> bool:
        return any(t.tag == tag and t.confidence >= min_confidence for t in self.tags)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "position": self.position,
            "extracted_at": self.extracted_at,
            "attributes": [a.__dict__ for a in self.attributes],
            "tags": [t.__dict__ for t in self.tags],
            "comp_mentions": [m.__dict__ for m in self.comp_mentions],
            "sources": list(self.sources),
        }

    @classmethod
    def from_dict(cls, d: dict) -> PlayerScoutingProfile:
        return cls(
            name=d["name"], position=d.get("position", ""),
            extracted_at=d["extracted_at"],
            attributes=[ContinuousAttribute(**a) for a in d.get("attributes", [])],
            tags=[TagAssertion(**t) for t in d.get("tags", [])],
            comp_mentions=[ComparableMention(**m) for m in d.get("comp_mentions", [])],
            sources=list(d.get("sources", [])),
        )


# --- SQLite persistence ---

def init_scouting_tables(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS scouting_profiles (
            name TEXT NOT NULL,
            position TEXT NOT NULL DEFAULT '',
            extracted_at TEXT,
            sources_json TEXT,
            PRIMARY KEY (name, position)
        );
        CREATE TABLE IF NOT EXISTS scouting_attributes (
            name TEXT NOT NULL,
            position TEXT NOT NULL DEFAULT '',
            attribute TEXT NOT NULL,
            value REAL NOT NULL,
            confidence REAL NOT NULL,
            source_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (name, position, attribute)
        );
        CREATE TABLE IF NOT EXISTS scouting_tags (
            name TEXT NOT NULL,
            position TEXT NOT NULL DEFAULT '',
            tag TEXT NOT NULL,
            confidence REAL NOT NULL,
            source_quote TEXT,
            source_url TEXT,
            PRIMARY KEY (name, position, tag)
        );
        CREATE TABLE IF NOT EXISTS scouting_comparable_mentions (
            name TEXT NOT NULL,
            position TEXT NOT NULL DEFAULT '',
            comp_name TEXT NOT NULL,
            source_quote TEXT,
            source_url TEXT,
            polarity TEXT NOT NULL DEFAULT 'style',
            PRIMARY KEY (name, position, comp_name, source_url)
        );
        CREATE INDEX IF NOT EXISTS idx_scouting_tags_tag ON scouting_tags(tag);
        CREATE INDEX IF NOT EXISTS idx_scouting_comp_mentions_comp ON scouting_comparable_mentions(comp_name);
    """)
    con.commit()


def upsert_profile(con: sqlite3.Connection, profile: PlayerScoutingProfile) -> None:
    """Idempotent upsert of a complete profile."""
    init_scouting_tables(con)
    con.execute(
        "INSERT OR REPLACE INTO scouting_profiles (name, position, extracted_at, sources_json) VALUES (?, ?, ?, ?)",
        (profile.name, profile.position, profile.extracted_at, json.dumps(profile.sources)),
    )
    # Wipe + reinsert child rows so a re-extraction is clean
    con.execute("DELETE FROM scouting_attributes WHERE name = ? AND position = ?", (profile.name, profile.position))
    con.execute("DELETE FROM scouting_tags WHERE name = ? AND position = ?", (profile.name, profile.position))
    con.execute("DELETE FROM scouting_comparable_mentions WHERE name = ? AND position = ?", (profile.name, profile.position))
    for a in profile.attributes:
        con.execute(
            "INSERT INTO scouting_attributes (name, position, attribute, value, confidence, source_count) VALUES (?, ?, ?, ?, ?, ?)",
            (profile.name, profile.position, a.name, a.value, a.confidence, a.source_count),
        )
    for t in profile.tags:
        con.execute(
            "INSERT OR REPLACE INTO scouting_tags (name, position, tag, confidence, source_quote, source_url) VALUES (?, ?, ?, ?, ?, ?)",
            (profile.name, profile.position, t.tag, t.confidence, t.source_quote, t.source_url),
        )
    for m in profile.comp_mentions:
        con.execute(
            "INSERT OR REPLACE INTO scouting_comparable_mentions (name, position, comp_name, source_quote, source_url, polarity) VALUES (?, ?, ?, ?, ?, ?)",
            (profile.name, profile.position, m.comp_name, m.source_quote, m.source_url, m.polarity),
        )
    con.commit()


def load_profile(con: sqlite3.Connection, name: str, position: str = "") -> PlayerScoutingProfile | None:
    init_scouting_tables(con)
    head = con.execute(
        "SELECT extracted_at, sources_json FROM scouting_profiles WHERE name = ? AND position = ?",
        (name, position),
    ).fetchone()
    if not head:
        return None
    extracted_at, sources_json = head
    attrs = [
        ContinuousAttribute(name=r[0], value=r[1], confidence=r[2], source_count=r[3])
        for r in con.execute(
            "SELECT attribute, value, confidence, source_count FROM scouting_attributes WHERE name = ? AND position = ?",
            (name, position),
        )
    ]
    tags = [
        TagAssertion(tag=r[0], confidence=r[1], source_quote=r[2] or "", source_url=r[3] or "")
        for r in con.execute(
            "SELECT tag, confidence, source_quote, source_url FROM scouting_tags WHERE name = ? AND position = ?",
            (name, position),
        )
    ]
    mentions = [
        ComparableMention(comp_name=r[0], source_quote=r[1] or "", source_url=r[2] or "", polarity=r[3] or "style")
        for r in con.execute(
            "SELECT comp_name, source_quote, source_url, polarity FROM scouting_comparable_mentions WHERE name = ? AND position = ?",
            (name, position),
        )
    ]
    return PlayerScoutingProfile(
        name=name, position=position, extracted_at=extracted_at,
        attributes=attrs, tags=tags, comp_mentions=mentions,
        sources=json.loads(sources_json) if sources_json else [],
    )
