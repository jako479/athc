"""The scheduler's League from two league files: conferences, divisions and
names from the upcoming season's `.lge`, standings from the previous season's,
teams matched by name with the season's renames, the last tiebreak a coin toss
drawn from the run's seed.

Real PNFL files (2046 to 2048) cover the standings rules against the league's
own published order; built `LgeFile` objects cover the shapes and errors no
real file holds.
"""

from __future__ import annotations

import random
import shutil
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

from athc.errors import ConfigFileError
from athc.fbpro98_lge import Conference, Division, Game, LgeFile, Record, Team
from athc.scheduler.domain.league import League
from athc.scheduler.league_files import league_from_files, load_league
from athc.scheduler.schedulers.errors import SchedulerError
from tests.unit.fbpro98_lge.conftest import build_empty_roster

DATA = Path(__file__).resolve().parents[2] / "integration" / "data"
LEAGUE = "divisions"
PREVIOUS_2046 = "PNFL-2046-after-super-bowl"
UPCOMING_2047 = "PNFL-2047-after-week1"
PREVIOUS_2047 = "PNFL-2047-after-super-bowl"
UPCOMING_2048 = "PNFL-2048-after-week1"
RENAMES_2048 = {"Baltimore": "Los Angeles"}
RENAMES_2047 = {
    "Houston": "Miami",
    "New York A": "Cincinnati",
    "Indianapolis": "Baltimore",
    "New York N": "New York",
}
RULES = Path("scheduler.toml")
SEED = 0  # the run's seed: draws the coin toss

# The 2048 standings as the league published them (the former shipped
# 2048.league.ini): playoff finish, record, strength of schedule.
REAL_2048_OVERALL = [
    "Miami",
    "Minnesota",
    "Los Angeles",
    "Chicago",
    "Denver",
    "Washington",
    "Atlanta",
    "Las Vegas",
    "New England",
    "Green Bay",
    "Cincinnati",
    "New York",
    "San Francisco",
    "Jacksonville",
    "Philadelphia",
    "Pittsburgh",
    "Seattle",
    "Buffalo",
]
REAL_2048_FINISH = {
    "East1": ["Miami", "New England", "Jacksonville", "Buffalo"],
    "West1": ["Los Angeles", "Denver", "Las Vegas", "Cincinnati", "Pittsburgh"],
    "East2": ["Washington", "Atlanta", "New York", "Philadelphia"],
    "West2": ["Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"],
}

# The 2047 order with SEED; level teams fall to the seed's coin toss.
OVERALL_2047 = [
    "Pittsburgh",
    "Washington",
    "Minnesota",
    "Cincinnati",
    "Miami",
    "Buffalo",
    "Seattle",
    "San Francisco",
    "Baltimore",
    "Las Vegas",
    "Philadelphia",
    "Chicago",
    "Green Bay",
    "Denver",
    "Jacksonville",
    "Atlanta",
    "New York",
    "New England",
]
FINISH_2047 = {
    "East1": ["Miami", "Buffalo", "Jacksonville", "New England"],
    "West1": ["Pittsburgh", "Cincinnati", "Baltimore", "Las Vegas", "Denver"],
    "East2": ["Washington", "Philadelphia", "Atlanta", "New York"],
    "West2": ["Minnesota", "Seattle", "San Francisco", "Chicago", "Green Bay"],
}


def _files(tmp_path: Path, previous: str, upcoming: str) -> tuple[Path, Path]:
    """The two fixtures copied to `previous\\<LEAGUE>.lge` and
    `upcoming\\<LEAGUE>.lge`; returns the two files."""
    files: list[Path] = []
    for kind, fixture in (("previous", previous), ("upcoming", upcoming)):
        folder = tmp_path / kind
        folder.mkdir()
        files.append(
            Path(shutil.copy(DATA / f"{fixture}.lge", folder / f"{LEAGUE}.lge"))
        )
    return files[0], files[1]


def _no_warning(line: str) -> None:
    raise AssertionError(f"unexpected warning: {line}")


