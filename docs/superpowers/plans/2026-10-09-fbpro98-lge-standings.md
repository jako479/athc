# fbpro98_lge Standings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each team's regular-season record and each division's and conference's standings order, from the `.lge` schedule chunk.

**Architecture:** `Record` joins the model and `Team` carries one; `Division.standings` / `Conference.standings` sort by win percentage, then point differential, stable. The reader's walks now return heads and names, `_read_schedule` tallies played regular-season games per team number, and `_build` assembles the model.

**Tech Stack:** Python 3.13 stdlib, pytest.

**Spec:** `docs/superpowers/specs/2026-10-09-fbpro98-lge-standings-design.md`

## Global Constraints

- Text files UTF-8, CRLF, final newline; ruff, ruff format, pyright, pytest (coverage at least 92%) all green.
- Libraries never print or log; failures raise `InvalidLgeError` with the path.
- Every new limit tested at the limit and one past it.
- Commit messages one line, prefixed `fbpro98_lge:`.

## Review Focus

- A schedule chunk from a file before week 1 (every game unplayed, scores `0xFF`): all records zero. Test: `test_before_week_one_records_are_zero_and_standings_keep_file_order`.
- Playoff weeks with unknown teams (`0xFF`): skipped, not rejected. Test: `test_playoff_games_do_not_count` (real file) and `test_playoff_games_skipped`.
- A tie game: both teams get a tie, not a win. Test: `test_record_counts_played_regular_season_games`.
- Equal win percentage from different records (8-8 and 7-7-2): ranked by point differential. Test: `test_equal_win_percentage_ranked_by_point_differential`.
- A played game naming team 0 or N+1: rejected, not an `IndexError`. Test: `test_played_game_with_unknown_team_rejected`.

---

### Task 1: Record and standings in the model

**Files:** Modify `src/athc/fbpro98_lge/model.py`, `src/athc/fbpro98_lge/__init__.py`, `tests/unit/fbpro98_lge/test_model.py`.

**Interfaces:**
- Produces: `Record(wins, losses, ties, points_for, points_against)` with `games`, `win_percentage`, `point_differential`; `Team(name, nickname, record)`; `Division.standings`, `Conference.standings` -> `tuple[Team, ...]`; `Record` exported.

- [ ] **Step 1: Write the failing tests** — replace `tests/unit/fbpro98_lge/test_model.py` with:

```python
"""Tests for athc.fbpro98_lge.model."""

import dataclasses

import pytest

from athc.fbpro98_lge import Conference, Division, LgeFile, Record, Team

NO_GAMES = Record(wins=0, losses=0, ties=0, points_for=0, points_against=0)


def _team(name: str, record: tuple[int, int, int, int, int]) -> Team:
    return Team(name=name, nickname="", record=Record(*record))


def _names(teams: tuple[Team, ...]) -> tuple[str, ...]:
    return tuple(team.name for team in teams)


def test_nested_access():
    team = Team(name="Denver", nickname="Broncos", record=NO_GAMES)
    division = Division(name="West", teams=(team,))
    lge = LgeFile(conferences=(Conference(name="AFC", divisions=(division,)),))
    assert lge.conferences[0].name == "AFC"
    assert lge.conferences[0].divisions[0].name == "West"
    assert lge.conferences[0].divisions[0].teams[0].nickname == "Broncos"


@pytest.mark.parametrize(
    ("name", "nickname", "official_name"),
    [
        ("Denver", "Broncos", "Denver Broncos"),
        ("Denver", "", "Denver"),
        ("", "Broncos", "Broncos"),
        ("", "", ""),
    ],
)
def test_official_name(name: str, nickname: str, official_name: str):
    team = Team(name=name, nickname=nickname, record=NO_GAMES)
    assert team.official_name == official_name


def test_frozen():
    team = Team(name="Denver", nickname="Broncos", record=NO_GAMES)
    with pytest.raises(dataclasses.FrozenInstanceError):
        team.name = "Dallas"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("record", "games", "win_percentage", "point_differential"),
    [
        ((5, 1, 0, 164, 112), 6, 5 / 6, 52),
        ((9, 6, 1, 362, 323), 16, 9.5 / 16, 39),
        ((0, 0, 1, 10, 10), 1, 0.5, 0),
        ((0, 0, 0, 0, 0), 0, 0.0, 0),
    ],
)
def test_record_totals(
    record: tuple[int, int, int, int, int],
    games: int,
    win_percentage: float,
    point_differential: int,
):
    totals = Record(*record)
    assert totals.games == games
    assert totals.win_percentage == win_percentage
    assert totals.point_differential == point_differential


def test_division_standings_rank_by_win_percentage_counting_ties_as_half():
    teams = (
        _team("8-7-1", (8, 7, 1, 0, 0)),
        _team("9-7", (9, 7, 0, 0, 0)),
        _team("9-6-1", (9, 6, 1, 0, 0)),
    )
    division = Division(name="East", teams=teams)
    assert _names(division.standings) == ("9-6-1", "9-7", "8-7-1")


def test_equal_win_percentage_ranked_by_point_differential():
    teams = (_team("8-8", (8, 8, 0, 300, 297)), _team("7-7-2", (7, 7, 2, 300, 290)))
    division = Division(name="East", teams=teams)
    assert _names(division.standings) == ("7-7-2", "8-8")


def test_level_teams_keep_file_order():
    teams = (_team("first", (8, 8, 0, 300, 300)), _team("second", (8, 8, 0, 310, 310)))
    division = Division(name="East", teams=teams)
    assert _names(division.standings) == ("first", "second")


def test_conference_standings_rank_across_divisions():
    east = Division(
        name="East",
        teams=(_team("A", (4, 2, 0, 0, 0)), _team("B", (2, 4, 0, 0, 0))),
    )
    west = Division(
        name="West",
        teams=(_team("C", (6, 0, 0, 0, 0)), _team("D", (3, 3, 0, 0, 0))),
    )
    conference = Conference(name="AFC", divisions=(east, west))
    assert _names(conference.standings) == ("C", "A", "D", "B")
```

