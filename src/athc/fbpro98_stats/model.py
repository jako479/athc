"""In-memory data model for FbPro98 .dat stats files.

The file's records grouped by block and id: one dict per block, id to the
player's or team's stats, one field per category. A category with no record is
None, never a zero object, so a writer can tell a record to insert from one to
change. Every dict and list is in id order, not file order. Mutable classes,
edited by assignment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(slots=True)
class StatsFile:
    """Full in-memory representation of a `.dat` stats file."""

    player_last_game: dict[int, PlayerStats] = field(default_factory=dict)
    """By player id (`.pyr`): each player's latest game."""

    player_season: dict[int, PlayerStats] = field(default_factory=dict)
    """By player id."""

    player_career: dict[int, PlayerStats] = field(default_factory=dict)
    """By player id."""

    team_last_game: dict[int, TeamStats] = field(default_factory=dict)
    """By team number (`.lge`): each team's latest game."""

    team_season: dict[int, TeamStats] = field(default_factory=dict)
    """By team number."""

    opponents_last_game: dict[int, TeamStats] = field(default_factory=dict)
    """By team number: what its opponents did against it."""

    opponents_season: dict[int, TeamStats] = field(default_factory=dict)
    """By team number: what its opponents did against it."""

    players_of_the_game: list[PlayerOfTheGame] = field(default_factory=list)
    """The last week's Players of the Game and the Player of the Week."""

    all_pro: list[AllProPick] = field(default_factory=list)
    """The season's All-Pro team."""

    coach_of_the_year: int | None = None
    """The season's Coach of the Year: a team number."""

    awards: list[Award] = field(default_factory=list)
    """Every season's awards."""


@dataclass(slots=True)
class PlayerStats:
    """One player's stats in one block; None where the file has no record.
    Category 15 records are honors, in `StatsFile`."""

    extra_points: ExtraPoints | None = None
    field_goals: FieldGoals | None = None
    rushing: Rushing | None = None
    passing: Passing | None = None
    receiving: Receiving | None = None
    interceptions: Interceptions | None = None
    punting: Punting | None = None
    punt_returns: PuntReturns | None = None
    kick_returns: KickReturns | None = None
    fumbles: int | None = None
    fumble_recoveries: FumbleRecoveries | None = None
    sacks: int | None = None
    safeties: int | None = None
    tackles: int | None = None
    hall_of_fame_points: HallOfFamePoints | None = None

    penalties: int | None = None
    """Last game only."""

    hall_of_fame_nominee: HallOfFameNominee | None = None
    """Career only."""

    two_point_conversions: TwoPointConversions | None = None


@dataclass(slots=True)
class TeamStats:
    """One team's stats, or its opponents', in one block; None where the file
    has no record."""

    extra_points: ExtraPoints | None = None
    field_goals: FieldGoals | None = None
    rushing: Rushing | None = None
    passing: Passing | None = None
    receiving: Receiving | None = None
    interceptions: Interceptions | None = None
    punting: Punting | None = None
    punt_returns: PuntReturns | None = None
    kick_returns: KickReturns | None = None
    fumbles: int | None = None
    fumble_recoveries: FumbleRecoveries | None = None
    sacks: int | None = None
    safeties: int | None = None
    tackles: int | None = None
    first_downs: FirstDowns | None = None
    downs: Downs | None = None
    game_details: GameDetails | None = None
    two_point_conversions: TwoPointConversions | None = None


@dataclass(slots=True)
class ExtraPoints:
    """Category 0."""

    attempts: int
    made: int


@dataclass(slots=True)
class FieldGoalRange:
    """Field goals from one distance range."""

    made: int
    attempts: int


@dataclass(slots=True)
class FieldGoals:
    """Category 1."""

    long: int

    ranges: list[FieldGoalRange]
    """Five: 10-19, 20-29, 30-39, 40-49 and 50+ yards."""


@dataclass(slots=True)
class Rushing:
    """Category 2."""

    attempts: int
    yards: int
    long: int
    touchdowns: int


@dataclass(slots=True)
class Passing:
    """Category 3."""

    attempts: int
    yards: int
    long: int
    touchdowns: int
    completions: int
    interceptions: int
    sacked: int
    sack_yards: int


@dataclass(slots=True)
class Receiving:
    """Category 4."""

    receptions: int
    yards: int
    long: int
    touchdowns: int


@dataclass(slots=True)
class Interceptions:
    """Category 5."""

    interceptions: int
    yards: int
    long: int
    touchdowns: int


@dataclass(slots=True)
class Punting:
    """Category 6."""

    punts: int
    yards: int
    long: int
    blocked: int
    returns: int
    return_yards: int
    touchbacks: int


@dataclass(slots=True)
class PuntReturns:
    """Category 7."""

    returns: int
    yards: int
    long: int
    touchdowns: int
    fair_catches: int


@dataclass(slots=True)
class KickReturns:
    """Category 8."""

    returns: int
    yards: int
    long: int
    touchdowns: int


@dataclass(slots=True)
class FumbleRecoveries:
    """Category 10."""

    recoveries: int
    yards: int
    long: int
    touchdowns: int


@dataclass(slots=True)
class HallOfFamePoints:
    """Player category 14."""

    count: int
    conference: int
    points: int


@dataclass(slots=True)
class HallOfFameNominee:
    """Player career category 16."""

    points: int
    year_retired: int

    year_elected: int | None
    """None until elected."""


@dataclass(slots=True)
class FirstDowns:
    """Team category 14."""

    total: int
    rushing: int
    passing: int
    penalty: int


@dataclass(slots=True)
class Downs:
    """Team category 15."""

    first_downs: int
    third_down_attempts: int
    third_downs_made: int
    fourth_down_attempts: int
    fourth_downs_made: int


@dataclass(slots=True)
class GameDetails:
    """Team category 16. Opponent and score are the team's own, in its
    opponents' blocks too: the last game's, or in season blocks the latest
    regular-season game's. The other values are the block's own."""

    opponent: int
    """Team number."""

    penalties: int
    penalty_yards: int
    possession_seconds: int
    score: int
    opponent_score: int
    fumbles_lost: int


@dataclass(slots=True)
class TwoPointConversions:
    """Category 17."""

    attempts: int
    made: int


@dataclass(slots=True)
class PlayerOfTheGame:
    """One Player of the Game from the last week, or the Player of the Week."""

    game: int | None
    """The game's place among the week's games in the `.lge`, from 0; None
    for the Player of the Week."""

    points: int

    player: int
    """Player id."""

    team: int
    """Team number."""

    opponent: int
    """Team number."""


@dataclass(slots=True)
class AllProPick:
    """One player on the season's All-Pro team."""

    position: int

    conference: int

    pick: int
    """0 consensus, 1 first team, 2-4 second team."""

    player: int
    """Player id."""


class AwardKind(Enum):
    """What an award is for."""

    MVP = "MVP"
    OFFENSIVE_PLAYER_OF_THE_YEAR = "offensive player of the year"
    DEFENSIVE_PLAYER_OF_THE_YEAR = "defensive player of the year"
    ROOKIE_OF_THE_YEAR = "rookie of the year"


@dataclass(slots=True)
class Award:
    """One season's award to one player."""

    kind: AwardKind

    conference: int | None
    """0 or 1 for the offensive and defensive awards; None for the MVP and
    rookie of the year, which are league-wide."""

    year: int
    """The season's year mod 100, as the file keeps it."""

    player: int
    """Player id."""
