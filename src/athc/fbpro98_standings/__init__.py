"""Rank a Front Page Sports Football Pro '98 league's teams from its `.lge`
files: division, conference and league standings by the game's, the
scheduler's or the NFL's tie-breakers."""

from athc.fbpro98_standings.errors import StandingsError
from athc.fbpro98_standings.methods import Method
from athc.fbpro98_standings.standings import Standings

__all__ = ["Method", "Standings", "StandingsError"]
