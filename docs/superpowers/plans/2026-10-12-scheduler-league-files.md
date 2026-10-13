# generate-schedule from the league files — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `generate-schedule` builds its `League` from two `.lge` files (previous season for standings, upcoming season for structure and names) and the `<season>.league.ini` standings files go away.

**Architecture:** `fbpro98_lge` exposes the played games (per week and per playoff round) and the count of games not played. A new `scheduler/league_files.py` reads both files, matches teams by name with the season's `[renames]`, ranks the previous season (playoff finish, win percentage, strength of schedule, point differential) and builds the domain `League`; the domain identifies conferences and divisions by file position. The CLI takes `--previous folder` and optional `--upcoming folder`.

**Tech Stack:** Python 3.13, Click, stdlib `tomllib`, pytest; OR-Tools unchanged.

**Spec:** [docs/superpowers/specs/2026-10-12-scheduler-league-files-design.md](../specs/2026-10-12-scheduler-league-files-design.md)

## Global Constraints

- Every text file UTF-8, CRLF, final newline; `*.lge` fixtures are binary.
- Ruff format (88 columns, double quotes), ruff lint and pyright standard must pass; pytest with coverage >= 92%.
- Every limit the change introduces is tested at the limit and one past it.
- Errors: `AthcError` subclasses with `reason` and the file's `path`; libraries never print; wording per `docs/design/architecture.md` ("Wording").
- Commits one line, prefixed by the owning tool (`fbpro98_lge:`, `scheduler:`); no AI mention, no trailers.
- The conference league's pinned CP-SAT checksums and goldens must not change; the divisional golden is re-frozen on the real 2047 -> 2048 data.
- Overnight: implement inline, one final review, no questions.

## Review Focus

1. A previous-season file from mid-playoffs (`47PNFL17`): `Season not finished: 3 game(s) not played.` naming that file — Task 4.
2. A previous-season file with a renamed team and no `[renames]`: the error lists the team and the table to add — Task 4.
3. An upcoming file whose conferences each hold one division: a league without divisions, every division-less rule applies — Task 4.
4. A `[renames.<season>]` table with a non-year key or a non-string value: `ConfigFileError` naming `scheduler.toml`, table and key — Task 3.
5. `--upcoming` absent and `league.toml` has no `path`: `ConfigFileError` naming `league.toml` — Task 5.

---

### Task 1: fbpro98_lge — played games, playoffs, unplayed count, public `standings`

**Files:**
- Modify: `src/athc/fbpro98_lge/model.py`, `reader.py`, `__init__.py`
- Test: `tests/unit/fbpro98_lge/test_model.py`, `test_reader.py`, `README.md`
- Docs: `docs/fbpro98_lge/README.md`, `ARCHITECTURE.md`

**Interfaces (produces):**
```python
@dataclass(frozen=True, slots=True)
class Game:
    home: Team; home_score: int; away: Team; away_score: int
    winner -> Team | None   # None on a tie
    loser -> Team | None
def standings(teams: Iterable[Team]) -> tuple[Team, ...]   # win %, point differential, given order
LgeFile.weeks: tuple[tuple[Game, ...], ...] = ()      # regular season, played games per week
LgeFile.playoffs: tuple[tuple[Game, ...], ...] = ()   # played games per round
LgeFile.unplayed_games: int = 0
```

- [ ] **Step 1: Tests (reader).** In `test_reader.py` after the standings section:

```python
def test_games_and_playoffs_after_the_super_bowl():
    lge = read_lge("PNFL-after-super-bowl", DATA)
    assert [len(week) for week in lge.weeks] == [9] * 16
    assert [len(round_) for round_ in lge.playoffs] == [4, 2, 1]
    final = lge.playoffs[-1][0]
    assert (final.winner.name, final.loser.name) == ("Miami", "Minnesota")
    assert lge.unplayed_games == 0

def test_games_before_the_playoffs():
    lge = read_lge("PNFL-after-week16", DATA)
    assert lge.playoffs == ((), (), ())
    assert lge.unplayed_games == 7

def test_games_before_week_one():
    lge = read_lge("PNFL-before-week1", DATA)
    assert lge.weeks == ((),) * 16
    assert lge.unplayed_games == 144 + 7

def test_games_reference_the_teams():
    lge = read_lge("PNFL", DATA)
    teams = [t for c in lge.conferences for d in c.divisions for t in d.teams]
    assert sum(len(week) for week in lge.weeks) == 54
    assert all(g.home in teams and g.away in teams for w in lge.weeks for g in w)
```
Built bytes (two teams, `make_chunks(((2,),))`): a tie's `winner`/`loser` are `None`; an unplayed playoff game (status 2) is skipped and counted (`unplayed_games == 1`, `playoffs == ((),)`); a played playoff game with team 1 and N is read; team 0 and N+1 raise `InvalidLgeError` matching `No team 0` / `No team 3` and `week 2` (the playoff round's week number).

- [ ] **Step 2: Tests (model).** `test_standings_is_public_and_keeps_the_given_order_for_level_teams` calling `standings(...)` with two 8-8 teams and one 9-7 team; `test_game_winner_and_loser` parametrized over home win, away win, tie.

- [ ] **Step 3: Run** `uv run pytest tests/unit/fbpro98_lge -q` — the new tests fail (no `Game`, `standings`, `weeks`).

- [ ] **Step 4: Implement.** `model.py`: add `Game`, rename `_ranked` to public `standings` (docstring: "`teams` best first: win percentage, then point differential, then the given order"), the three `LgeFile` fields with defaults. `reader.py`: `_read_schedule` returns a `_Schedule` (`records`, `weeks`, `playoffs` as lists of `(home, home_score, away, away_score)` per week/round, `unplayed`); it checks team numbers of every played game, regular or playoff, and counts every unplayed one; `parse_lge` builds the conferences, flattens the teams in file order, then maps numbers to `Game`s. Export `Game`, `standings` in `__init__.py`.

- [ ] **Step 5: Run** the lge suite, then `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`.

- [ ] **Step 6: Docs.** README features/API (games, playoffs, unplayed count, `standings`), ARCHITECTURE "does" / "does NOT" lists, test matrix rows.

- [ ] **Step 7: Commit** `fbpro98_lge: played games, playoffs and unplayed count`.

### Task 2: scheduler domain — conferences and divisions by number, `build_league` from objects

**Files:**
- Modify: `src/athc/scheduler/domain/league.py`
- Test: `tests/unit/scheduler/conftest.py`, `test_league.py`, `test_matchups.py:303-340`, `test_writers.py:14-17`, `test_cli.py:244`

**Interfaces (produces):**
```python
Conference(number: int, name: str)
Division(number: int, name: str, conference: Conference, expected_size: int)
ordered_teams(teams) -> list[Team]          # conference number, division number, metro
build_league(teams: Sequence[Team], overall: Sequence[Team],
             division_standings: Mapping[Division, Sequence[Team]] | None = None) -> League
```
`build_league` raises `ValueError`: duplicate metro; not exactly two conferences; a conference without nine teams; `overall` not every team once; with `division_standings`, a team without a division or a division whose finish does not list exactly its members once; without, a team that has a division.

- [ ] **Step 1: Test helper** in `tests/unit/scheduler/conftest.py` replacing the direct `build_league` calls, keeping every existing name table:

```python
def league_from_tables(
    standings: Mapping[str, Sequence[str]], overall: Sequence[str], *, divisions: bool
) -> League:
    """A League from name tables, numbering conferences and divisions by first
    appearance. With `divisions`, keys are `<CONFERENCE>_<DIVISION>`; else
    conference names."""
    conferences: dict[str, Conference] = {}
    teams: list[Team] = []
    finish: dict[Division, tuple[Team, ...]] = {}
    for key, metros in standings.items():
        conference_name = key.partition("_")[0] if divisions else key
        conference = conferences.setdefault(
            conference_name, Conference(len(conferences) + 1, conference_name)
        )
        division = (
            Division(len(finish) + 1, key, conference, len(metros)) if divisions else None
        )
        members = tuple(Team(metro, conference, division) for metro in metros)
        teams.extend(members)
        if division is not None:
            finish[division] = members
    by_metro = {team.metro: team for team in teams}
    return build_league(
        teams, [by_metro[m] for m in overall], finish if divisions else None
    )
```
`CONFERENCES_LEAGUE` lists `EASTERN` before `WESTERN` so the canonical order (and the pinned models) stay.

