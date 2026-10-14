# standings command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `athc standings` shows a league's standings as played so far, in four views: the game's standings screen and ESPN's League, Conference and Division tabs.

**Architecture:** A Click leaf command (`src/athc/cli/standings.py`) reads the league's `.lge` with `fbpro98_lge`, ranks it with the `fbpro98_standings` library, and prints lines built by a new Click-free tool package, `src/athc/standings/`: `records.py` computes each team's row values from the regular-season games, `views.py` lays the rows out as text.

**Tech Stack:** Python 3.13, Click, Rich console (`athc.console`), pytest with CliRunner.

**Spec:** `docs/superpowers/specs/2026-10-13-standings-command-design.md`

## Global Constraints

- Usage line: `athc standings [-h] [--view game|league|conference|division] [--method scheduler|game|nfl] [--league name]`.
- Defaults: `--view game`, `--method scheduler`.
- Reads `<league>.lge` from the league's `path` in league.toml.
- Exit 0; 2 on any error (no league, no `path`, missing or broken `.lge`, bad option).
- Every value counts regular-season games only.
- Unnamed conference: `AFC` (first), `NFC` (second). Division header: conference and division names in capitals, `AFC EAST`.
- Team name: `Team.name` in the game view; `Team.official_name` (name and nickname) in the ESPN views.
- Plain text, no borders; names left-aligned, numbers right-aligned; each column as wide as its widest entry.
- Every text file is UTF-8 with CRLF line endings and a final newline. Before each commit, convert every file the task wrote, one call per file: `uv run python -c "import pathlib, sys; p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding='utf-8').replace('\r\n', '\n'); p.write_bytes(t.replace('\n', '\r\n').encode('utf-8'))" <file>`. Never `sed -i` (it strips CRLF).
- One command per call, never chained: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`.
- Commit messages: one line, prefixed `standings:`, no mention of any AI tool, no trailers.

## Plan decision

- The command passes a fixed coin-toss seed (`seed=0`) to `Standings`, so the same league file always shows the same order. The spec is silent on the coin toss; a viewer showing a different order on each run of the same file would read as a bug, and the goldens need a stable order.

## Review Focus

1. A file before week 1 (no games): every row reads 0, `.000`, `0-0`, DIFF `0`, STRK `-`, and the command exits 0. Test: Task 3 `test_before_week_one_shows_every_team_at_zero`.
2. Teams level after every tie-breaker (any early-season file): the order is the same on every run. Test: Task 3 `test_same_file_same_order` (before week 1 every team is level, so the coin decides every place).
3. A file after the Super Bowl: playoff games never count in W, L, T, the splits, points or the streak. Tests: Task 1 `test_playoff_games_not_counted` and the after-Super-Bowl file in `test_rows_match_the_file_records`.
4. A team name wider than every header: the column widens and every other line still lines up. Test: Task 2 view tests (`Seattle Seahawks` is the widest entry).
5. A one-conference league (the 8-12 team stock leagues): the game view is a single column with no gap. Test: Task 2 `test_game_view_one_conference`.

---

### Task 1: Each team's row values (`records.py`)

**Files:**
- Create: `src/athc/standings/__init__.py`
- Create: `src/athc/standings/records.py`
- Test: `tests/unit/standings/test_records.py`
- Create: `tests/unit/standings/README.md`

**Interfaces:**
- Consumes: `athc.fbpro98_lge.LgeFile`, `Team` (`LgeFile.conferences`, `.weeks`, `.teams`; `Game.home`, `.home_score`, `.away`, `.away_score`).
- Produces:
  - `Split(wins: int, losses: int, ties: int)` — frozen dataclass.
  - `Row(team: Team, overall: Split, home: Split, away: Split, division: Split, conference: Split, points_for: int, points_against: int, streak: str)` — frozen dataclass.
  - `rows_of(lge: LgeFile) -> dict[int, Row]` — keyed by `id(team)`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/standings/test_records.py`:

```python
"""Each team's standings row from the regular-season games."""

from __future__ import annotations

import pytest

from athc.fbpro98_lge import LgeFile
from athc.standings import Row, Split, rows_of
from tests.unit.fbpro98_standings.leagues import build_league, real_lge, win

# A and B share a division; C is in A's conference, another division; D is in
# the other conference.
SHAPE = [[["A", "B"], ["C"]], [["D"]]]


def _row(lge: LgeFile, name: str) -> Row:
    team = next(team for team in lge.teams if team.name == name)
    return rows_of(lge)[id(team)]


def test_overall_counts_wins_losses_and_ties() -> None:
    lge = build_league(SHAPE, [win("A", "B"), ("A", 10, "C", 10), win("D", "A")])
    assert _row(lge, "A").overall == Split(1, 1, 1)


def test_home_and_away() -> None:
    # win() puts the winner at home: A wins at home, then loses at C.
    lge = build_league(SHAPE, [win("A", "B"), win("C", "A")])
    row = _row(lge, "A")
    assert row.home == Split(1, 0, 0)
    assert row.away == Split(0, 1, 0)


def test_division_and_conference() -> None:
    lge = build_league(SHAPE, [win("A", "B"), win("C", "A"), win("A", "D")])
    row = _row(lge, "A")
    assert row.division == Split(1, 0, 0)  # B only
    assert row.conference == Split(1, 1, 0)  # B and C, never D


def test_points_for_and_against() -> None:
    lge = build_league(SHAPE, [("A", 24, "B", 17), ("C", 30, "A", 3)])
    row = _row(lge, "A")
    assert (row.points_for, row.points_against) == (27, 47)


@pytest.mark.parametrize(
    ("games", "streak"),
    [
        ([win("B", "A"), win("A", "B"), win("A", "C")], "W2"),
        ([win("A", "B"), win("B", "A"), win("C", "A")], "L2"),
        ([win("A", "B"), ("A", 10, "C", 10)], "-"),
        ([win("A", "B"), ("A", 10, "C", 10), win("A", "D")], "W1"),
        ([], "-"),
    ],
    ids=["wins", "losses", "tie last", "tie ends the run", "no games"],
)
def test_streak(games: list[tuple[str, int, str, int]], streak: str) -> None:
    lge = build_league(SHAPE, games)
    assert _row(lge, "A").streak == streak


def test_playoff_games_not_counted() -> None:
    lge = build_league(SHAPE, [win("B", "A")], playoffs=[[win("A", "D")]])
    row = _row(lge, "A")
    assert row.overall == Split(0, 1, 0)
    assert (row.points_for, row.points_against) == (10, 20)
    assert row.streak == "L1"


def test_every_team_has_a_row() -> None:
    lge = build_league(SHAPE)
    assert {id(team) for team in lge.teams} == set(rows_of(lge))


@pytest.mark.parametrize(
    "filename",
    [
        "PNFL-2048-after-week16.lge",
        "PNFL-after-super-bowl.lge",
        "PNFL-before-week1.lge",
        "NFLPI97R.LGE",
    ],
)
def test_rows_match_the_file_records(filename: str) -> None:
    """The reader's own records count the same regular-season games."""
    lge = real_lge(filename)
    rows = rows_of(lge)
    for team in lge.teams:
        row = rows[id(team)]
        record = team.record
        assert (
            row.overall.wins,
            row.overall.losses,
            row.overall.ties,
            row.points_for,
            row.points_against,
        ) == (
            record.wins,
            record.losses,
            record.ties,
            record.points_for,
            record.points_against,
        ), team.name
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/standings/test_records.py -v --no-cov`
Expected: FAIL at collection, `ModuleNotFoundError: No module named 'athc.standings'`.

