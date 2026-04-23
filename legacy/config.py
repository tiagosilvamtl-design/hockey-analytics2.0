"""Central config: paths, TTLs, strength states, thresholds, URLs."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

DATA_DIR = ROOT / "data"
CACHE_DB = DATA_DIR / "cache.sqlite"
STORE_DB = DATA_DIR / "store.sqlite"

NST_ACCESS_KEY: str | None = os.getenv("NST_ACCESS_KEY")
NST_RATE_LIMIT_PER_SEC = float(os.getenv("NST_RATE_LIMIT_PER_SEC", "1"))
NST_USER_AGENT = os.getenv(
    "NST_USER_AGENT",
    "claudehockey/0.1 (personal research)",
)

NST_DATA_BASE = "https://data.naturalstattrick.com"
NST_PUBLIC_BASE = "https://www.naturalstattrick.com"

def nst_base() -> str:
    """Use the keyed data subdomain when a key is present; else the public site."""
    return NST_DATA_BASE if NST_ACCESS_KEY else NST_PUBLIC_BASE

STRENGTH_STATES = ["5v5", "5v4", "4v5", "all"]
GAME_TYPES = {"regular": 2, "playoff": 3}

MIN_TOI_FOR_SWAP = 200.0
LINE_COMBO_MIN_TOI = 50.0
LINE_COMBO_DIVERGENCE_PP = 0.10

CACHE_TTL_LIVE_HOURS = 6
CACHE_TTL_COMPLETED_DAYS = 7
CACHE_TTL_HISTORICAL_DAYS = 30

CURRENT_SEASON = "20252026"
PRIOR_SEASONS = ["20242025", "20232024", "20222023"]