- [ ] **Step 2: Tests.** Rewrite `test_league.py`: constructions use `Conference(1, "AFC")`, `Division(1, "AFC_EAST", AFC, 4)`; the key-parsing tests go; add `test_conferences_with_empty_names_stay_distinct` (two `Conference(n, "")`), `test_league_orders_by_number_not_name` (conference 1 named "Z" first), and the `build_league` errors above, each with a `match=`. Update `test_matchups.py:335`, `test_writers.py:14-17`, `test_cli.py:244`.

- [ ] **Step 3: Implement** `domain/league.py` per the interfaces; drop `build_teams`, `_clean`, the key split.

- [ ] **Step 4: Run** `uv run pytest tests/unit/scheduler -q -p no:cacheprovider --no-cov -k "not checksum"` (the checksum test still loads INI until Task 6), ruff, pyright.

- [ ] **Step 5: Commit** `scheduler: conferences and divisions identified by file position`.

### Task 3: scheduler config — `[renames]`, INI loader removed

**Files:**
- Modify: `src/athc/scheduler/config.py`, `src/athc/config.py` (drop `STANDINGS_DIR`, add `LEAGUE_PATH_KEY = "path"`), `src/athc/cli/check_ppp.py` (import it)
- Test: `tests/unit/scheduler/test_config.py`

**Interfaces (produces):** `SchedulerConfig.renames: Mapping[int, Mapping[str, str]]` (season -> previous name -> new name), parsed from `[renames.<season>]`.

- [ ] **Step 1: Tests.** Remove every `load_league` / `find_league_path` / INI test and `DIVISION_STANDINGS` etc. Add:

```python
def test_load_scheduler_config_reads_renames(config_dir):
    _write_scheduler_toml(config_dir, '[renames.2048]\nBaltimore = "Los Angeles"\n[renames.2049]\n"Los Angeles" = "Baltimore"\nSeattle = "Detroit"\n')
    assert _load().renames == {2048: {"Baltimore": "Los Angeles"}, 2049: {"Los Angeles": "Baltimore", "Seattle": "Detroit"}}

def test_renames_default_to_none():
    assert SchedulerConfig().renames == {}

@pytest.mark.parametrize(("body", "reason"), [
    ("[renames]\nx = 1\n", "[renames] x: Must be a season year, e.g. 2048."),
    ("[renames.abc]\nA = \"B\"\n", "[renames] abc: Must be a season year, e.g. 2048."),
    ("[renames]\n2048 = \"x\"\n", "[renames.2048]: Must be a table."),
    ("[renames.2048]\nA = 1\n", "[renames.2048] A: Must be a team name."),
    ("[renames.2048]\nA = \" \"\n", "[renames.2048] A: Must be a team name."),
    ("[renames.2048]\nA = \"A\"\n", "[renames.2048] A: Renames the team to itself."),
    ("[renames.2048]\nA = \"C\"\nB = \"C\"\n", "[renames.2048]: Two teams renamed to C."),
])
def test_bad_renames_name_the_table_and_key(tmp_path, body, reason): ...
```
Also `[renames]` not a table (`renames = 1`) -> `[renames]: Must be a table.`; names are stripped.

- [ ] **Step 2: Implement** `_renames(data.get("renames"), path)`; delete `load_league`, `find_league_path`, `_read_config`, `_require_section`, `_required_multiline`, `_parse_multiline`, `DIVISION_SECTION`, `CONFERENCE_SECTION`, `configparser` import, `STANDINGS_DIR`/`league_dir` import if unused (`scheduler_rules_path` still needs `league_dir`), the `build_league`/`Team` imports no longer used. `check_ppp.py` imports `LEAGUE_PATH_KEY` from `athc.config`.