- [ ] **Step 3: Write the implementation**

`src/athc/standings/__init__.py`:

```python
"""Show a league's standings as text: the game's standings screen, and
ESPN's League, Conference and Division tabs."""

from athc.standings.records import Row, Split, rows_of

__all__ = ["Row", "Split", "rows_of"]
```

`src/athc/standings/records.py`:

```python
"""Each team's standings row, from one league file's regular-season games."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from athc.fbpro98_lge import LgeFile, Team


@dataclass(frozen=True, slots=True)
class Split:
    """Wins, losses and ties in some of a team's games."""

    wins: int
    losses: int
    ties: int


@dataclass(frozen=True, slots=True)
class Row:
    """One team's standings values, from its regular-season games."""

    team: Team
    overall: Split
    home: Split
    away: Split
    division: Split
    """Against the team's own division."""

    conference: Split
    """Against the team's own conference."""

    points_for: int
    points_against: int
    streak: str
    """`W3`, `L2`: the run of wins or losses ending with the latest game; `-`
    when the latest game was a tie or none was played."""


@dataclass(frozen=True, slots=True)
class _Game:
    """One played regular-season game, from one team's side."""

    scored: int
    allowed: int
    home: bool
    division: bool
    conference: bool


def rows_of(lge: LgeFile) -> dict[int, Row]:
    """Each team's row, keyed by `id(team)`: teams are found by identity, so
    two teams that look the same never mix."""
    division_of: dict[int, int] = {}
    conference_of: dict[int, int] = {}
    division_number = 0
    for conference_number, conference in enumerate(lge.conferences):
        for division in conference.divisions:
            for team in division.teams:
                division_of[id(team)] = division_number
                conference_of[id(team)] = conference_number
            division_number += 1
    games: dict[int, list[_Game]] = {id(team): [] for team in lge.teams}
    for week in lge.weeks:
        for game in week:
            home, away = id(game.home), id(game.away)
            division = division_of[home] == division_of[away]
            conference = conference_of[home] == conference_of[away]
            games[home].append(
                _Game(
                    scored=game.home_score,
                    allowed=game.away_score,
                    home=True,
                    division=division,
                    conference=conference,
                )
            )
            games[away].append(
                _Game(
                    scored=game.away_score,
                    allowed=game.home_score,
                    home=False,
                    division=division,
                    conference=conference,
                )
            )
    return {id(team): _row(team, games[id(team)]) for team in lge.teams}


def _row(team: Team, games: list[_Game]) -> Row:
    return Row(
        team=team,
        overall=_split(games),
        home=_split(game for game in games if game.home),
        away=_split(game for game in games if not game.home),
        division=_split(game for game in games if game.division),
        conference=_split(game for game in games if game.conference),
        points_for=sum(game.scored for game in games),
        points_against=sum(game.allowed for game in games),
        streak=_streak(games),
    )


def _split(games: Iterable[_Game]) -> Split:
    wins = losses = ties = 0
    for game in games:
        if game.scored > game.allowed:
            wins += 1
        elif game.scored < game.allowed:
            losses += 1
        else:
            ties += 1
    return Split(wins, losses, ties)


def _streak(games: list[_Game]) -> str:
    # The games are in week order, so the latest is last.
    if not games or games[-1].scored == games[-1].allowed:
        return "-"
    won = games[-1].scored > games[-1].allowed
    run = 0
    for game in reversed(games):
        if game.scored == game.allowed or (game.scored > game.allowed) != won:
            break
        run += 1
    return f"{'W' if won else 'L'}{run}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/standings/test_records.py -v --no-cov`
Expected: PASS, 15 tests.

- [ ] **Step 5: Write the test matrix**

`tests/unit/standings/README.md`:

```markdown
# standings — Test Matrix

Cases covered for the standings command's tool package. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `built` = a league built in code; `golden` = a real `.lge` from `tests/unit/fbpro98_lge/data/`. Status: ☑ done.

## records.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Overall wins, losses, ties | built | 1-1-1 | `test_overall_counts_wins_losses_and_ties` | ☑ |
| Home and away | built | home 1-0, away 0-1 | `test_home_and_away` | ☑ |
| Division and conference | built | division 1-0, conference 1-1 | `test_division_and_conference` | ☑ |
| Points for and against | built | 27, 47 | `test_points_for_and_against` | ☑ |
| Streak: wins, losses, tie last, tie ends the run, no games | built | `W2`, `L2`, `-`, `W1`, `-` | `test_streak` `[P]` | ☑ |
| Playoff games not counted | built | regular season only | `test_playoff_games_not_counted` | ☑ |
| Every team has a row | built | one per team | `test_every_team_has_a_row` | ☑ |
| Rows match the file's own records | golden | W, L, T, PF, PA equal `Team.record` | `test_rows_match_the_file_records` `[P]` | ☑ |
```

- [ ] **Step 6: Commit**

Convert the four files this task wrote to CRLF (Global Constraints command), then:

```bash
git add src/athc/standings tests/unit/standings
git commit -m "standings: each team's row values"
```

---

### Task 2: The four views (`views.py`)

**Files:**
- Create: `src/athc/standings/views.py`
- Modify: `src/athc/standings/__init__.py`
- Test: `tests/unit/standings/test_views.py`
- Modify: `tests/unit/standings/README.md`

