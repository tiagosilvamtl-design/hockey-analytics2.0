"""Seed the scouting corpus with manually-extracted profiles from web research.

This is the v1 ingest: Claude (running this work) did WebSearch + WebFetch on
each priority player, extracted structured attributes + tags + comp mentions
from the responses, and codified them here. The result is persisted to the
scouting_* tables in store.sqlite via lemieux.core.scouting.upsert_profile.

For larger corpus runs, future versions will automate this loop with
WebSearch -> LLM-extract -> upsert. The schema (PlayerScoutingProfile +
ContinuousAttribute + TagAssertion + ComparableMention) is identical
between manual and automated ingest, so downstream consumers
(find_players_by_tag, tag_split_study, etc.) don't care which path produced
the rows.

Confidence convention used here:
  - 0.9-1.0: explicitly stated in source text (e.g. "tenacious forecheck" -> warrior)
  - 0.7-0.85: strongly implied by multiple text passages
  - 0.5-0.65: directionally supported, single source
  - <0.5: speculative; not assigned

Continuous attributes use a 1-5 scale; confidence reflects how well the source
text supports the value. Confidence is what the tag-cohort studies filter by.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "lemieux-core" / "src"))

from lemieux.core import (
    ComparableMention,
    ContinuousAttribute,
    PlayerScoutingProfile,
    TagAssertion,
    upsert_profile,
)


TODAY = date.today().isoformat()
DB = REPO / "legacy" / "data" / "store.sqlite"


def attr(name, value, conf, n=1):
    return ContinuousAttribute(name=name, value=value, confidence=conf, source_count=n)


def tag(t, conf, quote, url):
    return TagAssertion(tag=t, confidence=conf, source_quote=quote, source_url=url)


def comp(name, quote, url, polarity="style"):
    return ComparableMention(comp_name=name, source_quote=quote, source_url=url, polarity=polarity)


# ============================================================
# Priority cohort — 12 players researched on 2026-04-28
# ============================================================
PROFILES: list[PlayerScoutingProfile] = []

# --- Brendan Gallagher (R, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Brendan Gallagher", position="R", extracted_at=TODAY,
    sources=["https://en.wikipedia.org/wiki/Brendan_Gallagher",
             "https://sportsforecaster.com/nhl/p/18502/Brendan_Gallagher"],
    attributes=[
        attr("skating", 3.0, 0.7), attr("hands", 3.0, 0.7),
        attr("hockey_iq", 4.0, 0.8), attr("compete", 5.0, 0.95),
        attr("size", 1.5, 0.95), attr("speed", 3.0, 0.6),
        attr("shot", 3.0, 0.6), attr("vision", 3.0, 0.5),
        attr("defense", 3.0, 0.5),
    ],
    tags=[
        tag("warrior", 0.95,
            "tenacious forecheck, fearless, willing to go to the dirty areas, crashes the net",
            "https://sportsforecaster.com/nhl/p/18502/Brendan_Gallagher"),
        tag("agitator", 0.85,
            "first-class pest who has become a rare combination of agitation and offensive production",
            "https://sportsforecaster.com/nhl/p/18502/Brendan_Gallagher"),
        tag("top_six", 0.6, "alternate captain; primary forward role through career",
            "https://en.wikipedia.org/wiki/Brendan_Gallagher"),
        tag("power_forward", 0.5,
            "plays bigger than his actual size; battles in front of the net",
            "https://sportsforecaster.com/nhl/p/18502/Brendan_Gallagher"),
        tag("consistent", 0.6, "approach is an example for teammates",
            "https://sportsforecaster.com/nhl/p/18502/Brendan_Gallagher"),
    ],
))

# --- Kirby Dach (C, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Kirby Dach", position="C", extracted_at=TODAY,
    sources=["https://www.eliteprospects.com/player/268089/kirby-dach",
             "https://www.habseyesontheprize.com/kirby-dach-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"],
    attributes=[
        attr("skating", 4.0, 0.8), attr("hands", 4.0, 0.85),
        attr("hockey_iq", 4.0, 0.8), attr("compete", 3.0, 0.7),
        attr("size", 5.0, 0.95), attr("speed", 4.0, 0.75),
        attr("shot", 3.0, 0.6), attr("vision", 4.5, 0.9),
        attr("defense", 4.0, 0.8),
    ],
    tags=[
        tag("playmaker", 0.9, "pass-first player, which defines much of his playing approach",
            "https://www.habseyesontheprize.com/kirby-dach-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"),
        tag("two_way", 0.85,
            "Dach's greatest asset to an NHL roster is his play on the defensive half of the ice",
            "https://www.habseyesontheprize.com/kirby-dach-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"),
        tag("top_six", 0.85,
            "proper top-six centre who could seamlessly slide onto the top line",
            "https://www.habseyesontheprize.com/kirby-dach-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"),
    ],
    comp_mentions=[
        comp("Phillip Danault",
             "essentially a bigger, faster Phillip Danault who can absorb the most difficult matchups",
             "https://www.habseyesontheprize.com/kirby-dach-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/",
             polarity="style"),
    ],
))

# --- Cole Caufield (R, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Cole Caufield", position="R", extracted_at=TODAY,
    sources=["https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/",
             "https://en.wikipedia.org/wiki/Cole_Caufield"],
    attributes=[
        attr("skating", 4.0, 0.8), attr("hands", 5.0, 0.9),
        attr("hockey_iq", 4.0, 0.8), attr("compete", 4.0, 0.7),
        attr("size", 1.5, 0.9), attr("speed", 4.5, 0.85),
        attr("shot", 5.0, 0.95), attr("vision", 4.0, 0.7),
        attr("defense", 2.5, 0.7),
    ],
    tags=[
        tag("sniper", 0.95,
            "shot that absolutely leaps off his stick with pinpoint accuracy; relies on precision and release speed",
            "https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
        tag("top_six", 0.9, "game-breaking goal scorer",
            "https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
        tag("specialist_pp", 0.7, "thrives under pressure; difficult to contain on the man advantage",
            "https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
        tag("fast", 0.7, "low centre of gravity facilitates fast and flashy puckhandling at pace",
            "https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
    ],
    comp_mentions=[
        comp("Patrik Laine",
             "differs from other well-known snipers such as Patrik Laine in that he relies more on precision and release speed than sheer velocity",
             "https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/",
             polarity="style"),
        comp("Alex Ovechkin",
             "differs from other well-known snipers such as Alex Ovechkin in that he relies more on precision and release speed than sheer velocity or heaviness",
             "https://www.habseyesontheprize.com/cole-caufield-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/",
             polarity="style"),
    ],
))

# --- Nick Suzuki (C, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Nick Suzuki", position="C", extracted_at=TODAY,
    sources=["https://thehockeywriters.com/canadiens-nick-suzuki-might-be-the-nhls-most-underrated-captain/",
             "https://en.wikipedia.org/wiki/Nick_Suzuki"],
    attributes=[
        attr("skating", 4.0, 0.7), attr("hands", 4.0, 0.85),
        attr("hockey_iq", 5.0, 0.95), attr("compete", 4.0, 0.85),
        attr("size", 3.0, 0.7), attr("speed", 4.0, 0.7),
        attr("shot", 3.5, 0.7), attr("vision", 5.0, 0.95),
        attr("defense", 5.0, 0.95),
    ],
    tags=[
        tag("two_way", 0.95, "emerging as one of the NHL's best two-way centers",
            "https://thehockeywriters.com/canadiens-nick-suzuki-might-be-the-nhls-most-underrated-captain/"),
        tag("playmaker", 0.85, "smart offensive center, thinks the game at a fast pace",
            "https://thehockeywriters.com/canadiens-nick-suzuki-might-be-the-nhls-most-underrated-captain/"),
        tag("shutdown", 0.8, "frontrunner for the 2026 Selke Trophy; carries demanding defensive assignments",
            "https://thehockeywriters.com/canadiens-nick-suzuki-might-be-the-nhls-most-underrated-captain/"),
        tag("top_six", 0.95, "captain and 1C",
            "https://thehockeywriters.com/canadiens-nick-suzuki-might-be-the-nhls-most-underrated-captain/"),
        tag("consistent", 0.85, "calm under pressure",
            "https://thehockeywriters.com/canadiens-nick-suzuki-might-be-the-nhls-most-underrated-captain/"),
    ],
))

# --- Juraj Slafkovský (L, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Juraj Slafkovský", position="L", extracted_at=TODAY,
    sources=["https://lwosports.com/canadiens-power-forward-slafkovsky-takes-step/",
             "https://www.eliteprospects.com/player/527423/juraj-slafkovsky"],
    attributes=[
        attr("skating", 3.5, 0.7), attr("hands", 4.5, 0.9),
        attr("hockey_iq", 4.0, 0.8), attr("compete", 4.0, 0.8),
        attr("size", 5.0, 0.95), attr("speed", 3.5, 0.7),
        attr("shot", 4.0, 0.8), attr("vision", 4.0, 0.8),
        attr("defense", 3.5, 0.7),
    ],
    tags=[
        tag("power_forward", 0.95,
            "Built like a power forward, with a 218-pound frame; learned to use his physical skills and play a heavier game",
            "https://lwosports.com/canadiens-power-forward-slafkovsky-takes-step/"),
        tag("top_six", 0.9, "top-six winger",
            "https://lwosports.com/canadiens-power-forward-slafkovsky-takes-step/"),
        tag("specialist_pp", 0.7,
            "Revolutionized the Habs' Power Play (per the YouTube headline)",
            "https://www.youtube.com/watch?v=t_R9PhRTkbY"),
    ],
    comp_mentions=[
        comp("Josh Anderson",
             "Having Anderson on his line provided him with an example of what a power forward must do to be effective",
             "https://lwosports.com/canadiens-power-forward-slafkovsky-takes-step/",
             polarity="style"),
    ],
))

# --- Lane Hutson (D, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Lane Hutson", position="D", extracted_at=TODAY,
    sources=["https://www.nhl.com/news/lane-hutson-transforming-montreal-canadiens",
             "https://www.habseyesontheprize.com/lane-hutson-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"],
    attributes=[
        attr("skating", 5.0, 0.95), attr("hands", 5.0, 0.9),
        attr("hockey_iq", 5.0, 0.95), attr("compete", 4.0, 0.7),
        attr("size", 1.5, 0.95), attr("speed", 5.0, 0.95),
        attr("shot", 3.5, 0.6), attr("vision", 5.0, 0.95),
        attr("defense", 3.5, 0.6),
    ],
    tags=[
        tag("offensive_d", 0.95,
            "mobile, undersized defender with strong edgework and exceptionally quick feet; turns every puck touch into a Grade-A scoring chance",
            "https://www.habseyesontheprize.com/lane-hutson-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"),
        tag("puck_mover", 0.95, "constant threat with the puck on his stick because of his puck-handling and passing skills",
            "https://www.habseyesontheprize.com/lane-hutson-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"),
        tag("playmaker", 0.85, "exceptional ice awareness; deceptive playmaking",
            "https://www.habseyesontheprize.com/lane-hutson-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/"),
    ],
    comp_mentions=[
        comp("Andrei Markov",
             "arguably the most creative defensive prospect that Montreal has had in several decades, potentially moreso than cerebral Andrei Markov",
             "https://www.habseyesontheprize.com/lane-hutson-2024-montreal-canadiens-top-25-under-25-prospect-profile-projection-scouting-stats/",
             polarity="style"),
    ],
))

# --- Zachary Bolduc (R, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Zachary Bolduc", position="R", extracted_at=TODAY,
    sources=["https://www.eliteprospects.com/player/529393/zachary-bolduc",
             "https://sportsforecaster.com/nhl/p/1020824/Zack_Bolduc"],
    attributes=[
        attr("skating", 4.5, 0.85), attr("hands", 4.0, 0.8),
        attr("hockey_iq", 4.0, 0.8), attr("compete", 4.0, 0.8),
        attr("size", 3.5, 0.7), attr("speed", 4.5, 0.85),
        attr("shot", 3.5, 0.7), attr("vision", 4.0, 0.7),
        attr("defense", 4.0, 0.7),
    ],
    tags=[
        tag("two_way", 0.85, "one of the better two-way forwards, knows how to contribute offensively while being reliable in his own end",
            "https://sportsforecaster.com/nhl/p/1020824/Zack_Bolduc"),
        tag("fast", 0.85, "Bolduc is fast and forechecks hard, strong skater with size and strength",
            "https://sportsforecaster.com/nhl/p/1020824/Zack_Bolduc"),
        tag("warrior", 0.65, "fast and forechecks hard; tools give him the upper hand in downhill battles",
            "https://sportsforecaster.com/nhl/p/1020824/Zack_Bolduc"),
    ],
))

# --- Josh Anderson (R, MTL) — warrior cohort candidate ---
PROFILES.append(PlayerScoutingProfile(
    name="Josh Anderson", position="R", extracted_at=TODAY,
    sources=["https://en.wikipedia.org/wiki/Josh_Anderson_(ice_hockey)",
             "https://sportsforecaster.com/nhl/p/19282/Josh_Anderson"],
    attributes=[
        attr("skating", 4.5, 0.85), attr("hands", 3.0, 0.7),
        attr("hockey_iq", 3.5, 0.7), attr("compete", 5.0, 0.9),
        attr("size", 5.0, 0.9), attr("speed", 4.5, 0.85),
        attr("shot", 3.5, 0.7), attr("vision", 3.0, 0.6),
        attr("defense", 3.5, 0.7),
    ],
    tags=[
        tag("power_forward", 0.95, "Power forward known for speed and physicality, becoming known as 'the Powerhorse'",
            "https://en.wikipedia.org/wiki/Josh_Anderson_(ice_hockey)"),
        tag("warrior", 0.9, "willingness to go to the front of the net and to the corners; physical winger; tone-setting role",
            "https://sportsforecaster.com/nhl/p/19282/Josh_Anderson"),
        tag("fast", 0.85, "tremendous acceleration; rare combination of size and quickness",
            "https://sportsforecaster.com/nhl/p/19282/Josh_Anderson"),
        tag("bottom_six", 0.65, "shifting roles from a top-six winger in previous years to more of a physical, tone-setting middle-six option",
            "https://sportsforecaster.com/nhl/p/19282/Josh_Anderson"),
    ],
))

# --- Brandon Hagel (L, TBL) — warrior cohort candidate ---
PROFILES.append(PlayerScoutingProfile(
    name="Brandon Hagel", position="L", extracted_at=TODAY,
    sources=["https://thehockeywriters.com/lightning-hagel-trust-drive-own-line-2024-25/",
             "https://www.tsn.ca/nhl/article/emotional-leader-hagel-a-central-figure-in-lightning-canadiens-series/"],
    attributes=[
        attr("skating", 4.5, 0.8), attr("hands", 4.0, 0.8),
        attr("hockey_iq", 4.5, 0.85), attr("compete", 5.0, 0.95),
        attr("size", 2.5, 0.7), attr("speed", 4.0, 0.8),
        attr("shot", 4.0, 0.75), attr("vision", 4.0, 0.75),
        attr("defense", 4.5, 0.85),
    ],
    tags=[
        tag("two_way", 0.95, "Hagel is classified as a two-way forward; strong play in all three zones",
            "https://thehockeywriters.com/lightning-hagel-trust-drive-own-line-2024-25/"),
        tag("warrior", 0.9, "gritty style; willing to do anything to win, regardless of the task; can drop the gloves",
            "https://thehockeywriters.com/lightning-hagel-trust-drive-own-line-2024-25/"),
        tag("top_six", 0.9, "trusted to drive his own line; led Lightning in expected goals-for percentage",
            "https://thehockeywriters.com/lightning-hagel-trust-drive-own-line-2024-25/"),
        tag("clutch", 0.75, "emotional leader and central figure in the Lightning-Canadiens series",
            "https://www.tsn.ca/nhl/article/emotional-leader-hagel-a-central-figure-in-lightning-canadiens-series/"),
        tag("specialist_pk", 0.7, "can kill a penalty",
            "https://thehockeywriters.com/lightning-hagel-trust-drive-own-line-2024-25/"),
    ],
))

# --- Mathieu Olivier (R, CBJ) — warrior/enforcer reference ---
PROFILES.append(PlayerScoutingProfile(
    name="Mathieu Olivier", position="R", extracted_at=TODAY,
    sources=["https://www.nhl.com/bluejackets/news/mathieu-olivier-blue-jackets-toughest-players-in-nhl",
             "https://thehockeywriters.com/blue-jackets-mathieu-olivier-proving-more-than-just-enforcer/"],
    attributes=[
        attr("skating", 3.0, 0.7), attr("hands", 2.5, 0.7),
        attr("hockey_iq", 3.0, 0.6), attr("compete", 5.0, 0.95),
        attr("size", 5.0, 0.95), attr("speed", 3.0, 0.7),
        attr("shot", 2.5, 0.6), attr("vision", 2.5, 0.6),
        attr("defense", 3.0, 0.6),
    ],
    tags=[
        tag("enforcer", 0.95, "one of the few NHLers that have been able to take the enforcer role and keep it relevant",
            "https://www.nhl.com/bluejackets/news/mathieu-olivier-blue-jackets-toughest-players-in-nhl"),
        tag("warrior", 0.9, "loves to play a physical brand of hockey and initiate contact; momentum-changing hits",
            "https://www.nhl.com/bluejackets/news/mathieu-olivier-blue-jackets-toughest-players-in-nhl"),
        tag("bottom_six", 0.95, "depth role as a professional",
            "https://thehockeywriters.com/blue-jackets-mathieu-olivier-proving-more-than-just-enforcer/"),
    ],
))

# --- Phillip Danault (C, MTL) ---
PROFILES.append(PlayerScoutingProfile(
    name="Phillip Danault", position="C", extracted_at=TODAY,
    sources=["https://en.wikipedia.org/wiki/Phillip_Danault",
             "https://sportsforecaster.com/nhl/p/19016/Phillip_Danault"],
    attributes=[
        attr("skating", 3.5, 0.7), attr("hands", 3.0, 0.7),
        attr("hockey_iq", 4.5, 0.85), attr("compete", 4.5, 0.85),
        attr("size", 4.0, 0.8), attr("speed", 3.5, 0.7),
        attr("shot", 3.0, 0.6), attr("vision", 3.5, 0.65),
        attr("defense", 5.0, 0.95),
    ],
    tags=[
        tag("shutdown", 0.95, "excellent center for a checking line; strong defensive performance against opposing top forwards",
            "https://sportsforecaster.com/nhl/p/19016/Phillip_Danault"),
        tag("two_way", 0.85, "complete package includes speed, grit, intensity and good defensive play",
            "https://sportsforecaster.com/nhl/p/19016/Phillip_Danault"),
        tag("specialist_pk", 0.85, "good penalty killer",
            "https://sportsforecaster.com/nhl/p/19016/Phillip_Danault"),
        tag("warrior", 0.7, "speed, grit, intensity; dedicated teammate",
            "https://sportsforecaster.com/nhl/p/19016/Phillip_Danault"),
    ],
))

# --- Ivan Demidov (R, MTL) — playmaker/sniper hybrid ---
PROFILES.append(PlayerScoutingProfile(
    name="Ivan Demidov", position="R", extracted_at=TODAY,
    sources=["https://www.habseyesontheprize.com/ivan-demidov-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/",
             "https://www.eliteprospects.com/player/619202/ivan-demidov"],
    attributes=[
        attr("skating", 4.5, 0.8), attr("hands", 5.0, 0.95),
        attr("hockey_iq", 5.0, 0.9), attr("compete", 4.0, 0.7),
        attr("size", 3.0, 0.7), attr("speed", 4.5, 0.8),
        attr("shot", 4.5, 0.85), attr("vision", 5.0, 0.95),
        attr("defense", 3.0, 0.6),
    ],
    tags=[
        tag("playmaker", 0.95, "manipulates passing lanes into existence and threads the puck into traffic",
            "https://www.habseyesontheprize.com/ivan-demidov-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
        tag("sniper", 0.8, "lethal wrister with a real quick release",
            "https://www.habseyesontheprize.com/ivan-demidov-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
        tag("top_six", 0.9, "elite creativity and puck skill; offensive threat",
            "https://www.habseyesontheprize.com/ivan-demidov-2025-montreal-canadiens-top-25-under-25-prospect-ranking-scouting-report-stats-projection/"),
    ],
))


# --- Tom Wilson (R, WSH) — warrior cohort expander ---
PROFILES.append(PlayerScoutingProfile(
    name="Tom Wilson", position="R", extracted_at=TODAY,
    sources=["https://en.wikipedia.org/wiki/Tom_Wilson_(ice_hockey)",
             "https://thehockeynews.com/news/latest-news/capitals-tom-wilson-just-keeps-getting-better"],
    attributes=[
        attr("skating", 3.0, 0.7), attr("hands", 3.0, 0.7),
        attr("hockey_iq", 3.5, 0.7), attr("compete", 5.0, 0.95),
        attr("size", 5.0, 0.95), attr("speed", 3.0, 0.7),
        attr("shot", 3.5, 0.7), attr("vision", 3.0, 0.6),
        attr("defense", 3.5, 0.7),
    ],
    tags=[
        tag("warrior", 0.95, "Heavy Hitter; almost unmatched ability to get under opponents' skin",
            "https://en.wikipedia.org/wiki/Tom_Wilson_(ice_hockey)"),
        tag("agitator", 0.95, "Player type Agitator; placed on the Rat Line of agitators",
            "https://en.wikipedia.org/wiki/Tom_Wilson_(ice_hockey)"),
        tag("power_forward", 0.9, "6'4\" 218 power forward, strong scoring record and highly physical",
            "https://en.wikipedia.org/wiki/Tom_Wilson_(ice_hockey)"),
        tag("two_way", 0.7, "Two-Way Forward; works hard and back checking",
            "https://en.wikipedia.org/wiki/Tom_Wilson_(ice_hockey)"),
        tag("top_six", 0.85, "Top-Six Power Forward",
            "https://devilsarmynetwork.com/trade-profile-tom-wilson-capitals/"),
    ],
))

# --- Sam Bennett (C, FLA) — warrior who has actual playoff data ---
PROFILES.append(PlayerScoutingProfile(
    name="Sam Bennett", position="C", extracted_at=TODAY,
    sources=["https://www.espn.com/nhl/story/_/id/45487805/nhl-2025-playoffs-stanley-cup-final-panthers-sam-bennett-mvp-conn-smythe-scoring-hits",
             "https://thehockeynews.com/nhl/florida-panthers/players/physical-skilled-sam-bennett-personifies-florida-panthers-style-of-hockey"],
    attributes=[
        attr("skating", 4.0, 0.8), attr("hands", 4.0, 0.8),
        attr("hockey_iq", 4.0, 0.8), attr("compete", 5.0, 0.95),
        attr("size", 4.0, 0.85), attr("speed", 4.0, 0.8),
        attr("shot", 4.0, 0.8), attr("vision", 3.5, 0.75),
        attr("defense", 4.0, 0.8),
    ],
    tags=[
        tag("warrior", 0.95, "physical aspect to the game especially in the playoffs is invaluable; capable of really fine play at speed and also capable of the big hit",
            "https://www.nhl.com/panthers/news/sam-bennett-proving-to-be-perfect-fit-with-florida-x6990"),
        tag("clutch", 0.95, "Conn Smythe Trophy as playoff MVP 2024-25; led playoffs with 15 goals; Built for this time of year",
            "https://www.espn.com/nhl/story/_/id/45487805/nhl-2025-playoffs-stanley-cup-final-panthers-sam-bennett-mvp-conn-smythe-scoring-hits"),
        tag("top_six", 0.9, "personifies Florida Panthers style of hockey; key playoff role",
            "https://thehockeynews.com/nhl/florida-panthers/players/physical-skilled-sam-bennett-personifies-florida-panthers-style-of-hockey"),
        tag("two_way", 0.8, "hard on pucks, hard on the body; the worst to play against, but the best to play with",
            "https://thehockeynews.com/nhl/florida-panthers/players/physical-skilled-sam-bennett-personifies-florida-panthers-style-of-hockey"),
    ],
))

# --- Brad Marchand (L, BOS/FLA) — pest/warrior + two-way star ---
PROFILES.append(PlayerScoutingProfile(
    name="Brad Marchand", position="L", extracted_at=TODAY,
    sources=["https://en.wikipedia.org/wiki/Brad_Marchand",
             "https://www.espn.com/nhl/story/_/id/17951883/nhl-boston-bruins-left-winger-brad-marchand-evolved-pest-one-nhl-best"],
    attributes=[
        attr("skating", 4.5, 0.85), attr("hands", 4.5, 0.85),
        attr("hockey_iq", 5.0, 0.9), attr("compete", 5.0, 0.95),
        attr("size", 2.5, 0.85), attr("speed", 4.5, 0.85),
        attr("shot", 4.0, 0.8), attr("vision", 4.5, 0.85),
        attr("defense", 5.0, 0.95),
    ],
    tags=[
        tag("agitator", 0.95, "characterized as a pest; frustrates his opponents through physical or verbal attacks",
            "https://en.wikipedia.org/wiki/Brad_Marchand"),
        tag("warrior", 0.85, "ultracompetitive; the power of 'The Pest'; turned defense into offense with attacker's mindset",
            "https://www.espn.com/nhl/story/_/id/17951883/nhl-boston-bruins-left-winger-brad-marchand-evolved-pest-one-nhl-best"),
        tag("two_way", 0.95, "one of the most productive, feared two-way wingers Boston has ever had; career leader in short-handed goals",
            "https://nesn.com/boston-bruins/news/brad-marchand-bruins-legacy-captain-short-handed-ace/bdff5f736340664979bad4bf"),
        tag("specialist_pk", 0.9, "Boston's career leader in short-handed goals; Short-Handed Ace",
            "https://nesn.com/boston-bruins/news/brad-marchand-bruins-legacy-captain-short-handed-ace/bdff5f736340664979bad4bf"),
        tag("top_six", 0.95, "franchise cornerstone, Stanley Cup champion, captain",
            "https://nesn.com/boston-bruins/news/brad-marchand-bruins-legacy-captain-short-handed-ace/bdff5f736340664979bad4bf"),
        tag("clutch", 0.85, "captain; one of the most productive, feared two-way wingers",
            "https://nesn.com/boston-bruins/news/brad-marchand-bruins-legacy-captain-short-handed-ace/bdff5f736340664979bad4bf"),
    ],
    comp_mentions=[
        comp("Theo Fleury",
             "Marchand has modelled his behaviour after that of Theo Fleury, a former pest who was able to leverage frustration into offensive production",
             "https://en.wikipedia.org/wiki/Brad_Marchand", polarity="style"),
    ],
))

# --- Corey Perry (R, EDM/CHI vet) — pest who's still effective in playoffs ---
PROFILES.append(PlayerScoutingProfile(
    name="Corey Perry", position="R", extracted_at=TODAY,
    sources=["https://thehockeywriters.com/nhls-all-star-pests-corey-perry-brad-marchand-set-to-face-off-for-2025-stanley-cup/",
             "https://www.eliteprospects.com/player/8541/corey-perry/scouting-report"],
    attributes=[
        attr("skating", 2.5, 0.8), attr("hands", 4.0, 0.8),
        attr("hockey_iq", 4.5, 0.85), attr("compete", 4.5, 0.85),
        attr("size", 4.0, 0.85), attr("speed", 2.5, 0.8),
        attr("shot", 4.0, 0.8), attr("vision", 4.0, 0.8),
        attr("defense", 3.0, 0.7),
    ],
    tags=[
        tag("agitator", 0.95, "one of the NHL's premier pests; loves to get under the skin of his opponents; nicknamed The Worm",
            "https://thehockeywriters.com/nhls-all-star-pests-corey-perry-brad-marchand-set-to-face-off-for-2025-stanley-cup/"),
        tag("warrior", 0.9, "stands his ground in front of goalies and when engaged in physical confrontation, absorbs cruel levels of abuse",
            "https://www.eliteprospects.com/player/8541/corey-perry/scouting-report"),
        tag("clutch", 0.9, "thrives at the most important time of the year, the playoffs",
            "https://thehockeywriters.com/nhls-all-star-pests-corey-perry-brad-marchand-set-to-face-off-for-2025-stanley-cup/"),
        tag("specialist_pp", 0.85, "only used on the top power play unit as a spark",
            "https://www.eliteprospects.com/player/8541/corey-perry/scouting-report"),
        tag("bottom_six", 0.65, "playing in more of a specialist role now, can't keep up with top line minutes anymore",
            "https://www.eliteprospects.com/player/8541/corey-perry/scouting-report"),
    ],
))


# ============================================================
def main():
    # Higher timeout so we wait for the Edge background job's commits to release
    # the DB rather than failing immediately on contention.
    con = sqlite3.connect(DB, timeout=60)
    print(f"Persisting {len(PROFILES)} profiles to {DB}")
    for p in PROFILES:
        upsert_profile(con, p)
        print(f"  ✓ {p.name:25s} ({p.position})  "
              f"{len(p.attributes)} attrs, {len(p.tags)} tags, {len(p.comp_mentions)} comps")
    con.close()
    print("\nDone. Tag-cohort studies now have a populated corpus to query.")


if __name__ == "__main__":
    main()