- [ ] **Step 3: Run** the config tests, ruff, pyright. **Commit** `scheduler: [renames] tables; standings INI loader removed`.

### Task 4: `scheduler/league_files.py`

**Files:**
- Create: `src/athc/scheduler/league_files.py`
- Modify: `src/athc/scheduler/schedulers/errors.py` (docstring)
- Test: `tests/unit/scheduler/test_league_files.py` (new); fixtures `tests/integration/data/PNFL-20{46,47}-after-super-bowl.lge`, `PNFL-20{47,48}-after-week1.lge` (copied already)

**Interfaces (produces):**
```python
def load_league(league: str, previous_dir: StrPath, upcoming_dir: StrPath,
                renames: Mapping[str, str], *, season: int, rules_path: Path | None = None) -> League
def league_from_files(previous: LgeFile, upcoming: LgeFile, renames: Mapping[str, str], *,
                      season: int, previous_path: Path, upcoming_path: Path,
                      rules_path: Path | None = None) -> League
```

- [ ] **Step 1: Tests (real files).**

```python
DATA = Path(__file__).resolve().parents[2] / "integration" / "data"
PREVIOUS_2047 = DATA / "PNFL-2047-after-super-bowl.lge"   # read via a tmp folder named <league>.lge

def test_2048_league_matches_the_real_final_standings(tmp_path):
    league = _load(tmp_path, "PNFL-2047-after-super-bowl", "PNFL-2048-after-week1", {"Baltimore": "Los Angeles"}, season=2048)
    assert [t.metro for t in league.rankings.overall] == ["Miami", "Minnesota", "Los Angeles", "Chicago", "Denver", "Washington", "Atlanta", "Las Vegas", "New England", "Green Bay", "Cincinnati", "New York", "San Francisco", "Jacksonville", "Philadelphia", "Pittsburgh", "Seattle", "Buffalo"]
    finish = {d.name + str(d.conference.number): [t.metro for t in o] for d, o in league.division_standings.items()}
    assert finish == {"East1": ["Miami", "New England", "Jacksonville", "Buffalo"], "West1": ["Los Angeles", "Denver", "Las Vegas", "Cincinnati", "Pittsburgh"], "East2": ["Washington", "Atlanta", "New York", "Philadelphia"], "West2": ["Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"]}
    assert [c.name for c in league.conferences] == ["", ""]
```
2046 -> 2047 with `{"Houston": "Miami", "New York A": "Cincinnati", "Indianapolis": "Baltimore", "New York N": "New York"}`: Jacksonville's division is number 1 (East), Cincinnati's and Baltimore's number 2; `East1 == ["Miami", "Buffalo", "Jacksonville", "New England"]`, `West1 == ["Pittsburgh", "Cincinnati", "Baltimore", "Las Vegas", "Denver"]`; overall starts `Pittsburgh, Washington, Minnesota, Cincinnati, Miami, Buffalo, Seattle, San Francisco, Baltimore`.
Errors: previous = `PNFL-2048-after-week1` -> `SchedulerError` `== f"{path}: Season not finished: 142 game(s) not played."`; no renames -> `f"{previous}: Team(s) not in {upcoming}: Baltimore. List renamed teams under [renames.2048] in {rules}."`; `{"Nowhere": "Los Angeles"}` -> `ConfigFileError` `f"{rules}: [renames.2048] Nowhere: Not a team in {previous}."`; `{"Baltimore": "Nowhere"}` -> `... Not a team in {upcoming}.`

- [ ] **Step 2: Tests (built `LgeFile`s).** A helper builds an `LgeFile` from `(conference name, [(division name, [(team, wins, losses, ties, pf, pa)])])` plus explicit `weeks` and `playoffs` `Game`s. Cases: conference-only shape (`has_divisions is False`, no `division_standings`); three conferences -> `SchedulerError` `f"{upcoming}: Expected exactly 2 conferences, got 3."`; a conference of eight -> `... must have exactly 9 teams; got 8.`; duplicate team name in the upcoming file -> `f"{upcoming}: Team name repeats: Denver."`; playoff tier beats a better record; same record and tier -> strength of schedule decides (two teams 1-1 whose opponents are 2-0 vs 0-2); same strength -> point differential; a tied playoff game -> `SchedulerError` `f"{previous}: Playoff round 1: Tied game, A 10, B 10."`; champion first, runner-up second, bye team (first appears in round 2) ranked by its exit round.