**Interfaces:**
- Consumes: `Row`, `Split`, `rows_of` (Task 1); `athc.fbpro98_standings.Standings` (`division(d)`, `conference(c)`, `league()`, each `tuple[Team, ...]`).
- Produces:
  - `View = Literal["game", "league", "conference", "division"]`, `VIEWS: tuple[View, ...]`.
  - `render(view: View, lge: LgeFile, standings: Standings, league: str) -> list[str]`.
  - `percentage(split: Split) -> str`, `record(split: Split) -> str`, `difference(points_for: int, points_against: int) -> str`.

- [ ] **Step 1: Write the failing tests**

The league below has every team at a different W-L-T %, so no tie-breaker is reached and the scheduler's order is plain W-L-T %: league Miami, Denver, Seattle, Buffalo, Dallas, Chicago; AFC Miami, Denver, Buffalo; NFC Seattle, Dallas, Chicago (the scheduler's conference standings are the league order). Hand-worked rows:

| Team | W-L-T | PCT | HOME | AWAY | DIV | CONF | PF | PA | DIFF | STRK |
|---|---|---|---|---|---|---|---|---|---|---|
| Miami Dolphins | 3-0-0 | 1.000 | 2-0 | 1-0 | 1-0 | 1-0 | 75 | 44 | +31 | W3 |
| Denver Broncos | 1-0-1 | .750 | 1-0 | 0-0-1 | 0-0 | 0-0 | 24 | 13 | +11 | - |
| Seattle Seahawks | 2-1-0 | .667 | 2-0 | 0-1 | 1-0 | 1-0 | 64 | 56 | +8 | W1 |
| Buffalo Bills | 2-2-0 | .500 | 1-0 | 1-2 | 0-1 | 0-1 | 81 | 60 | +21 | W1 |
| Dallas Cowboys | 0-1-1 | .250 | 0-0-1 | 0-1 | 0-0 | 0-0 | 23 | 30 | -7 | - |
| Chicago Bears | 0-4-0 | .000 | 0-2 | 0-2 | 0-1 | 0-1 | 26 | 90 | -64 | L4 |

`tests/unit/standings/test_views.py`:

```python
"""The four standings views, on a small league built in code."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from athc.fbpro98_lge import Conference, Division, Game, LgeFile, Record, Team
from athc.fbpro98_standings import Standings
from athc.standings import Split, View, difference, percentage, record, render

NO_GAMES = Record(0, 0, 0, 0, 0)

# Conference name -> division name -> teams as (name, nickname).
Shape = Sequence[tuple[str, Sequence[tuple[str, Sequence[tuple[str, str]]]]]]
# Home team, home score, away team, away score, by team name.
Played = tuple[str, int, str, int]


def _league(shape: Shape, games: Sequence[Played] = ()) -> LgeFile:
    """One regular-season week per game."""
    teams = {
        name: Team(name=name, nickname=nickname, record=NO_GAMES)
        for _, divisions in shape
        for _, members in divisions
        for name, nickname in members
    }
    conferences: list[Conference] = []
    for conference_name, divisions in shape:
        built: list[Division] = []
        for division_name, members in divisions:
            in_division = tuple(teams[name] for name, _ in members)
            built.append(Division(division_name, in_division, in_division))
        in_conference = tuple(team for division in built for team in division.teams)
        conferences.append(Conference(conference_name, tuple(built), in_conference))
    weeks = tuple(
        (Game(teams[home], home_score, teams[away], away_score),)
        for home, home_score, away, away_score in games
    )
    return LgeFile(conferences=tuple(conferences), weeks=weeks)


# Two unnamed conferences; each has one two-team division and one one-team
# division, in opposite order, so the game view pads the shorter block.
SHAPE: Shape = [
    (
        "",
        [
            ("East", [("Miami", "Dolphins"), ("Buffalo", "Bills")]),
            ("West", [("Denver", "Broncos")]),
        ],
    ),
    (
        "",
        [
            ("East", [("Dallas", "Cowboys")]),
            ("West", [("Seattle", "Seahawks"), ("Chicago", "Bears")]),
        ],
    ),
]
GAMES: list[Played] = [
    ("Miami", 24, "Buffalo", 17),
    ("Chicago", 7, "Miami", 21),
    ("Seattle", 27, "Chicago", 10),
    ("Buffalo", 20, "Dallas", 13),
    ("Denver", 14, "Chicago", 3),
    ("Miami", 30, "Seattle", 20),
    ("Seattle", 17, "Buffalo", 16),
    ("Chicago", 6, "Buffalo", 28),
    ("Dallas", 10, "Denver", 10),
]
HEADER = "W  L  T    PCT   HOME   AWAY  DIV  CONF  PF  PA  DIFF  STRK"


def _render(view: View, lge: LgeFile | None = None) -> list[str]:
    lge = lge or _league(SHAPE, GAMES)
    return render(view, lge, Standings(lge, method="scheduler"), "PNFL")


def test_game_view() -> None:
    assert _render("game") == [
        "AFC EAST  W  L  T  PF  PA    NFC EAST  W  L  T  PF  PA",
        "Miami     3  0  0  75  44    Dallas    0  1  1  23  30",
        "Buffalo   2  2  0  81  60",
        "",
        "AFC WEST  W  L  T  PF  PA    NFC WEST  W  L  T  PF  PA",
        "Denver    1  0  1  24  13    Seattle   2  1  0  64  56",
        " " * 29 + "Chicago   0  4  0  26  90",
    ]


def test_league_view() -> None:
    assert _render("league") == [
        "PNFL",
        " " * 21 + HEADER,
        "1  Miami Dolphins    3  0  0  1.000    2-0    1-0  1-0   1-0  75  44   +31    W3",
        "2  Denver Broncos    1  0  1   .750    1-0  0-0-1  0-0   0-0  24  13   +11     -",
        "3  Seattle Seahawks  2  1  0   .667    2-0    0-1  1-0   1-0  64  56    +8    W1",
        "4  Buffalo Bills     2  2  0   .500    1-0    1-2  0-1   0-1  81  60   +21    W1",
        "5  Dallas Cowboys    0  1  1   .250  0-0-1    0-1  0-0   0-0  23  30    -7     -",
        "6  Chicago Bears     0  4  0   .000    0-2    0-2  0-1   0-1  26  90   -64    L4",
    ]


def test_conference_view() -> None:
    assert _render("conference") == [
        "AFC",
        " " * 21 + HEADER,
        "1  Miami Dolphins    3  0  0  1.000    2-0    1-0  1-0   1-0  75  44   +31    W3",
        "2  Denver Broncos    1  0  1   .750    1-0  0-0-1  0-0   0-0  24  13   +11     -",
        "3  Buffalo Bills     2  2  0   .500    1-0    1-2  0-1   0-1  81  60   +21    W1",
        "",
        "NFC",
        " " * 21 + HEADER,
        "1  Seattle Seahawks  2  1  0   .667    2-0    0-1  1-0   1-0  64  56    +8    W1",
        "2  Dallas Cowboys    0  1  1   .250  0-0-1    0-1  0-0   0-0  23  30    -7     -",
        "3  Chicago Bears     0  4  0   .000    0-2    0-2  0-1   0-1  26  90   -64    L4",
    ]


def test_division_view() -> None:
    assert _render("division") == [
        "AFC",
        "AFC EAST          " + HEADER,
        "Miami Dolphins    3  0  0  1.000    2-0    1-0  1-0   1-0  75  44   +31    W3",
        "Buffalo Bills     2  2  0   .500    1-0    1-2  0-1   0-1  81  60   +21    W1",
        "AFC WEST          " + HEADER,
        "Denver Broncos    1  0  1   .750    1-0  0-0-1  0-0   0-0  24  13   +11     -",
        "",
        "NFC",
        "NFC EAST          " + HEADER,
        "Dallas Cowboys    0  1  1   .250  0-0-1    0-1  0-0   0-0  23  30    -7     -",
        "NFC WEST          " + HEADER,
        "Seattle Seahawks  2  1  0   .667    2-0    0-1  1-0   1-0  64  56    +8    W1",
        "Chicago Bears     0  4  0   .000    0-2    0-2  0-1   0-1  26  90   -64    L4",
    ]


def test_game_view_one_conference() -> None:
    """A named conference keeps its name; one conference is one column."""
    lge = _league([("Big", [("North", [("A", "")]), ("South", [("B", "")])])])
    assert _render("game", lge) == [
        "BIG NORTH  W  L  T  PF  PA",
        "A          0  0  0   0   0",
        "",
        "BIG SOUTH  W  L  T  PF  PA",
        "B          0  0  0   0   0",
    ]


@pytest.mark.parametrize(
    ("split", "text"),
    [
        (Split(0, 0, 0), ".000"),
        (Split(0, 3, 0), ".000"),
        (Split(1, 1, 0), ".500"),
        (Split(0, 0, 1), ".500"),
        (Split(2, 1, 0), ".667"),
        (Split(3, 0, 0), "1.000"),
    ],
    ids=["no games", "no wins", "half", "a tie is half a win", "rounded", "all wins"],
)
def test_percentage(split: Split, text: str) -> None:
    assert percentage(split) == text


@pytest.mark.parametrize(
    ("split", "text"),
    [(Split(2, 1, 0), "2-1"), (Split(0, 1, 1), "0-1-1"), (Split(0, 0, 0), "0-0")],
    ids=["no ties", "ties", "no games"],
)
def test_record(split: Split, text: str) -> None:
    assert record(split) == text


@pytest.mark.parametrize(
    ("points_for", "points_against", "text"),
    [(164, 141, "+23"), (104, 112, "-8"), (10, 10, "0")],
    ids=["ahead", "behind", "even"],
)
def test_difference(points_for: int, points_against: int, text: str) -> None:
    assert difference(points_for, points_against) == text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/standings/test_views.py -v --no-cov`
