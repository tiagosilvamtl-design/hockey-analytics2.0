"""NHL team full-name → 3-letter abbreviation mapping.

NST uses full names on teamtable.php and 3-letter abbreviations on playerteams.php.
We normalize to abbreviations everywhere downstream so team_id joins across tables.
"""
from __future__ import annotations

NAME_TO_ABBREV: dict[str, str] = {
    "Anaheim Ducks": "ANA",
    "Arizona Coyotes": "ARI",
    "Boston Bruins": "BOS",
    "Buffalo Sabres": "BUF",
    "Calgary Flames": "CGY",
    "Carolina Hurricanes": "CAR",
    "Chicago Blackhawks": "CHI",
    "Colorado Avalanche": "COL",
    "Columbus Blue Jackets": "CBJ",
    "Dallas Stars": "DAL",
    "Detroit Red Wings": "DET",
    "Edmonton Oilers": "EDM",
    "Florida Panthers": "FLA",
    "Los Angeles Kings": "L.A",
    "Minnesota Wild": "MIN",
    "Montreal Canadiens": "MTL",
    "Nashville Predators": "NSH",
    "New Jersey Devils": "NJD",
    "New York Islanders": "NYI",
    "New York Rangers": "NYR",
    "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI",
    "Pittsburgh Penguins": "PIT",
    "San Jose Sharks": "SJS",
    "Seattle Kraken": "SEA",
    "St Louis Blues": "STL",
    "St. Louis Blues": "STL",
    "Tampa Bay Lightning": "T.B",
    "Toronto Maple Leafs": "TOR",
    "Utah Hockey Club": "UTA",
    "Utah Mammoth": "UTA",
    "Vancouver Canucks": "VAN",
    "Vegas Golden Knights": "VGK",
    "Washington Capitals": "WSH",
    "Winnipeg Jets": "WPG",
}

# NST's skater tables sometimes use different short codes than the map values above.
# Reverse map lets us go either direction.
ABBREV_ALIASES: dict[str, str] = {
    "T.B": "TBL",
    "L.A": "LAK",
    "N.J": "NJD",
    "S.J": "SJS",
}


def to_abbrev(name_or_abbrev: str) -> str:
    """Best-effort normalize to NST skater-table abbreviation."""
    if not name_or_abbrev:
        return ""
    s = str(name_or_abbrev).strip()
    if s in NAME_TO_ABBREV:
        return NAME_TO_ABBREV[s]
    # Already an abbreviation?
    if len(s) <= 4:
        return s
    return s