def _load(
    tmp_path: Path, previous: str, upcoming: str, renames: dict[str, str], season: int
) -> League:
    previous_file, upcoming_file = _files(tmp_path, previous, upcoming)
    return load_league(
        previous_file,
        upcoming_file,
        renames,
        season=season,
        seed=SEED,
        rules_path=RULES,
        warn=_no_warning,
    )


def _coin_toss(names: Sequence[str], seed: int = SEED) -> list[str]:
    """The previous teams, in previous-file order, shuffled from `seed`."""
    tossed = list(names)
    random.Random(seed).shuffle(tossed)
    return tossed


def _finish(league: League) -> dict[str, list[str]]:
    return {
        f"{division.name}{division.conference.number}": [t.metro for t in order]
        for division, order in league.division_standings.items()
    }


def _overall(league: League) -> list[str]:
    return [team.metro for team in league.rankings.overall]


# --- real seasons --------------------------------------------------------------


def test_2048_league_matches_the_real_final_standings(tmp_path: Path) -> None:
    league = _load(tmp_path, PREVIOUS_2047, UPCOMING_2048, RENAMES_2048, 2048)
    assert _overall(league) == REAL_2048_OVERALL
    assert _finish(league) == REAL_2048_FINISH
    assert league.has_divisions
    assert [c.name for c in league.conferences] == ["", ""]
    assert [d.name for d in league.divisions] == ["East", "West", "East", "West"]
    assert [d.expected_size for d in league.divisions] == [4, 5, 4, 5]


def test_2047_league_follows_realignment_and_renames(tmp_path: Path) -> None:
    # 2046 -> 2047: Jacksonville moved to the East; the renamed Cincinnati and
    # Baltimore moved to the West. Finish orders use the 2046 records of the
    # teams now in each division; the overall order follows the 2046 playoffs.
    league = _load(tmp_path, PREVIOUS_2046, UPCOMING_2047, RENAMES_2047, 2047)
    teams = {team.metro: team for team in league.teams}
    assert teams["Jacksonville"].division is not None
    assert teams["Jacksonville"].division.number == 1
    assert {teams["Cincinnati"].division, teams["Baltimore"].division} == {
        teams["Denver"].division
    }
    finish = _finish(league)
    assert finish["East1"] == ["Miami", "Buffalo", "Jacksonville", "New England"]
    assert finish["West1"] == [
        "Pittsburgh",
        "Cincinnati",
        "Baltimore",
        "Las Vegas",
        "Denver",
    ]
    assert _overall(league) == OVERALL_2047
    assert _finish(league) == FINISH_2047


def test_unfinished_season_is_a_warning(tmp_path: Path) -> None:
    # The 2048 opening-week file gives the standings: the warning names it,
    # and the League is built from the games played.
    previous, upcoming = _files(tmp_path, UPCOMING_2048, UPCOMING_2048)
    said: list[str] = []
    league = load_league(
        previous,
        upcoming,
        {},
        season=2048,
        seed=SEED,
        rules_path=RULES,
        warn=said.append,
    )
    assert said == [f"{previous}: Season not finished. 142 game(s) not played."]
    assert len(league.teams) == 18


def test_unmatched_previous_team_names_the_renames_table(tmp_path: Path) -> None:
    previous, upcoming = _files(tmp_path, PREVIOUS_2047, UPCOMING_2048)
    with pytest.raises(SchedulerError) as exc:
        load_league(
            previous,
            upcoming,
            {},
            season=2048,
            seed=SEED,
            rules_path=RULES,
            warn=_no_warning,
        )
    assert str(exc.value) == (
        f"{previous}: Team(s) not in {upcoming}: Baltimore. "
        f"List renamed teams under [renames.2048] in {RULES}."
    )


