"""Read a Front Page Sports Football Pro '98 league file (.lg2)."""

from athc.fbpro98_lg2.model import (
    FilePair,
    HalfFiles,
    Lg2File,
    TeamFiles,
)
from athc.fbpro98_lg2.reader import (
    InvalidLg2Error,
    UnsupportedLg2Error,
    parse_lg2,
    read_lg2,
)

__all__ = [
    "FilePair",
    "HalfFiles",
    "InvalidLg2Error",
    "Lg2File",
    "TeamFiles",
    "UnsupportedLg2Error",
    "parse_lg2",
    "read_lg2",
]