Expected: FAIL at collection, `ImportError: cannot import name 'difference' from 'athc.standings'`.

- [ ] **Step 3: Write the implementation**

`src/athc/standings/views.py`:

```python
"""The standings views as lines of text: the game's standings screen, and
ESPN's League, Conference and Division tabs."""

from __future__ import annotations

from collections.abc import Container, Sequence
from typing import Literal, get_args

from athc.fbpro98_lge import Conference, Division, LgeFile, Team
from athc.fbpro98_standings import Standings
from athc.standings.records import Row, Split, rows_of

View = Literal["game", "league", "conference", "division"]
VIEWS: tuple[View, ...] = get_args(View)

# What the game's standings screen shows for a conference the file leaves
# unnamed, as PNFL's does.
_UNNAMED = ("AFC", "NFC")
_GAME_COLUMNS = tuple("W L T PF PA".split())
_ESPN_COLUMNS = tuple("W L T PCT HOME AWAY DIV CONF PF PA DIFF STRK".split())
_SEP = "  "  # between columns
_GAP = "    "  # between the game view's conference columns

# One line of a view: its cells, or a plain string (a title or a blank line).
_Line = str | list[str]


def render(view: View, lge: LgeFile, standings: Standings, league: str) -> list[str]:
    """The view's lines; `league` is the league's name, the league view's
    title."""
    rows = rows_of(lge)
    names = [
        conference.name or _UNNAMED[index]
        for index, conference in enumerate(lge.conferences)
    ]
    match view:
        case "game":
            return _game(lge, standings, rows, names)
        case "league":
            return _league(standings, rows, league)
        case "conference":
            return _conference(lge, standings, rows, names)
        case "division":
            return _division(lge, standings, rows, names)


def percentage(split: Split) -> str:
    """(W + T / 2) / games to three decimals, no leading zero below one:
    `.800`, `1.000`; `.000` before any game."""
    games = split.wins + split.losses + split.ties
    if not games:
        return ".000"
    return f"{(split.wins + split.ties / 2) / games:.3f}".removeprefix("0")


def record(split: Split) -> str:
    """`2-1`, or `0-1-1` with ties."""
    text = f"{split.wins}-{split.losses}"
    return f"{text}-{split.ties}" if split.ties else text


def difference(points_for: int, points_against: int) -> str:
    """Points for minus points against, signed: `+23`, `-8`, `0`."""
    value = points_for - points_against
    return f"{value:+d}" if value else "0"


def _game(
    lge: LgeFile, standings: Standings, rows: dict[int, Row], names: list[str]
) -> list[str]:
    columns = [
        _game_column(name, conference, standings, rows)
        for name, conference in zip(names, lge.conferences, strict=True)
    ]
    return _side_by_side(columns)


def _game_column(
    name: str, conference: Conference, standings: Standings, rows: dict[int, Row]
) -> list[list[str]]:
    """One conference's divisions, a block of lines each, aligned together."""
    lines: list[_Line] = []
    sizes: list[int] = []
    for division in conference.divisions:
        teams = standings.division(division)
        lines.append([_header(name, division), *_GAME_COLUMNS])
        for team in teams:
            row = rows[id(team)]
            overall = row.overall
            lines.append(
                [
                    team.name,
                    str(overall.wins),
                    str(overall.losses),
                    str(overall.ties),
                    str(row.points_for),
                    str(row.points_against),
                ]
            )
        sizes.append(len(teams) + 1)
    aligned = _aligned(lines, left={0})
    blocks: list[list[str]] = []
    start = 0
    for size in sizes:
        blocks.append(aligned[start : start + size])
        start += size
    return blocks


def _side_by_side(columns: list[list[list[str]]]) -> list[str]:
    """Each conference's blocks down its own column, block N of every column
    starting on the same line, a blank line between."""
    widths = [
        max(len(line) for block in column for line in block) for column in columns
    ]
    lines: list[str] = []
    for index in range(max(len(column) for column in columns)):
        if index:
            lines.append("")
        blocks = [column[index] if index < len(column) else [] for column in columns]
        for number in range(max(len(block) for block in blocks)):
            cells = [
                (block[number] if number < len(block) else "").ljust(width)
                for block, width in zip(blocks, widths, strict=True)
            ]
            lines.append(_GAP.join(cells).rstrip())
    return lines


def _league(standings: Standings, rows: dict[int, Row], league: str) -> list[str]:
    lines: list[_Line] = [league, ["", "", *_ESPN_COLUMNS]]
    lines += _numbered(standings.league(), rows)
    return _aligned(lines, left={1})


def _conference(
    lge: LgeFile, standings: Standings, rows: dict[int, Row], names: list[str]
) -> list[str]:
    lines: list[_Line] = []
    for index, (name, conference) in enumerate(
        zip(names, lge.conferences, strict=True)
    ):
        if index:
            lines.append("")
        lines += [name, ["", "", *_ESPN_COLUMNS]]
        lines += _numbered(standings.conference(conference), rows)
    return _aligned(lines, left={1})


def _division(
    lge: LgeFile, standings: Standings, rows: dict[int, Row], names: list[str]
) -> list[str]:
    lines: list[_Line] = []
    for index, (name, conference) in enumerate(
        zip(names, lge.conferences, strict=True)
    ):
        if index:
            lines.append("")
        lines.append(name)
        for division in conference.divisions:
            lines.append([_header(name, division), *_ESPN_COLUMNS])
            lines += [
                [team.official_name, *_espn_cells(rows[id(team)])]
                for team in standings.division(division)
            ]
    return _aligned(lines, left={0})


def _numbered(teams: Sequence[Team], rows: dict[int, Row]) -> list[_Line]:
    return [
        [str(number), team.official_name, *_espn_cells(rows[id(team)])]
        for number, team in enumerate(teams, 1)
    ]


def _espn_cells(row: Row) -> list[str]:
    overall = row.overall
    return [
        str(overall.wins),
        str(overall.losses),
        str(overall.ties),
        percentage(overall),
        record(row.home),
        record(row.away),
        record(row.division),
        record(row.conference),
        str(row.points_for),
        str(row.points_against),
        difference(row.points_for, row.points_against),
        row.streak,
    ]


def _header(conference: str, division: Division) -> str:
    """`AFC EAST`: the conference and division names in capitals."""
    return " ".join(part for part in (conference, division.name) if part).upper()


def _aligned(lines: Sequence[_Line], left: Container[int]) -> list[str]:
    """Plain strings as they are; cell lines in columns as wide as their
    widest entry across every cell line, the columns in `left` left-aligned,
    the rest right-aligned."""
    tables = [line for line in lines if isinstance(line, list)]
    widths = [
        max(len(cells[column]) for cells in tables) for column in range(len(tables[0]))
    ]
    out: list[str] = []
    for line in lines:
        if isinstance(line, str):
            out.append(line)
            continue
        cells = [
            cell.ljust(width) if column in left else cell.rjust(width)
            for column, (cell, width) in enumerate(zip(line, widths, strict=True))
        ]
        out.append(_SEP.join(cells).rstrip())
    return out
```