@pytest.mark.parametrize(
    ("renames", "reason"),
    [
        ({"Nowhere": "Los Angeles"}, "Nowhere: Not a team in {previous}."),
        ({"Baltimore": "Nowhere"}, "Baltimore: Not a team in {upcoming}."),
        (
            {"Baltimore": "Denver"},
            "Baltimore: Another team in {previous} is named Denver.",
        ),
    ],
)
def test_rename_naming_an_unknown_or_taken_team(
    tmp_path: Path, renames: dict[str, str], reason: str
) -> None:
    previous, upcoming = _files(tmp_path, PREVIOUS_2047, UPCOMING_2048)
    with pytest.raises(ConfigFileError) as exc:
        load_league(
            previous,
            upcoming,
            renames,
            season=2048,
            seed=SEED,
            rules_path=RULES,
            warn=_no_warning,
        )
    assert str(exc.value) == f"{RULES}: [renames.2048] " + reason.format(
        previous=previous, upcoming=upcoming
    )


def test_a_name_passed_along_a_chain_of_renames_is_accepted(tmp_path: Path) -> None:
    # Denver becomes Los Angeles and Baltimore takes the name Denver: the
    # 2047 Baltimore's standing (13-3, third overall) belongs to 2048's Denver.
    renames = {"Baltimore": "Denver", "Denver": "Los Angeles"}
    league = _load(tmp_path, PREVIOUS_2047, UPCOMING_2048, renames, 2048)
    assert _overall(league)[2] == "Denver"
    assert _overall(league)[4] == "Los Angeles"
    swap = {"Los Angeles": "Denver", "Denver": "Los Angeles"}
    assert _overall(league) == [swap.get(n, n) for n in REAL_2048_OVERALL]
    assert _finish(league) == {
        k: [swap.get(n, n) for n in v] for k, v in REAL_2048_FINISH.items()
    }


# --- built files -----------------------------------------------------------------

PREVIOUS = Path("previous") / "x.lge"
UPCOMING = Path("upcoming") / "x.lge"
NO_GAMES = Record(0, 0, 0, 0, 0)


def _team(name: str, record: Record = NO_GAMES) -> Team:
    return Team(name=name, nickname="", record=record, roster=build_empty_roster())


def _conference(name: str, *divisions: tuple[str, Sequence[Team]]) -> Conference:
    # Standings in file order: the loader ranks from the games itself.
    return Conference(
        name=name,
        divisions=[
            Division(name=division, teams=list(teams), standings=list(teams))
            for division, teams in divisions
        ],
        standings=[team for _, teams in divisions for team in teams],
    )


def _lge(
    *conferences: Conference,
    weeks: Sequence[Sequence[Game]] = (),
    playoffs: Sequence[Sequence[Game]] = (),
    unplayed: int = 0,
) -> LgeFile:
    return LgeFile(
        conferences=list(conferences),
        weeks=[list(week) for week in weeks],
        playoffs=[list(round_) for round_ in playoffs],
        unplayed_games=unplayed,
    )


def _nine(prefix: str, records: dict[str, Record] | None = None) -> list[Team]:
    """Teams `<prefix>1` to `<prefix>9`, with the given records (else none)."""
    records = records or {}
    return [
        _team(f"{prefix}{i}", records.get(f"{prefix}{i}", NO_GAMES))
        for i in range(1, 10)
    ]


def _two_conferences(
    records: dict[str, Record] | None = None,
    weeks: Sequence[Sequence[Game]] = (),
    playoffs: Sequence[Sequence[Game]] = (),
) -> LgeFile:
    """Two conferences of one nine-team division each: a league without
    divisions in the scheduler's terms."""
    return _lge(
        _conference("A", ("Only", _nine("A", records))),
        _conference("B", ("Only", _nine("B", records))),
        weeks=weeks,
        playoffs=playoffs,
    )


def _build(
    previous: LgeFile, upcoming: LgeFile | None = None, *, seed: int = SEED
) -> League:
    return league_from_files(
        previous,
        upcoming or _two_conferences(),
        {},
        season=2048,
        seed=seed,
        previous_path=PREVIOUS,
        upcoming_path=UPCOMING,
        rules_path=RULES,
        warn=_no_warning,
    )