- [ ] **Step 3: Implement.**

```python
"""Build the scheduler's League from two league files: the upcoming season's
`.lge` gives the conferences, divisions and team names; the previous season's
gives the standings. Teams are matched by name, with the season's renames."""

def load_league(league, previous_dir, upcoming_dir, renames, *, season, rules_path=None):
    previous_path = Path(previous_dir) / f"{league}.lge"
    upcoming_path = Path(upcoming_dir) / f"{league}.lge"
    return league_from_files(read_lge(league, previous_dir), read_lge(league, upcoming_dir), renames, season=season, previous_path=previous_path, upcoming_path=upcoming_path, rules_path=rules_path)

def league_from_files(previous, upcoming, renames, *, season, previous_path, upcoming_path, rules_path=None):
    if previous.unplayed_games:
        raise SchedulerError(f"Season not finished: {previous.unplayed_games} game(s) not played.", previous_path)
    previous_by_name = _by_name(previous, previous_path)
    upcoming_by_name = _by_name(upcoming, upcoming_path)
    table = f"[renames.{season}]"
    for old, new in renames.items():
        if old not in previous_by_name: raise ConfigFileError(f"{table} {old}: Not a team in {previous_path}.", rules_path)
        if new not in upcoming_by_name: raise ConfigFileError(f"{table} {old}: Not a team in {upcoming_path}.", rules_path)
    new_name = {old: renames.get(old, old) for old in previous_by_name}
    missing = [old for old, new in new_name.items() if new not in upcoming_by_name]
    if missing:
        raise SchedulerError(f"Team(s) not in {upcoming_path}: {', '.join(missing)}. List renamed teams under {table} in {rules_path}.", previous_path)
    extra = sorted(set(upcoming_by_name) - set(new_name.values()))
    if extra:
        raise SchedulerError(f"Team(s) not in {previous_path}: {', '.join(extra)}.", upcoming_path)
    previous_of = {upcoming_by_name[new]: previous_by_name[old] for old, new in new_name.items()}
    ...build conferences/divisions/teams from `upcoming`; `has_divisions = any(len(c.divisions) > 1 for c in upcoming.conferences)`
    ...division_standings = {division: [domain_team[t] for t in standings(previous_of[m] for m in division.teams)]}
    ...overall by _rank_key(previous) over the previous teams
    try: return build_league(teams, overall, division_standings or None)
    except ValueError as error: raise SchedulerError(sentence(str(error)), upcoming_path) from error
```
Ranking: `tier[team]` = 0 for no playoff game, the round it lost in, `len(previous.playoffs) + 1` for the last round's winner; `strength[team]` = sum over regular-season opponents of `wins + ties / 2` over sum of their `games` (0.0 with no games); key `(-tier, -win_percentage, -strength, -point_differential, file index)`. Hashing uses the library `Team` objects; file index comes from `enumerate` over the previous file's teams. A `Game.loser is None` in the playoffs raises `SchedulerError(f"Playoff round {r}: Tied game, {home} {hs}, {away} {as}.", previous_path)`.

`errors.py`: "Raised when the scheduler cannot build a league from its files, a matchup list or a schedule."

- [ ] **Step 4: Run** `uv run pytest tests/unit/scheduler/test_league_files.py -q --no-cov`, ruff, pyright. **Commit** `scheduler: league built from the previous and upcoming league files`.

### Task 5: main and CLI

**Files:**
- Modify: `src/athc/scheduler/main.py`, `src/athc/cli/generate_schedule.py`
- Test: `tests/unit/scheduler/test_cli.py`

**Interfaces:** `generate_schedule(*, league, season, config_path, previous_dir, upcoming_dir, output_dir, seed, time_limit, command_line, progress=None)`.

