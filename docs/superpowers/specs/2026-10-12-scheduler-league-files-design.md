# generate-schedule: standings and structure from the league files — design

Date: 2026-10-12. Status: written unattended on the user's go-ahead; awaiting review.

## Goal

`generate-schedule` reads what it needs from the game's own league files
instead of a hand-written `<season>.league.ini`:

- the **previous season's** `.lge` gives the standings (regular-season
  records, playoff results);
- the **upcoming season's** `.lge` gives the conferences, divisions and team
  names.

The `standings\` folders and the `[OverallStandings]` / `[DivisionStandings]`
/ `[ConferenceStandings]` INI format go away.

## Current state (main 2f4b2a8)

- `fbpro98_lge` reads names and regular-season records; division and
  conference standings rank by win percentage, point differential, file
  order. Playoff games and unplayed games are skipped unread.
- `fbpro98_lg2` is complete for its purpose and is not needed here.
- The scheduler's `League` (`domain/league.py`) is built from INI name
  tables: `<CONFERENCE>_<DIVISION>` keys, conferences and divisions compared
  and sorted by name. `scheduler/config.py` loads the INI;
  `generate-schedule` resolves `standings\<season>.league.ini`.
- The user's season archive holds every week's league files:
  `E:\PNFL\League - League Files\<season>\<yy>PNFL<n>\PNFL.lge`, the league
  just after week `n`; `<yy>PNFL19` is after the Super Bowl.

## Facts checked against the real files

- A relocation renames the team; a realignment moves it to another division
  and changes the team numbers (2046 -> 2047 swapped two teams between the
  AFC divisions). So teams are matched between the two files **by name**,
  with a per-season list of renames; never by team number.
- The league's final 1-18 order (the shipped 2048 standings, built by the
  user from pnfl.biz) is reproduced exactly by: playoff finish, then win
  percentage, then strength of schedule (opponents' combined record that
  season, tougher first), then point differential. Point differential alone
  gets two tie groups wrong. The lge library's own standings order (no
  strength of schedule) stays as the user decided it; the scheduler adds
  strength of schedule for the overall order only.
- 2046 -> 2047: the shipped 2047 standings file names Houston -> Miami,
  New York A -> Cincinnati, Indianapolis -> Baltimore, New York N -> New York
  in its header and division section, but its overall section fits
  New York A -> Baltimore and Indianapolis -> Cincinnati. The real list
  comes in the morning; the shipped renames follow the header for now.

## Decisions

From the request:

- Both libraries exist; only `fbpro98_lge` grows, and only by what this
  feature needs: played games (regular season by week, playoffs by round)
  and the count of games not yet played.
- Same architecture, errors and wording as the other libraries and
  commands; messages and behavior unchanged unless this change needs it.

Taken unattended, each the mainstream default:

- `--previous folder` (required) names the folder holding the previous
  season's league files; `--upcoming folder` (optional) the upcoming
  season's, defaulting to `path` in `league.toml`, the folder that holds the
  league's files. Each folder's `<league>.lge` is read.
- Renames live in `scheduler.toml`, one table per upcoming season:
  `[renames.2048]` with `Baltimore = "Los Angeles"` (previous name = new
  name). Teams not listed match by name.
- A league whose conferences each hold one division is a league without
  divisions (the conference-only shape); any conference with two or more
  divisions makes it a league with divisions.
- The previous season must be finished: every regular-season and playoff
  game played. Playoff finish ranks a team by the round it went out in; the
  champion ranks first, the runner-up second.
- Each upcoming division's finish order is its members ranked by their
  previous-season records with the library's standings order (win
  percentage, point differential, previous-file order), so a division whose
  membership changed still gets a sensible order.
- Conferences and divisions are identified and ordered by file position
  (`number`), not name: the PNFL's conference names are empty and both
  conferences have an `East`. The canonical team order (conference, division,
  metro) is unchanged for every existing test league, so the pinned CP-SAT
  models for the conference league stay the same; the divisional golden
  moves to real data and is re-frozen.

## fbpro98_lge additions

```python
Game(home: Team, home_score: int, away: Team, away_score: int)
Game.winner / Game.loser          # None on a tie
LgeFile.weeks: tuple[tuple[Game, ...], ...]      # regular season, played games per week
LgeFile.playoffs: tuple[tuple[Game, ...], ...]   # played games per round
LgeFile.unplayed_games: int                      # regular season and playoffs
ranked(lge, teams=None) -> tuple[Team, ...]      # the library's ranking, public
```

- The reader keeps the raw games while walking the schedule, builds the
  teams, then the `Game` objects. A played game, playoff or regular, naming a
  team outside 1..N is an `InvalidLgeError` (today only regular ones are
  checked). Unplayed games are still skipped, counted.
- `Division.standings` and `Conference.standings` are ranked by the reader
  with the same rule; `ranked` is the public call for any teams of a file,
  every team by default.

## Scheduler: a League from two league files

New module `src/athc/scheduler/league_files.py`:

```python
load_league(league, previous_dir, upcoming_dir, renames, *, rules_path) -> League
```

1. Read both files (`read_lge`); `OSError` and `InvalidLgeError` propagate.
2. Previous season not finished -> `SchedulerError`, naming the previous
   file: `Season not finished: 3 game(s) not played.`
3. A team name repeated in either file -> `SchedulerError` naming that file.
4. Renames: a previous name not in the previous file, or a new name not in
   the upcoming file -> `ConfigFileError` naming `scheduler.toml`:
   `[renames.2048] Baltimore: Not a team in <file>.`
5. Match every previous team to an upcoming team by (renamed) name. Leftovers
   on either side -> `SchedulerError` naming the previous file: `Team(s) not
   in <upcoming file>: Baltimore. List renamed teams under [renames.2048] in
   <scheduler.toml>.` (or the upcoming file: `Team(s) not in <previous
   file>: ...`).
6. Build the domain from the upcoming file: `Conference(number, name)`,
   `Division(number, name, conference, expected_size)`, `Team(metro=name,
   ...)`; no divisions when every conference has one.
7. Division finish: the library's `ranked` over each upcoming division's
   members' previous-season teams, under the previous season's own
   divisions. Overall: playoff finish, win percentage, strength of schedule,
   point differential, previous-file order.
8. `build_league(teams, overall, division_standings)`; its `ValueError`
   (two conferences of nine, duplicates) becomes a `SchedulerError` naming
   the upcoming file.

`domain/league.py`: `Conference` and `Division` gain `number` (first field);
`build_league` takes built objects instead of name tables; `ordered_teams`,
`League.conferences` and `League.divisions` order by number. The INI
`build_teams` and key parsing go. `SchedulerError`'s docstring widens to
cover a league the scheduler cannot build from its files.

`scheduler/config.py`: `load_league`, `find_league_path`, the INI helpers and
`STANDINGS_DIR` go; `SchedulerConfig.renames: Mapping[int, Mapping[str,
str]]` is parsed from `[renames.<season>]` (season a year; values non-empty
strings; a new name used twice or a team renamed to itself is an error).

`scheduler/main.py`: `generate_schedule(league, season, config_path,
previous_dir, upcoming_dir, ...)` loads the rules, then the league through
`league_files.load_league` with `config.renames.get(season, {})`.

## Command

```
athc generate-schedule [-h] --season year --previous folder [--upcoming folder]
                       [--seed number] [--time-limit number] [--league name]