# Every team of `_two_conferences`, in previous-file order, and its two
# one-division conferences.
EIGHTEEN = [f"A{i}" for i in range(1, 10)] + [f"B{i}" for i in range(1, 10)]
ONLY_DIVISIONS = (EIGHTEEN[:9], EIGHTEEN[9:])


def _no_game_order(names: Iterable[str]) -> list[str]:
    """`names` of `_two_conferences` as the overall order puts them when no
    game decides: previous-season division finish, which the coin toss sets,
    then the coin toss."""
    tossed = _coin_toss(EIGHTEEN)
    place = {
        name: index
        for members in ONLY_DIVISIONS
        for index, name in enumerate((n for n in tossed if n in members), 1)
    }
    wanted = set(names)
    return sorted((name for name in tossed if name in wanted), key=place.__getitem__)


def _by_name(lge: LgeFile) -> dict[str, Team]:
    return {
        team.name: team
        for conference in lge.conferences
        for division in conference.divisions
        for team in division.teams
    }


def _game(home: Team, away: Team, home_score: int = 20, away_score: int = 10) -> Game:
    return Game(home=home, home_score=home_score, away=away, away_score=away_score)


def test_one_division_per_conference_is_a_league_without_divisions() -> None:
    league = _build(_two_conferences())
    assert not league.has_divisions
    assert league.division_standings == {}
    assert [c.name for c in league.conferences] == ["A", "B"]
    # No game played: the coin toss orders each conference's one division,
    # and the overall order goes by that finish, then the coin toss.
    assert _overall(league) == _no_game_order(EIGHTEEN)


def test_three_conferences_rejected() -> None:
    upcoming = _lge(
        _conference("A", ("Only", _nine("A"))),
        _conference("B", ("Only", _nine("B")[:5])),
        _conference("C", ("Only", _nine("B")[5:])),
    )
    with pytest.raises(SchedulerError) as exc:
        _build(_two_conferences(), upcoming)
    assert str(exc.value) == f"{UPCOMING}: Expected exactly 2 conferences, got 3."


def test_conference_of_eight_rejected() -> None:
    previous = _lge(
        _conference("A", ("Only", _nine("A"))),
        _conference("B", ("Only", _nine("B")[:8])),
    )
    upcoming = _lge(
        _conference("A", ("Only", _nine("A"))),
        _conference("B", ("Only", _nine("B")[:8])),
    )
    with pytest.raises(SchedulerError) as exc:
        _build(previous, upcoming)
    assert str(exc.value) == f"{UPCOMING}: B must have exactly 9 teams; got 8."


def test_team_name_repeated_in_a_file_rejected() -> None:
    twice = _nine("A")
    twice[8] = _team("A1")
    upcoming = _lge(
        _conference("A", ("Only", twice)), _conference("B", ("Only", _nine("B")))
    )
    with pytest.raises(SchedulerError) as exc:
        _build(_two_conferences(), upcoming)
    assert str(exc.value) == f"{UPCOMING}: Team name repeats: A1."


def test_team_only_in_the_upcoming_file_is_reported() -> None:
    previous = _lge(
        _conference("A", ("Only", _nine("A"))),
        _conference("B", ("Only", _nine("B")[:8])),
    )
    with pytest.raises(SchedulerError) as exc:
        _build(previous, _two_conferences())
    assert str(exc.value) == f"{UPCOMING}: Team(s) not in {PREVIOUS}: B9."


def test_playoff_finish_outranks_record() -> None:
    # B9 has the worst record but won the title over A1, the best.
    records = {"A1": Record(10, 0, 0, 0, 0), "B9": Record(0, 10, 0, 0, 0)}
    previous = _two_conferences(records)
    teams = _by_name(previous)
    previous = _two_conferences(records, playoffs=[[_game(teams["B9"], teams["A1"])]])
    # Third: the first of the level rest, by the coin toss's division finish.
    third = _no_game_order(set(EIGHTEEN) - {"B9", "A1"})[0]
    assert _overall(_build(previous))[:3] == ["B9", "A1", third]