`src/athc/standings/__init__.py` becomes:

```python
"""Show a league's standings as text: the game's standings screen, and
ESPN's League, Conference and Division tabs."""

from athc.standings.records import Row, Split, rows_of
from athc.standings.views import VIEWS, View, difference, percentage, record, render

__all__ = [
    "VIEWS",
    "Row",
    "Split",
    "View",
    "difference",
    "percentage",
    "record",
    "render",
    "rows_of",
]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/standings -v --no-cov`
Expected: PASS, 15 + 17 = 32 tests.

- [ ] **Step 5: Add the views to the test matrix**

Append to `tests/unit/standings/README.md`:

```markdown

## views.py

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Game view: conference columns, divisions stacked, the shorter block padded | built | exact lines | `test_game_view` | ☑ |
| League view: title, header, every team numbered | built | exact lines | `test_league_view` | ☑ |
| Conference view: each conference numbered from 1 | built | exact lines | `test_conference_view` | ☑ |
| Division view: conference titles, division headers | built | exact lines | `test_division_view` | ☑ |
| One named conference: one column, its own name | built | exact lines | `test_game_view_one_conference` | ☑ |
| PCT: no games, no wins, half, a tie, rounded, all wins | values | `.000` `.000` `.500` `.500` `.667` `1.000` | `test_percentage` `[P]` | ☑ |
| Record: no ties, ties, no games | values | `2-1` `0-1-1` `0-0` | `test_record` `[P]` | ☑ |
| DIFF: ahead, behind, even | values | `+23` `-8` `0` | `test_difference` `[P]` | ☑ |
```

- [ ] **Step 6: Commit**

Convert the files this task wrote or changed to CRLF (Global Constraints command), then:

```bash
git add src/athc/standings tests/unit/standings
git commit -m "standings: the four views"
```

---

### Task 3: The command

**Files:**
- Create: `src/athc/cli/standings.py`
- Modify: `pyproject.toml` (the `[project.entry-points."athc.commands"]` table)
- Test: `tests/integration/test_standings.py`
- Create: `tests/integration/expected/standings_game.txt`, `standings_league.txt`, `standings_conference.txt`, `standings_division.txt`
- Modify: `tests/integration/test_cli_root.py`
- Modify: `tests/integration/README.md`

**Interfaces:**
- Consumes: `render`, `VIEWS`, `View` (Task 2); `athc.fbpro98_standings.Standings`, `Method`; `athc.fbpro98_lge.read_lge(league: str, league_dir) -> LgeFile`; `athc.config.load_league_config`, `LEAGUE_PATH_KEY`, `LEAGUE_FILE`; `athc.errors.ConfigFileError(reason, path)`; `athc.cli.CONTEXT_SETTINGS`, `AthcCommand`, `league_option`; `athc.console.console.print`.
- Produces: the Click command `standings` in `athc.cli.standings`, registered as `athc standings`.

- [ ] **Step 1: Write the failing tests**