- [ ] **Step 2: Run, expect FAIL** — `uv run pytest tests/unit/fbpro98_lge/test_model.py --no-cov -q` → `ImportError: cannot import name 'Record'`.

- [ ] **Step 3: Implement** — in `model.py` add `from collections.abc import Iterable`, then before `Team`:

```python
@dataclass(frozen=True, slots=True)
class Record:
    """A team's regular-season record from the games played so far."""

    wins: int
    losses: int
    ties: int
    points_for: int
    points_against: int

    @property
    def games(self) -> int:
        """Games played."""
        return self.wins + self.losses + self.ties

    @property
    def win_percentage(self) -> float:
        """Wins plus half the ties, over games played; 0.0 before any game."""
        if not self.games:
            return 0.0
        return (self.wins + self.ties / 2) / self.games

    @property
    def point_differential(self) -> int:
        """Points for minus points against."""
        return self.points_for - self.points_against
```

`Team` gains, after `nickname`:

```python
    record: Record
    """Regular-season record."""
```

After `Team`:

```python
def _ranked(teams: Iterable[Team]) -> tuple[Team, ...]:
    # sorted() is stable, so teams still level stay in file order.
    return tuple(
        sorted(
            teams,
            key=lambda team: (
                -team.record.win_percentage,
                -team.record.point_differential,
            ),
        )
    )
```

`Division` gains:

```python
    @property
    def standings(self) -> tuple[Team, ...]:
        """Its teams, best first: win percentage, then point differential,
        then file order."""
        return _ranked(self.teams)
```

`Conference` gains:

```python
    @property
    def standings(self) -> tuple[Team, ...]:
        """Every team in its divisions, best first, ranked as
        `Division.standings`."""
        return _ranked(team for division in self.divisions for team in division.teams)
```

`__init__.py` exports `Record`.

- [ ] **Step 4: Run, expect PASS** for `test_model.py` (reader tests fail until Task 2; that is expected).
- [ ] **Step 5: Commit** after Task 2 (the suite is red between them; one commit covers both).

---

### Task 2: Reader reads the schedule

**Files:** Modify `src/athc/fbpro98_lge/schema.py`, `reader.py`; `tests/unit/fbpro98_lge/conftest.py`, `test_reader.py`, `test_schema.py`. Add fixtures `PNFL-before-week1.lge`, `PNFL-after-week16.lge`, `PNFL-after-super-bowl.lge` (already copied).

**Interfaces:**
- Consumes: Task 1 `Record`, `Team(name, nickname, record)`.
- Produces: schema `SCHEDULE_HEADER_SIZE = 3`, `SCHEDULE_REGULAR_WEEKS_OFFSET = 0x00`, `SCHEDULE_PLAYOFF_ROUNDS_OFFSET = 0x01`, `GAME = Struct("6B")`, `GAME_PLAYED = 0`; conftest `build_game(home, home_score, away, away_score, status=GAME_PLAYED, overtime=0)`, `build_schedule_data(regular=(), playoffs=())` with fixtures `make_game`, `make_schedule_data`.

- [ ] **Step 1: Write the failing tests**

`test_schema.py` gains:

```python
def test_schedule_layout():
    assert schema.SCHEDULE_HEADER_SIZE == 3
    assert schema.SCHEDULE_REGULAR_WEEKS_OFFSET == 0x00
    assert schema.SCHEDULE_PLAYOFF_ROUNDS_OFFSET == 0x01
    assert schema.GAME.format == "6B"
    assert schema.GAME_PLAYED == 0
```

`conftest.py` gains (and `build_chunks` ends with `build_chunk(ID_S03, build_schedule_data())`):

```python
def build_game(
    home: int,
    home_score: int,
    away: int,
    away_score: int,
    status: int = GAME_PLAYED,
    overtime: int = 0,
) -> bytes:
    """One S03 game."""
    return GAME.pack(home, home_score, away, away_score, overtime, status)


def build_schedule_data(
    regular: Sequence[Sequence[bytes]] = (), playoffs: Sequence[Sequence[bytes]] = ()
) -> bytes:
    """S03 data: the header, then each week's game count and games."""
    data = bytearray([len(regular), len(playoffs), 0])
    for games in [*regular, *playoffs]:
        data.append(len(games))
        data += b"".join(games)
    return bytes(data)
```

plus fixtures `make_game` and `make_schedule_data` returning them.

`test_reader.py`: `PNFL` gains each team's record from the six played weeks; tests that compared a `Team` to names compare `(team.name, team.nickname)`; the built expectation becomes `Team("T1", "N1", NO_GAMES)`; `test_bare_chunk_header_accepted` is replaced by the schedule limits below. New tests:

```python
# --- standings ---

# Division order on the game's Week Seven standings screen.
PNFL_WEEK_SEVEN = (
    ("Jacksonville", "San Diego", "Miami", "New England"),
    ("Baltimore", "Pittsburgh", "Las Vegas", "Cincinnati", "Denver"),
    ("Atlanta", "Philadelphia", "Washington", "New York"),
    ("Minnesota", "San Francisco", "Chicago", "Green Bay", "Detroit"),
)


def test_division_standings_match_the_game():
    lge = read_lge(LEAGUE, FIXTURE_DIR)
    standings = tuple(
        tuple(team.name for team in division.standings)
        for conference in lge.conferences
        for division in conference.divisions
    )
    assert standings == PNFL_WEEK_SEVEN


def test_final_regular_season_records():
    records = {team.name: team.record for team in _teams(_parse_fixture(WEEK16))}
    assert records["New England"] == Record(7, 8, 1, 351, 369)
    assert records["Denver"] == Record(9, 6, 1, 362, 323)
    assert records["Baltimore"] == Record(13, 3, 0, 371, 235)
    assert records["Cincinnati"] == Record(7, 9, 0, 359, 456)
    # 16 weeks of 9 games: every game is one win or two ties.
    wins = sum(record.wins for record in records.values())
    ties = sum(record.ties for record in records.values())
    assert wins + ties // 2 == 16 * 9


def test_conference_standings_break_ties_by_point_differential():
    afc, nfc = _parse_fixture(WEEK16).conferences
    assert tuple(team.name for team in afc.standings) == (
        "Baltimore", "Miami", "Denver", "Las Vegas", "New England",
        "Cincinnati", "Jacksonville", "Pittsburgh", "Buffalo",
    )
    # 7-9: New York -40 above Green Bay -43; 6-10: Philadelphia +14 above
    # San Francisco -60.
    assert tuple(team.name for team in nfc.standings) == (
        "Chicago", "Minnesota", "Washington", "Atlanta", "New York",
        "Green Bay", "Philadelphia", "San Francisco", "Seattle",
    )


def test_playoff_games_do_not_count():
    final = [team.record for team in _teams(_parse_fixture(WEEK16))]
    after = [team.record for team in _teams(_parse_fixture(SUPER_BOWL))]
    assert after == final


def test_before_week_one_records_are_zero_and_standings_keep_file_order():
    lge = _parse_fixture(BEFORE_WEEK1)
    assert {team.record for team in _teams(lge)} == {NO_GAMES}
    for conference in lge.conferences:
        teams = tuple(t for division in conference.divisions for t in division.teams)
        assert conference.standings == teams
        for division in conference.divisions:
            assert division.standings == division.teams


def _with_schedule(make_chunks, make_chunk, data: bytes) -> list[bytes]:
    chunks = make_chunks(((2,),))
    chunks[-1] = make_chunk(ID_S03, data)
    return chunks


def test_record_counts_played_regular_season_games(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    regular = [[make_game(1, 21, 2, 14)], [make_game(2, 10, 1, 10, overtime=1)]]
    data = make_schedule_data(regular)
    first, second = _teams(parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data))))
    assert first.record == Record(1, 0, 1, 31, 24)
    assert second.record == Record(0, 1, 1, 24, 31)


def test_unplayed_games_skipped(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    # Unplayed games carry 0xFF scores, and 0xFF teams when not yet known.
    regular = [[make_game(0xFF, 0xFF, 0xFF, 0xFF, status=2)]]
    data = make_schedule_data(regular)
    lge = parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data)))
    assert {team.record for team in _teams(lge)} == {NO_GAMES}


def test_playoff_games_skipped(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    data = make_schedule_data(playoffs=[[make_game(1, 30, 2, 3)]])
    lge = parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data)))
    assert {team.record for team in _teams(lge)} == {NO_GAMES}


@pytest.mark.parametrize(("home", "away"), [(1, 2), (2, 1)])
def test_played_game_with_first_and_last_team_accepted(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, home, away
):
    data = make_schedule_data([[make_game(home, 7, away, 3)]])
    lge = parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data)))
    assert _teams(lge)[home - 1].record.wins == 1


@pytest.mark.parametrize(("home", "away", "bad"), [(0, 2, 0), (1, 3, 3)])
def test_played_game_with_unknown_team_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, home, away, bad
):
    data = make_schedule_data([[make_game(home, 7, away, 3)]])
    with pytest.raises(
        InvalidLgeError, match=rf"week 1: no team {bad} \(teams are 1-2\)$"
    ):
        parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data)))


def test_schedule_shorter_than_its_header_rejected(make_chunks, make_chunk, make_lge):
    # The 3-byte header alone is the default built schedule: accepted.
    chunks = make_chunks()
    chunks[S03] = make_chunk(ID_S03, bytes(2))
    with pytest.raises(InvalidLgeError, match=r"is 2 bytes, expected at least 3$"):
        parse_lge(make_lge(chunks))


@pytest.mark.parametrize("cut", [1, 7])
def test_schedule_cut_short_in_a_week_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, cut: int
):
    # 1: the game's last byte is missing; 7: the whole week is.
    data = make_schedule_data([[make_game(1, 7, 2, 3)]])[:-cut]
    with pytest.raises(InvalidLgeError, match=r"is cut short in week 1$"):
        parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data)))


def test_schedule_with_data_after_the_last_week_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    data = make_schedule_data([[make_game(1, 7, 2, 3)]]) + b"\x00"
    with pytest.raises(InvalidLgeError, match=r"has data after the last week$"):
        parse_lge(make_lge(_with_schedule(make_chunks, make_chunk, data)))
```