- [ ] **Step 1: Tests.** `_write_season_files` becomes `_write_league_files(tmp_path)` copying `PNFL-2047-after-super-bowl.lge` to `tmp/previous/<LEAGUE>.lge` and `PNFL-2048-after-week1.lge` to `tmp/upcoming/<LEAGUE>.lge`; `league.toml` in the league folder sets `path` to the upcoming folder. Every invocation adds `--previous <tmp/previous>`. New: `test_requires_previous`; `test_upcoming_defaults_to_the_league_path` (`captured["upcoming_dir"] == upcoming folder`); `test_upcoming_option_overrides_the_league_path`; `test_errors_when_league_has_no_path` (`FAIL {league.toml}: No path for the league. Set path in this file.`); `test_errors_when_previous_file_missing` (`FAIL {previous}\{LEAGUE}.lge: The system cannot find the path specified.` through the stubbed-free real `main`? — use the real `run_generate` with the solver stubbed via `_stub_solver`); the old "division standings section" tests become `test_main_errors_when_season_not_finished` (upcoming file as previous) and `test_main_builds_the_league_and_reaches_the_solver` (asserts `kwargs["league"].has_divisions`).

- [ ] **Step 2: Implement.** `main.py` loads the rules, then `league_files.load_league(league, previous_dir, upcoming_dir, scheduler_config.renames.get(season, {}), season=season, rules_path=Path(config_path))`. `generate_schedule.py`:

```python
@click.option("--previous", "previous_dir", required=True, metavar="folder", help="Folder holding the previous season's league files; its <league>.lge gives the standings.")
@click.option("--upcoming", "upcoming_dir", default=None, metavar="folder", help="Folder holding the upcoming season's league files; its <league>.lge gives the conferences, divisions and teams. Default: path in league.toml.")
```
with `_upcoming_dir(name, upcoming_dir)`: the option, else `load_league_config(name).path(LEAGUE_PATH_KEY)`, else `ConfigFileError(f"No {LEAGUE_PATH_KEY} for the league. Set {LEAGUE_PATH_KEY} in this file.", config.dir / LEAGUE_FILE)`. Docstring lists the two files and `scheduler.toml`.

- [ ] **Step 3: Run** the CLI tests, ruff, pyright. **Commit** `generate-schedule: --previous and --upcoming league folders`.

### Task 6: test suite — goldens on real data, built conference files, checksum

