"""Parse FbPro98 .dat stats files into StatsFile objects. See docs/formats/stats.md."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any

from athc.errors import FileFormatError
from athc.fbpro98_stats.model import (
    AllProPick,
    Award,
    AwardKind,
    Downs,
    ExtraPoints,
    FieldGoalRange,
    FieldGoals,
    FirstDowns,
    FumbleRecoveries,
    GameDetails,
    HallOfFameNominee,
    HallOfFamePoints,
    Interceptions,
    KickReturns,
    Passing,
    PlayerOfTheGame,
    PlayerStats,
    Punting,
    PuntReturns,
    Receiving,
    Rushing,
    StatsFile,
    TeamStats,
    TwoPointConversions,
)
from athc.fbpro98_stats.schema import (
    ALL_PRO_PICKS,
    AWARD_DEFENSE_FIRST_CONFERENCE,
    AWARD_DEFENSE_SECOND_CONFERENCE,
    AWARD_MVP,
    AWARD_OFFENSE_FIRST_CONFERENCE,
    AWARD_OFFENSE_SECOND_CONFERENCE,
    AWARD_ROOKIE,
    COACH_OF_THE_YEAR_ID,
    DELETED_MARK,
    DOWNS,
    EXTRA_POINTS,
    FIELD_GOAL_RANGES,
    FIELD_GOALS,
    FILE_END_OFFSET,
    FIRST_DOWNS,
    FUMBLE_RECOVERIES,
    FUMBLES,
    GAME_DETAILS,
    HALL_OF_FAME_NOMINEE,
    HALL_OF_FAME_POINTS,
    HEADER_SIZE,
    HONORS,
    INTERCEPTIONS,
    KICK_RETURNS,
    OPPONENTS_LAST_GAME,
    OPPONENTS_SEASON,
    PASSING,
    PENALTIES,
    PLAYER_CAREER,
    PLAYER_LAST_GAME,
    PLAYER_OF_THE_WEEK_ID,
    PLAYER_SEASON,
    PUNT_RETURNS,
    PUNTING,
    PUNTING_UNUSED_VALUE,
    RECEIVING,
    RECORD,
    RECORD_SIZE,
    RECORD_SIZE_OFFSET,
    RECORDS_OFFSET,
    RUSHING,
    SACKS,
    SAFETIES,
    SLOTS_END_OFFSET,
    TACKLES,
    TEAM_LAST_GAME,
    TEAM_SEASON,
    TWO_POINT_CONVERSIONS,
    U16,
    U32,
    VALUES_PER_RECORD,
)

StrPath = str | PathLike[str]

# A record's eight values, signed.
_Values = tuple[int, ...]
_Decoder = Callable[[_Values], object]


class InvalidStatsError(FileFormatError):
    """Raised when a `.dat` stats file is structurally invalid."""


def read_stats(league: str, league_dir: StrPath) -> StatsFile:
    """Read and parse a league's .dat stats file from disk.

    Args:
        league: League name; the file read is `<league>.dat`.
        league_dir: Folder holding the league's files.

    Returns:
        Parsed StatsFile.

    Raises:
        InvalidStatsError: If the file is shorter than its header, a header
            size or count does not match the file, or a record has an unknown
            type, a repeated type and id, or an honor id that does not decode.
        OSError: If the file cannot be opened or read.
    """
    file_path = Path(league_dir) / f"{league}.dat"
    return parse_stats(file_path.read_bytes(), file_path)


def parse_stats(buffer: bytes, path: StrPath = "<buffer>") -> StatsFile:
    """Parse a .dat stats file from raw bytes.

    Args:
        buffer: Full contents of a .dat file.
        path: Path used only in error messages. Defaults to "<buffer>" when
            parsing data that did not come from disk.

    Returns:
        Parsed StatsFile.

    Raises:
        InvalidStatsError: If the buffer is shorter than its header, a header
            size or count does not match the file, or a record has an unknown
            type, a repeated type and id, or an honor id that does not decode.
    """
    file_path = Path(path)
    if len(buffer) < HEADER_SIZE:
        raise InvalidStatsError(
            f"File is {len(buffer)} bytes, shorter than the {HEADER_SIZE}-byte header.",
            file_path,
        )
    (file_end,) = U32.unpack_from(buffer, FILE_END_OFFSET)
    if file_end != len(buffer) - 1:
        raise InvalidStatsError(
            f"File end at {FILE_END_OFFSET:#04x} is {file_end}, "
            f"expected {len(buffer) - 1}, the file size less one.",
            file_path,
        )
    (record_size,) = U16.unpack_from(buffer, RECORD_SIZE_OFFSET)
    if record_size != RECORD_SIZE:
        raise InvalidStatsError(
            f"Record size at {RECORD_SIZE_OFFSET:#04x} is {record_size}, "
            f"expected {RECORD_SIZE}.",
            file_path,
        )
    (slots_end,) = U32.unpack_from(buffer, SLOTS_END_OFFSET)
    _check_slots_end(slots_end, file_end, file_path)
    found = _Found()
    # Where each (type, id) was seen.
    seen: dict[tuple[int, int], int] = {}
    for offset in range(HEADER_SIZE, slots_end + 1, RECORD_SIZE):
        if buffer[offset] == DELETED_MARK:
            continue
        type_, id_, *values = RECORD.unpack_from(buffer, offset)
        label = f"Record at {offset:#x}"
        if type_ not in _STATS and type_ not in _HONORS:
            raise InvalidStatsError(
                f"{label}: Type {type_} is not a stats type.", file_path
            )
        if (type_, id_) in seen:
            raise InvalidStatsError(
                f"{label}: Type {type_}, id {id_} repeats "
                f"the record at {seen[type_, id_]:#x}.",
                file_path,
            )
        seen[type_, id_] = offset
        if type_ in _STATS:
            base, name, decode = _STATS[type_]
            found.stats[base].setdefault(id_, {})[name] = decode(tuple(values))
            continue
        problem = _HONORS[type_](found, id_, tuple(values))
        if problem:
            raise InvalidStatsError(f"{label}: {problem}", file_path)
    (records,) = U32.unpack_from(buffer, RECORDS_OFFSET)
    if records != len(seen):
        raise InvalidStatsError(
            f"Records at {RECORDS_OFFSET:#04x} is {records}, "
            f"expected {len(seen)}, the live slots.",
            file_path,
        )
    return found.stats_file()


def _check_slots_end(slots_end: int, file_end: int, path: Path) -> None:
    # Slots end is the last byte of the last slot, so an empty file's is the
    # header's last byte.
    label = f"Slots end at {SLOTS_END_OFFSET:#04x} is {slots_end}"
    if slots_end < HEADER_SIZE - 1:
        raise InvalidStatsError(
            f"{label}, below the header's last byte ({HEADER_SIZE - 1}).", path
        )
    if (slots_end - (HEADER_SIZE - 1)) % RECORD_SIZE:
        raise InvalidStatsError(
            f"{label}, not the end of a whole {RECORD_SIZE}-byte slot.", path
        )
    if slots_end > file_end:
        raise InvalidStatsError(f"{label}, past the file end ({file_end}).", path)


@dataclass(slots=True)
class _Found:
    """The records read so far, each kind of honor with its id for sorting."""

    stats: dict[int, dict[int, dict[str, Any]]] = field(
        default_factory=lambda: {base: {} for base in _BLOCKS}
    )
    """By block base, then id: the stats fields its records fill."""

    players_of_the_game: list[tuple[int, PlayerOfTheGame]] = field(default_factory=list)
    all_pro: list[tuple[int, AllProPick]] = field(default_factory=list)
    coach_of_the_year: int | None = None
    awards: list[tuple[int, Award]] = field(default_factory=list)

    def stats_file(self) -> StatsFile:
        # In id order, as the .idx keys them; slot order is only where the
        # game found room. Each block's class matches its field, which the
        # checker cannot see through the table.
        mappings: dict[str, Any] = {
            block.name: {
                id_: block.stats(**fields)
                for id_, fields in sorted(self.stats[base].items())
            }
            for base, block in _BLOCKS.items()
        }
        return StatsFile(
            **mappings,
            players_of_the_game=_in_id_order(self.players_of_the_game),
            all_pro=_in_id_order(self.all_pro),
            coach_of_the_year=self.coach_of_the_year,
            awards=_in_id_order(self.awards),
        )


def _in_id_order[T](honors: list[tuple[int, T]]) -> tuple[T, ...]:
    return tuple(honor for _, honor in sorted(honors, key=lambda item: item[0]))


def _player_of_the_game(found: _Found, id_: int, values: _Values) -> str | None:
    if not 1 <= id_ <= PLAYER_OF_THE_WEEK_ID:
        return f"Player of the Game id {id_} is not 1-{PLAYER_OF_THE_WEEK_ID}."
    honor = PlayerOfTheGame(
        game=None if id_ == PLAYER_OF_THE_WEEK_ID else id_ - 1,
        points=values[0],
        player=values[1],
        team=values[2],
        opponent=values[3],
    )
    found.players_of_the_game.append((id_, honor))
    return None


def _all_pro(found: _Found, id_: int, values: _Values) -> str | None:
    if id_ == COACH_OF_THE_YEAR_ID:
        found.coach_of_the_year = values[1]
        return None
    position_plus_one, conference, pick = id_ & 0xF, (id_ >> 4) & 0xF, id_ >> 8
    if pick >= ALL_PRO_PICKS:
        return f"All-Pro id {id_} has pick {pick}, above {ALL_PRO_PICKS - 1}."
    if not position_plus_one:
        return f"All-Pro id {id_} has a position + 1 of 0."
    honor = AllProPick(
        position=position_plus_one - 1,
        conference=conference,
        pick=pick,
        player=values[1],
    )
    found.all_pro.append((id_, honor))
    return None


# Award code: its kind and conference (None for a league-wide award).
_AWARDS = {
    AWARD_MVP: (AwardKind.MVP, None),
    AWARD_OFFENSE_FIRST_CONFERENCE: (AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR, 0),
    AWARD_DEFENSE_FIRST_CONFERENCE: (AwardKind.DEFENSIVE_PLAYER_OF_THE_YEAR, 0),
    AWARD_OFFENSE_SECOND_CONFERENCE: (AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR, 1),
    AWARD_DEFENSE_SECOND_CONFERENCE: (AwardKind.DEFENSIVE_PLAYER_OF_THE_YEAR, 1),
    AWARD_ROOKIE: (AwardKind.ROOKIE_OF_THE_YEAR, None),
}


def _award(found: _Found, id_: int, values: _Values) -> str | None:
    code, year = id_ & 0xFF, id_ >> 8
    if code not in _AWARDS:
        codes = ", ".join(str(known) for known in _AWARDS)
        return f"Award id {id_} has code {code}, not an award code ({codes})."
    kind, conference = _AWARDS[code]
    honor = Award(kind=kind, conference=conference, year=year, player=values[1])
    found.awards.append((id_, honor))
    return None


# Category 15 player types: files the record, or says why its id does not
# decode.
_HONORS: dict[int, Callable[[_Found, int, _Values], str | None]] = {
    PLAYER_LAST_GAME + HONORS: _player_of_the_game,
    PLAYER_SEASON + HONORS: _all_pro,
    PLAYER_CAREER + HONORS: _award,
}


def _take(stats: Callable[..., object], count: int) -> _Decoder:
    """A decoder that passes the first `count` values to `stats` in order."""
    return lambda values: stats(*values[:count])


def _first(values: _Values) -> int:
    return values[0]


def _field_goals(values: _Values) -> FieldGoals:
    # Each range packs two counts into its unsigned 16 bits.
    return FieldGoals(
        long=values[0],
        ranges=tuple(
            FieldGoalRange(made=value & 0xFF, attempts=(value & 0xFFFF) >> 8)
            for value in values[1 : 1 + FIELD_GOAL_RANGES]
        ),
    )


def _punting(values: _Values) -> Punting:
    return Punting(
        *values[:PUNTING_UNUSED_VALUE],
        *values[PUNTING_UNUSED_VALUE + 1 : VALUES_PER_RECORD],
    )


def _hall_of_fame_nominee(values: _Values) -> HallOfFameNominee:
    # Value 0 is leftover memory.
    return HallOfFameNominee(
        points=values[1], year_retired=values[2], year_elected=values[3] or None
    )


def _game_details(values: _Values) -> GameDetails:
    # The score packs both teams' into its unsigned 16 bits, own score high.
    score = values[4] & 0xFFFF
    return GameDetails(
        opponent=values[0],
        penalties=values[1],
        penalty_yards=values[2],
        possession_seconds=values[3],
        score=score >> 8,
        opponent_score=score & 0xFF,
        fumbles_lost=values[5],
    )


# Category: the stats field it fills and its decoder.
_SHARED: dict[int, tuple[str, _Decoder]] = {
    EXTRA_POINTS: ("extra_points", _take(ExtraPoints, 2)),
    FIELD_GOALS: ("field_goals", _field_goals),
    RUSHING: ("rushing", _take(Rushing, 4)),
    PASSING: ("passing", _take(Passing, 8)),
    RECEIVING: ("receiving", _take(Receiving, 4)),
    INTERCEPTIONS: ("interceptions", _take(Interceptions, 4)),
    PUNTING: ("punting", _punting),
    PUNT_RETURNS: ("punt_returns", _take(PuntReturns, 5)),
    KICK_RETURNS: ("kick_returns", _take(KickReturns, 4)),
    FUMBLES: ("fumbles", _first),
    FUMBLE_RECOVERIES: ("fumble_recoveries", _take(FumbleRecoveries, 4)),
    SACKS: ("sacks", _first),
    SAFETIES: ("safeties", _first),
    TACKLES: ("tackles", _first),
    TWO_POINT_CONVERSIONS: ("two_point_conversions", _take(TwoPointConversions, 2)),
}
_TEAM = {
    FIRST_DOWNS: ("first_downs", _take(FirstDowns, 4)),
    DOWNS: ("downs", _take(Downs, 5)),
    GAME_DETAILS: ("game_details", _game_details),
}
_HALL_OF_FAME_POINTS = (
    "hall_of_fame_points",
    _take(HallOfFamePoints, 3),
)


@dataclass(frozen=True, slots=True)
class _Block:
    """Where a block's records go: the StatsFile field, the stats class, and
    the categories beyond the shared ones that fill it (category 15 player
    records are honors)."""

    name: str
    stats: type[PlayerStats] | type[TeamStats]
    own: dict[int, tuple[str, _Decoder]]


_BLOCKS = {
    PLAYER_LAST_GAME: _Block(
        "player_last_game",
        PlayerStats,
        {HALL_OF_FAME_POINTS: _HALL_OF_FAME_POINTS, PENALTIES: ("penalties", _first)},
    ),
    PLAYER_SEASON: _Block(
        "player_season", PlayerStats, {HALL_OF_FAME_POINTS: _HALL_OF_FAME_POINTS}
    ),
    PLAYER_CAREER: _Block(
        "player_career",
        PlayerStats,
        {
            HALL_OF_FAME_POINTS: _HALL_OF_FAME_POINTS,
            HALL_OF_FAME_NOMINEE: ("hall_of_fame_nominee", _hall_of_fame_nominee),
        },
    ),
    TEAM_LAST_GAME: _Block("team_last_game", TeamStats, _TEAM),
    TEAM_SEASON: _Block("team_season", TeamStats, _TEAM),
    OPPONENTS_LAST_GAME: _Block("opponents_last_game", TeamStats, _TEAM),
    OPPONENTS_SEASON: _Block("opponents_season", TeamStats, _TEAM),
}

# Every stats type but the honors: its block base, stats field and decoder.
_STATS: dict[int, tuple[int, str, _Decoder]] = {
    base + category: (base, name, decode)
    for base, block in _BLOCKS.items()
    for category, (name, decode) in (_SHARED | block.own).items()
}
