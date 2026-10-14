# fbpro98_standings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new library, `src/athc/fbpro98_standings/`, that ranks a league's teams from its `.lge` files (division, conference and league standings) by the game's, the scheduler's or the NFL's tie-breakers.

**Architecture:** `season.py` turns one `LgeFile` into numbered teams with their games and playoff round; `steps.py` holds one function per tie-break step; `methods.py` lists each method's steps as data; `moves.py` matches the previous season's teams to the current season's; `standings.py` holds `Standings` (the public class) and `_Ranker` (the one ranking engine every method uses).

**Tech Stack:** Python 3.13, dataclasses, `fractions.Fraction`, `random.Random`, pytest, ruff, pyright.

**Spec:** `docs/superpowers/specs/2026-10-13-fbpro98-standings-design.md`

## Global Constraints

- Work only in `src/athc/fbpro98_standings/`, `tests/unit/fbpro98_standings/`, `docs/fbpro98_standings/` and the doc/meta files Task 8 names. Never change `fbpro98_lge`, the scheduler or generate-schedule.
- The library takes `LgeFile` objects; it never reads files.
- `method` is required: `Literal["game", "scheduler", "nfl"]`, no default. The argument for renamed teams is `team_moves` (previous name -> current name), never "renames".
- Coin toss: the library's own `random.Random`, seeded per toss from the seed and the level teams; no seed = a fresh toss.
- Python 3.13, full type hints, dataclasses, f-strings, pathlib. Ruff at 88 columns, double quotes; `ruff check`, `ruff format` and `pyright` (standard) must pass; `pytest` measures coverage and fails below 92%.
- Every text file is UTF-8, CRLF line endings, final newline, no BOM. After writing or editing any file, run the CRLF fix on it (one command, files as arguments):
  `uv run python -c "import pathlib, sys; [pathlib.Path(p).write_bytes(pathlib.Path(p).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')) for p in sys.argv[1:]]" <files>`
- One Bash command per call, never chained. Commands: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`. Do not run them as a baseline before changing anything.
- If `ruff check` reports only import order (I001), run `uv run ruff check . --fix` and re-run the CRLF fix on the touched files.
- Never change an expected test value to make a test pass. A failing expectation means the code is wrong: investigate, and if the cause is not in this plan's code, stop and report.
- Commit messages: one line, prefixed `fbpro98_standings:`. Never mention Claude, Anthropic or any AI tool; no Co-Authored-By lines.
- Do not merge. Report back and stop.

## Review Focus

- A season in progress (before week 1, or before the playoffs): teams with no games rank by coin toss without dividing by zero; pinned in Task 6, Step 1.
- A league without divisions (one division per conference): conference standings still put the (only) division winner first; pinned in Task 4, Step 1 (`test_game_conference_without_divisions`).
- A division with no teams (stock leagues have them): `division()` answers `()` and conference standings still work; pinned in Task 4, Step 1 (`test_an_empty_division_has_no_standings`).
- Two teams equal in every field: told apart by position, never by value; pinned in Task 4, Step 1 (`test_teams_that_look_alike_stay_apart`).
- Playoffs partly played: no champion until the last round is played; pinned in Task 1, Step 1 (`test_no_champion_before_the_final_is_played`).

---

### Task 1: Package, errors, and the season as numbers

**Files:**
- Create: `src/athc/fbpro98_standings/__init__.py`
- Create: `src/athc/fbpro98_standings/py.typed` (empty)
- Create: `src/athc/fbpro98_standings/errors.py`
- Create: `src/athc/fbpro98_standings/season.py`
- Create: `tests/unit/fbpro98_standings/leagues.py`
- Test: `tests/unit/fbpro98_standings/test_season.py`

**Interfaces:**
- Produces: `StandingsError(ValueError)`; `Result(opponent: int, scored: int, allowed: int, division: bool, conference: bool)` with properties `won`, `lost`; `Season(teams, division_of, conference_of, results, playoff_round, champion, runner_up)` with `division_members(division: int) -> tuple[int, ...]`; `season_of(lge: LgeFile) -> Season`.
- Test helpers (`tests/unit/fbpro98_standings/leagues.py`): `Shape`, `Played`, `NO_GAMES`, `win(winner, loser, by=10) -> Played`, `build_league(shape, games=(), playoffs=()) -> LgeFile`, `real_lge(filename) -> LgeFile`, `names(teams) -> tuple[str, ...]`.

- [x] **Step 1: Write the test helpers and the failing tests**

`tests/unit/fbpro98_standings/leagues.py`:

```python
"""Leagues for the fbpro98_standings tests.

`build_league` makes an `LgeFile` in code from a shape of team names and the
games by name; `win` writes one game. `real_lge` reads a real `.lge` from the
fbpro98_lge or integration test data. Records stay at zero: the library works
from the games, never from `Team.record`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from athc.fbpro98_lge import (
    Conference,
    Division,
    Game,
    LgeFile,
    Record,
    Team,
    parse_lge,
)

TESTS = Path(__file__).resolve().parents[2]
DATA_DIRS = (TESTS / "unit" / "fbpro98_lge" / "data", TESTS / "integration" / "data")
NO_GAMES = Record(0, 0, 0, 0, 0)

# Conferences, each a list of divisions, each a list of team names.
Shape = Sequence[Sequence[Sequence[str]]]
# Home team, home score, away team, away score.
Played = tuple[str, int, str, int]


def win(winner: str, loser: str, by: int = 10) -> Played:
    """A game the first team won by `by` points, at home."""
    return (winner, 10 + by, loser, 10)


def build_league(
    shape: Shape,
    games: Sequence[Played] = (),
    playoffs: Sequence[Sequence[Played]] = (),
) -> LgeFile:
    """Conferences `C1`.. and divisions `D1`.. in file order; one
    regular-season week per game; one playoff round per inner list."""
    teams = {
        name: Team(name=name, nickname="", record=NO_GAMES)
        for conference in shape
        for division in conference
        for name in division
    }
    conferences: list[Conference] = []
    count = 0
    for conference_number, conference in enumerate(shape, 1):
        divisions: list[Division] = []
        for division_names in conference:
            count += 1
            members = tuple(teams[name] for name in division_names)
            divisions.append(
                Division(name=f"D{count}", teams=members, standings=members)
            )
        members = tuple(team for division in divisions for team in division.teams)
        conferences.append(
            Conference(
                name=f"C{conference_number}",
                divisions=tuple(divisions),
                standings=members,
            )
        )

    def game(played: Played) -> Game:
        home, home_score, away, away_score = played
        return Game(teams[home], home_score, teams[away], away_score)

    return LgeFile(
        conferences=tuple(conferences),
        weeks=tuple((game(played),) for played in games),
        playoffs=tuple(
            tuple(game(played) for played in games_in_round)
            for games_in_round in playoffs
        ),
    )


def real_lge(filename: str) -> LgeFile:
    """A real `.lge` from the test data folders."""
    for folder in DATA_DIRS:
        path = folder / filename
        if path.exists():
            return parse_lge(path.read_bytes(), path)
    raise FileNotFoundError(filename)


def names(teams: Sequence[Team]) -> tuple[str, ...]:
    return tuple(team.name for team in teams)
```

`tests/unit/fbpro98_standings/test_season.py`:

```python
"""Tests for athc.fbpro98_standings.season: a league file's season as
numbers."""

from __future__ import annotations

from athc.fbpro98_standings.season import Result, season_of
from tests.unit.fbpro98_standings.leagues import build_league, names, real_lge, win

# Conference 1: division 1 is A and B, division 2 is C; conference 2 is D.
SHAPE = [[["A", "B"], ["C"]], [["D"]]]


def test_teams_numbered_in_file_order_with_their_division_and_conference():
    season = season_of(build_league(SHAPE))
    assert names(season.teams) == ("A", "B", "C", "D")
    assert season.division_of == (0, 0, 1, 2)
    assert season.conference_of == (0, 0, 0, 1)
    assert season.division_members(0) == (0, 1)


def test_a_game_counts_for_both_teams():
    season = season_of(build_league(SHAPE, [("A", 20, "B", 10)]))
    assert season.results[0] == (
        Result(opponent=1, scored=20, allowed=10, division=True, conference=True),
    )
    assert season.results[1] == (
        Result(opponent=0, scored=10, allowed=20, division=True, conference=True),
    )


def test_games_marked_division_and_conference():
    season = season_of(build_league(SHAPE, [("A", 20, "C", 10), ("A", 20, "D", 10)]))
    against_c, against_d = season.results[0]
    assert (against_c.division, against_c.conference) == (False, True)
    assert (against_d.division, against_d.conference) == (False, False)


def test_won_and_lost():
    season = season_of(build_league(SHAPE, [("A", 20, "B", 10), ("A", 10, "C", 10)]))
    won, tied = season.results[0]
    assert (won.won, won.lost) == (True, False)
    assert (tied.won, tied.lost) == (False, False)
    assert season.results[1][0].lost


def test_playoff_round_reached_and_the_final():
    # Round 1: A over B, D over C; final: D over A.
    lge = build_league(
        SHAPE, playoffs=[[win("A", "B"), win("D", "C")], [win("D", "A")]]
    )
    season = season_of(lge)
    assert season.playoff_round == (2, 1, 1, 3)
    assert (season.champion, season.runner_up) == (3, 0)


def test_a_bye_counts_by_the_later_round():
    # B sat out round 1 and won the final.
    lge = build_league(SHAPE, playoffs=[[win("A", "C")], [win("B", "A")]])
    season = season_of(lge)
    assert season.playoff_round == (2, 3, 1, 0)
    assert (season.champion, season.runner_up) == (1, 0)


def test_no_champion_before_the_final_is_played():
    lge = build_league(SHAPE, playoffs=[[win("A", "B")], []])
    season = season_of(lge)
    assert season.playoff_round == (2, 1, 0, 0)
    assert (season.champion, season.runner_up) == (None, None)


def test_real_season():
    season = season_of(real_lge("PNFL-2047-after-super-bowl.lge"))
    assert len(season.teams) == 18
    assert all(len(games) == 16 for games in season.results)
    champion, runner_up = season.champion, season.runner_up
    assert champion is not None
    assert runner_up is not None
    assert (season.teams[champion].name, season.teams[runner_up].name) == (
        "Miami",
        "Minnesota",
    )
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_standings/test_season.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'athc.fbpro98_standings'`.

- [x] **Step 3: Write the package**

`src/athc/fbpro98_standings/__init__.py`:

```python
"""Rank a Front Page Sports Football Pro '98 league's teams from its `.lge`
files: division, conference and league standings."""

from athc.fbpro98_standings.errors import StandingsError

__all__ = ["StandingsError"]
```

`src/athc/fbpro98_standings/py.typed`: an empty file.

`src/athc/fbpro98_standings/errors.py`:

```python
"""Errors raised by fbpro98_standings."""


class StandingsError(ValueError):
    """The league files and the team moves do not fit together."""
```

`src/athc/fbpro98_standings/season.py`:

```python
"""One league file's season as numbers: each team's played regular-season
games and how far it went in the playoffs.

Teams are numbered 0..N-1 in file order (conference, division, team), the
order `LgeFile.teams` gives, and found by identity, so two teams that look
the same never mix.
"""

from __future__ import annotations

from dataclasses import dataclass

from athc.fbpro98_lge import Game, LgeFile, Team


@dataclass(frozen=True, slots=True)
class Result:
    """One played regular-season game, from one team's side."""

    opponent: int
    scored: int
    allowed: int
    division: bool
    """The opponent was in the team's division."""

    conference: bool
    """The opponent was in the team's conference."""

    @property
    def won(self) -> bool:
        return self.scored > self.allowed

    @property
    def lost(self) -> bool:
        return self.scored < self.allowed