**Files:**
- Modify: `tests/conftest.py` (`make_league_dir` without `standings\`), `tests/integration/test_generate_schedule.py`, `tests/integration/test_config.py:496,562-572`, `tests/unit/scheduler/test_model_checksum.py`, `tests/unit/scheduler/test-matrix-config-loading.md`, `tests/integration/README.md`
- Create: `tests/integration/league_files.py` (the built conference `.lge` pair), `tests/integration/data/conferences-previous.lge`, `conferences-upcoming.lge`, `conferences.scheduler.toml` unchanged, `divisions.scheduler.toml` gains `[renames.2048]`
- Delete: `tests/integration/data/divisions.2026.ini`, `conferences.2029.ini`

- [ ] **Step 1: Built conference files.** `tests/integration/league_files.py` builds two `.lge` byte strings with the `tests/unit/fbpro98_lge/conftest.py` builders (import them as `tests.unit.fbpro98_lge.conftest`): conferences `EASTERN` (1) then `WESTERN` (2), one division each (`East`, `West`), the eighteen `CONFERENCES_*` teams in the finish orders of `tests/unit/scheduler/conftest.py`; the previous file's schedule is a 17-week round robin where the team placed higher in the wanted overall record order always wins 20-10 (wins by place: Texas 17 ... Michigan 0, the order `Texas, Ohio State, Tennessee, Notre Dame, Boston College, Arkansas, LSU, UCLA, Washington, Clemson, Oklahoma, Georgia, Penn State, USC, Colorado, Miami, Oregon, Michigan`), then three playoff rounds: round 1 Texas beats Ohio State, Tennessee beats Boston College, Notre Dame beats LSU, Arkansas beats UCLA; round 2 Texas beats Notre Dame, Tennessee beats Arkansas; round 3 Texas beats Tennessee. The upcoming file has the same teams and an empty schedule. A unit test (`tests/unit/scheduler/test_league_files.py`) asserts `league_from_files` on the pair `== CONFERENCES_LEAGUE`; a test asserts the committed fixtures equal the built bytes.

- [ ] **Step 2: Golden test.** `GoldenCase(league, season, previous, upcoming, renames)`: `divisions` = (2048, `PNFL-2047-after-super-bowl.lge`, `PNFL-2048-after-week1.lge`); `conferences` = (2029, the built pair). `_write_config` copies the files to `<tmp_path>/previous/<league>.lge` and `<tmp_path>/upcoming/<league>.lge` (plain folders, not under the config dir), writes `league.toml` with `path` = the upcoming folder, and the rules file. `_generate` passes `--previous`. `_validate` loads the league through `league_files.load_league`. `--bless` also writes the two built conference fixtures. Goldens for 2048 are new files `schedule_2048.*`; the 2026 goldens are deleted.

- [ ] **Step 3: Checksum test** loads each league the same way (a helper shared with the golden test, in `tests/integration/league_files.py`); the conference checksums must still match; the divisions pair is re-pinned from the first run.

- [ ] **Step 4: Run** `uv run pytest -q` (fast suite), then in the background `uv run python -m tests.integration.test_generate_schedule --bless` and `uv run pytest -m slow tests/integration/test_generate_schedule.py -q` to confirm. **Commit** `scheduler: goldens from the real 2047-2048 league files`.

### Task 7: shipped config, release docs, installer script

**Files:**
- Delete: `config/dev/leagues/PNFL/standings/`, `config/dev/leagues/PCFL/standings/`, same under `config/release/`
- Modify: `config/{dev,release}/leagues/PNFL/scheduler.toml` (`[renames.2047]`, `[renames.2048]`, `[renames.2049]` with a comment that 2047's list is to be confirmed), `config/{dev,release}/leagues/PCFL/scheduler.toml` (commented example), `config/release/leagues/PNFL/league.toml` (comment: `path` also gives the upcoming season's `.lge`), `config/release/docs/README.txt`, `COMMANDS.txt`, `SCHEDULER-COMMANDS.txt`, `packaging/sandbox-steps.ps1` (seed checks name `leagues\PNFL\scheduler.toml` and `leagues\PCFL\scheduler.toml`; the two schedule runs copy the fixture `.lge` files into `previous` / `upcoming` folders and pass `--previous` / `--upcoming`; the upgrade's deleted-and-restored file becomes `leagues\PCFL\pdbtoexcel.toml`)
- Test: `tests/unit/scheduler/test_config.py` shipped-file tests (`SHIPPED_STANDINGS` goes; the rules-file test loads each shipped `scheduler.toml`; the conference test checks the PCFL rules values only)

- [ ] **Step 1** Edit, **Step 2** `uv run pytest tests/unit/scheduler/test_config.py tests/integration/test_config.py -q --no-cov`, **Step 3 Commit** `scheduler: standings files replaced by [renames]; release docs`.

### Task 8: design docs and project meta

**Files:** `docs/scheduler/README.md`, `ARCHITECTURE.md`, `phase-1-matchups.md`; `docs/design/architecture.md` (layout tree, Config bullet), `fbpro98-files.md`, `installer.md`; `README.md`; `STATUS.md` (scheduler and fbpro98_lge sections, layout tree); `CHANGELOG.md` (top: `generate-schedule: reads the standings from the previous season's .lge and the conferences, divisions and teams from the upcoming season's; the standings\<season>.league.ini files are gone; renamed teams are listed under [renames.<season>] in scheduler.toml`; `fbpro98_lge: reads the played games, the playoff results and how many games are left`); `WORKLOG.md` (top entry).

- [ ] **Step 1** Edit, CRLF check (`git ls-files --eol`), **Step 2 Commit** `scheduler: docs for league-file standings`.

### Task 9: final checks and review

- [ ] `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright` — all green; slow goldens confirmed.
- [ ] One review pass over the whole branch (`superpowers:requesting-code-review` with the spec); fix what it finds.
- [ ] Hand-off: leave the worktree, two code blocks.