def test_champion_then_runner_up_then_losers_by_round_and_record() -> None:
    records = {
        "A1": Record(8, 2, 0, 0, 0),
        "A2": Record(9, 1, 0, 0, 0),
        "B1": Record(7, 3, 0, 0, 0),
        "B2": Record(6, 4, 0, 0, 0),
    }
    teams = _by_name(_two_conferences(records))
    playoffs = [
        [_game(teams["A1"], teams["A2"]), _game(teams["B1"], teams["B2"])],
        [_game(teams["A1"], teams["B1"])],
    ]
    previous = _two_conferences(records, playoffs=playoffs)
    assert _overall(_build(previous))[:4] == ["A1", "B1", "A2", "B2"]


def test_bye_team_ranks_by_the_round_it_went_out() -> None:
    # B1 sits out round 1, then beats A1 in round 2: champion.
    teams = _by_name(_two_conferences())
    playoffs = [
        [_game(teams["A1"], teams["A2"])],
        [_game(teams["B1"], teams["A1"])],
    ]
    assert _overall(_build(_two_conferences(playoffs=playoffs)))[:3] == [
        "B1",
        "A1",
        "A2",
    ]


def test_same_record_and_finish_ranked_by_strength_of_schedule() -> None:
    # A1 and A2 are both 1-1. A1 played two unbeaten teams, A2 two winless.
    records = {
        "A1": Record(1, 1, 0, 0, 0),
        "A2": Record(1, 1, 0, 0, 0),
        "A3": Record(2, 0, 0, 0, 0),
        "A4": Record(2, 0, 0, 0, 0),
        "A5": Record(0, 2, 0, 0, 0),
        "A6": Record(0, 2, 0, 0, 0),
    }
    # The games name the file's own teams, as a real file's do.
    base = _two_conferences(records)
    teams = _by_name(base)
    weeks = [
        [_game(teams["A1"], teams["A3"]), _game(teams["A2"], teams["A5"])],
        [_game(teams["A4"], teams["A1"]), _game(teams["A6"], teams["A2"])],
    ]
    overall = _overall(_build(_lge(*base.conferences, weeks=weeks)))
    assert overall.index("A1") < overall.index("A2")
    # Not the coin toss deciding: swap the roles.
    weeks = [
        [_game(teams["A2"], teams["A3"]), _game(teams["A1"], teams["A5"])],
        [_game(teams["A4"], teams["A2"]), _game(teams["A6"], teams["A1"])],
    ]
    overall = _overall(_build(_lge(*base.conferences, weeks=weeks)))
    assert overall.index("A2") < overall.index("A1")


def test_same_strength_ranked_by_point_differential() -> None:
    # A1 and B1 each won their division's one game against a team that went
    # 0-1: level on record, strength of schedule and division finish (first),
    # so point differential puts A1 ahead, where the coin toss would not.
    records = {
        "A1": Record(1, 0, 0, 30, 10),
        "A2": Record(0, 1, 0, 10, 30),
        "B1": Record(1, 0, 0, 20, 10),
        "B2": Record(0, 1, 0, 10, 20),
    }
    base = _two_conferences(records)
    teams = _by_name(base)
    weeks = [[_game(teams["A1"], teams["A2"]), _game(teams["B1"], teams["B2"])]]
    tossed = _coin_toss(EIGHTEEN)
    assert tossed.index("B1") < tossed.index("A1")
    overall = _overall(_build(_lge(*base.conferences, weeks=weeks)))
    assert overall[:2] == ["A1", "B1"]


def test_level_teams_go_by_the_coin_toss() -> None:
    # Level up to division finish, which the coin toss sets with no game played.
    level = {"A1", "A2", "B1"}
    records = {name: Record(1, 1, 0, 20, 20) for name in level}
    overall = _overall(_build(_two_conferences(records)))
    assert overall[:3] == _no_game_order(level)