@dataclass(frozen=True, slots=True)
class Season:
    """A season ready to rank."""

    teams: tuple[Team, ...]
    """The file's teams in file order: team N is at index N."""

    division_of: tuple[int, ...]
    """Each team's division, numbered from 0 in file order across
    conferences."""

    conference_of: tuple[int, ...]
    """Each team's conference, numbered from 0 in file order."""

    results: tuple[tuple[Result, ...], ...]
    """Each team's played regular-season games, in week order."""

    playoff_round: tuple[int, ...]
    """The playoff round each team went out in, counted from 1; one more than
    the last round for the champion; 0 with no playoff game."""

    champion: int | None
    """The last round's winner; None until that game is played."""

    runner_up: int | None
    """The last round's loser; None until that game is played."""

    def division_members(self, division: int) -> tuple[int, ...]:
        """The division's teams in file order."""
        return tuple(
            team for team, number in enumerate(self.division_of) if number == division
        )


def season_of(lge: LgeFile) -> Season:
    """The file's season: its regular-season games and playoff results."""
    teams = lge.teams
    number = {id(team): index for index, team in enumerate(teams)}
    division_of: list[int] = []
    conference_of: list[int] = []
    division_number = 0
    for conference_number, conference in enumerate(lge.conferences):
        for division in conference.divisions:
            division_of += [division_number] * len(division.teams)
            conference_of += [conference_number] * len(division.teams)
            division_number += 1
    results: list[list[Result]] = [[] for _ in teams]
    for week in lge.weeks:
        for game in week:
            home, away = number[id(game.home)], number[id(game.away)]
            for team, other, scored, allowed in (
                (home, away, game.home_score, game.away_score),
                (away, home, game.away_score, game.home_score),
            ):
                results[team].append(
                    Result(
                        opponent=other,
                        scored=scored,
                        allowed=allowed,
                        division=division_of[team] == division_of[other],
                        conference=conference_of[team] == conference_of[other],
                    )
                )
    playoff_round = [0] * len(teams)
    for round_number, games in enumerate(lge.playoffs, 1):
        for game in games:
            winner, loser = _winner_and_loser(game, number)
            playoff_round[loser] = round_number
            # A later round overwrites an earlier one, so a bye costs nothing.
            playoff_round[winner] = round_number + 1
    champion = runner_up = None
    if lge.playoffs and lge.playoffs[-1]:
        champion, runner_up = _winner_and_loser(lge.playoffs[-1][0], number)
    return Season(
        teams=teams,
        division_of=tuple(division_of),
        conference_of=tuple(conference_of),
        results=tuple(tuple(games) for games in results),
        playoff_round=tuple(playoff_round),
        champion=champion,
        runner_up=runner_up,
    )


def _winner_and_loser(game: Game, number: dict[int, int]) -> tuple[int, int]:
    # A playoff game cannot end tied: the game plays overtime until it does not.
    home, away = number[id(game.home)], number[id(game.away)]
    return (home, away) if game.home_score > game.away_score else (away, home)
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_standings/test_season.py -v --no-cov`
Expected: 8 passed.

- [x] **Step 5: Fix line endings, lint, type-check**

Run the CRLF fix on the six new files. Then `uv run ruff format .`, `uv run ruff check .`, `uv run pyright`. Expected: no errors.

- [x] **Step 6: Commit**

```bash
git add src/athc/fbpro98_standings tests/unit/fbpro98_standings
```

```bash
git commit -m "fbpro98_standings: package, errors and the season as numbers"
```

---

### Task 2: The tie-break steps

**Files:**
- Create: `src/athc/fbpro98_standings/steps.py`
- Test: `tests/unit/fbpro98_standings/test_steps.py`

**Interfaces:**
- Consumes: `Result`, `Season`, `season_of` (Task 1).
- Produces: `Value = Fraction | int`; `Values = Mapping[int, Value]`; `Context` (Protocol: attribute `season: Season`, method `division_order(division: int) -> tuple[int, ...]`); `Step = Callable[[Sequence[int], Context], Values | None]`; `percentage(results) -> Fraction`; steps `win_percentage`, `head_to_head`, `head_to_head_sweep`, `division_percentage`, `conference_percentage`, `common_net_points`, `strength_of_victory`, `net_points`, `division_net_points`, `conference_net_points`, `division_finish`, `playoff_round`, `champion_then_runner_up`; step factories `common_games(minimum: int) -> Step`, `strength_of_schedule(each_opponent_once: bool) -> Step`, `combined_ranking(scope: Literal["conference", "league"]) -> Step`. Every step returns a value per team, higher is better, or None when it does not apply.

- [x] **Step 1: Write the failing tests**

`tests/unit/fbpro98_standings/test_steps.py`:

```python
"""Tests for athc.fbpro98_standings.steps: each tie-break step on its own,
on small leagues built in code."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from athc.fbpro98_standings import steps
from athc.fbpro98_standings.season import Season, season_of
from tests.unit.fbpro98_standings.leagues import Played, Shape, build_league, win

# Conference 1: division 1 is A, B, C; division 2 is D, E. Conference 2: F.
SHAPE = [[["A", "B", "C"], ["D", "E"]], [["F"]]]
A, B, C, D, E, F = range(6)


@dataclass
class _Context:
    season: Season
    orders: dict[int, tuple[int, ...]] = field(default_factory=dict)

    def division_order(self, division: int) -> tuple[int, ...]:
        return self.orders[division]


def _context(
    *games: Played,
    shape: Shape = SHAPE,
    playoffs: list[list[Played]] | None = None,
) -> _Context:
    return _Context(season_of(build_league(shape, games, playoffs or [])))


def test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero():
    context = _context(win("A", "B"), ("A", 10, "D", 10))
    assert steps.percentage(context.season.results[A]) == Fraction(3, 4)
    assert steps.percentage(context.season.results[F]) == 0


def test_win_percentage_counts_every_game():
    context = _context(win("A", "B"), win("A", "F"), win("B", "F"))
    assert steps.win_percentage([A, B, F], context) == {
        A: 1,
        B: Fraction(1, 2),
        F: 0,
    }


def test_head_to_head_counts_only_games_among_the_level_teams():
    # B beat A; A's win over D does not count.
    context = _context(win("B", "A"), win("A", "D"), win("D", "B"))
    assert steps.head_to_head([A, B], context) == {A: 0, B: 1}


def test_sweep_with_two_teams_is_head_to_head():
    context = _context(win("B", "A"))
    assert steps.head_to_head_sweep([A, B], context) == {A: 0, B: 1}


def test_sweep_places_a_team_that_beat_every_other_first():
    context = _context(win("A", "B"), win("A", "C"), win("B", "C"))
    assert steps.head_to_head_sweep([A, B, C], context) == {A: 1, B: 0, C: 0}


def test_sweep_places_a_team_that_lost_to_every_other_last():
    context = _context(win("A", "C"), win("B", "C"), ("A", 10, "B", 10))
    assert steps.head_to_head_sweep([A, B, C], context) == {A: 0, B: 0, C: -1}


def test_no_sweep_in_a_cycle():
    context = _context(win("A", "B"), win("B", "C"), win("C", "A"))
    assert steps.head_to_head_sweep([A, B, C], context) is None


def test_no_sweep_without_a_game_against_every_other():
    # A beat B but never played C; C lost to B only.
    context = _context(win("A", "B"), win("B", "C"))
    assert steps.head_to_head_sweep([A, B, C], context) is None


def test_division_and_conference_percentage():
    # A: 2-1 in the division (B, B, C). B: 1-1 in the division (A, A), 2-1 in
    # the conference with its win over D; its win over F is outside it.
    context = _context(
        win("A", "B"), win("B", "A"), win("A", "C"), win("B", "D"), win("B", "F")
    )
    assert steps.division_percentage([A, B], context) == {
        A: Fraction(2, 3),
        B: Fraction(1, 2),
    }
    assert steps.conference_percentage([A, B], context) == {
        A: Fraction(2, 3),
        B: Fraction(2, 3),
    }


def test_net_points_by_kind_of_game():
    context = _context(
        win("A", "B", by=10),
        win("B", "A", by=20),
        win("A", "D", by=5),
        win("B", "F", by=7),
    )
    group = [A, B]
    assert steps.division_net_points(group, context) == {A: -10, B: 10}
    assert steps.conference_net_points(group, context) == {A: -5, B: 10}
    assert steps.net_points(group, context) == {A: -5, B: 17}


# One division: A and B against W, X, Y and Z.
COMMON = [[["A", "B", "W", "X", "Y", "Z"]]]


def test_common_games_at_the_minimum_apply():
    # Both played W, X, Y and Z: A won all four, B three.
    context = _context(
        *(win("A", other) for other in "WXYZ"),
        *(win("B", other) for other in "WXY"),
        win("Z", "B"),
        shape=COMMON,
    )
    assert steps.common_games(4)([0, 1], context) == {0: 1, 1: Fraction(3, 4)}


def test_common_games_one_short_of_the_minimum_skipped():
    context = _context(
        *(win("A", other) for other in "WXY"),
        *(win("B", other) for other in "WXY"),
        shape=COMMON,
    )
    assert steps.common_games(4)([0, 1], context) is None


def test_common_net_points():
    context = _context(
        *(win("A", other) for other in "WXYZ"),
        *(win("B", other) for other in "WXY"),
        win("Z", "B"),
        shape=COMMON,
    )
    assert steps.common_net_points([0, 1], context) == {0: 40, 1: 20}


# A beat X twice and Y once; B beat Y; X beat Y. X is 1-2, Y 0-3.
VICTORY = [[["A", "B", "X", "Y"]]]
VICTORY_GAMES = (
    win("A", "X"),
    win("A", "X"),
    win("A", "Y"),
    win("B", "Y"),
    win("X", "Y"),
)


def test_strength_of_victory_counts_every_win():
    context = _context(*VICTORY_GAMES, shape=VICTORY)
    # A: X's three games twice and Y's three: 2 wins in 9.
    assert steps.strength_of_victory([0, 1], context) == {0: Fraction(2, 9), 1: 0}


def test_strength_of_schedule_each_opponent_once_or_every_game():
    context = _context(*VICTORY_GAMES, shape=VICTORY)
    once = steps.strength_of_schedule(each_opponent_once=True)
    every = steps.strength_of_schedule(each_opponent_once=False)
    assert once([0, 1], context) == {0: Fraction(1, 6), 1: 0}
    assert every([0, 1], context) == {0: Fraction(2, 9), 1: 0}


def test_combined_ranking_within_the_conference_or_the_league():
    # Points for / against: A 30/0, B 20/20, C 30/80, D 60/40.
    context = _context(
        ("A", 30, "D", 0),
        ("B", 20, "C", 20),
        ("D", 60, "C", 10),
        shape=[[["A", "B", "C"]], [["D"]]],
    )
    group = [0, 1, 2]
    # Conference (A, B, C): A and C share first in points scored.
    assert steps.combined_ranking("conference")(group, context) == {
        0: 0,
        1: -3,
        2: -2,
    }
    # League: D outscored everyone.
    assert steps.combined_ranking("league")(group, context) == {
        0: -1,
        1: -4,
        2: -4,
    }


def test_division_finish_for_teams_of_one_division():
    context = _context()
    context.orders[0] = (B, A, C)
    assert steps.division_finish([A, B], context) == {A: -1, B: 0}


def test_division_finish_skipped_for_teams_of_different_divisions():
    assert steps.division_finish([A, D], _context()) is None


def test_playoff_round_and_champion_then_runner_up():
    # Round 1: A over B, D over C; final: D over A.
    context = _context(
        playoffs=[[win("A", "B"), win("D", "C")], [win("D", "A")]]
    )
    group = [A, B, C, D, E]
    assert steps.playoff_round(group, context) == {A: 2, B: 1, C: 1, D: 3, E: 0}
    assert steps.champion_then_runner_up(group, context) == {
        A: 1,
        B: 0,
        C: 0,
        D: 2,
        E: 0,
    }
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_standings/test_steps.py -v --no-cov`
Expected: FAIL with `ImportError: cannot import name 'steps'`.

- [x] **Step 3: Write `steps.py`**

`src/athc/fbpro98_standings/steps.py`:

```python
"""The tie-break steps.

