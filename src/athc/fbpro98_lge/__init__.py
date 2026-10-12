"""Read a Front Page Sports Football Pro '98 league file (.lge)."""

from athc.fbpro98_lge.model import Conference, Division, LgeFile, Record, Team
from athc.fbpro98_lge.reader import InvalidLgeError, parse_lge, read_lge

__all__ = [
    "Conference",
    "Division",
    "InvalidLgeError",
    "LgeFile",
    "Record",
    "Team",
    "parse_lge",
    "read_lge",
]