def _two_divisions(records: dict[str, Record] | None = None) -> LgeFile:
    """Two conferences of an East (4 teams) and a West (5): a league with
    divisions."""
    a, b = _nine("A", records), _nine("B", records)
    return _lge(
        _conference("A", ("East", a[:4]), ("West", a[4:])),
        _conference("B", ("East", b[:4]), ("West", b[4:])),
    )


DIVISION_MEMBERS = {
    "East1": EIGHTEEN[:4],
    "West1": EIGHTEEN[4:9],
    "East2": EIGHTEEN[9:13],
    "West2": EIGHTEEN[13:],
}


def test_coin_toss_orders_a_season_with_no_game_played() -> None:
    # Every team is level on every step of the standings, so the shuffle drawn
    # from the seed orders each division's finish, and the overall order goes
    # by division finish (the same divisions both seasons), then the shuffle.
    previous = upcoming = _two_divisions()
    league = _build(previous, upcoming)
    tossed = _coin_toss(EIGHTEEN)
    finish = _finish(league)
    assert finish == {
        key: [name for name in tossed if name in members]
        for key, members in DIVISION_MEMBERS.items()
    }
    place = {
        name: index for order in finish.values() for index, name in enumerate(order)
    }
    assert _overall(league) == sorted(tossed, key=lambda name: place[name])
    # The same seed gives the same order.
    assert _overall(_build(previous, upcoming)) == _overall(league)
    assert _finish(_build(previous, upcoming)) == finish


def test_division_finish_ranks_ahead_of_point_differential() -> None:
    # A1 (first in the previous season's East) and A5 (second in its West,
    # behind A7) are both 1-1 against opponents with the same combined record,
    # and A5 has the better point differential; division finish decides first.
    records = {
        "A1": Record(1, 1, 0, 30, 40),
        "A5": Record(1, 1, 0, 40, 30),
        "A6": Record(0, 1, 0, 10, 20),
        "A7": Record(2, 0, 0, 40, 20),
        "A8": Record(0, 1, 0, 10, 20),
    }
    base = _two_divisions(records)
    teams = _by_name(base)
    weeks = [
        [_game(teams["A1"], teams["A6"]), _game(teams["A5"], teams["A8"])],
        [_game(teams["A7"], teams["A1"])],
        [_game(teams["A7"], teams["A5"])],
    ]
    league = _build(_lge(*base.conferences, weeks=weeks), _two_divisions())
    assert _finish(league)["East1"][0] == "A1"
    assert _finish(league)["West1"][:2] == ["A7", "A5"]
    assert _overall(league)[:3] == ["A7", "A1", "A5"]


def _record(wins: int, losses: int) -> Record:
    return Record(wins, losses, 0, 20 * wins + 10 * losses, 10 * wins + 20 * losses)