Each step gives every level team a value, higher is better, or None when it
does not apply to these teams; the ranking then skips it. Values are exact
(`Fraction`), so equal records compare equal.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from fractions import Fraction
from typing import Literal, Protocol

from athc.fbpro98_standings.season import Result, Season

Value = Fraction | int
Values = Mapping[int, Value]


class Context(Protocol):
    """What a step may look at besides the level teams."""

    season: Season

    def division_order(self, division: int) -> tuple[int, ...]:
        """The season's division, in its standings by the same method."""
        ...


Step = Callable[[Sequence[int], Context], Values | None]


def percentage(results: Iterable[Result]) -> Fraction:
    """W-L-T percentage, a tie counting half a win; 0 with no game."""
    games = tuple(results)
    if not games:
        return Fraction(0)
    points = sum(2 if game.won else 0 if game.lost else 1 for game in games)
    return Fraction(points, 2 * len(games))


def win_percentage(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in every game."""
    results = context.season.results
    return {team: percentage(results[team]) for team in group}


def head_to_head(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in the games among the level teams only."""
    results = context.season.results
    level = set(group)
    return {
        team: percentage(game for game in results[team] if game.opponent in level)
        for team in group
    }


def head_to_head_sweep(group: Sequence[int], context: Context) -> Values | None:
    """Two teams: head-to-head. Three or more: only a team that beat every
    other level team, or lost to every one, is placed, first or last."""
    if len(group) == 2:
        return head_to_head(group, context)
    results = context.season.results
    for team in group:
        others = set(group) - {team}
        games = [game for game in results[team] if game.opponent in others]
        if {game.opponent for game in games} != others:
            continue
        if all(game.won for game in games):
            return {other: int(other == team) for other in group}
        if all(game.lost for game in games):
            return {other: -int(other == team) for other in group}
    return None


def division_percentage(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in division games."""
    results = context.season.results
    return {
        team: percentage(game for game in results[team] if game.division)
        for team in group
    }


def conference_percentage(group: Sequence[int], context: Context) -> Values:
    """W-L-T % in conference games."""
    results = context.season.results
    return {
        team: percentage(game for game in results[team] if game.conference)
        for team in group
    }


def _common_opponents(group: Sequence[int], context: Context) -> set[int]:
    results = context.season.results
    opponents = [{game.opponent for game in results[team]} for team in group]
    return opponents[0].intersection(*opponents[1:])


def common_games(minimum: int) -> Step:
    """W-L-T % against the opponents every level team played; skipped when a
    team played fewer than `minimum` such games."""

    def step(group: Sequence[int], context: Context) -> Values | None:
        common = _common_opponents(group, context)
        results = context.season.results
        games = {
            team: [game for game in results[team] if game.opponent in common]
            for team in group
        }
        if any(len(played) < minimum for played in games.values()):
            return None
        return {team: percentage(played) for team, played in games.items()}

    return step


def common_net_points(group: Sequence[int], context: Context) -> Values:
    """Net points against the opponents every level team played."""
    common = _common_opponents(group, context)
    results = context.season.results
    return {
        team: sum(
            game.scored - game.allowed
            for game in results[team]
            if game.opponent in common
        )
        for team in group
    }


def strength_of_victory(group: Sequence[int], context: Context) -> Values:
    """Combined W-L-T % of the teams beaten, every win counted."""
    results = context.season.results
    return {
        team: percentage(
            beaten
            for game in results[team]
            if game.won
            for beaten in results[game.opponent]
        )
        for team in group
    }


def strength_of_schedule(each_opponent_once: bool) -> Step:
    """Combined W-L-T % of the opponents, tougher higher: each opponent once
    (the game's manual), or every game counted (the NFL's)."""

    def step(group: Sequence[int], context: Context) -> Values:
        results = context.season.results
        values: dict[int, Value] = {}
        for team in group:
            opponents = [game.opponent for game in results[team]]
            if each_opponent_once:
                opponents = list(dict.fromkeys(opponents))
            values[team] = percentage(
                game for opponent in opponents for game in results[opponent]
            )
        return values

    return step


def combined_ranking(scope: Literal["conference", "league"]) -> Step:
    """A team's rank in points scored plus its rank in points allowed, among
    its conference's or the league's teams; lower is better, and equal
    values share a rank."""

    def step(group: Sequence[int], context: Context) -> Values:
        season = context.season
        scored = [sum(game.scored for game in games) for games in season.results]
        allowed = [sum(game.allowed for game in games) for games in season.results]
        values: dict[int, Value] = {}
        for team in group:
            pool = [
                other
                for other in range(len(season.teams))
                if scope == "league"
                or season.conference_of[other] == season.conference_of[team]
            ]
            scored_rank = sum(scored[other] > scored[team] for other in pool)
            allowed_rank = sum(allowed[other] < allowed[team] for other in pool)
            values[team] = -(scored_rank + allowed_rank)
        return values

    return step


def net_points(group: Sequence[int], context: Context) -> Values:
    """Points for minus points against, in every game."""
    results = context.season.results
    return {
        team: sum(game.scored - game.allowed for game in results[team])
        for team in group
    }


def division_net_points(group: Sequence[int], context: Context) -> Values:
    """Net points in division games."""
    results = context.season.results
    return {
        team: sum(game.scored - game.allowed for game in results[team] if game.division)
        for team in group
    }


def conference_net_points(group: Sequence[int], context: Context) -> Values:
    """Net points in conference games."""
    results = context.season.results
    return {
        team: sum(
            game.scored - game.allowed for game in results[team] if game.conference
        )
        for team in group
    }


def division_finish(group: Sequence[int], context: Context) -> Values | None:
    """Level teams all of one division keep their order in its standings;
    skipped for teams of different divisions."""
    divisions = {context.season.division_of[team] for team in group}
    if len(divisions) != 1:
        return None
    order = context.division_order(divisions.pop())
    return {team: -order.index(team) for team in group}


def playoff_round(group: Sequence[int], context: Context) -> Values:
    """The playoff round reached; the champion highest."""
    season = context.season
    return {team: season.playoff_round[team] for team in group}


def champion_then_runner_up(group: Sequence[int], context: Context) -> Values:
    """The champion first, the Super Bowl loser second, every other team
    level."""
    season = context.season
    return {
        team: 2 if team == season.champion else 1 if team == season.runner_up else 0
        for team in group
    }
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_standings/test_steps.py -v --no-cov`
Expected: 19 passed.

- [x] **Step 5: Fix line endings, lint, type-check**

CRLF fix on both files; `uv run ruff format .`; `uv run ruff check .`; `uv run pyright`. Expected: no errors.

- [x] **Step 6: Commit**

```bash
git add src/athc/fbpro98_standings/steps.py tests/unit/fbpro98_standings/test_steps.py
```

```bash
git commit -m "fbpro98_standings: the tie-break steps"
```

---

### Task 3: Matching two seasons with team moves

**Files:**
- Create: `src/athc/fbpro98_standings/moves.py`
- Test: `tests/unit/fbpro98_standings/test_moves.py`

**Interfaces:**
- Consumes: `StandingsError` (Task 1).
- Produces: `match(previous: LgeFile, current: LgeFile, team_moves: Mapping[str, str]) -> tuple[int, ...]`: for each current team in file order, the index of its previous-season team in `previous.teams`.

- [x] **Step 1: Write the failing tests**

`tests/unit/fbpro98_standings/test_moves.py`:

```python
"""Tests for athc.fbpro98_standings.moves: matching the previous season's
teams to the current season's."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_standings import StandingsError
from athc.fbpro98_standings.moves import match
from tests.unit.fbpro98_standings.leagues import Shape, build_league

# Previous season: division 1 is A and B, division 2 is C.
PREVIOUS = [[["A", "B"], ["C"]]]


def _match(
    current: Shape,
    team_moves: dict[str, str] | None = None,
    previous: Shape = PREVIOUS,
) -> tuple[int, ...]:
    return match(build_league(previous), build_league(current), team_moves or {})


def test_teams_match_by_name_wherever_they_moved():
    # C moved into A's division, B into C's old one.
    assert _match([[["A", "C"], ["B"]]]) == (0, 2, 1)


def test_a_team_move_matches_a_renamed_team():
    assert _match([[["A", "B"], ["X"]]], {"C": "X"}) == (0, 1, 2)


def test_team_moves_may_swap_names():
    assert _match([[["B", "A"], ["C"]]], {"A": "B", "B": "A"}) == (0, 1, 2)


@pytest.mark.parametrize(
    ("previous", "current", "team_moves", "message"),
    [
        (
            [[["A", "A"]]],
            [[["A", "B"]]],
            {},
            "Team name repeats in the previous file: A.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "A"]]],
            {},
            "Team name repeats in the current file: A.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "B"]]],
            {"Z": "B"},
            "Team move Z: Not a team in the previous file.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "B"]]],
            {"A": "Z"},
            "Team move A: Z is not a team in the current file.",
        ),
        (
            [[["A", "B"]]],
            [[["B", "C"]]],
            {"A": "B"},
            "Team move A: Another team in the previous file is named B.",
        ),
        (
            [[["A", "B", "C"]]],
            [[["X", "C"]]],
            {"A": "X", "B": "X"},
            "Team move B: X is also the new name of A.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "C"]]],
            {},
            "Team(s) not in the current file: B. "
            "List each team whose name changed in the team moves.",
        ),
        (
            [[["A", "B"]]],
            [[["A", "B", "C"]]],
            {},
            "Team(s) not in the previous file: C.",
        ),
    ],
)
def test_mismatch_rejected(previous, current, team_moves, message):
    with pytest.raises(StandingsError, match=re.escape(message)):
        _match(current, team_moves, previous)
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_standings/test_moves.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'athc.fbpro98_standings.moves'`.

- [x] **Step 3: Write `moves.py`**

`src/athc/fbpro98_standings/moves.py`:

```python
"""Match the previous season's teams to the current season's: by name, with
the team moves for the teams whose name changed. A team that only changed
division needs nothing; the current file says where it is."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from athc.fbpro98_lge import LgeFile, Team
from athc.fbpro98_standings.errors import StandingsError


def match(
    previous: LgeFile, current: LgeFile, team_moves: Mapping[str, str]
) -> tuple[int, ...]:
    """For each current team, in file order, its previous-season team's index
    in `previous.teams`.

    Raises:
        StandingsError: a team name repeats in either file; a team move names
            a team not in the previous file, a name not in the current file,
            a name another previous-season team keeps, or a name another move
            already took; a team of one file has no match in the other.
    """
    previous_by_name = _by_name(previous.teams, "previous")
    current_by_name = _by_name(current.teams, "current")
    taken: dict[str, str] = {}
    for old, new in team_moves.items():
        if old not in previous_by_name:
            raise StandingsError(f"Team move {old}: Not a team in the previous file.")
        if new not in current_by_name:
            raise StandingsError(
                f"Team move {old}: {new} is not a team in the current file."
            )
        # Another previous-season team keeps that name, unless it moves too.
        if new in previous_by_name and new not in team_moves:
            raise StandingsError(
                f"Team move {old}: Another team in the previous file is named {new}."
            )
        if new in taken:
            raise StandingsError(
                f"Team move {old}: {new} is also the new name of {taken[new]}."
            )
        taken[new] = old
    new_names = {old: team_moves.get(old, old) for old in previous_by_name}
    missing = [old for old, new in new_names.items() if new not in current_by_name]
    if missing:
        raise StandingsError(
            f"Team(s) not in the current file: {', '.join(missing)}. "
            "List each team whose name changed in the team moves."
        )
    matched = set(new_names.values())
    extra = [name for name in current_by_name if name not in matched]
    if extra:
        raise StandingsError(f"Team(s) not in the previous file: {', '.join(extra)}.")
    old_of = {new: old for old, new in new_names.items()}
    return tuple(previous_by_name[old_of[team.name]] for team in current.teams)


def _by_name(teams: Sequence[Team], which: str) -> dict[str, int]:
    by_name: dict[str, int] = {}
    for number, team in enumerate(teams):
        if team.name in by_name:
            raise StandingsError(f"Team name repeats in the {which} file: {team.name}.")
        by_name[team.name] = number
    return by_name
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_standings/test_moves.py -v --no-cov`
Expected: 11 passed.

- [x] **Step 5: Fix line endings, lint, type-check**

CRLF fix on both files; `uv run ruff format .`; `uv run ruff check .`; `uv run pyright`. Expected: no errors.

- [x] **Step 6: Commit**

```bash
git add src/athc/fbpro98_standings/moves.py tests/unit/fbpro98_standings/test_moves.py
```

```bash
git commit -m "fbpro98_standings: match two seasons with team moves"
```

---

### Task 4: Standings, the ranking engine and the game method

**Files:**
- Create: `src/athc/fbpro98_standings/methods.py`
- Create: `src/athc/fbpro98_standings/standings.py`
- Modify: `src/athc/fbpro98_standings/__init__.py`
- Test: `tests/unit/fbpro98_standings/test_ranking.py`
- Test: `tests/unit/fbpro98_standings/test_game.py`

**Interfaces:**
- Consumes: `season_of`, `Season` (Task 1); `steps`, `Step`, `Value`, `Context` (Task 2); `match` (Task 3).
- Produces: `Method` (here `Literal["game"]`; Tasks 5 and 6 widen it); `METHODS: tuple[Method, ...]`; `Rules(sort: tuple[Step, ...], breakers: tuple[Step, ...])`; `MethodRules(division: Rules, conference: Rules | None, league: Rules)`; `GAME`; `RULES: dict[Method, MethodRules]`; `Standings(current, previous=None, team_moves=None, *, method, seed=None)` with `division(d)`, `conference(c)`, `league()`, each returning `tuple[Team, ...]` of the current file's own objects; `_Ranker(season: Season, method: MethodRules, seed: int | None)` with `season`, `division(teams)`, `conference(teams)`, `league()`, `division_order(division)`, `_order(teams: list[int], rules: Rules) -> tuple[int, ...]`, `_break(group, rules)`, `_toss(group)`.

- [x] **Step 1: Write the failing tests**

`tests/unit/fbpro98_standings/test_ranking.py`:

```python
"""Tests for athc.fbpro98_standings.standings: the ranking engine, the coin
toss, and the caller's mistakes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import pytest

from athc.fbpro98_lge import Conference, Division, Game, LgeFile, Team
from athc.fbpro98_standings import Method, Standings
from athc.fbpro98_standings.methods import MethodRules, Rules
from athc.fbpro98_standings.season import season_of
from athc.fbpro98_standings.standings import _Ranker
from athc.fbpro98_standings.steps import Context, Values
from tests.unit.fbpro98_standings.leagues import NO_GAMES, build_league, names

SIX = [[["A", "B", "C", "D", "E", "F"]]]
THREE = [[["A", "B", "C"]]]
A, B, C = range(3)
# A pair is separated by its place here: A over B, C over B, A over C.
PAIR_ORDER = (A, C, B)


def _pairs(group: Sequence[int], context: Context) -> Values:
    """Separates only a pair: the one earlier in PAIR_ORDER."""
    if len(group) != 2:
        return dict.fromkeys(group, 0)
    return {team: -PAIR_ORDER.index(team) for team in group}


def _a_and_b_over_c(group: Sequence[int], context: Context) -> Values:
    return {team: int(team != C) for team in group}


def _ranker(rules: Rules) -> _Ranker:
    season = season_of(build_league(THREE))
    return _Ranker(season, MethodRules(rules, None, rules), seed=0)


def test_regroup_ranks_the_placed_teams_and_the_rest_again():
    # Three level teams: the second step places A and B over C; A and B start
    # over at the first step, which puts A first.
    rules = Rules(sort=(), breakers=(_pairs, _a_and_b_over_c))
    assert _ranker(rules)._order([A, B, C], rules) == (A, B, C)


def test_a_seed_repeats_the_coin_toss():
    lge = build_league(SIX)
    division = lge.conferences[0].divisions[0]
    first = Standings(lge, method="game", seed=7).division(division)
    second = Standings(lge, method="game", seed=7).division(division)
    assert names(first) == names(second)
    assert sorted(names(first)) == ["A", "B", "C", "D", "E", "F"]


def test_the_coin_toss_does_not_depend_on_what_was_asked_before():
    lge = build_league(SIX)
    division = lge.conferences[0].divisions[0]
    one = Standings(lge, method="game", seed=7)
    two = Standings(lge, method="game", seed=7)
    league_first = one.league()
    division_second = one.division(division)
    division_first = two.division(division)
    league_second = two.league()
    assert (league_first, division_second) == (league_second, division_first)


def test_without_a_seed_the_same_question_gets_the_same_answer():
    lge = build_league(SIX)
    division = lge.conferences[0].divisions[0]
    standings = Standings(lge, method="game")
    assert standings.division(division) == standings.division(division)
    assert standings.league() == standings.league()


def test_unknown_method_rejected():
    with pytest.raises(ValueError, match="Unknown method: 'xfl'"):
        Standings(build_league(SIX), method=cast(Method, "xfl"))


def test_team_moves_need_the_previous_file():
    with pytest.raises(ValueError, match="team_moves needs the previous season's"):
        Standings(build_league(SIX), team_moves={"A": "B"}, method="game")


def test_a_division_of_another_file_rejected():
    other = build_league(SIX).conferences[0].divisions[0]
    with pytest.raises(ValueError, match="Not a division of the current file: 'D1'"):
        Standings(build_league(SIX), method="game").division(other)


def test_a_conference_of_another_file_rejected():
    other = build_league(SIX).conferences[0]
    with pytest.raises(ValueError, match="Not a conference of the current file: 'C1'"):
        Standings(build_league(SIX), method="game").conference(other)


def test_an_empty_division_has_no_standings():
    lge = build_league([[["A", "B"], []]])
    conference = lge.conferences[0]
    standings = Standings(lge, method="game", seed=0)
    assert standings.division(conference.divisions[1]) == ()
    assert sorted(names(standings.conference(conference))) == ["A", "B"]


def test_teams_that_look_alike_stay_apart():
    # Two teams equal in every field: told apart by position, never by value.
    first = Team(name="A", nickname="", record=NO_GAMES)
    second = Team(name="A", nickname="", record=NO_GAMES)
    division = Division(name="D1", teams=(first, second), standings=(first, second))
    lge = LgeFile(
        conferences=(
            Conference(name="C1", divisions=(division,), standings=(first, second)),
        ),
        weeks=((Game(second, 20, first, 10),),),
    )
    ranked = Standings(lge, method="game").division(division)
    assert ranked[0] is second
    assert ranked[1] is first
```

`tests/unit/fbpro98_standings/test_game.py`:

```python
"""Tests for the game method: the FbPro98 manual's tie-breakers (page 129)
and its draft order (page 136), reversed, for league standings."""

from __future__ import annotations

import pytest

from athc.fbpro98_lge import LgeFile
from athc.fbpro98_standings import Standings
from tests.unit.fbpro98_standings.leagues import build_league, names, real_lge, win

# Each division's season-end order, as the game showed it (2048) and as the
# manual's steps give it (2043, 2046); the fbpro98_lge tests hold the same.
GAME_DIVISIONS = [
    (
        "PNFL-2048-after-week16.lge",
        (
            ("Miami", "Buffalo", "New England", "Jacksonville"),
            ("Cincinnati", "Pittsburgh", "Las Vegas", "Denver", "Los Angeles"),
            ("Washington", "Atlanta", "New York", "Philadelphia"),
            ("Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"),
        ),
    ),
    (
        "PNFL-2043-after-super-bowl.lge",
        (
            ("New York A", "Indianapolis", "New England", "Jacksonville"),
            ("Kansas City", "Minnesota", "Los Angeles", "Las Vegas", "Pittsburgh"),
            ("Washington", "Detroit", "New York N", "Atlanta"),
            ("Chicago", "San Francisco", "New Orleans", "Seattle", "Anaheim"),
        ),
    ),
    (
        "PNFL-2046-after-super-bowl.lge",
        (
            ("New York A", "Buffalo", "Indianapolis", "New England"),
            ("Pittsburgh", "Houston", "Las Vegas", "Jacksonville", "Denver"),
            ("Washington", "Philadelphia", "Atlanta", "New York N"),
            ("Minnesota", "Seattle", "San Francisco", "Chicago", "Green Bay"),
        ),
    ),
]


def _divisions(standings: Standings, lge: LgeFile) -> tuple[tuple[str, ...], ...]:
    return tuple(
        names(standings.division(division))
        for conference in lge.conferences
        for division in conference.divisions
    )


@pytest.mark.parametrize(("filename", "expected"), GAME_DIVISIONS)
def test_game_division_standings_match_the_game(filename, expected):
    lge = real_lge(filename)
    assert _divisions(Standings(lge, method="game", seed=0), lge) == expected


def test_game_conference_standings_put_division_winners_first():
    # 2047 after week 16. Division winners: Baltimore and Miami; Chicago and
    # Washington. 7-9: New York beat Green Bay; 6-10: Philadelphia beat San
    # Francisco.
    lge = real_lge("PNFL-after-week16.lge")
    standings = Standings(lge, method="game", seed=0)
    afc, nfc = lge.conferences
    assert names(standings.conference(afc)) == (
        "Baltimore",
        "Miami",
        "Denver",
        "Las Vegas",
        "New England",
        "Cincinnati",
        "Jacksonville",
        "Pittsburgh",
        "Buffalo",
    )
    assert names(standings.conference(nfc)) == (
        "Chicago",
        "Washington",
        "Minnesota",
        "Atlanta",
        "New York",
        "Green Bay",
        "Philadelphia",
        "San Francisco",
        "Seattle",
    )


def test_game_ranks_the_placed_teams_and_the_rest_again():
    # T1, T2, T3 split head-to-head in a cycle with equal division and
    # conference records and division net points. Net points in all games
    # place T1 first; T2 and T3 start over at head-to-head, where T2 beat T3,
    # although strength of schedule would favor T3.
    lge = build_league(
        [[["T1", "T2", "T3"], ["T4", "T5"]], [["T6"]]],
        [
            win("T1", "T2"),
            win("T2", "T3"),
            win("T3", "T1"),
            win("T1", "T4", by=20),
            win("T2", "T5", by=5),
            win("T3", "T4", by=5),
            win("T4", "T6"),
            win("T4", "T6"),
            win("T4", "T6"),
        ],
    )
    division = lge.conferences[0].divisions[0]
    assert names(Standings(lge, method="game").division(division)) == (
        "T1",
        "T2",
        "T3",
    )


def test_game_league_puts_the_champion_and_runner_up_first():
    # A is 2-0 but lost in round 1; B is 0-2 and won the final over D.
    lge = build_league(
        [[["A", "B"], ["C", "D"]]],
        [win("A", "B"), win("A", "C"), win("C", "D"), win("D", "B")],
        [[win("D", "A")], [win("B", "D")]],
    )
    assert names(Standings(lge, method="game").league()) == ("B", "D", "A", "C")


def test_game_league_breaks_record_ties_on_strength_of_schedule():
    # C, D and E are 1-1. Their opponents, each once: E's A (2-0) and D
    # (1-1) = 3/4; C's A and B (0-2) = 1/2; D's B and E = 1/4.
    lge = build_league(
        [[["A", "B", "C", "D", "E"]]],
        [win("A", "E"), win("A", "C"), win("C", "B"), win("D", "B"), win("E", "D")],
    )
    assert names(Standings(lge, method="game").league()) == ("A", "E", "C", "D", "B")


def test_game_conference_without_divisions():
    # One division per conference: its winner first, then the rest.
    lge = build_league([[["A", "B"]], [["C", "D"]]], [win("B", "A"), win("D", "C")])
    standings = Standings(lge, method="game")
    first, second = lge.conferences
    assert names(standings.conference(first)) == ("B", "A")
    assert names(standings.conference(second)) == ("D", "C")
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_standings/test_ranking.py tests/unit/fbpro98_standings/test_game.py -v --no-cov`
Expected: FAIL with `ImportError: cannot import name 'Method'`.

- [x] **Step 3: Write `methods.py`**

`src/athc/fbpro98_standings/methods.py`:

```python
"""The tie-break methods as data.

For division, conference and league standings, each method gives the steps
that sort every team and the tie-breakers for the teams still level. Net
touchdowns, in the game's and the NFL's lists, are not in the league file and
are left out; the coin toss, always last, is the ranking's own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from athc.fbpro98_standings import steps
from athc.fbpro98_standings.steps import Step

Method = Literal["game"]
METHODS: tuple[Method, ...] = get_args(Method)


@dataclass(frozen=True, slots=True)
class Rules:
    """How one method orders one kind of standings."""

    sort: tuple[Step, ...]
    """Steps that sort every team, in turn, best first."""

    breakers: tuple[Step, ...]
    """Tie-breakers for the teams level on every sort step. The first that
    separates a level group places its best teams; they and the rest are each
    ranked again from the first tie-breaker."""


@dataclass(frozen=True, slots=True)
class MethodRules:
    """One method's rules for each kind of standings."""

    division: Rules

    conference: Rules | None
    """Division winners first, then the rest, each by these rules; None for
    the conference's teams in league order."""

    league: Rules


# The manual's list (page 129).
_GAME_TIES = Rules(
    sort=(steps.win_percentage,),
    breakers=(
        steps.head_to_head,
        steps.division_percentage,
        steps.conference_percentage,
        steps.division_net_points,
        steps.net_points,
        steps.strength_of_schedule(each_opponent_once=True),
    ),
)

GAME = MethodRules(
    division=_GAME_TIES,
    conference=_GAME_TIES,
    # The draft order (page 136), reversed.
    league=Rules(
        sort=(
            steps.champion_then_runner_up,
            steps.win_percentage,
            steps.strength_of_schedule(each_opponent_once=True),
        ),
        breakers=(),
    ),
)

RULES: dict[Method, MethodRules] = {"game": GAME}
```

- [x] **Step 4: Write `standings.py`**

`src/athc/fbpro98_standings/standings.py`:

```python
"""Standings: a league's teams ranked by one tie-break method."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping
from itertools import groupby

from athc.fbpro98_lge import Conference, Division, LgeFile, Team
from athc.fbpro98_standings.methods import (
    METHODS,
    RULES,
    Method,
    MethodRules,
    Rules,
)
from athc.fbpro98_standings.moves import match
from athc.fbpro98_standings.season import Season, season_of
from athc.fbpro98_standings.steps import Value


class Standings:
    """A league's standings by one tie-break method.

    With only `current`, ranks the current file's season as played so far.
    With `previous` too, ranks the previous file's season, as played under its
    own divisions, and answers for the current file's divisions, conferences
    and teams; `team_moves` maps each team whose name changed from its
    previous name to its current one. `seed` makes the coin toss repeatable.

    Raises:
        ValueError: an unknown method; `team_moves` without `previous`.
        StandingsError: the two files and the team moves do not fit together.
    """

    def __init__(
        self,
        current: LgeFile,
        previous: LgeFile | None = None,
        team_moves: Mapping[str, str] | None = None,
        *,
        method: Method,
        seed: int | None = None,
    ) -> None:
        if method not in METHODS:
            raise ValueError(
                f"Unknown method: {method!r}. Valid: {', '.join(METHODS)}"
            )
        if team_moves and previous is None:
            raise ValueError("team_moves needs the previous season's file.")
        self._current = current
        self._number = {id(team): number for number, team in enumerate(current.teams)}
        self._ranked_of: tuple[int, ...]
        if previous is None:
            self._ranked_of = tuple(range(len(current.teams)))
            season = season_of(current)
        else:
            self._ranked_of = match(previous, current, team_moves or {})
            season = season_of(previous)
        self._current_of = {
            ranked: number for number, ranked in enumerate(self._ranked_of)
        }
        self._ranker = _Ranker(season, RULES[method], seed)

    def division(self, division: Division) -> tuple[Team, ...]:
        """The division's teams, best first.

        Raises:
            ValueError: not a division of the current file.
        """
        if not any(
            known is division
            for conference in self._current.conferences
            for known in conference.divisions
        ):
            raise ValueError(f"Not a division of the current file: {division.name!r}.")
        return self._teams(self._ranker.division(self._ranked(division.teams)))

    def conference(self, conference: Conference) -> tuple[Team, ...]:
        """The conference's teams, best first.

        Raises:
            ValueError: not a conference of the current file.
        """
        if not any(known is conference for known in self._current.conferences):
            raise ValueError(
                f"Not a conference of the current file: {conference.name!r}."
            )
        teams = [team for division in conference.divisions for team in division.teams]
        return self._teams(self._ranker.conference(self._ranked(teams)))

    def league(self) -> tuple[Team, ...]:
        """Every team, in final order."""
        return self._teams(self._ranker.league())

    def _ranked(self, teams: Iterable[Team]) -> tuple[int, ...]:
        # The current teams' numbers in the season being ranked.
        return tuple(self._ranked_of[self._number[id(team)]] for team in teams)

    def _teams(self, numbers: Iterable[int]) -> tuple[Team, ...]:
        teams = self._current.teams
        return tuple(teams[self._current_of[number]] for number in numbers)


class _Ranker:
    """Orders one season's teams, by their numbers in it, by one method.
    Every answer is kept, so the same question gets the same answer even when
    the coin was tossed without a seed."""

    def __init__(self, season: Season, method: MethodRules, seed: int | None) -> None:
        self.season = season
        self._method = method
        self._seed = seed
        self._answers: dict[tuple[str, tuple[int, ...]], tuple[int, ...]] = {}

    def division(self, teams: Iterable[int]) -> tuple[int, ...]:
        rules = self._method.division
        return self._kept("division", teams, lambda group: self._order(group, rules))

    def conference(self, teams: Iterable[int]) -> tuple[int, ...]:
        rules = self._method.conference
        if rules is None:
            members = set(teams)
            return tuple(team for team in self.league() if team in members)
        return self._kept(
            "conference", teams, lambda group: self._winners_first(group, rules)
        )

    def league(self) -> tuple[int, ...]:
        rules = self._method.league
        return self._kept(
            "league",
            range(len(self.season.teams)),
            lambda group: self._order(group, rules),
        )

    def division_order(self, division: int) -> tuple[int, ...]:
        """One of the season's own divisions, by the division rules."""
        return self.division(self.season.division_members(division))

    def _kept(
        self,
        kind: str,
        teams: Iterable[int],
        rank: Callable[[list[int]], tuple[int, ...]],
    ) -> tuple[int, ...]:
        group = sorted(teams)
        key = (kind, tuple(group))
        if key not in self._answers:
            self._answers[key] = rank(group)
        return self._answers[key]

    def _winners_first(self, teams: list[int], rules: Rules) -> tuple[int, ...]:
        winners = {
            self.division_order(division)[0] for division in set(self.season.division_of)
        }
        first = [team for team in teams if team in winners]
        rest = [team for team in teams if team not in winners]
        return self._order(first, rules) + self._order(rest, rules)

    def _order(self, teams: list[int], rules: Rules) -> tuple[int, ...]:
        """Sort by the sort steps, then break each level group."""
        values = [
            value for step in rules.sort if (value := step(teams, self)) is not None
        ]

        def key(team: int) -> tuple[Value, ...]:
            return tuple(-value[team] for value in values)

        ordered: list[int] = []
        for _, level in groupby(sorted(teams, key=key), key=key):
            ordered += self._break(list(level), rules)
        return tuple(ordered)

    def _break(self, group: list[int], rules: Rules) -> list[int]:
        """The first tie-breaker that separates the group places its best
        teams; they and the rest are each ranked again from the first one.
        Level after every tie-breaker: the coin toss."""
        if len(group) == 1:
            return group
        for step in rules.breakers:
            values = step(group, self)
            if values is None:
                continue
            best = max(values.values())
            top = [team for team in group if values[team] == best]
            if len(top) < len(group):
                rest = [team for team in group if values[team] != best]
                return self._break(top, rules) + self._break(rest, rules)
        return self._toss(group)

    def _toss(self, group: list[int]) -> list[int]:
        """The level teams in a random order: the same for a given seed and
        the same teams, whatever was asked before."""
        teams = sorted(group)
        coin = (
            random.Random()
            if self._seed is None
            else random.Random(f"{self._seed}:{teams}")
        )
        coin.shuffle(teams)
        return teams
```

- [x] **Step 5: Export the public names**

`src/athc/fbpro98_standings/__init__.py`:

```python
"""Rank a Front Page Sports Football Pro '98 league's teams from its `.lge`
files: division, conference and league standings by the game's, the
scheduler's or the NFL's tie-breakers."""

from athc.fbpro98_standings.errors import StandingsError
from athc.fbpro98_standings.methods import Method
from athc.fbpro98_standings.standings import Standings

__all__ = ["Method", "Standings", "StandingsError"]
```

- [x] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_standings -v --no-cov`
Expected: all passed (Tasks 1-4). If a `GAME_DIVISIONS` case fails, do not touch the expected orders: find the step that decides the failing pair and report it.

- [x] **Step 7: Fix line endings, lint, type-check**

CRLF fix on the five touched files; `uv run ruff format .`; `uv run ruff check .`; `uv run pyright`. Expected: no errors.

- [x] **Step 8: Commit**

```bash
git add src/athc/fbpro98_standings tests/unit/fbpro98_standings
```

```bash
git commit -m "fbpro98_standings: Standings, the ranking engine and the game method"
```

---

### Task 5: The scheduler method

**Files:**
- Modify: `src/athc/fbpro98_standings/methods.py`
- Test: `tests/unit/fbpro98_standings/test_scheduler.py`

**Interfaces:**
- Consumes: `Rules`, `MethodRules`, `_GAME_TIES`, `RULES` (Task 4); `steps.division_finish`, `steps.playoff_round` (Task 2).
- Produces: `Method = Literal["game", "scheduler"]`; `SCHEDULER`; `RULES` with `"scheduler"`.

- [x] **Step 1: Write the failing tests**

`tests/unit/fbpro98_standings/test_scheduler.py`:

```python
"""Tests for the scheduler method: league standings by playoff round,
record, strength of schedule (every game), division finish and point
differential; conference standings in league order; division standings by
the game's steps."""

from __future__ import annotations

from athc.fbpro98_standings import Standings
from tests.unit.fbpro98_standings.leagues import build_league, names, real_lge, win

# The 2048 standings file's overall order (git dade898^,
# config/release/leagues/PNFL/standings/2048.league.ini), in the 2047 file's
# names: Baltimore became Los Angeles for 2048.
OVERALL_2047 = (
    "Miami",
    "Minnesota",
    "Baltimore",
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
)

# The 2047 standings file's overall order (git dade898^, 2047.league.ini) in
# the 2046 file's names. That file's overall section was written with New
# York A as Baltimore and Indianapolis as Cincinnati; Houston became Miami
# and New York N became New York.
OVERALL_2046 = (
    "Pittsburgh",
    "Washington",
    "Minnesota",
    "New York A",
    "Houston",
    "Buffalo",
    "Seattle",
    "San Francisco",
    "Indianapolis",
    "Las Vegas",
    "Philadelphia",
    "Chicago",
    "Green Bay",
    "Denver",
    "Jacksonville",
    "Atlanta",
    "New York N",
    "New England",
)


def test_scheduler_league_matches_the_2048_standings_file():
    lge = real_lge("PNFL-2047-after-super-bowl.lge")
    assert names(Standings(lge, method="scheduler", seed=0).league()) == OVERALL_2047


def test_scheduler_league_breaks_a_division_tie_on_division_finish():
    # Chicago and Green Bay: both 6-10, out of the playoffs, equal strength of
    # schedule, one division; Chicago finished above Green Bay in it.
    lge = real_lge("PNFL-2046-after-super-bowl.lge")
    assert names(Standings(lge, method="scheduler", seed=0).league()) == OVERALL_2046


def test_scheduler_division_finish_skipped_across_divisions():
    # A and C (1-0) and B and D (0-1) are level through strength of schedule
    # in different divisions: point differential decides.
    lge = build_league(
        [[["A", "B"], ["C", "D"]]],
        [win("A", "B", by=20), win("C", "D", by=5)],
    )
    assert names(Standings(lge, method="scheduler").league()) == ("A", "C", "D", "B")


def test_scheduler_division_finish_overrides_point_differential():
    # A, B and C are 1-1 in one division with equal strength of schedule. The
    # division's order is B, C, A (B on division net points, then C over A
    # head-to-head); point differential alone would give B, A, C.
    lge = build_league(
        [[["A", "B", "C"]]],
        [win("A", "B", by=1), win("B", "C", by=30), win("C", "A", by=1)],
    )
    assert names(Standings(lge, method="scheduler").league()) == ("B", "C", "A")


def test_scheduler_conference_standings_follow_the_league_order():
    lge = real_lge("PNFL-2047-after-super-bowl.lge")
    standings = Standings(lge, method="scheduler", seed=0)
    for conference in lge.conferences:
        members = {
            team.name for division in conference.divisions for team in division.teams
        }
        expected = tuple(name for name in OVERALL_2047 if name in members)
        assert names(standings.conference(conference)) == expected
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_standings/test_scheduler.py -v --no-cov`
Expected: FAIL with `ValueError: Unknown method: 'scheduler'. Valid: game`.

- [x] **Step 3: Add the scheduler method**

In `src/athc/fbpro98_standings/methods.py`, replace `Method = Literal["game"]` with:

```python
Method = Literal["game", "scheduler"]
```

Replace the `RULES` line at the end with:

```python
SCHEDULER = MethodRules(
    # The game's own steps.
    division=_GAME_TIES,
    conference=None,
    league=Rules(
        sort=(
            steps.playoff_round,
            steps.win_percentage,
            steps.strength_of_schedule(each_opponent_once=False),
        ),
        breakers=(steps.division_finish, steps.net_points),
    ),
)

RULES: dict[Method, MethodRules] = {"game": GAME, "scheduler": SCHEDULER}
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_standings -v --no-cov`
Expected: all passed. If an `OVERALL_*` test fails, do not touch the expected order: report which teams differ and the step that placed them.

- [x] **Step 5: Fix line endings, lint, type-check**

CRLF fix on both files; `uv run ruff format .`; `uv run ruff check .`; `uv run pyright`. Expected: no errors.

- [x] **Step 6: Commit**

```bash
git add src/athc/fbpro98_standings/methods.py tests/unit/fbpro98_standings/test_scheduler.py
```

```bash
git commit -m "fbpro98_standings: the scheduler method"
```

---

### Task 6: The NFL method

**Files:**
- Modify: `src/athc/fbpro98_standings/methods.py`
- Modify: `src/athc/fbpro98_standings/standings.py`
- Modify: `tests/unit/fbpro98_standings/test_ranking.py`
- Test: `tests/unit/fbpro98_standings/test_nfl.py`

**Interfaces:**
- Consumes: everything from Tasks 2-5.
- Produces: `Method = Literal["game", "scheduler", "nfl"]`; `Rules` gains `one_advances: bool = False` and `by_division_first: bool = False`; `NFL`; `RULES` with `"nfl"`; `_Ranker` gains `_regroup`, `_best`, `_narrow`, `_best_of_each`.

- [x] **Step 1: Write the failing tests**

`tests/unit/fbpro98_standings/test_nfl.py`:

```python
"""Tests for the NFL method: only one team advances at a time, and teams of
different divisions go on only as each division's best."""

from __future__ import annotations

from collections.abc import Sequence

from athc.fbpro98_standings import Standings
from athc.fbpro98_standings.methods import MethodRules, Rules
from athc.fbpro98_standings.season import season_of
from athc.fbpro98_standings.standings import _Ranker
from athc.fbpro98_standings.steps import Context, Step, Values
from tests.unit.fbpro98_standings.leagues import Shape, build_league, names, real_lge

A, B, C = range(3)
# A pair is separated by its place here: A over B, C over B, A over C.
PAIR_ORDER = (A, C, B)


def _pairs(group: Sequence[int], context: Context) -> Values:
    """Separates only a pair: the one earlier in PAIR_ORDER."""
    if len(group) != 2:
        return dict.fromkeys(group, 0)
    return {team: -PAIR_ORDER.index(team) for team in group}


def _a_and_b_over_c(group: Sequence[int], context: Context) -> Values:
    return {team: int(team != C) for team in group}


def _prefer(*order: int) -> Step:
    """A step that ranks teams by their place in `order`."""

    def step(group: Sequence[int], context: Context) -> Values:
        return {team: -order.index(team) for team in group}

    return step


def _ranker(shape: Shape, method: MethodRules) -> _Ranker:
    return _Ranker(season_of(build_league(shape)), method, seed=0)


def test_nfl_sends_the_teams_a_step_dropped_back_to_the_first_tie_breaker():
    # The second step drops C; A advances over B on the first. Then B and C
    # start over at the first step, where C beats B.
    rules = Rules(sort=(), breakers=(_pairs, _a_and_b_over_c), one_advances=True)
    ranker = _ranker([[["A", "B", "C"]]], MethodRules(rules, None, rules))
    assert ranker._order([A, B, C], rules) == (A, C, B)


def test_nfl_conference_keeps_only_each_divisions_best():
    # One conference: A1 and A2 in one division, B1 in the other.
    a1, a2, b1 = range(3)
    division = Rules(sort=(), breakers=(_prefer(a1, a2, b1),), one_advances=True)
    conference = Rules(
        sort=(),
        breakers=(_prefer(b1, a2, a1),),
        one_advances=True,
        by_division_first=True,
    )
    league = Rules(sort=(), breakers=())
    ranker = _ranker([[["A1", "A2"], ["B1"]]], MethodRules(division, conference, league))
    # A1 is its division's best; B1 beats it. Then A1 and A2, one division,
    # go by the division rules.
    assert ranker._order([a1, a2, b1], conference) == (b1, a1, a2)


def test_nfl_league_keeps_each_divisions_then_each_conferences_best():
    # Conference 1: A1 and A2, each its own division; conference 2: B1.
    a1, a2, b1 = range(3)
    division = Rules(sort=(), breakers=(), one_advances=True)
    conference = Rules(
        sort=(),
        breakers=(_prefer(a2, a1, b1),),
        one_advances=True,
        by_division_first=True,
    )
    league = Rules(
        sort=(),
        breakers=(_prefer(a1, b1, a2),),
        one_advances=True,
        by_division_first=True,
    )
    ranker = _ranker([[["A1"], ["A2"]], [["B1"]]], MethodRules(division, conference, league))
    # A2 is conference 1's best and B1 beats it for the league. Then A1 and
    # A2, one conference, go by the conference rules.
    assert ranker._order([a1, a2, b1], league) == (b1, a2, a1)


def test_nfl_on_a_real_season():
    lge = real_lge("PNFL-2047-after-super-bowl.lge")
    standings = Standings(lge, method="nfl", seed=0)
    league = names(standings.league())
    assert league[:2] == ("Miami", "Minnesota")
    assert sorted(league) == sorted(names(lge.teams))
    for conference in lge.conferences:
        teams = [team for division in conference.divisions for team in division.teams]
        assert sorted(names(standings.conference(conference))) == sorted(names(teams))
        for division in conference.divisions:
            assert sorted(names(standings.division(division))) == sorted(
                names(division.teams)
            )
```

Append to `tests/unit/fbpro98_standings/test_ranking.py` (add `real_lge` to its `tests.unit.fbpro98_standings.leagues` import and `METHODS` to an `athc.fbpro98_standings.methods` import):

```python
@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize(
    "filename", ["PNFL-before-week1.lge", "PNFL-after-week16.lge"]
)
def test_every_method_on_a_season_not_finished(method, filename):
    # Before week 1 every team is level; after week 16 no playoff game is
    # played. Every request still lists each team once.
    lge = real_lge(filename)
    standings = Standings(lge, method=method, seed=0)
    assert sorted(names(standings.league())) == sorted(names(lge.teams))
    for conference in lge.conferences:
        teams = [team for division in conference.divisions for team in division.teams]
        assert sorted(names(standings.conference(conference))) == sorted(names(teams))
        for division in conference.divisions:
            assert sorted(names(standings.division(division))) == sorted(
                names(division.teams)
            )
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_standings/test_nfl.py tests/unit/fbpro98_standings/test_ranking.py -v --no-cov`
Expected: FAIL with `TypeError: Rules.__init__() got an unexpected keyword argument 'one_advances'`.

- [x] **Step 3: Add the NFL rules**

In `src/athc/fbpro98_standings/methods.py`:

Replace the `Method` line with:

```python
Method = Literal["game", "scheduler", "nfl"]
```

Replace the whole `Rules` class with:

```python
@dataclass(frozen=True, slots=True)
class Rules:
    """How one method orders one kind of standings."""

    sort: tuple[Step, ...]
    """Steps that sort every team, in turn, best first."""

    breakers: tuple[Step, ...]
    """Tie-breakers for the teams level on every sort step."""

    one_advances: bool = False
    """Only the best team of a level group is placed at a time; a step that
    drops some teams sends the rest back to the first tie-breaker (the NFL).
    Otherwise the first tie-breaker that separates a group places its best
    teams, and they and the rest are each ranked again (the game)."""

    by_division_first: bool = False
    """Level teams of one division use the division rules; otherwise only
    each division's best goes on (the NFL's wild-card and draft rules)."""
```

Replace the `RULES` line at the end with:

```python
# The NFL's tiebreaking procedures and draft order, reversed, for league
# standings.
_NFL_DIVISION = Rules(
    sort=(steps.win_percentage,),
    breakers=(
        steps.head_to_head,
        steps.division_percentage,
        steps.common_games(minimum=0),
        steps.conference_percentage,
        steps.strength_of_victory,
        steps.strength_of_schedule(each_opponent_once=False),
        steps.combined_ranking("conference"),
        steps.combined_ranking("league"),
        steps.common_net_points,
        steps.net_points,
    ),
    one_advances=True,
)

NFL = MethodRules(
    division=_NFL_DIVISION,
    # The wild-card steps.
    conference=Rules(
        sort=(steps.win_percentage,),
        breakers=(
            steps.head_to_head_sweep,
            steps.conference_percentage,
            steps.common_games(minimum=4),
            steps.strength_of_victory,
            steps.strength_of_schedule(each_opponent_once=False),
            steps.combined_ranking("conference"),
            steps.combined_ranking("league"),
            steps.conference_net_points,
            steps.net_points,
        ),
        one_advances=True,
        by_division_first=True,
    ),
    # Teams of different conferences: the interconference steps.
    league=Rules(
        sort=(
            steps.playoff_round,
            steps.win_percentage,
            steps.strength_of_schedule(each_opponent_once=False),
        ),
        breakers=(
            steps.head_to_head,
            steps.common_games(minimum=4),
            steps.strength_of_victory,
            steps.combined_ranking("league"),
            steps.net_points,
        ),
        one_advances=True,
        by_division_first=True,
    ),
)

RULES: dict[Method, MethodRules] = {
    "game": GAME,
    "scheduler": SCHEDULER,
    "nfl": NFL,
}
```

- [x] **Step 4: Teach the engine the NFL's way**

In `src/athc/fbpro98_standings/standings.py`, change the import line `from collections.abc import Callable, Iterable, Mapping` to:

```python
from collections.abc import Callable, Iterable, Mapping, Sequence
```

Replace the whole `_break` method of `_Ranker` with these five methods:

```python
    def _break(self, group: list[int], rules: Rules) -> list[int]:
        """Orders one level group: one team at a time (the NFL), or by
        regrouping (the game)."""
        if len(group) == 1:
            return group
        if not rules.one_advances:
            return self._regroup(group, rules)
        ordered: list[int] = []
        rest = list(group)
        while rest:
            best = self._best(rest, rules)
            ordered.append(best)
            rest.remove(best)
        return ordered

    def _regroup(self, group: list[int], rules: Rules) -> list[int]:
        """The first tie-breaker that separates the group places its best
        teams; they and the rest are each ranked again from the first one.
        Level after every tie-breaker: the coin toss."""
        if len(group) == 1:
            return group
        for step in rules.breakers:
            values = step(group, self)
            if values is None:
                continue
            best = max(values.values())
            top = [team for team in group if values[team] == best]
            if len(top) < len(group):
                rest = [team for team in group if values[team] != best]
                return self._regroup(top, rules) + self._regroup(rest, rules)
        return self._toss(group)

    def _best(self, group: list[int], rules: Rules) -> int:
        """The single best team of a level group. A step that drops some teams
        sends the rest back to the first tie-breaker; level after every one,
        the coin toss."""
        candidates = list(group)
        while len(candidates) > 1:
            candidates, narrowed = self._narrow(candidates, rules)
            if narrowed is not rules:
                return self._best(candidates, narrowed)
            for step in rules.breakers:
                values = step(candidates, self)
                if values is None:
                    continue
                best = max(values.values())
                top = [team for team in candidates if values[team] == best]
                if len(top) < len(candidates):
                    candidates = top
                    break
            else:
                return self._toss(candidates)[0]
        return candidates[0]

    def _narrow(self, group: list[int], rules: Rules) -> tuple[list[int], Rules]:
        """The NFL's rule for teams of different divisions. Teams of one
        division use the division rules; in league standings, teams of one
        conference use the conference rules. Otherwise only each division's
        best goes on, and in league standings only each conference's best of
        those."""
        if not rules.by_division_first:
            return group, rules
        season = self.season
        method = self._method
        if len({season.division_of[team] for team in group}) == 1:
            return group, method.division
        conference = method.conference
        if rules is method.league and conference is not None:
            if len({season.conference_of[team] for team in group}) == 1:
                return group, conference
            group = self._best_of_each(group, season.division_of, method.division)
            return self._best_of_each(group, season.conference_of, conference), rules
        return self._best_of_each(group, season.division_of, method.division), rules

    def _best_of_each(
        self, group: list[int], part_of: Sequence[int], rules: Rules
    ) -> list[int]:
        """The best team of each division (or conference) in the group."""
        parts: dict[int, list[int]] = {}
        for team in group:
            parts.setdefault(part_of[team], []).append(team)
        return sorted(self._break(members, rules)[0] for members in parts.values())
```

- [x] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_standings -v --no-cov`
Expected: all passed.

- [x] **Step 6: Fix line endings, lint, type-check**

CRLF fix on the four touched files; `uv run ruff format .`; `uv run ruff check .`; `uv run pyright`. Expected: no errors.

- [x] **Step 7: Commit**

```bash
git add src/athc/fbpro98_standings tests/unit/fbpro98_standings
```

```bash
git commit -m "fbpro98_standings: the NFL method"
```

---

### Task 7: Two seasons on real files

**Files:**
- Test: `tests/unit/fbpro98_standings/test_two_seasons.py`

**Interfaces:**
- Consumes: `Standings`, `StandingsError` (Tasks 1-6). No library change is expected; a failure here is a bug in Tasks 1-6.

- [x] **Step 1: Write the tests**

`tests/unit/fbpro98_standings/test_two_seasons.py`:

```python
"""Tests for Standings with the previous season's file: last season's
results for the current season's divisions and teams."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_standings import Standings, StandingsError
from tests.unit.fbpro98_standings.leagues import names, real_lge

# The 2048 standings file (git dade898^,
# config/release/leagues/PNFL/standings/2048.league.ini): the overall order,
# then each division's finish, in the 2048 file's division order.
OVERALL_2048 = (
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
)
DIVISIONS_2048 = (
    ("Miami", "New England", "Jacksonville", "Buffalo"),
    ("Los Angeles", "Denver", "Las Vegas", "Cincinnati", "Pittsburgh"),
    ("Washington", "Atlanta", "New York", "Philadelphia"),
    ("Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"),
)
MOVES_2048 = {"Baltimore": "Los Angeles"}
MOVES_2047 = {
    "Houston": "Miami",
    "New York A": "Cincinnati",
    "Indianapolis": "Baltimore",
    "New York N": "New York",
}


def test_2047_to_2048_matches_the_2048_standings_file():
    previous = real_lge("PNFL-2047-after-super-bowl.lge")
    current = real_lge("PNFL-2048-after-week1.lge")
    standings = Standings(current, previous, MOVES_2048, method="scheduler", seed=0)
    assert names(standings.league()) == OVERALL_2048
    assert (
        tuple(
            names(standings.division(division))
            for conference in current.conferences
            for division in conference.divisions
        )
        == DIVISIONS_2048
    )


def test_answers_are_the_current_files_teams():
    previous = real_lge("PNFL-2047-after-super-bowl.lge")
    current = real_lge("PNFL-2048-after-week1.lge")
    standings = Standings(current, previous, MOVES_2048, method="scheduler", seed=0)
    assert all(
        any(team is known for known in current.teams) for team in standings.league()
    )


def test_a_team_that_changed_division_brings_its_record():
    # 2047 AFC East: Miami (11-5 as Houston) and Jacksonville (5-11) came from
    # the West; Buffalo (10-6) and New England (3-13) stayed.
    previous = real_lge("PNFL-2046-after-super-bowl.lge")
    current = real_lge("PNFL-2047-after-week1.lge")
    standings = Standings(current, previous, MOVES_2047, method="scheduler", seed=0)
    east = next(
        division
        for conference in current.conferences
        for division in conference.divisions
        if "Miami" in names(division.teams)
    )
    assert names(standings.division(east)) == (
        "Miami",
        "Buffalo",
        "Jacksonville",
        "New England",
    )


def test_a_missing_team_move_is_an_error():
    previous = real_lge("PNFL-2047-after-super-bowl.lge")
    current = real_lge("PNFL-2048-after-week1.lge")
    with pytest.raises(
        StandingsError,
        match=re.escape("Team(s) not in the current file: Baltimore."),
    ):
        Standings(current, previous, method="scheduler")
```

- [x] **Step 2: Run the tests**

Run: `uv run pytest tests/unit/fbpro98_standings/test_two_seasons.py -v --no-cov`
Expected: 4 passed. If one fails, do not touch the expected values: find the bug in Tasks 1-6, fix it there with its own test, or stop and report.

- [x] **Step 3: Fix line endings, lint, type-check**

CRLF fix on the file; `uv run ruff format .`; `uv run ruff check .`; `uv run pyright`. Expected: no errors.

- [x] **Step 4: Commit**

```bash
git add tests/unit/fbpro98_standings/test_two_seasons.py
```

```bash
git commit -m "fbpro98_standings: two seasons on real files"
```

---

### Task 8: Docs and project meta

**Files:**
- Create: `docs/fbpro98_standings/README.md`
- Create: `docs/fbpro98_standings/ARCHITECTURE.md`
- Create: `tests/unit/fbpro98_standings/README.md`
- Modify: `docs/design/architecture.md` (package tree near line 65; library list near line 97)
- Modify: `STATUS.md` (new section after `## fbpro98_profile (library)`)
- Modify: `CHANGELOG.md` (top of the `## athc` list)
- Modify: `WORKLOG.md` (top of the list)

- [x] **Step 1: Write the library README**

`docs/fbpro98_standings/README.md`:

````markdown
# fbpro98-standings

Library that ranks a Front Page Sports Football Pro '98 league's teams from its `.lge` files: division, conference and league standings, by the game's, the scheduler's or the NFL's tie-breakers.

## Features

- Division, conference and league (final) standings, best first
- Three tie-break methods: `game` (the manual's), `scheduler` (generate-schedule's), `nfl` (the NFL's)
- One season, or last season's results for this season's divisions and teams, with team moves for teams whose name changed
- A repeatable coin toss with a seed

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_lge import read_lge
from athc.fbpro98_standings import Standings

current = read_lge("PNFL", league_dir)
standings = Standings(current, method="game")
for conference in current.conferences:
    standings.conference(conference)           # its teams, best first
    for division in conference.divisions:
        standings.division(division)           # its teams, best first
standings.league()                             # every team, final order

previous = read_lge("PNFL", previous_dir)
standings = Standings(
    current, previous, {"Baltimore": "Los Angeles"}, method="scheduler", seed=1
)
```

## API

- `Standings(current, previous=None, team_moves=None, *, method, seed=None)`: standings by one method. With `previous`, last season's results for the current file's divisions and teams; `team_moves` maps a renamed team's previous name to its current one; `seed` repeats the coin toss.
- `Standings.division(division)`, `Standings.conference(conference)`, `Standings.league()`: the current file's teams, best first.
- `Method`: `"game"`, `"scheduler"` or `"nfl"`.
- `StandingsError`: the two files and the team moves do not fit together.
````

- [x] **Step 2: Write the architecture doc**

`docs/fbpro98_standings/ARCHITECTURE.md`:

```markdown
# fbpro98-standings — Architecture

Library that ranks a league's teams from its `.lge` files by one of three tie-break methods.

## Module layout

```
src/athc/fbpro98_standings/
├── __init__.py    # public API: Standings, Method, StandingsError
├── standings.py   # Standings; _Ranker, the one ranking engine
├── methods.py     # each method's steps for division, conference and league standings
├── steps.py       # one function per tie-break step
├── moves.py       # match the previous season's teams to the current season's
├── season.py      # one LgeFile as numbered teams, games and playoff rounds
└── errors.py      # StandingsError
```

## What this package does

- Ranks from the games in the file (regular season for records, playoffs for the playoff round), never from the records the file stores. Exact arithmetic (`Fraction`).
- One engine for every method: sort by the method's first steps, then break each level group with its tie-breakers; teams level after every step get a coin toss.
- Game: the manual's list (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule with each opponent once); conference standings put division winners first; league standings are the draft order reversed (champion, Super Bowl loser, then record and strength of schedule).
- Scheduler: division standings by the game's list; league standings by playoff round, record, strength of schedule (every game), division finish, point differential; conference standings in league order.
- NFL: the NFL's division, wild-card and draft-order steps; one team advances at a time, and teams of different divisions go on only as each division's best.
- With the previous season's file: ranks last season as played, under its own divisions, and answers with the current file's teams; teams match by name plus the team moves.

## What this package does NOT do

- Read files; the caller passes `LgeFile` objects from `fbpro98_lge`.
- Net touchdowns: not in the file, so that step is skipped.
- Know a league's team moves; the caller passes them.

## Testing

- `tests/unit/fbpro98_standings/`: each step on built leagues, each method on built leagues and the PNFL's real files, two seasons, every error. Matrix: [tests/unit/fbpro98_standings/README.md](../../tests/unit/fbpro98_standings/README.md).
```

- [x] **Step 3: Write the test matrix**

`tests/unit/fbpro98_standings/README.md`:

```markdown
# fbpro98_standings — Test Matrix

Cases covered for the standings library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `built` = a league built in code (`leagues.py`); `golden` = a real `.lge` from `tests/unit/fbpro98_lge/data/` or `tests/integration/data/`. Status: ☑ done.

## season.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Teams numbered in file order, with division and conference | built | numbers, divisions, conferences | `test_teams_numbered_in_file_order_with_their_division_and_conference` | ☑ |
| A game counts for both teams | built | both results | `test_a_game_counts_for_both_teams` | ☑ |
| Division and conference games marked | built | flags | `test_games_marked_division_and_conference` | ☑ |
| Won, lost, tied | built | `won` / `lost` | `test_won_and_lost` | ☑ |
| Playoff round reached; champion and runner-up | built | rounds | `test_playoff_round_reached_and_the_final` | ☑ |
| A bye counts by the later round | built | rounds | `test_a_bye_counts_by_the_later_round` | ☑ |
| No champion before the final | built | None | `test_no_champion_before_the_final_is_played` | ☑ |
| Real season | golden | 18 teams, 16 games, Miami over Minnesota | `test_real_season` | ☑ |

## steps.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Percentage: tie half a win, no game 0 | built | 3/4, 0 | `test_percentage_counts_a_tie_as_half_a_win_and_no_game_as_zero` | ☑ |
| W-L-T % | built | values | `test_win_percentage_counts_every_game` | ☑ |
| Head-to-head among the level teams only | built | values | `test_head_to_head_counts_only_games_among_the_level_teams` | ☑ |
| Sweep: two teams, beat all, lost to all, cycle, not all played | built | values / None | `test_sweep_*`, `test_no_sweep_*` | ☑ |
| Division and conference % | built | values | `test_division_and_conference_percentage` | ☑ |
| Net points: division, conference, all | built | values | `test_net_points_by_kind_of_game` | ☑ |
| Common games: four accepted, three skipped | built | values / None | `test_common_games_at_the_minimum_apply`, `test_common_games_one_short_of_the_minimum_skipped` | ☑ |
| Net points in common games | built | values | `test_common_net_points` | ☑ |
| Strength of victory, every win | built | 2/9 | `test_strength_of_victory_counts_every_win` | ☑ |
| Strength of schedule, each opponent once or every game | built | 1/6, 2/9 | `test_strength_of_schedule_each_opponent_once_or_every_game` | ☑ |
| Combined ranking, conference and league, shared ranks | built | values | `test_combined_ranking_within_the_conference_or_the_league` | ☑ |
| Division finish: one division, different divisions | built | values / None | `test_division_finish_*` | ☑ |
| Playoff round; champion then runner-up | built | values | `test_playoff_round_and_champion_then_runner_up` | ☑ |

## moves.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Match by name wherever a team moved | built | numbers | `test_teams_match_by_name_wherever_they_moved` | ☑ |
| A renamed team | built | numbers | `test_a_team_move_matches_a_renamed_team` | ☑ |
| Two teams swap names | built | numbers | `test_team_moves_may_swap_names` | ☑ |
| Repeated name, bad move, missing or extra team | built | `StandingsError` | `test_mismatch_rejected` `[P]` | ☑ |

## standings.py and the methods

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Regroup: placed teams and the rest ranked again | built | A, B, C | `test_regroup_ranks_the_placed_teams_and_the_rest_again` | ☑ |
| Coin toss: a seed repeats it, request order does not matter, answers kept | built | equal orders | `test_a_seed_repeats_the_coin_toss`, `test_the_coin_toss_does_not_depend_on_what_was_asked_before`, `test_without_a_seed_the_same_question_gets_the_same_answer` | ☑ |
| Caller mistakes | built | `ValueError` | `test_unknown_method_rejected`, `test_team_moves_need_the_previous_file`, `test_a_division_of_another_file_rejected`, `test_a_conference_of_another_file_rejected` | ☑ |
| Empty division; teams that look alike | built | `()`; by position | `test_an_empty_division_has_no_standings`, `test_teams_that_look_alike_stay_apart` | ☑ |
| Every method before week 1 and before the playoffs | golden | each team once | `test_every_method_on_a_season_not_finished` `[P]` | ☑ |
| Game: division standings as the game shows them | golden | 2043, 2046, 2048 orders | `test_game_division_standings_match_the_game` `[P]` | ☑ |
| Game: conference standings, division winners first | golden | 2047 orders | `test_game_conference_standings_put_division_winners_first` | ☑ |
| Game: regroup after a step places one team | built | T1, T2, T3 | `test_game_ranks_the_placed_teams_and_the_rest_again` | ☑ |
| Game: league standings | built | orders | `test_game_league_*` | ☑ |
| Game: league without divisions | built | winner first | `test_game_conference_without_divisions` | ☑ |
| Scheduler: league standings as the 2048 and 2047 standings files | golden | orders | `test_scheduler_league_matches_the_2048_standings_file`, `test_scheduler_league_breaks_a_division_tie_on_division_finish` | ☑ |
| Scheduler: division finish skipped across divisions, or over point differential | built | orders | `test_scheduler_division_finish_*` | ☑ |
| Scheduler: conference in league order | golden | orders | `test_scheduler_conference_standings_follow_the_league_order` | ☑ |
| NFL: one team advances; each division's and conference's best | built | orders | `test_nfl_sends_the_teams_a_step_dropped_back_to_the_first_tie_breaker`, `test_nfl_conference_keeps_only_each_divisions_best`, `test_nfl_league_keeps_each_divisions_then_each_conferences_best` | ☑ |
| NFL: real season | golden | Miami, Minnesota first; each team once | `test_nfl_on_a_real_season` | ☑ |
| Two seasons: 2047 -> 2048 as the 2048 standings file; current teams; a team that changed division; a missing move | golden | orders, error | `test_two_seasons.py` | ☑ |
```

- [x] **Step 4: Update the architecture doc**

In `docs/design/architecture.md`, in the `# LIBRARIES` part of the package tree, after the `fbpro98_profile/` line, add:

```
    fbpro98_standings/         py.typed  standings.py  methods.py  steps.py  moves.py  season.py
```

In the library docs list, after `- [fbpro98_profile](../fbpro98_profile/README.md)`, add:

```markdown
- [fbpro98_standings](../fbpro98_standings/README.md)
```

- [x] **Step 5: Update STATUS, CHANGELOG, WORKLOG**

`STATUS.md`: after the `## fbpro98_profile (library)` section and before `## gameplan`, add:

```markdown
## fbpro98_standings (library)

Ranks a league's teams from its `.lge` files: division, conference and league
standings by the game's, the scheduler's or the NFL's tie-breakers. Docs:
[README](docs/fbpro98_standings/README.md)

- One season, or last season's results for this season's divisions and
  teams, with team moves for teams whose name changed; a seeded coin toss.
- Library in, with unit tests. Nothing uses it yet: `fbpro98_lge` and
  `generate-schedule` keep their own ranking for now.
```

`CHANGELOG.md`: as the first line of the `## athc` list, add:

```markdown
- fbpro98_standings: new library that ranks division, conference and league standings from `.lge` files by the game's, the scheduler's or the NFL's tie-breakers
```

`WORKLOG.md`: as the first entry of the list, add (the date from `date +%F`):

```markdown
- <date> — **fbpro98_standings**: tie-breaking moved toward its own library,
  since it is a game rule and not part of the file format. One engine ranks
  for three methods (the game's, generate-schedule's, the NFL's), from one
  season or from last season's results for this season's divisions, with
  team moves for renamed teams and a seeded coin toss. Nothing uses it yet.
```

- [x] **Step 6: Fix line endings**

CRLF fix on the seven files of this task.

- [x] **Step 7: Run every check**

Run each, one per call:
`uv run pytest`
`uv run ruff check .`
`uv run ruff format .`
`uv run pyright`
Expected: all green, coverage at or above 92%.

- [x] **Step 8: Commit**

```bash
git add docs/fbpro98_standings tests/unit/fbpro98_standings/README.md docs/design/architecture.md STATUS.md CHANGELOG.md WORKLOG.md
```

```bash
git commit -m "fbpro98_standings: docs, status and changelog"
```

- [x] **Step 9: Mark the spec and plan done**

In `docs/superpowers/specs/2026-10-13-fbpro98-standings-design.md`, change the status line to `Status: implemented.`; in this plan, tick every step. CRLF fix on both, then:

```bash
git add docs/superpowers
```

```bash
git commit -m "fbpro98_standings: spec and plan done"
```

Then report back and stop; do not merge.
