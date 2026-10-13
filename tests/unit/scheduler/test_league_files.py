"""The scheduler's League from two league files: conferences, divisions and
names from the upcoming season's `.lge`, standings from the previous season's,
teams matched by name with the season's renames.

Real PNFL files (2046 to 2048) cover the standings rules against the league's
own published order; built `LgeFile` objects cover the shapes and errors no
real file holds.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

import pytest

from athc.errors import ConfigFileError
from athc.fbpro98_lge import Conference, Division, Game, LgeFile, Record, Team
from athc.scheduler.domain.league import League
from athc.scheduler.league_files import league_from_files, load_league
from athc.scheduler.schedulers.errors import SchedulerError

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


def _folders(tmp_path: Path, previous: str, upcoming: str) -> tuple[Path, Path]:
    """Two folders, each holding a fixture copied to `<LEAGUE>.lge`."""
    folders: list[Path] = []
    for kind, fixture in (("previous", previous), ("upcoming", upcoming)):
        folder = tmp_path / kind
        folder.mkdir()
        shutil.copy(DATA / f"{fixture}.lge", folder / f"{LEAGUE}.lge")
        folders.append(folder)
    return folders[0], folders[1]


def _load(
    tmp_path: Path, previous: str, upcoming: str, renames: dict[str, str], season: int
) -> League:
    previous_dir, upcoming_dir = _folders(tmp_path, previous, upcoming)
    return load_league(
        LEAGUE, previous_dir, upcoming_dir, renames, season=season, rules_path=RULES
    )


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
    assert _overall(league)[:9] == [
        "Pittsburgh",
        "Washington",
        "Minnesota",
        "Cincinnati",
        "Miami",
        "Buffalo",
        "Seattle",
        "San Francisco",
        "Baltimore",
    ]


def test_previous_season_must_be_finished(tmp_path: Path) -> None:
    previous_dir, upcoming_dir = _folders(tmp_path, UPCOMING_2048, UPCOMING_2048)
    with pytest.raises(SchedulerError) as exc:
        load_league(
            LEAGUE, previous_dir, upcoming_dir, {}, season=2048, rules_path=RULES
        )
    assert str(exc.value) == (
        f"{previous_dir / f'{LEAGUE}.lge'}: Season not finished: "
        "142 game(s) not played."
    )


def test_unmatched_previous_team_names_the_renames_table(tmp_path: Path) -> None:
    previous_dir, upcoming_dir = _folders(tmp_path, PREVIOUS_2047, UPCOMING_2048)
    with pytest.raises(SchedulerError) as exc:
        load_league(
            LEAGUE, previous_dir, upcoming_dir, {}, season=2048, rules_path=RULES
        )
    previous, upcoming = previous_dir / f"{LEAGUE}.lge", upcoming_dir / f"{LEAGUE}.lge"
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
    previous_dir, upcoming_dir = _folders(tmp_path, PREVIOUS_2047, UPCOMING_2048)
    with pytest.raises(ConfigFileError) as exc:
        load_league(
            LEAGUE, previous_dir, upcoming_dir, renames, season=2048, rules_path=RULES
        )
    previous, upcoming = previous_dir / f"{LEAGUE}.lge", upcoming_dir / f"{LEAGUE}.lge"
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


# --- built files -----------------------------------------------------------------

PREVIOUS = Path("previous") / "x.lge"
UPCOMING = Path("upcoming") / "x.lge"
NO_GAMES = Record(0, 0, 0, 0, 0)


def _team(name: str, record: Record = NO_GAMES) -> Team:
    return Team(name=name, nickname="", record=record)


def _conference(name: str, *divisions: tuple[str, Sequence[Team]]) -> Conference:
    # Standings in file order: the loader ranks from the games itself.
    return Conference(
        name=name,
        divisions=tuple(
            Division(name=division, teams=tuple(teams), standings=tuple(teams))
            for division, teams in divisions
        ),
        standings=tuple(team for _, teams in divisions for team in teams),
    )


def _lge(
    *conferences: Conference,
    weeks: Sequence[Sequence[Game]] = (),
    playoffs: Sequence[Sequence[Game]] = (),
    unplayed: int = 0,
) -> LgeFile:
    return LgeFile(
        conferences=conferences,
        weeks=tuple(tuple(week) for week in weeks),
        playoffs=tuple(tuple(round_) for round_ in playoffs),
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


def _build(previous: LgeFile, upcoming: LgeFile | None = None) -> League:
    return league_from_files(
        previous,
        upcoming or _two_conferences(),
        {},
        season=2048,
        previous_path=PREVIOUS,
        upcoming_path=UPCOMING,
        rules_path=RULES,
    )


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
    # No game played: the previous file's order stands.
    assert _overall(league) == [f"A{i}" for i in range(1, 10)] + [
        f"B{i}" for i in range(1, 10)
    ]


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
    assert _overall(_build(previous))[:3] == ["B9", "A1", "A2"]


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
    teams = _by_name(_two_conferences(records))
    weeks = [
        [_game(teams["A1"], teams["A3"]), _game(teams["A2"], teams["A5"])],
        [_game(teams["A4"], teams["A1"]), _game(teams["A6"], teams["A2"])],
    ]
    overall = _overall(_build(_two_conferences(records, weeks=weeks)))
    assert overall.index("A1") < overall.index("A2")
    # The ordering is in the previous file's order otherwise: swap the roles.
    weeks = [
        [_game(teams["A2"], teams["A3"]), _game(teams["A1"], teams["A5"])],
        [_game(teams["A4"], teams["A2"]), _game(teams["A6"], teams["A1"])],
    ]
    overall = _overall(_build(_two_conferences(records, weeks=weeks)))
    assert overall.index("A2") < overall.index("A1")


def test_same_strength_ranked_by_point_differential() -> None:
    records = {
        "A1": Record(1, 1, 0, 20, 30),
        "A2": Record(1, 1, 0, 30, 20),
    }
    overall = _overall(_build(_two_conferences(records)))
    assert overall[:2] == ["A2", "A1"]


def test_level_teams_keep_the_previous_file_order() -> None:
    records = {name: Record(1, 1, 0, 20, 20) for name in ("A1", "A2", "B1")}
    overall = _overall(_build(_two_conferences(records)))
    assert overall[:3] == ["A1", "A2", "B1"]


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


def test_level_division_members_keep_the_previous_file_order() -> None:
    # No game played, so every team is level; the upcoming file lists each
    # division's members in reverse, and the finish follows the previous file.
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
    assert finish["East1"] == ["A1", "A2", "A3", "A4"]
    assert finish["West1"] == ["A5", "A6", "A7", "A8", "A9"]


def test_moved_teams_tie_broken_by_the_previous_seasons_divisions() -> None:
    # A1 (East) and A5 (West) are both 1-1 and never met, so division record
    # decides: A5 went 1-0 in the West (beat A6) and A1 0-1 in the East (lost
    # to A2), so A5 finishes ahead of A1 despite A1's earlier file position.
    # A5 then moves to the East, where its loss to A2 would make it 0-1, level
    # with A1 on every step and behind it on file order, if the upcoming
    # divisions counted; they do not.
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