def test_a_team_that_moved_ranks_by_its_previous_division() -> None:
    # A5 and A6 are both 1-1 against opponents with the same combined record
    # (A5: A6 and A1; A6: A5 and A7), and A6 has the better point
    # differential. In the previous West A5 finished second (it beat A6) and
    # A6 third, behind A7. A5 then moves to the East, behind A3 and A1 there,
    # and A6 is second in the new West: the previous divisions decide.
    records = {
        "A1": _record(2, 1),
        "A2": _record(0, 1),
        "A3": _record(1, 0),
        "A5": Record(1, 1, 0, 30, 40),
        "A6": Record(1, 1, 0, 40, 30),
        "A7": _record(2, 1),
        "A8": _record(0, 1),
        "A9": _record(0, 1),
    }
    base = _two_divisions(records)
    teams = _by_name(base)
    weeks = [
        [
            _game(teams["A5"], teams["A6"]),
            _game(teams["A3"], teams["A1"]),
            _game(teams["A7"], teams["A8"]),
        ],
        [_game(teams["A1"], teams["A5"]), _game(teams["A6"], teams["A7"])],
        [_game(teams["A1"], teams["A2"]), _game(teams["A7"], teams["A9"])],
    ]
    a_new, b_new = _nine("A"), _nine("B")
    upcoming = _lge(
        _conference(
            "A", ("East", [*a_new[:3], a_new[4]]), ("West", [a_new[3], *a_new[5:]])
        ),
        _conference("B", ("East", b_new[:4]), ("West", b_new[4:])),
    )
    league = _build(_lge(*base.conferences, weeks=weeks), upcoming)
    assert _finish(league)["East1"][:3] == ["A3", "A1", "A5"]
    assert _finish(league)["West1"][:2] == ["A7", "A6"]
    assert _overall(league)[:5] == ["A3", "A1", "A7", "A5", "A6"]
    # A4 and the B teams played no game: A4 beats 0-1 A8 and A9 on division
    # net points; the B divisions go by the coin toss.
    assert _finish(league) == {
        "East1": ["A3", "A1", "A5", "A2"],
        "West1": ["A7", "A6", "A4", "A8", "A9"],
        "East2": ["B3", "B1", "B2", "B4"],
        "West2": ["B8", "B7", "B9", "B6", "B5"],
    }
    # The winless go by strength of schedule (A8, A2 and A9 played 2-1 teams),
    # then previous division finish, then the coin toss.
    assert _overall(league) == [
        "A3",
        "A1",
        "A7",
        "A5",
        "A6",
        "A8",
        "A2",
        "A9",
        "B3",
        "B8",
        "B1",
        "B7",
        "B2",
        "A4",
        "B9",
        "B6",
        "B4",
        "B5",
    ]


def test_tied_playoff_game_rejected() -> None:
    teams = _by_name(_two_conferences())
    playoffs = [[_game(teams["A1"], teams["A2"], 10, 10)]]
    with pytest.raises(SchedulerError) as exc:
        _build(_two_conferences(playoffs=playoffs))
    assert str(exc.value) == f"{PREVIOUS}: Playoff round 1: Tied game, A1 10, A2 10."


def _round_robin(order: Sequence[Team]) -> list[Game]:
    """Every pair meets once; the team earlier in `order` wins 20-10."""
    return [
        _game(winner, loser)
        for i, winner in enumerate(order)
        for loser in order[i + 1 :]
    ]


def test_division_finish_ranks_the_upcoming_members_by_previous_season() -> None:
    # Two divisions per conference; the upcoming file swaps A4 and A5 between
    # the A divisions, and each finish ranks its new members on the previous
    # season's games. Strength order: A5, A9, then A1 to A8 in file order.
    strength = ["A5", "A9", "A1", "A2", "A3", "A4", "A6", "A7", "A8"]
    records = {
        name: Record(8 - i, i, 0, 20 * (8 - i) + 10 * i, 10 * (8 - i) + 20 * i)
        for i, name in enumerate(strength)
    }
    records |= {f"B{i}": Record(0, 0, 0, 0, 0) for i in range(1, 10)}
    a, b = _nine("A", records), _nine("B", records)
    by_name = {team.name: team for team in a}
    previous = _lge(
        _conference("A", ("East", a[:4]), ("West", a[4:])),
        _conference("B", ("East", b[:4]), ("West", b[4:])),
        weeks=[_round_robin([by_name[name] for name in strength])],
    )
    a_new, b_new = _nine("A"), _nine("B")
    upcoming = _lge(
        _conference(
            "A", ("East", [*a_new[:3], a_new[4]]), ("West", [a_new[3], *a_new[5:]])
        ),
        _conference("B", ("East", b_new[:4]), ("West", b_new[4:])),
    )
    league = _build(previous, upcoming)
    assert league.has_divisions
    assert _finish(league)["East1"] == ["A5", "A1", "A2", "A3"]
    assert _finish(league)["West1"] == ["A9", "A4", "A6", "A7", "A8"]
    # The B teams played no game: the coin toss orders their divisions, and
    # they follow the A teams overall by that finish, then the coin toss.
    assert _finish(league) == {
        "East1": ["A5", "A1", "A2", "A3"],
        "West1": ["A9", "A4", "A6", "A7", "A8"],
        "East2": ["B3", "B1", "B2", "B4"],
        "West2": ["B8", "B7", "B9", "B6", "B5"],
    }
    assert _overall(league) == [
        *strength,
        "B3",
        "B8",
        "B1",
        "B7",
        "B2",
        "B9",
        "B6",
        "B4",
        "B5",
    ]