`tests/integration/test_standings.py`:

```python
"""Integration tests for `athc standings`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.standings import standings
from athc.errors import FILE_NOT_FOUND
from athc.fbpro98_lge import LgeFile, parse_lge
from athc.fbpro98_standings import Method, Standings
from tests.conftest import LEAGUE, OTHER_LEAGUE, no_league_selected
from tests.integration.conftest import EXPECTED

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]

LGE_DATA = Path(__file__).resolve().parents[1] / "unit" / "fbpro98_lge" / "data"
MID_SEASON = LGE_DATA / "PNFL-2048-after-week16.lge"
BEFORE_WEEK_ONE = LGE_DATA / "PNFL-before-week1.lge"


def _install(make_league: MakeLeague, tmp_path: Path, name: str, source: Path) -> Path:
    """A league folder whose `path` holds `source` as `<name>.lge`."""
    files = tmp_path / f"{name}-files"
    files.mkdir()
    shutil.copy(source, files / f"{name}.lge")
    make_league(name, f"[league]\npath = '{files}'\n")
    return files


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig, tmp_path: Path) -> Path:
    """The selected league, its `.lge` the mid-season PNFL file."""
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return _install(make_league, tmp_path, LEAGUE, MID_SEASON)


def _lge(path: Path = MID_SEASON) -> LgeFile:
    return parse_lge(path.read_bytes(), path)


def _expected(view: str) -> list[str]:
    return (EXPECTED / f"standings_{view}.txt").read_text(encoding="utf-8").splitlines()


def _espn_rows(lines: list[str]) -> list[list[str]]:
    """The cells of each team row of an ESPN view: the lines whose last cell
    is a streak (`W3`, `L2`, `-`)."""
    rows: list[list[str]] = []
    for line in lines:
        cells = line.split()
        if cells and (cells[-1] == "-" or cells[-1][0] in "WL"):
            rows.append(cells)
    return rows


@pytest.mark.parametrize("view", ["game", "league", "conference", "division"])
def test_view_matches_golden(runner, view: str) -> None:
    result = runner.invoke(standings, ["--view", view])
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == _expected(view)


def test_defaults_are_the_game_view_by_the_scheduler(runner) -> None:
    default = runner.invoke(standings, [])
    chosen = runner.invoke(standings, ["--view", "game", "--method", "scheduler"])
    assert default.exit_code == 0
    assert default.stdout == chosen.stdout


def test_records_match_the_file(runner) -> None:
    """W, L, T, PF and PA of every team equal the file's own records."""
    result = runner.invoke(standings, ["--view", "league"])
    records = {team.official_name: team.record for team in _lge().teams}
    rows = _espn_rows(result.stdout.splitlines())
    assert len(rows) == len(records)
    for cells in rows:
        name = " ".join(cells[1:-12])
        record = records[name]
        wins, losses, ties = cells[-12:-9]
        points_for, points_against = cells[-4:-2]
        assert (wins, losses, ties, points_for, points_against) == (
            str(record.wins),
            str(record.losses),
            str(record.ties),
            str(record.points_for),
            str(record.points_against),
        ), name


def test_league_view_numbers_every_team(runner) -> None:
    result = runner.invoke(standings, ["--view", "league"])
    numbers = [cells[0] for cells in _espn_rows(result.stdout.splitlines())]
    assert numbers == [str(number) for number in range(1, len(_lge().teams) + 1)]


def test_conference_view_numbers_each_conference(runner) -> None:
    result = runner.invoke(standings, ["--view", "conference"])
    numbers = [cells[0] for cells in _espn_rows(result.stdout.splitlines())]
    expected = [
        str(number)
        for conference in _lge().conferences
        for number in range(
            1, sum(len(division.teams) for division in conference.divisions) + 1
        )
    ]
    assert numbers == expected


@pytest.mark.parametrize("method", ["scheduler", "game", "nfl"])
def test_method_orders_the_league_view(runner, method: Method) -> None:
    result = runner.invoke(standings, ["--view", "league", "--method", method])
    assert result.exit_code == 0
    names = [" ".join(cells[1:-12]) for cells in _espn_rows(result.stdout.splitlines())]
    ranked = Standings(_lge(), method=method, seed=0)
    assert names == [team.official_name for team in ranked.league()]


def test_before_week_one_shows_every_team_at_zero(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    _install(make_league, tmp_path, OTHER_LEAGUE, BEFORE_WEEK_ONE)
    result = runner.invoke(
        standings, ["--view", "league", "--league", OTHER_LEAGUE]
    )
    assert result.exit_code == 0
    rows = _espn_rows(result.stdout.splitlines())
    assert len(rows) == len(_lge(BEFORE_WEEK_ONE).teams)
    for cells in rows:
        assert cells[-12:] == [
            "0", "0", "0", ".000", "0-0", "0-0", "0-0", "0-0", "0", "0", "0", "-",
        ]  # fmt: skip


def test_same_file_same_order(runner, make_league: MakeLeague, tmp_path: Path) -> None:
    """Before week 1 every team is level, so the coin decides every place."""
    _install(make_league, tmp_path, OTHER_LEAGUE, BEFORE_WEEK_ONE)
    args = ["--view", "league", "--league", OTHER_LEAGUE]
    first = runner.invoke(standings, args).stdout
    assert all(runner.invoke(standings, args).stdout == first for _ in range(4))


def test_league_option_picks_the_league(
    runner, make_league: MakeLeague, tmp_path: Path
) -> None:
    _install(make_league, tmp_path, OTHER_LEAGUE, BEFORE_WEEK_ONE)
    result = runner.invoke(standings, ["--view", "league", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout.splitlines()[0] == OTHER_LEAGUE


def test_no_league_selected(runner, config_dir: Path, write_config: WriteConfig) -> None:
    write_config("[athc]\n")
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert result.stdout == ""


def test_no_path(runner, config_dir: Path) -> None:
    folder = config_dir / "leagues" / LEAGUE
    (folder / "league.toml").write_text("[league]\n", encoding="utf-8")
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: No path for the league. "
        "Set path in this file.\n"
    )
    assert result.stdout == ""


def test_missing_lge(runner, league: Path) -> None:
    (league / f"{LEAGUE}.lge").unlink()
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league / f'{LEAGUE}.lge'}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_broken_lge(runner, league: Path) -> None:
    (league / f"{LEAGUE}.lge").write_bytes(b"")
    result = runner.invoke(standings, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {league / f'{LEAGUE}.lge'}: Empty file.\n"
    assert result.stdout == ""


@pytest.mark.parametrize("option", ["--view", "--method"])
def test_bad_choice_is_a_usage_error(runner, option: str) -> None:
    result = runner.invoke(standings, [option, "bogus"])
    assert result.exit_code == 2
    assert f"Invalid value for '{option}'" in result.stderr
    assert result.stdout == ""
```

