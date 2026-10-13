"""Read a Front Page Sports Football Pro '98 league file (.lge)."""

from athc.fbpro98_lge.model import (
    Conference,
    Division,
    Game,
    LgeFile,
    Record,
    Team,
    ranked,
)
from athc.fbpro98_lge.reader import InvalidLgeError, parse_lge, read_lge

__all__ = [
    "Conference",
    "Division",
    "Game",
    "InvalidLgeError",
    "LgeFile",
    "Record",
    "Team",
    "parse_lge",
    "ranked",
    "read_lge",
]
