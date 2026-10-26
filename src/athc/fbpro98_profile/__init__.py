"""Parse and edit a Front Page Sports Football Pro '98 coaching profile (.prf)."""

from athc.fbpro98_profile.model import (
    DEFENSE_DISPLAY_CATEGORIES,
    OFFENSE_DISPLAY_CATEGORIES,
    CategoryWeights,
    Down,
    FieldPosition,
    GameState,
    MinutesRemaining,
    PatGameState,
    PatMinutesRemaining,
    PatPointSpread,
    PatSituation,
    PointSpread,
    Profile,
    ProfileType,
    Situation,
    SubstitutionPair,
    SubstitutionSettings,
    YardsToGo,
)
from athc.fbpro98_profile.reader import (
    InvalidProfileError,
    UnsupportedProfileError,
    parse_profile,
    read_profile,
)
from athc.fbpro98_profile.writer import (
    build_profile,
    write_profile,
)

__all__ = [
    "DEFENSE_DISPLAY_CATEGORIES",
    "OFFENSE_DISPLAY_CATEGORIES",
    "CategoryWeights",
    "Down",
    "FieldPosition",
    "GameState",
    "InvalidProfileError",
    "MinutesRemaining",
    "PatGameState",
    "PatMinutesRemaining",
    "PatPointSpread",
    "PatSituation",
    "PointSpread",
    "Profile",
    "ProfileType",
    "Situation",
    "SubstitutionPair",
    "SubstitutionSettings",
    "UnsupportedProfileError",
    "YardsToGo",
    "build_profile",
    "parse_profile",
    "read_profile",
    "write_profile",
]
