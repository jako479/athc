"""Tests for athc.fbpro98_stats.reader.

Real fixtures in data/ (the 2047 PNFL season) cover whole-file parsing and are
checked against the .lge; built bytes cover each category, the honors, and
every check at its limit and one past it.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from athc.fbpro98_lge import LgeFile, read_lge
from athc.fbpro98_stats import (
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
    InvalidStatsError,
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
    parse_stats,
    read_stats,
)

RUSHING = Rushing(attempts=1, yards=2, long=3, touchdowns=4)
EXTRA_POINTS = ExtraPoints(attempts=1, made=2)
TWO_POINT_CONVERSIONS = TwoPointConversions(attempts=1, made=2)

# The two player last-game rushing records `_two_slots` builds, decoded.
TWO_RUSHERS = StatsFile(
    player_last_game={
        1: PlayerStats(rushing=Rushing(attempts=1, yards=0, long=0, touchdowns=0)),
        2: PlayerStats(rushing=Rushing(attempts=2, yards=0, long=0, touchdowns=0)),
    }
)

# The 2047 PNFL season: copies of PNFL.dat from 47PNFL1, 47PNFL9, 47PNFL16 and
# 47PNFL19 (after the Super Bowl), and 47PNFL1's PNFL.lge. Expected values are
# the bytes at the offset each comment names, or the .lge.
FIXTURE_DIR = Path(__file__).resolve().parent / "data"
LGE_DIR = Path(__file__).resolve().parents[1] / "fbpro98_lge" / "data"
WEEK1 = "PNFL-after-week1"
WEEK9 = "PNFL-after-week9"
WEEK16 = "PNFL-after-week16"
SUPER_BOWL = "PNFL-after-super-bowl"


def _stats(league: str) -> StatsFile:
    return read_stats(league, FIXTURE_DIR)


def _team_numbers(lge: LgeFile) -> dict[int, int]:
    # Team objects to team numbers: team N is at index N - 1.
    return {id(team): number for number, team in enumerate(lge.teams, 1)}


# --- real files ---


def test_read_returns_stats_file_and_matches_parse():
    # Equality also checks the class: a dataclass equals only its own kind.
    stats = _stats(WEEK16)
    assert parse_stats((FIXTURE_DIR / f"{WEEK16}.dat").read_bytes()) == stats


def test_read_accepts_str_league_dir():
    assert read_stats(WEEK16, str(FIXTURE_DIR)) == _stats(WEEK16)


def _record_count(stats: StatsFile) -> int:
    mappings = (
        stats.player_last_game,
        stats.player_season,
        stats.player_career,
        stats.team_last_game,
        stats.team_season,
        stats.opponents_last_game,
        stats.opponents_season,
    )
    categories = sum(
        getattr(entry, item.name) is not None
        for mapping in mappings
        for entry in mapping.values()
        for item in fields(entry)
    )
    honors = len(stats.players_of_the_game) + len(stats.all_pro) + len(stats.awards)
    return categories + honors + (stats.coach_of_the_year is not None)


@pytest.mark.parametrize(
    ("league", "records"),
    # The header's record count at 0x18.
    [(WEEK1, 14567), (WEEK9, 16273), (WEEK16, 16802), (SUPER_BOWL, 15038)],
)
def test_every_record_is_read(league: str, records: int):
    assert _record_count(_stats(league)) == records


@pytest.mark.parametrize(
    ("league", "sizes"),
    # Distinct ids per block, category 15 player records left out.
    [
        (WEEK1, (591, 591, 2355, 18, 18, 18, 18)),
        (WEEK9, (596, 826, 2401, 18, 18, 18, 18)),
        (WEEK16, (569, 875, 2413, 18, 18, 18, 18)),
        (SUPER_BOWL, (62, 875, 2413, 2, 18, 2, 18)),
    ],
)
def test_block_sizes(league: str, sizes: tuple[int, ...]):
    stats = _stats(league)
    assert (
        len(stats.player_last_game),
        len(stats.player_season),
        len(stats.player_career),
        len(stats.team_last_game),
        len(stats.team_season),
        len(stats.opponents_last_game),
        len(stats.opponents_season),
    ) == sizes


def test_player_season_record():
    # Player 4037, the season's passing yards leader.
    assert _stats(WEEK16).player_season[4037] == PlayerStats(
        rushing=Rushing(attempts=58, yards=64, long=16, touchdowns=0),  # 0x4130C
        passing=Passing(  # 0x1D77C
            attempts=615,
            yards=4386,
            long=73,
            touchdowns=28,
            completions=344,
            interceptions=10,
            sacked=31,
            sack_yards=176,
        ),
        fumbles=4,  # 0x32AB4
        tackles=2,  # 0x32410
        hall_of_fame_points=HallOfFamePoints(  # 0x417A8
            count=1181, conference=0, points=819
        ),
    )


def test_player_career_record():
    assert _stats(WEEK16).player_career[4037] == PlayerStats(
        rushing=Rushing(attempts=520, yards=1383, long=35, touchdowns=19),  # 0x3D554
        passing=Passing(  # 0x3A2C8
            attempts=3516,
            yards=25773,
            long=78,
            touchdowns=230,
            completions=1987,
            interceptions=51,
            sacked=172,
            sack_yards=955,
        ),
        fumbles=44,  # 0x30200
        fumble_recoveries=FumbleRecoveries(  # 0x2D460
            recoveries=13, yards=-43, long=10, touchdowns=0
        ),
        tackles=4,  # 0x27934
        hall_of_fame_points=HallOfFamePoints(  # 0x304A8
            count=27604, conference=0, points=9709
        ),
        two_point_conversions=TwoPointConversions(attempts=17, made=6),  # 0x3C064
    )


def test_player_last_game_record():
    # Player 5595, the one player with a penalty in week 1.
    assert _stats(WEEK1).player_last_game[5595] == PlayerStats(
        tackles=2,  # 0x3B81C
        hall_of_fame_points=HallOfFamePoints(  # 0x465DC
            count=0, conference=1, points=-15
        ),
        penalties=1,  # 0xA7F8
    )


def test_career_total_past_32767_reads_negative():
    # Player 550, the 2047 MVP: career passing yards stored 0xA6D6 (42,710)
    # at 0x30D4, as the game shows them.
    assert _stats(WEEK16).player_career[550].passing == Passing(
        attempts=5996,
        yards=-22826,
        long=93,
        touchdowns=276,
        completions=3560,
        interceptions=112,
        sacked=362,
        sack_yards=1968,
    )


# Team 3: a record in every team category.
TEAM_3_SEASON = TeamStats(
    extra_points=ExtraPoints(attempts=32, made=31),  # 0x47BBC
    field_goals=FieldGoals(  # 0x33B80
        long=53,
        ranges=[
            FieldGoalRange(made=0, attempts=0),
            FieldGoalRange(made=5, attempts=6),
            FieldGoalRange(made=9, attempts=10),
            FieldGoalRange(made=3, attempts=6),
            FieldGoalRange(made=3, attempts=5),
        ],
    ),
    rushing=Rushing(attempts=395, yards=1725, long=38, touchdowns=18),  # 0x2B034
    passing=Passing(  # 0x2C63C
        attempts=588,
        yards=3610,
        long=46,
        touchdowns=21,
        completions=335,
        interceptions=14,
        sacked=25,
        sack_yards=125,
    ),
    receiving=Receiving(  # 0x3CA64
        receptions=335, yards=3610, long=46, touchdowns=21
    ),
    interceptions=Interceptions(  # 0x3C474
        interceptions=8, yards=152, long=71, touchdowns=1
    ),
    punting=Punting(  # 0x43E90
        punts=72,
        yards=3112,
        long=61,
        blocked=0,
        returns=32,
        return_yards=320,
        touchbacks=20,
    ),
    punt_returns=PuntReturns(  # 0x42798
        returns=44, yards=289, long=35, touchdowns=0, fair_catches=12
    ),
    kick_returns=KickReturns(  # 0xF2D0
        returns=85, yards=1911, long=101, touchdowns=1
    ),
    fumbles=17,  # 0x3F390
    fumble_recoveries=FumbleRecoveries(  # 0x25FA8
        recoveries=14, yards=-12, long=6, touchdowns=0
    ),
    sacks=38,  # 0x47644
    safeties=1,  # 0x7FA8
    tackles=847,  # 0x450D8
    first_downs=FirstDowns(  # 0x4D2B0
        total=337, rushing=115, passing=207, penalty=15
    ),
    downs=Downs(  # 0x1A338
        first_downs=337,
        third_down_attempts=208,
        third_downs_made=84,
        fourth_down_attempts=15,
        fourth_downs_made=7,
    ),
    game_details=GameDetails(  # 0x1E00
        opponent=11,
        penalties=16,
        penalty_yards=93,
        possession_seconds=28827,
        score=20,
        opponent_score=9,
        fumbles_lost=9,
    ),
    two_point_conversions=TwoPointConversions(attempts=9, made=6),  # 0x3F9D0
)
# What team 3's opponents did: no safety against it.
TEAM_3_OPPONENTS_SEASON = TeamStats(
    extra_points=ExtraPoints(attempts=38, made=38),  # 0x33338
    field_goals=FieldGoals(  # 0x450C4
        long=48,
        ranges=[
            FieldGoalRange(made=1, attempts=1),
            FieldGoalRange(made=6, attempts=6),
            FieldGoalRange(made=10, attempts=13),
            FieldGoalRange(made=10, attempts=16),
            FieldGoalRange(made=0, attempts=1),
        ],
    ),
    rushing=Rushing(attempts=403, yards=1483, long=51, touchdowns=16),  # 0x4D120
    passing=Passing(  # 0x3B24
        attempts=557,
        yards=3896,
        long=58,
        touchdowns=23,
        completions=320,
        interceptions=8,
        sacked=38,
        sack_yards=189,
    ),
    receiving=Receiving(  # 0x49CA0
        receptions=320, yards=3896, long=58, touchdowns=23
    ),
    interceptions=Interceptions(  # 0x4CA4
        interceptions=14, yards=167, long=32, touchdowns=1
    ),
    punting=Punting(  # 0x35868
        punts=71,
        yards=3067,
        long=70,
        blocked=0,
        returns=32,
        return_yards=289,
        touchbacks=18,
    ),
    punt_returns=PuntReturns(  # 0x285C8
        returns=40, yards=320, long=46, touchdowns=0, fair_catches=8
    ),
    kick_returns=KickReturns(  # 0x3CDE8
        returns=75, yards=1713, long=62, touchdowns=0
    ),
    fumbles=15,  # 0x2C4C0
    fumble_recoveries=FumbleRecoveries(  # 0x37AF0
        recoveries=18, yards=-15, long=8, touchdowns=1
    ),
    sacks=25,  # 0x29298
    tackles=842,  # 0x4C7E8
    first_downs=FirstDowns(  # 0x474C8
        total=309, rushing=93, passing=204, penalty=12
    ),
    downs=Downs(  # 0x44688
        first_downs=309,
        third_down_attempts=228,
        third_downs_made=92,
        fourth_down_attempts=19,
        fourth_downs_made=13,
    ),
    # Opponent and score are team 3's own, as in its team block.
    game_details=GameDetails(  # 0x37A78
        opponent=11,
        penalties=26,
        penalty_yards=155,
        possession_seconds=29763,
        score=20,
        opponent_score=9,
        fumbles_lost=6,
    ),
    two_point_conversions=TwoPointConversions(attempts=3, made=2),  # 0x48E2C
)


@pytest.mark.parametrize(
    ("mapping", "expected"),
    [
        ("team_season", TEAM_3_SEASON),
        ("opponents_season", TEAM_3_OPPONENTS_SEASON),
    ],
)
def test_team_and_opponents_season_record(mapping: str, expected: TeamStats):
    assert getattr(_stats(WEEK16), mapping)[3] == expected


def test_players_of_the_game_after_week_one():
    # Ids 1-9 at 0x17F20, 0x434E0, 0x4B938, 0x489E0, 0x403F8, 0x31790,
    # 0x21958, 0x742C, 0x3BE48; the Player of the Week at 0x4C84C.
    assert _stats(WEEK1).players_of_the_game == [
        PlayerOfTheGame(game=0, points=62, player=3987, team=9, opponent=3),
        PlayerOfTheGame(game=1, points=76, player=3579, team=16, opponent=6),
        PlayerOfTheGame(game=2, points=60, player=3090, team=5, opponent=2),
        PlayerOfTheGame(game=3, points=67, player=4969, team=8, opponent=7),
        PlayerOfTheGame(game=4, points=69, player=1496, team=13, opponent=1),
        PlayerOfTheGame(game=5, points=49, player=550, team=4, opponent=10),
        PlayerOfTheGame(game=6, points=65, player=5740, team=12, opponent=11),
        PlayerOfTheGame(game=7, points=76, player=2605, team=18, opponent=15),
        PlayerOfTheGame(game=8, points=56, player=2069, team=17, opponent=14),
        PlayerOfTheGame(game=None, points=96, player=3579, team=16, opponent=6),
    ]


def test_no_players_of_the_game_after_the_super_bowl():
    assert _stats(SUPER_BOWL).players_of_the_game == []


@pytest.mark.parametrize(
    ("league", "team"),
    # Value 1 at 0x4F790, then 0x52170. Until week 16 it is the previous
    # season's.
    [(WEEK1, 2), (WEEK9, 2), (WEEK16, 7), (SUPER_BOWL, 7)],
)
def test_coach_of_the_year(league: str, team: int):
    assert _stats(league).coach_of_the_year == team


def test_all_pro_team():
    all_pro = _stats(WEEK16).all_pro
    assert len(all_pro) == 68
    assert all_pro[0] == AllProPick(  # id 0x0001 at 0x4F790
        position=0, conference=0, pick=0, player=550
    )
    assert all_pro[28] == AllProPick(  # id 0x0101 at 0x2C088
        position=0, conference=0, pick=1, player=4037
    )
    assert all_pro[-1] == AllProPick(  # id 0x041B at 0x2BE1C
        position=10, conference=1, pick=4, player=4591
    )


def test_awards():
    awards = _stats(WEEK16).awards
    assert len(awards) == 84
    # Ids 0x2F5A-0x2F5E at 0x5210C-0x5215C, then 0x2F63 at 0x4DE68.
    assert awards[-6:] == [
        Award(kind=AwardKind.MVP, conference=None, year=47, player=550),
        Award(
            kind=AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR,
            conference=0,
            year=47,
            player=550,
        ),
        Award(
            kind=AwardKind.DEFENSIVE_PLAYER_OF_THE_YEAR,
            conference=0,
            year=47,
            player=4350,
        ),
        Award(
            kind=AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR,
            conference=1,
            year=47,
            player=5810,
        ),
        Award(
            kind=AwardKind.DEFENSIVE_PLAYER_OF_THE_YEAR,
            conference=1,
            year=47,
            player=2468,
        ),
        Award(kind=AwardKind.ROOKIE_OF_THE_YEAR, conference=None, year=47, player=7793),
    ]


@pytest.mark.parametrize(
    ("player", "expected"),
    [
        # 0xEBB4: not elected yet.
        (109, HallOfFameNominee(points=2994, year_retired=2045, year_elected=None)),
        # 0x105B8: elected in 2047.
        (192, HallOfFameNominee(points=10249, year_retired=2042, year_elected=2047)),
    ],
)
def test_hall_of_fame_nominee(player: int, expected: HallOfFameNominee):
    assert _stats(WEEK16).player_career[player].hall_of_fame_nominee == expected


def _points(team: TeamStats) -> int:
    # The scoring stats in team or opponents' season records, as points.
    returns = (
        team.rushing,
        team.receiving,
        team.interceptions,
        team.punt_returns,
        team.kick_returns,
        team.fumble_recoveries,
    )
    touchdowns = sum(stat.touchdowns for stat in returns if stat is not None)
    extra_points = team.extra_points.made if team.extra_points else 0
    field_goals = (
        sum(item.made for item in team.field_goals.ranges) if team.field_goals else 0
    )
    two_point = team.two_point_conversions.made if team.two_point_conversions else 0
    return (
        6 * touchdowns
        + extra_points
        + 3 * field_goals
        + 2 * two_point
        + 2 * (team.safeties or 0)
    )


def test_season_points_match_the_lge_after_week_one():
    # From week 3 the .dat gives Pittsburgh (team 9) a touchdown more than
    # the .lge score of its game with Minnesota, so later weeks are not
    # checked.
    stats = _stats(WEEK1)
    lge = read_lge(WEEK1, FIXTURE_DIR)
    scored = {n: _points(team) for n, team in stats.team_season.items()}
    allowed = {n: _points(team) for n, team in stats.opponents_season.items()}
    assert scored == {n: team.record.points_for for n, team in enumerate(lge.teams, 1)}
    assert allowed == {
        n: team.record.points_against for n, team in enumerate(lge.teams, 1)
    }


@pytest.mark.parametrize(
    ("league", "teams"),
    # The last regular-season week, then the Super Bowl alone.
    [(WEEK16, set(range(1, 19))), (SUPER_BOWL, {4, 17})],
)
def test_last_game_block_holds_the_last_games_teams(league: str, teams: set[int]):
    assert set(_stats(league).team_last_game) == teams


def _last_game(team: TeamStats) -> tuple[int, int, int] | None:
    # Opponent, own score, opponent's score.
    details = team.game_details
    if details is None:
        return None
    return (details.opponent, details.score, details.opponent_score)


@pytest.mark.parametrize("league", [WEEK16, SUPER_BOWL])
def test_last_game_matches_the_lge(league: str):
    lge = read_lge(league, LGE_DIR)
    number = _team_numbers(lge)
    # The teams of the .lge's last played week or round, each with that game.
    rounds = [week for week in (*lge.weeks, *lge.playoffs) if week]
    expected: dict[int, tuple[int, int, int] | None] = {}
    for game in rounds[-1]:
        home, away = number[id(game.home)], number[id(game.away)]
        expected[home] = (away, game.home_score, game.away_score)
        expected[away] = (home, game.away_score, game.home_score)
    found = {
        team: _last_game(record)
        for team, record in _stats(league).team_last_game.items()
    }
    assert found == expected


def test_playoffs_leave_season_and_career_unchanged():
    regular, playoffs = _stats(WEEK16), _stats(SUPER_BOWL)
    assert playoffs.player_season == regular.player_season
    assert playoffs.player_career == regular.player_career
    assert playoffs.team_season == regular.team_season
    assert playoffs.opponents_season == regular.opponents_season
    assert playoffs.all_pro == regular.all_pro
    assert playoffs.coach_of_the_year == regular.coach_of_the_year
    assert playoffs.awards == regular.awards


# --- header ---


def test_header_alone_is_an_empty_stats_file(make_dat):
    assert parse_stats(make_dat()) == StatsFile()


def test_shorter_than_the_header_rejected(make_dat):
    with pytest.raises(InvalidStatsError, match="140-byte header"):
        parse_stats(make_dat()[:139])


@pytest.mark.parametrize("file_end", [138, 140])
def test_file_end_must_be_the_size_less_one(make_dat, file_end: int):
    with pytest.raises(InvalidStatsError, match="File end"):
        parse_stats(make_dat(file_end=file_end))


@pytest.mark.parametrize("record_size", [19, 21])
def test_record_size_must_be_20(make_dat, record_size: int):
    with pytest.raises(InvalidStatsError, match="Record size"):
        parse_stats(make_dat(record_size=record_size))


def test_slots_end_below_the_header_rejected(make_dat):
    with pytest.raises(InvalidStatsError, match=r"Slots end .* below"):
        parse_stats(make_dat(slots_end=138))


def _two_slots(make_record) -> list[bytes]:
    return [make_record(2, 1, [1]), make_record(2, 2, [2])]


@pytest.mark.parametrize("slots_end", [139 + 39, 139 + 41])
def test_slots_end_not_whole_records_rejected(make_dat, make_record, slots_end: int):
    # The tail keeps 139 + 41 inside the file, so only the slot size is wrong.
    buffer = make_dat(_two_slots(make_record), slots_end=slots_end, tail=bytes(20))
    with pytest.raises(InvalidStatsError, match=r"Slots end .* whole"):
        parse_stats(buffer)


def test_slots_end_at_whole_records_accepted(make_dat, make_record):
    # No tail: the slots end at the file's last byte.
    buffer = make_dat(_two_slots(make_record), slots_end=139 + 40)
    assert parse_stats(buffer) == TWO_RUSHERS


@pytest.mark.parametrize(
    "tail",
    [
        # File end 198: slots end 199 is one byte past it.
        pytest.param(bytes(19), id="one byte past"),
        # File end 179: one whole slot past it.
        pytest.param(b"", id="one slot past"),
    ],
)
def test_slots_running_past_the_file_end_rejected(make_dat, make_record, tail: bytes):
    buffer = make_dat(_two_slots(make_record), slots_end=139 + 60, tail=tail)
    with pytest.raises(InvalidStatsError, match=r"Slots end .* past"):
        parse_stats(buffer)


@pytest.mark.parametrize("tail", [b"\xff" * 20, b"\x00" * 20])
def test_bytes_after_the_slots_ignored(make_dat, tail: bytes):
    assert parse_stats(make_dat(tail=tail)) == StatsFile()


def _live_deleted_live(make_record, make_deleted) -> list[bytes]:
    return [make_record(2, 1, [1]), make_deleted(), make_record(2, 2, [2])]


@pytest.mark.parametrize("records", [3, 1])
def test_record_count_must_match_live_slots(
    make_dat, make_record, make_deleted, records: int
):
    buffer = make_dat(_live_deleted_live(make_record, make_deleted), records=records)
    with pytest.raises(InvalidStatsError, match="Records"):
        parse_stats(buffer)


def test_record_count_of_live_slots_accepted(make_dat, make_record, make_deleted):
    buffer = make_dat(_live_deleted_live(make_record, make_deleted), records=2)
    assert parse_stats(buffer) == TWO_RUSHERS


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        pytest.param(
            {"file_end": 158, "record_size": 21},
            "File end",
            id="file end, then record size",
        ),
        pytest.param(
            {"record_size": 21, "slots_end": 138},
            "Record size",
            id="record size, then slots end",
        ),
        pytest.param({"slots_end": 138}, "Slots end", id="slots end, then the slot"),
        pytest.param({"records": 2}, "Type 18", id="the slot, then the record count"),
    ],
)
def test_first_problem_in_check_order_reported(
    make_dat, make_record, overrides: dict[str, int], reason: str
):
    # The one slot has an unknown type, so each buffer has two problems.
    buffer = make_dat([make_record(18, 1, [1])], **overrides)
    with pytest.raises(InvalidStatsError, match=reason):
        parse_stats(buffer)


def test_error_names_the_path_first(make_dat):
    with pytest.raises(InvalidStatsError, match=r"^league\.dat: ") as info:
        parse_stats(make_dat()[:139], "league.dat")
    assert info.value.path == Path("league.dat")


def test_missing_file_raises_oserror_for_built_path(tmp_path: Path):
    with pytest.raises(OSError) as info:
        read_stats("missing", tmp_path)
    assert Path(info.value.filename) == tmp_path / "missing.dat"


# --- records ---

# Category, its values, the field it fills and what it decodes to; the same in
# player and team blocks. Values count up so each one's position shows.
STANDARD_CATEGORIES = [
    pytest.param(0, [1, 2], "extra_points", EXTRA_POINTS, id="extra points"),
    pytest.param(
        1,
        [1, 0x0201, 0x0403, 0x0605, 0x0807, 0x0A09],
        "field_goals",
        FieldGoals(
            long=1,
            ranges=[
                FieldGoalRange(made=1, attempts=2),
                FieldGoalRange(made=3, attempts=4),
                FieldGoalRange(made=5, attempts=6),
                FieldGoalRange(made=7, attempts=8),
                FieldGoalRange(made=9, attempts=10),
            ],
        ),
        id="field goals",
    ),
    pytest.param(2, [1, 2, 3, 4], "rushing", RUSHING, id="rushing"),
    pytest.param(
        3,
        [1, 2, 3, 4, 5, 6, 7, 8],
        "passing",
        Passing(
            attempts=1,
            yards=2,
            long=3,
            touchdowns=4,
            completions=5,
            interceptions=6,
            sacked=7,
            sack_yards=8,
        ),
        id="passing",
    ),
    pytest.param(
        4,
        [1, 2, 3, 4],
        "receiving",
        Receiving(receptions=1, yards=2, long=3, touchdowns=4),
        id="receiving",
    ),
    pytest.param(
        5,
        [1, 2, 3, 4],
        "interceptions",
        Interceptions(interceptions=1, yards=2, long=3, touchdowns=4),
        id="interceptions",
    ),
    # Value 3 is always 0 in the game's files; the 9 there is skipped.
    pytest.param(
        6,
        [1, 2, 3, 9, 4, 5, 6, 7],
        "punting",
        Punting(
            punts=1, yards=2, long=3, blocked=4, returns=5, return_yards=6, touchbacks=7
        ),
        id="punting",
    ),
    pytest.param(
        7,
        [1, 2, 3, 4, 5],
        "punt_returns",
        PuntReturns(returns=1, yards=2, long=3, touchdowns=4, fair_catches=5),
        id="punt returns",
    ),
    pytest.param(
        8,
        [1, 2, 3, 4],
        "kick_returns",
        KickReturns(returns=1, yards=2, long=3, touchdowns=4),
        id="kick returns",
    ),
    pytest.param(9, [7], "fumbles", 7, id="fumbles"),
    pytest.param(
        10,
        [1, 2, 3, 4],
        "fumble_recoveries",
        FumbleRecoveries(recoveries=1, yards=2, long=3, touchdowns=4),
        id="fumble recoveries",
    ),
    pytest.param(11, [7], "sacks", 7, id="sacks"),
    pytest.param(12, [7], "safeties", 7, id="safeties"),
    pytest.param(13, [7], "tackles", 7, id="tackles"),
    pytest.param(
        17, [1, 2], "two_point_conversions", TWO_POINT_CONVERSIONS, id="two-point"
    ),
]


@pytest.mark.parametrize(
    ("category", "values", "field", "expected"), STANDARD_CATEGORIES
)
def test_player_category_decoded(
    make_dat, make_record, category: int, values: list[int], field: str, expected: Any
):
    stats = parse_stats(make_dat([make_record(32 + category, 9, values)]))
    assert stats.player_season == {9: PlayerStats(**{field: expected})}


@pytest.mark.parametrize(
    ("category", "values", "field", "expected"), STANDARD_CATEGORIES
)
def test_team_category_decoded(
    make_dat, make_record, category: int, values: list[int], field: str, expected: Any
):
    stats = parse_stats(make_dat([make_record(130 + category, 9, values)]))
    assert stats.team_season == {9: TeamStats(**{field: expected})}


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        pytest.param(
            0, StatsFile(player_last_game={3: PlayerStats(rushing=RUSHING)}), id="0"
        ),
        pytest.param(
            32, StatsFile(player_season={3: PlayerStats(rushing=RUSHING)}), id="32"
        ),
        pytest.param(
            64, StatsFile(player_career={3: PlayerStats(rushing=RUSHING)}), id="64"
        ),
        pytest.param(
            96, StatsFile(team_last_game={3: TeamStats(rushing=RUSHING)}), id="96"
        ),
        pytest.param(
            130, StatsFile(team_season={3: TeamStats(rushing=RUSHING)}), id="130"
        ),
        pytest.param(
            164,
            StatsFile(opponents_last_game={3: TeamStats(rushing=RUSHING)}),
            id="164",
        ),
        pytest.param(
            198, StatsFile(opponents_season={3: TeamStats(rushing=RUSHING)}), id="198"
        ),
    ],
)
def test_each_block_fills_its_own_mapping(
    make_dat, make_record, base: int, expected: StatsFile
):
    assert parse_stats(make_dat([make_record(base + 2, 3, [1, 2, 3, 4])])) == expected


def test_records_of_one_id_group_together(make_dat, make_record):
    slots = [make_record(34, 9, [1, 2, 3, 4]), make_record(35, 9, [5, 6, 7, 8])]
    passing = Passing(
        attempts=5,
        yards=6,
        long=7,
        touchdowns=8,
        completions=0,
        interceptions=0,
        sacked=0,
        sack_yards=0,
    )
    assert parse_stats(make_dat(slots)).player_season == {
        9: PlayerStats(rushing=RUSHING, passing=passing)
    }


@pytest.mark.parametrize(
    ("stored", "yards"), [(0xFFFF, -1), (0x8000, -32768), (0x7FFF, 32767)]
)
def test_values_are_signed(make_dat, make_record, stored: int, yards: int):
    stats = parse_stats(make_dat([make_record(34, 1, [1, stored, 3, 4])]))
    assert stats.player_season[1].rushing == Rushing(
        attempts=1, yards=yards, long=3, touchdowns=4
    )


@pytest.mark.parametrize(
    ("stored", "made", "attempts"), [(0x00FF, 255, 0), (0xFF00, 0, 255)]
)
def test_field_goal_range_bytes_read_unsigned(
    make_dat, make_record, stored: int, made: int, attempts: int
):
    stats = parse_stats(make_dat([make_record(33, 1, [40, stored])]))
    assert stats.player_season[1].field_goals == FieldGoals(
        long=40,
        ranges=[
            FieldGoalRange(made=made, attempts=attempts),
            FieldGoalRange(made=0, attempts=0),
            FieldGoalRange(made=0, attempts=0),
            FieldGoalRange(made=0, attempts=0),
            FieldGoalRange(made=0, attempts=0),
        ],
    )


def test_values_past_a_category_are_ignored(make_dat, make_record):
    record = make_record(34, 1, [1, 2, 3, 4, 0x7777, 0x7777, 0x7777, 0x7777])
    assert parse_stats(make_dat([record])).player_season == {
        1: PlayerStats(rushing=RUSHING)
    }


def test_deleted_slot_skipped(make_dat, make_record):
    # Past its mark, the slot is a whole rushing record.
    slot = b"\xff" + make_record(34, 1, [1, 2, 3, 4])[1:]
    assert parse_stats(make_dat([slot])) == StatsFile()


@pytest.mark.parametrize("id_", [0, 65535])
def test_ids_at_both_ends_are_keys(make_dat, make_record, id_: int):
    stats = parse_stats(make_dat([make_record(34, id_, [1, 2, 3, 4])]))
    assert stats.player_season == {id_: PlayerStats(rushing=RUSHING)}


def test_mappings_are_in_id_order(make_dat, make_record):
    slots = [make_record(34, id_, [id_]) for id_ in (7, 2, 5)]
    assert list(parse_stats(make_dat(slots)).player_season) == [2, 5, 7]


PLAYER_FIRST = PlayerStats(extra_points=EXTRA_POINTS)
PLAYER_LAST = PlayerStats(two_point_conversions=TWO_POINT_CONVERSIONS)
TEAM_FIRST = TeamStats(extra_points=EXTRA_POINTS)
TEAM_LAST = TeamStats(two_point_conversions=TWO_POINT_CONVERSIONS)


@pytest.mark.parametrize(
    ("type_", "mapping", "expected"),
    [
        (0, "player_last_game", PLAYER_FIRST),
        (17, "player_last_game", PLAYER_LAST),
        (32, "player_season", PLAYER_FIRST),
        (49, "player_season", PLAYER_LAST),
        (64, "player_career", PLAYER_FIRST),
        (81, "player_career", PLAYER_LAST),
        (96, "team_last_game", TEAM_FIRST),
        (113, "team_last_game", TEAM_LAST),
        (130, "team_season", TEAM_FIRST),
        (147, "team_season", TEAM_LAST),
        (164, "opponents_last_game", TEAM_FIRST),
        (181, "opponents_last_game", TEAM_LAST),
        (198, "opponents_season", TEAM_FIRST),
        (215, "opponents_season", TEAM_LAST),
    ],
)
def test_stats_types_accepted(
    make_dat, make_record, type_: int, mapping: str, expected: PlayerStats | TeamStats
):
    # Categories 0 and 17, each block's ends, both hold attempts then made.
    stats = parse_stats(make_dat([make_record(type_, 1, [1, 2])]))
    assert getattr(stats, mapping) == {1: expected}


@pytest.mark.parametrize(
    "type_",
    [18, 31, 48, 50, 63, 82, 95, 114, 129, 148, 163, 182, 197, 216, 0xFFFE],
)
def test_other_types_rejected(make_dat, make_record, type_: int):
    # Type 48, player season category 16, is unused.
    with pytest.raises(
        InvalidStatsError, match=rf"at 0x8c: Type {type_} is not a stats type\."
    ):
        parse_stats(make_dat([make_record(type_, 1, [1])]))


def test_duplicate_record_rejected(make_dat, make_record):
    slots = [make_record(34, 1, [1]), make_record(34, 1, [2])]
    with pytest.raises(InvalidStatsError, match="at 0xa0: Type 34, id 1 repeats"):
        parse_stats(make_dat(slots))


def test_same_type_other_id_accepted(make_dat, make_record):
    slots = [make_record(34, 1, [1]), make_record(34, 2, [2])]
    assert parse_stats(make_dat(slots)).player_season == {
        1: PlayerStats(rushing=Rushing(attempts=1, yards=0, long=0, touchdowns=0)),
        2: PlayerStats(rushing=Rushing(attempts=2, yards=0, long=0, touchdowns=0)),
    }


def test_first_problem_in_slot_order_reported(make_dat, make_record):
    # A repeat at 0xa0, then an unknown type at 0xb4: the repeat is reported,
    # though the type check is the first of each slot's checks.
    slots = [make_record(34, 1, [1]), make_record(34, 1, [1]), make_record(18, 1, [1])]
    with pytest.raises(InvalidStatsError, match="at 0xa0: Type 34, id 1 repeats"):
        parse_stats(make_dat(slots))


# --- categories 14-16 and honors ---


@pytest.mark.parametrize(
    ("type_", "mapping"),
    [(14, "player_last_game"), (46, "player_season"), (78, "player_career")],
)
def test_hall_of_fame_points_in_each_player_block(
    make_dat, make_record, type_: int, mapping: str
):
    stats = parse_stats(make_dat([make_record(type_, 5, [1, 2, 3])]))
    points = HallOfFamePoints(count=1, conference=2, points=3)
    assert getattr(stats, mapping) == {5: PlayerStats(hall_of_fame_points=points)}


def test_penalties_in_player_last_game(make_dat, make_record):
    stats = parse_stats(make_dat([make_record(16, 5, [7])]))
    assert stats.player_last_game == {5: PlayerStats(penalties=7)}


@pytest.mark.parametrize(("stored", "year_elected"), [(0, None), (2047, 2047)])
def test_hall_of_fame_nominee_in_player_career(
    make_dat, make_record, stored: int, year_elected: int | None
):
    # Value 0 is leftover memory.
    stats = parse_stats(make_dat([make_record(80, 5, [0x5555, 1, 2040, stored])]))
    nominee = HallOfFameNominee(points=1, year_retired=2040, year_elected=year_elected)
    assert stats.player_career == {5: PlayerStats(hall_of_fame_nominee=nominee)}


@pytest.mark.parametrize(
    ("category", "values", "field", "expected"),
    [
        pytest.param(
            14,
            [1, 2, 3, 4],
            "first_downs",
            FirstDowns(total=1, rushing=2, passing=3, penalty=4),
            id="first downs",
        ),
        pytest.param(
            15,
            [1, 2, 3, 4, 5],
            "downs",
            Downs(
                first_downs=1,
                third_down_attempts=2,
                third_downs_made=3,
                fourth_down_attempts=4,
                fourth_downs_made=5,
            ),
            id="downs",
        ),
        pytest.param(
            16,
            [1, 2, 3, 4, 0x0506, 7],
            "game_details",
            GameDetails(
                opponent=1,
                penalties=2,
                penalty_yards=3,
                possession_seconds=4,
                score=5,
                opponent_score=6,
                fumbles_lost=7,
            ),
            id="game details",
        ),
    ],
)
@pytest.mark.parametrize(
    ("base", "mapping"),
    [
        (96, "team_last_game"),
        (130, "team_season"),
        (164, "opponents_last_game"),
        (198, "opponents_season"),
    ],
)
def test_team_categories_14_to_16(
    make_dat,
    make_record,
    base: int,
    mapping: str,
    category: int,
    values: list[int],
    field: str,
    expected: Any,
):
    stats = parse_stats(make_dat([make_record(base + category, 5, values)]))
    assert getattr(stats, mapping) == {5: TeamStats(**{field: expected})}


def _game_details(score: int, opponent_score: int, possession: int) -> GameDetails:
    return GameDetails(
        opponent=3,
        penalties=0,
        penalty_yards=0,
        possession_seconds=possession,
        score=score,
        opponent_score=opponent_score,
        fumbles_lost=0,
    )


@pytest.mark.parametrize(
    ("stored", "score", "opponent_score"),
    [(0x1E18, 30, 24), (0x00FF, 0, 255), (0xFF00, 255, 0)],
)
def test_game_score_split(
    make_dat, make_record, stored: int, score: int, opponent_score: int
):
    stats = parse_stats(make_dat([make_record(146, 5, [3, 0, 0, 1800, stored])]))
    assert stats.team_season[5].game_details == _game_details(
        score, opponent_score, 1800
    )


def test_possession_past_32767_reads_negative(make_dat, make_record):
    stats = parse_stats(make_dat([make_record(146, 5, [3, 0, 0, 0x8001, 0])]))
    assert stats.team_season[5].game_details == _game_details(0, 0, -32767)


@pytest.mark.parametrize(("id_", "game"), [(1, 0), (98, 97), (99, None)])
def test_player_of_the_game(make_dat, make_record, id_: int, game: int | None):
    stats = parse_stats(make_dat([make_record(15, id_, [25, 1234, 3, 4])]))
    expected = PlayerOfTheGame(game=game, points=25, player=1234, team=3, opponent=4)
    assert stats == StatsFile(players_of_the_game=[expected])


@pytest.mark.parametrize("id_", [0, 100])
def test_player_of_the_game_id_out_of_range_rejected(make_dat, make_record, id_: int):
    with pytest.raises(
        InvalidStatsError, match=rf"at 0x8c: Player of the Game id {id_} is not 1-99\."
    ):
        parse_stats(make_dat([make_record(15, id_, [25, 1234, 3, 4])]))


@pytest.mark.parametrize(
    ("id_", "position", "conference", "pick"),
    [(0x0001, 0, 0, 0), (0x04FF, 14, 15, 4)],
)
def test_all_pro_pick_decoded(
    make_dat, make_record, id_: int, position: int, conference: int, pick: int
):
    # Only value 1 is read; the others are junk.
    values = [0x1111, 6283, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777]
    stats = parse_stats(make_dat([make_record(47, id_, values)]))
    expected = AllProPick(
        position=position, conference=conference, pick=pick, player=6283
    )
    assert stats == StatsFile(all_pro=[expected])


@pytest.mark.parametrize(
    ("id_", "reason"),
    [
        (0x0501, r"pick 5, above 4"),
        (0x0100, r"a position \+ 1 of 0"),
        # One past Coach of the Year.
        (4097, r"pick 16, above 4"),
    ],
)
def test_all_pro_id_rejected(make_dat, make_record, id_: int, reason: str):
    with pytest.raises(
        InvalidStatsError, match=rf"at 0x8c: All-Pro id {id_} has {reason}\."
    ):
        parse_stats(make_dat([make_record(47, id_, [0, 6283])]))


def test_coach_of_the_year_decoded(make_dat, make_record):
    stats = parse_stats(make_dat([make_record(47, 4096, [0x1111, 7, 0x2222])]))
    assert stats == StatsFile(coach_of_the_year=7)


@pytest.mark.parametrize(
    ("code", "kind", "conference"),
    [
        (90, AwardKind.MVP, None),
        (91, AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR, 0),
        (92, AwardKind.DEFENSIVE_PLAYER_OF_THE_YEAR, 0),
        (93, AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR, 1),
        (94, AwardKind.DEFENSIVE_PLAYER_OF_THE_YEAR, 1),
        (99, AwardKind.ROOKIE_OF_THE_YEAR, None),
    ],
)
def test_award_decoded(
    make_dat, make_record, code: int, kind: AwardKind, conference: int | None
):
    stats = parse_stats(make_dat([make_record(79, code + 47 * 256, [0x3333, 6283])]))
    expected = Award(kind=kind, conference=conference, year=47, player=6283)
    assert stats == StatsFile(awards=[expected])


@pytest.mark.parametrize("code", [89, 95, 98, 100])
def test_award_code_rejected(make_dat, make_record, code: int):
    id_ = code + 47 * 256
    with pytest.raises(
        InvalidStatsError, match=rf"at 0x8c: Award id {id_} has code {code},"
    ):
        parse_stats(make_dat([make_record(79, id_, [0, 6283])]))


def test_stats_are_edited_by_assignment():
    stats = _stats(WEEK16)
    stats.team_season[3] = TeamStats(rushing=RUSHING)
    stats.player_season[4037].passing = None
    del stats.awards[:-1]
    assert stats.team_season[3] == TeamStats(rushing=RUSHING)
    assert stats.player_season[4037].passing is None
    assert len(stats.awards) == 1


def test_players_of_the_game_in_id_order(make_dat, make_record):
    slots = [make_record(15, id_, [1, 2, 3, 4]) for id_ in (99, 3, 1)]
    stats = parse_stats(make_dat(slots))
    assert [honor.game for honor in stats.players_of_the_game] == [0, 2, None]


def test_all_pro_in_id_order(make_dat, make_record):
    slots = [make_record(47, id_, [0, 6283]) for id_ in (0x0102, 0x0001, 0x0011)]
    stats = parse_stats(make_dat(slots))
    assert [(pick.pick, pick.conference, pick.position) for pick in stats.all_pro] == [
        (0, 0, 0),
        (0, 1, 0),
        (1, 0, 1),
    ]


def test_awards_in_id_order(make_dat, make_record):
    slots = [
        make_record(79, code + year * 256, [0, 6283])
        for code, year in [(91, 47), (99, 46), (90, 47)]
    ]
    stats = parse_stats(make_dat(slots))
    assert [(award.year, award.kind) for award in stats.awards] == [
        (46, AwardKind.ROOKIE_OF_THE_YEAR),
        (47, AwardKind.MVP),
        (47, AwardKind.OFFENSIVE_PLAYER_OF_THE_YEAR),
    ]