In `tests/integration/test_cli_root.py`:

- add `from athc.cli.standings import standings` to the imports (sorted after `from athc.cli.profile.check import check as profile_check`);
- append `standings,` to `LEAGUE_COMMANDS` after `generate_schedule,`;
- in `_unknown_league_args`, before the final `return` (the `generate_schedule` one), add:

```python
    if command is standings:
        return []
```

- append to `USAGE_CASES`, after the `convert-pdb` entry:

```python
    (
        ("standings",),
        "athc standings [-h] [--view game|league|conference|division] "
        "[--method scheduler|game|nfl] [--league name]",
    ),
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_standings.py -v --no-cov`
Expected: FAIL at collection, `ModuleNotFoundError: No module named 'athc.cli.standings'`.

- [ ] **Step 3: Write the command**

`src/athc/cli/standings.py`:

```python
"""`athc standings` — show a league's standings."""

from __future__ import annotations

import click

from athc.cli import CONTEXT_SETTINGS, AthcCommand, league_option
from athc.config import LEAGUE_FILE, LEAGUE_PATH_KEY, load_league_config
from athc.console import console
from athc.errors import ConfigFileError
from athc.fbpro98_lge import read_lge
from athc.fbpro98_standings import Method, Standings
from athc.standings import VIEWS, View, render

# The default first, the order the usage line lists them in.
_METHODS: tuple[Method, ...] = ("scheduler", "game", "nfl")
# One fixed coin toss, so the same league file always shows the same order.
_SEED = 0


@click.command(name="standings", cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
@click.option(
    "--view",
    type=click.Choice(VIEWS),
    default="game",
    show_default=True,
    help="The game's standings screen, or an ESPN standings tab.",
)
@click.option(
    "--method",
    type=click.Choice(_METHODS),
    default="scheduler",
    show_default=True,
    help="Tie-breakers: the scheduler's, the game's or the NFL's.",
)
@league_option
def standings(view: View, method: Method, league: str | None) -> None:
    """Show the league's standings as played so far.

    Reads the league's <league>.lge from the folder `path` names in its
    league.toml.

    \b
      --view game         the game's standings screen
      --view league       every team, numbered (ESPN's League tab)
      --view conference   each conference, numbered (ESPN's Conference tab)
      --view division     each division (ESPN's Division tab)
    """
    config = load_league_config(league)
    folder = config.path(LEAGUE_PATH_KEY)
    if folder is None:
        raise ConfigFileError(
            f"No {LEAGUE_PATH_KEY} for the league. Set {LEAGUE_PATH_KEY} in this file.",
            config.dir / LEAGUE_FILE,
        )
    lge = read_lge(config.name, folder)
    ranked = Standings(lge, method=method, seed=_SEED)
    for line in render(view, lge, ranked, config.name):
        console.print(line)
```

In `pyproject.toml`, add to `[project.entry-points."athc.commands"]`, after the `profile = ...` line:

```toml
standings = "athc.cli.standings:standings"
```

Then reinstall so the entry point is registered:

Run: `uv sync`

- [ ] **Step 4: Write the goldens**

Write each view's output from the mid-season file to its golden, with CRLF endings. Run this one command (the script lives in the scratchpad, not the repo; `<scratchpad>` is the session's scratchpad directory):

`<scratchpad>/write_standings_goldens.py`:

```python
"""Write tests/integration/expected/standings_<view>.txt from the mid-season
PNFL file, the way the command renders it for the test league."""

from pathlib import Path

from athc.fbpro98_lge import parse_lge
from athc.fbpro98_standings import Standings
from athc.standings import VIEWS, render

ROOT = Path.cwd()
SOURCE = ROOT / "tests" / "unit" / "fbpro98_lge" / "data" / "PNFL-2048-after-week16.lge"
lge = parse_lge(SOURCE.read_bytes(), SOURCE)
ranked = Standings(lge, method="scheduler", seed=0)
for view in VIEWS:
    lines = render(view, lge, ranked, "test_league")
    path = ROOT / "tests" / "integration" / "expected" / f"standings_{view}.txt"
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    print(path)
```

Run: `uv run python <scratchpad>/write_standings_goldens.py`
Expected: four paths printed.

Check each golden by hand before going on:
- `standings_game.txt`: two columns, AFC on the left, NFC on the right; each division header `AFC EAST`, `AFC WEST`, `NFC EAST`, `NFC WEST` followed by `W  L  T  PF  PA`; 18 team rows in all; city names only.
- `standings_league.txt`: first line `test_league`; 18 rows numbered 1-18; full team names.
- `standings_conference.txt`: `AFC` and `NFC` titles, each list numbered from 1, 18 rows in all.
- `standings_division.txt`: `AFC` and `NFC` titles, four division headers, no numbers.
- In every file the columns line up, and no line ends in a space.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_standings.py tests/integration/test_cli_root.py -v --no-cov`
Expected: PASS (test_standings.py: 20 tests; test_cli_root.py: the new `standings` cases pass with the rest).

- [ ] **Step 6: Add the command to the integration test matrix**

Append to `tests/integration/README.md`:

```markdown

---

# `athc standings`