def test_level_division_members_go_by_the_coin_toss() -> None:
    # No game played, so every team is level; the upcoming file lists each
    # division's members in reverse, and the finish follows the coin toss,
    # neither file's order.
    a, b = _nine("A"), _nine("B")
    previous = _lge(
        _conference("A", ("East", a[:4]), ("West", a[4:])),
        _conference("B", ("East", b[:4]), ("West", b[4:])),
    )
    a_new, b_new = _nine("A"), _nine("B")
    upcoming = _lge(
        _conference("A", ("East", a_new[3::-1]), ("West", a_new[:3:-1])),
        _conference("B", ("East", b_new[3::-1]), ("West", b_new[:3:-1])),
    )
    finish = _finish(_build(previous, upcoming))
    tossed = _coin_toss(EIGHTEEN)
    assert finish["East1"] == [
        name for name in tossed if name in ("A1", "A2", "A3", "A4")
    ]
    assert finish["West1"] == [
        name for name in tossed if name in ("A5", "A6", "A7", "A8", "A9")
    ]


def test_moved_teams_tie_broken_by_the_previous_seasons_divisions() -> None:
    # A1 (East) and A5 (West) are both 1-1 and never met, so division record
    # decides: A5 went 1-0 in the West (beat A6) and A1 0-1 in the East (lost
    # to A2), so A5 finishes ahead of A1 despite A1's earlier place in the coin
    # toss. A5 then moves to the East, where its loss to A2 would make it 0-1,
    # level with A1 on every step and behind it on the coin toss, if the
    # upcoming divisions counted; they do not.
    records = {
        "A1": Record(1, 1, 0, 30, 30),
        "A2": Record(2, 0, 0, 40, 20),
        "A5": Record(1, 1, 0, 30, 30),
        "A6": Record(0, 2, 0, 20, 40),
    }
    a, b = _nine("A", records), _nine("B")
    by_name = {team.name: team for team in a}
    previous = _lge(
        _conference("A", ("East", a[:4]), ("West", a[4:])),
        _conference("B", ("East", b[:4]), ("West", b[4:])),
        weeks=[
            [_game(by_name["A2"], by_name["A1"]), _game(by_name["A5"], by_name["A6"])],
            [_game(by_name["A1"], by_name["A6"]), _game(by_name["A2"], by_name["A5"])],
        ],
    )
    a_new, b_new = _nine("A"), _nine("B")
    upcoming = _lge(
        _conference(
            "A", ("East", [*a_new[:3], a_new[4]]), ("West", [a_new[3], *a_new[5:]])
        ),
        _conference("B", ("East", b_new[:4]), ("West", b_new[4:])),
    )
    assert _finish(_build(previous, upcoming))["East1"] == ["A2", "A5", "A1", "A3"]
    league = _build(previous, upcoming)
    # A6 (0-2) falls behind the teams with no game on division net points;
    # those, and the B divisions, go by the coin toss.
    assert _finish(league) == {
        "East1": ["A2", "A5", "A1", "A3"],
        "West1": ["A4", "A7", "A8", "A9", "A6"],
        "East2": ["B3", "B1", "B2", "B4"],
        "West2": ["B8", "B7", "B9", "B6", "B5"],
    }
    # A5 is ahead of A1 on previous division finish, A6 ahead of the teams
    # with no game on strength of schedule; the rest go by previous division
    # finish, then the coin toss.
    assert _overall(league) == [
        "A2",
        "A5",
        "A1",
        "A6",
        "B3",
        "B8",
        "B1",
        "B7",
        "A7",
        "A3",
        "B2",
        "B9",
        "A8",
        "A4",
        "B6",
        "A9",
        "B4",
        "B5",
    ]