```

`--upcoming` absent: `path` from `league.toml` (its key moves to
`athc.config.LEAGUE_PATH_KEY`, shared with `check-ppp`); no `path` ->
`ConfigFileError` as `check-ppp` words it. Output and result lines unchanged.

## Shipped config

- Delete `config/dev/leagues/*/standings/` and `config/release/leagues/*/standings/`.
- PNFL `scheduler.toml` gains `[renames.2047]`, `[renames.2048]`,
  `[renames.2049]` from the old standings headers; PCFL's a commented example.
- Release docs (`README.txt`, `COMMANDS.txt`, `SCHEDULER-COMMANDS.txt`), the
  installer sandbox script and `installer.md` lose the standings folder and
  describe the two folders and `[renames]`.

## Tests

- `fbpro98_lge`: games and playoffs from the 2047 fixtures (after week 16: no
  playoff game; after the Super Bowl: 4, 2, 1 games, champion Miami);
  `unplayed_games` before week 1, after week 16, after the Super Bowl; built
  bytes: a tie's `winner` is None, an unplayed playoff game skipped and
  counted, a played playoff game with team 0 / N+1 rejected, team 1 / N
  accepted; `standings` public.
- Scheduler unit tests: `league_files` on the real 2047 -> 2048 files equals
  the shipped 2048 standings (overall and divisions); 2046 -> 2047 handles
  the realignment and four renames; every error above, both sides of each
  limit; `[renames]` parsing. Domain tests move from key parsing to built
  objects. CLI tests cover `--previous`, `--upcoming` and the `path`
  default.
- Golden integration test: `divisions` becomes the real 2047 -> 2048 season
  (previous `PNFL-2047-after-super-bowl.lge`, upcoming
  `PNFL-2048-after-week1.lge`, season 2048, one rename) with re-frozen
  goldens and checksums; `conferences` keeps its league through a built
  `.lge` pair (previous with results, upcoming without), written by the
  `--bless` script and checked by a test, so its goldens stay.
- Fixtures: the four real files above in `tests/integration/data/`; the INI
  fixtures and `make_league_dir`'s `standings\` go.

## Docs

`docs/scheduler/README.md`, `ARCHITECTURE.md`, `phase-1-matchups.md`;
`docs/fbpro98_lge/README.md`, `ARCHITECTURE.md`; `docs/design/architecture.md`
(config layout, library list), `fbpro98-files.md`, `installer.md`; test
matrices; `README.md`, `STATUS.md`, `CHANGELOG.md`, `WORKLOG.md`.

## Open for the morning

- The real rename lists (2046 -> 2047 in particular).
- Where the renames belong (`scheduler.toml` table vs `league.toml`) and
  whether `--upcoming` should default to `path`.
- Division ties: the game's own screen put 2046 Chicago ahead of Green Bay
  (same record, Green Bay's point differential better); the library's
  order, as decided, uses point differential.

## Out of scope

- Reading anything else from the `.lge`; writing league files.
- The lg2 library; other commands.