with module constants `NO_GAMES = Record(0, 0, 0, 0, 0)`, `BEFORE_WEEK1 = "PNFL-before-week1.lge"`, `WEEK16 = "PNFL-after-week16.lge"`, `SUPER_BOWL = "PNFL-after-super-bowl.lge"`.

- [ ] **Step 2: Run, expect FAIL** — `uv run pytest tests/unit/fbpro98_lge --no-cov -q` → schema constants and `Team(..., record)` missing.

- [ ] **Step 3: Implement** — schema gains:

```python
# S03: a header, then per week a game count and that many games.
SCHEDULE_HEADER_SIZE = 3
SCHEDULE_REGULAR_WEEKS_OFFSET = 0x00
SCHEDULE_PLAYOFF_ROUNDS_OFFSET = 0x01
GAME = Struct("6B")  # home, home score, away, away score, overtime, status
GAME_PLAYED = 0
```

reader: walks return `(heads, names)`; `_read_schedule(chunks, team_count) -> list[Record]`; `_record(scores)`; `_build(heads, names, records)`; `_Chunks` gains `offset` and a public `error`:

```python
# A conference's name and its divisions' names and team counts, in file order.
_Heads = list[tuple[str, list[tuple[str, int]]]]


def parse_lge(...):
    ...
    walk = _walk_grouped if chunks.grouped() else _walk_nested
    heads, names = walk(chunks, conference_count)
    records = _read_schedule(chunks, len(names))
    chunks.finish()
    return LgeFile(conferences=_build(heads, names, records))


def _walk_nested(chunks: _Chunks, conference_count: int) -> tuple[_Heads, list[tuple[str, str]]]:
    # Each conference, then its divisions, each followed by its teams, each
    # followed by its roster.
    heads: _Heads = []
    names: list[tuple[str, str]] = []
    for _ in range(conference_count):
        name, division_count = _take_conference(chunks)
        divisions: list[tuple[str, int]] = []
        for _ in range(division_count):
            division_name, team_count = _take_division(chunks)
            divisions.append((division_name, team_count))
            for _ in range(team_count):
                names.append(_take_team(chunks))
                _take_roster(chunks)
        heads.append((name, divisions))
    return heads, names


def _walk_grouped(chunks: _Chunks, conference_count: int) -> tuple[_Heads, list[tuple[str, str]]]:
    # Every conference, then every division, team and roster, in the same
    # order as a nested file; the counts nest them.
    conferences = [_take_conference(chunks) for _ in range(conference_count)]
    division_count = sum(count for _, count in conferences)
    divisions = iter([_take_division(chunks) for _ in range(division_count)])
    heads = [(name, list(islice(divisions, count))) for name, count in conferences]
    team_count = sum(count for _, division_heads in heads for _, count in division_heads)
    names = [_take_team(chunks) for _ in range(team_count)]
    for _ in range(team_count):
        _take_roster(chunks)
    return heads, names


def _read_schedule(chunks: _Chunks, team_count: int) -> list[Record]:
    offset = chunks.offset
    data = chunks.take(ID_S03)
    label = f"S03 chunk at {offset:#x}"
    if len(data) < SCHEDULE_HEADER_SIZE:
        raise chunks.error(
            f"{label} is {len(data)} bytes, expected at least {SCHEDULE_HEADER_SIZE}"
        )
    regular_weeks = data[SCHEDULE_REGULAR_WEEKS_OFFSET]
    weeks = regular_weeks + data[SCHEDULE_PLAYOFF_ROUNDS_OFFSET]
    # One (scored, allowed) pair per played game, by team number - 1.
    scores: list[list[tuple[int, int]]] = [[] for _ in range(team_count)]
    position = SCHEDULE_HEADER_SIZE
    for week in range(1, weeks + 1):
        if position == len(data):
            raise chunks.error(f"{label} is cut short in week {week}")
        end = position + 1 + data[position] * GAME.size
        if end > len(data):
            raise chunks.error(f"{label} is cut short in week {week}")
        # Playoff games never count; unplayed ones may not name their teams yet.
        if week <= regular_weeks:
            for home, home_score, away, away_score, _, status in GAME.iter_unpack(
                data[position + 1 : end]
            ):
                if status != GAME_PLAYED:
                    continue
                for number in (home, away):
                    if not 1 <= number <= team_count:
                        raise chunks.error(
                            f"{label}, week {week}: no team {number} "
                            f"(teams are 1-{team_count})"
                        )
                scores[home - 1].append((home_score, away_score))
                scores[away - 1].append((away_score, home_score))
        position = end
    if position != len(data):
        raise chunks.error(f"{label} has data after the last week")
    return [_record(team_scores) for team_scores in scores]


def _record(scores: list[tuple[int, int]]) -> Record:
    return Record(
        wins=sum(scored > allowed for scored, allowed in scores),
        losses=sum(scored < allowed for scored, allowed in scores),
        ties=sum(scored == allowed for scored, allowed in scores),
        points_for=sum(scored for scored, _ in scores),
        points_against=sum(allowed for _, allowed in scores),
    )


def _build(heads: _Heads, names: list[tuple[str, str]], records: list[Record]) -> tuple[Conference, ...]:
    # Teams are numbered 1..N in file order, the numbers the schedule uses.
    teams = iter(
        Team(name=name, nickname=nickname, record=record)
        for (name, nickname), record in zip(names, records, strict=True)
    )
    return tuple(
        Conference(
            name=name,
            divisions=tuple(
                Division(name=division_name, teams=tuple(islice(teams, count)))
                for division_name, count in divisions
            ),
        )
        for name, divisions in heads
    )
```

`_take_team` returns `(name, nickname)`; `_parse_nested`, `_parse_grouped`, `_parse_conference`, `_parse_division`, `_parse_team` go.

- [ ] **Step 4: Run, expect PASS** — `uv run pytest tests/unit/fbpro98_lge --no-cov -q`.
- [ ] **Step 5: Commit** — `git add src/athc/fbpro98_lge tests/unit/fbpro98_lge` then `git commit -m "fbpro98_lge: team records and standings"`.

---

### Task 3: Docs and full checks

- [ ] Update `docs/fbpro98_lge/README.md`, `ARCHITECTURE.md`, `tests/unit/fbpro98_lge/README.md`, `docs/fbpro98_lge/specs/lge.md` (weeks played `255` after the season), `docs/design/fbpro98-files.md`, `STATUS.md`, `CHANGELOG.md` (new line at the top of the `fbpro98_lge` section).
- [ ] CRLF pass; `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`, one per call, all green.
- [ ] Commit `fbpro98_lge: standings docs`.