In [test_standings.py](test_standings.py). The selected league's `path` holds `tests/unit/fbpro98_lge/data/PNFL-2048-after-week16.lge` as `test_league.lge` (an autouse fixture); a second league holds `PNFL-before-week1.lge`. Goldens in `expected/standings_{game,league,conference,division}.txt`. Exit 0 done / 2 error.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Each view | mid-season | stdout equals the golden; stderr empty | `test_view_matches_golden` `[P]` | ☑ |
| Defaults | mid-season | same as `--view game --method scheduler` | `test_defaults_are_the_game_view_by_the_scheduler` | ☑ |
| Records match the file | mid-season | W, L, T, PF, PA equal `Team.record` | `test_records_match_the_file` | ☑ |
| League view numbered 1 to the team count | mid-season | 1-18 | `test_league_view_numbers_every_team` | ☑ |
| Conference view numbered per conference | mid-season | 1-9, 1-9 | `test_conference_view_numbers_each_conference` | ☑ |
| Each method orders the league view | mid-season | the library's `league()` order | `test_method_orders_the_league_view` `[P]` | ☑ |
| Before week 1 | before week 1 | every row 0, `.000`, `0-0`, `0`, `-` | `test_before_week_one_shows_every_team_at_zero` | ☑ |
| Same file, same order | before week 1 | five runs alike | `test_same_file_same_order` | ☑ |
| `--league` picks the league | second league | its name as the title | `test_league_option_picks_the_league` | ☑ |
| No league selected | athc.ini without league | exit 2; stderr: `FAIL No league selected ...`; stdout empty | `test_no_league_selected` | ☑ |
| No `path` | league.toml without `path` | exit 2; stderr: `FAIL <league.toml>: No path for the league. Set path in this file.` | `test_no_path` | ☑ |
| Missing `.lge` | file removed | exit 2; stderr: `FAIL <file>: The system cannot find the file specified.` | `test_missing_lge` | ☑ |
| Broken `.lge` | empty file | exit 2; stderr: `FAIL <file>: Empty file.` | `test_broken_lge` | ☑ |
| Bad `--view` / `--method` | `bogus` | usage error on stderr, exit 2 | `test_bad_choice_is_a_usage_error` `[P]` | ☑ |
```

- [ ] **Step 7: Commit**

Convert the files this task wrote or changed to CRLF (Global Constraints command; the goldens are already CRLF), then:

```bash
git add src/athc/cli/standings.py pyproject.toml tests/integration
git commit -m "standings: athc standings command"
```

---

### Task 4: Docs, line endings and the full check

**Files:**
- Create: `docs/standings/README.md`
- Modify: `docs/design/architecture.md`
- Modify: `README.md`
- Modify: `config/release/docs/COMMANDS.txt`, `config/release/docs/README.txt`, `config/release/docs/USAGE_ORIGINAL.txt`
- Modify: `STATUS.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: the finished command from Task 3.
- Produces: docs only.

- [ ] **Step 1: Write `docs/standings/README.md`**

````markdown
# standings

Show a league's standings as played so far, from its current `.lge` file.

## Usage

```bash
athc standings
athc standings --view league
athc standings --view division --method nfl --league PCFL
```

The league comes from `--league name`, or from `[athc] league` in
`athc.ini`. Its `.lge`, named after the league, is read from the folder
`path` names in its `league.toml`.

## Views

- `game` (default): the game's standings screen. One column per conference,
  its divisions stacked down it; each division under a header like
  `AFC EAST`; W, L, T, PF, PA; city names.
- `league`: ESPN's League tab. The league's name, then every team numbered
  from 1.
- `conference`: ESPN's Conference tab. Each conference's teams, numbered
  from 1.
- `division`: ESPN's Division tab. Each conference, then each division under
  its header.

The ESPN views show W, L, T, PCT, HOME, AWAY, DIV, CONF, PF, PA, DIFF and
STRK, with full team names. A record reads `2-1`, or `0-1-1` with ties;
STRK is `-` when the latest game was a tie or none was played.

A conference the file leaves unnamed shows as AFC (first) or NFC (second).

## Order

`--method` picks the tie-breakers: `scheduler` (default), `game` or `nfl`,
from the standings library. Teams still level at the end are ordered by one
fixed coin toss, so the same file always shows the same order.

Only regular-season games count.

## Output and exit codes

The view goes to stdout. Exit 0; 2 on an error: no league, no `path` in
`league.toml`, a missing or broken `.lge`, a bad option.
````

Convert it, and every file edited in this task, to CRLF (Global Constraints command).

- [ ] **Step 2: Update `docs/design/architecture.md`**

- Project layout: under `cli/`, add `standings.py                       # athc standings (leaf)` after the `autocontinue.py` line; under `# TOOLS`, add `standings/       records.py  views.py` after the `autocontinue/` line.
- Cross-cutting conventions, CLI: in the `--league name` bullet, add `standings` to the list of league-aware commands, after `generate-schedule`.

- [ ] **Step 3: Update `README.md`**

Read `README.md` end to end first. Where it lists the commands, add `athc standings` with the one-line help, `Show the league's standings as played so far.`, in the same form as its neighbors.

- [ ] **Step 4: Update the release docs**

`config/release/docs/COMMANDS.txt`, after the `15) config` section and before `EXIT CODES`:

```
16) standings  --  show the league's standings as played so far
    -----------------------------------------------------------

   Reads the league's .lge from the folder path names in its league.toml.
   --view game (the default) shows the game's standings screen; --view
   league, conference or division shows ESPN's tab of that name, with home,
   away, division and conference records, point difference and streak.
   --method picks the tie-breakers: scheduler (the default), game or nfl.

   Show help:
      athc standings -h

   Example terminal calls:
      athc standings
      athc standings --view league
      athc standings --view division --method nfl --league PCFL
```

`config/release/docs/README.txt`: in REQUIREMENTS, add `standings` to the `Windows 8.1 or newer:` list, after `profile`, keeping the list wrapped as it is.

`config/release/docs/USAGE_ORIGINAL.txt`: replace the `athc --help` block's output with what `uv run athc --help` prints now, and add an `athc standings --help` section (title line, a dashed line under it, then exactly what `uv run athc standings --help` prints) after the `athc playpool check --help` section.

- [ ] **Step 5: Update `STATUS.md`**

- In the Commands block, add `athc standings                 DONE` after `athc profile diff`, aligned like the others.
- Change `Eight commands are in.` to `Nine commands are in.`
- Add a `## standings` section at the top of the component sections (right after the Commands block), with one bullet:

```markdown
## standings

- `athc standings` (2026-10-13): the league's standings as played so far,
  from its current `.lge`; `--view game` (default, the game's screen),
  `league`, `conference`, `division` (ESPN's tabs); `--method scheduler`
  (default), `game`, `nfl`; one fixed coin toss. Detail:
  [docs/standings/README.md](docs/standings/README.md).
```

- [ ] **Step 6: Update `CHANGELOG.md`**

Add at the top of the `## athc` list:

```markdown
- standings: new `athc standings` command shows the league's standings as played so far, as the game's standings screen or ESPN's League, Conference and Division tabs
```

- [ ] **Step 7: Check the line endings**

Run: `git ls-files --eol src/athc/standings src/athc/cli/standings.py tests/unit/standings tests/integration/test_standings.py tests/integration/expected docs/standings`
Expected: every file shows `w/crlf`. Convert any `w/lf` file (Global Constraints command), then run this check again.

- [ ] **Step 8: Run the full checks**

Run each on its own:

- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`
- `uv run pyright`

Expected: all green; pytest coverage at or above 92%. If `ruff format` changed a file, convert it back to CRLF (Global Constraints command), then run the four again.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "standings: docs"
```
