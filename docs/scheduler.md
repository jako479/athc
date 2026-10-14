# generate-schedule

Generates a league's season schedule with OR-Tools, plus a companion sortable HTML report.

## Install

OR-Tools (the solver) is a required dependency, so any install includes it. For development:

```bash
uv sync
```

## Usage

```bash
athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge
athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge --seed 7
athc generate-schedule --season 2030 --league PCFL --previous D:\PCFL\2029\PCFL.lge --upcoming D:\PCFL\2030\PCFL.lge
athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge --time-limit 900
```

`--season YEAR` is required. `--league NAME` names the league (default: the one set with `athc config set league`). The league data comes from two of the game's own league files, each a `.lge` file named outright:

- `--previous FILE` — the previous season's `.lge`, saved after its last playoff game: the standings (each team's record, opponents and playoff finish). Default: the `--upcoming` file, which then gives the standings too, and `[renames.<season>]` is ignored.
- `--upcoming FILE` — the upcoming season's `.lge`: the conferences, divisions and team names. Default: `<league>.lge` in `path` in the league's `league.toml`, the folder that holds the league's files. With neither: `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.`
- `--seed NUMBER` — 0 to 2147483647, for a repeatable run; without it a seed from 0 to 1,000,000 is drawn, and the last line shows it.
- `--time-limit LIMIT` — 1 or more, in the solver's own time units, not seconds; it replaces `time_limit` (placing games into weeks) for this run only.

A file's season cannot be read from it, so a `--previous` of the wrong season shows only through its team names (`Team(s) not in <file>: ...`).

Teams are matched by name. A team that changed its name between the two seasons is listed in the league's `scheduler.toml` (in the league's folder in the athc settings folder; find it with `athc config path`), one table per upcoming season: `[renames.2048]` with `Baltimore = "Los Angeles"` (previous name = new name). The same file holds the rule amounts and solver settings; every key defaults, and `time_limit` and `phase1_time_limit` must be positive numbers.

It writes a `.txt` and `.html` schedule plus a sortable HTML report to the **current folder**, named `schedule_<season>_<timestamp>` (the report adds `_report.html`); a rerun in the same minute replaces them. Progress (`Generating the <season> schedule`, `Phase 1: ...`, `Phase 2: ...`) prints on stderr as it runs; then `OK   <file>` per file written and `Generated <n> games (seed <s>)`. Exit `0` = written, `2` = an error (`FAIL <why>`: config, a league file, no feasible schedule, I/O, `Missing ortools. Reinstall athc.`) or bad arguments, `130` = Ctrl+C. Shared console and codes: [architecture](architecture.md#console-run-log-and-errors).

Ctrl+C stops the run with `FAIL Interrupted.` and nothing written; during a solve, the search stops at the press. A press while the three files are written takes effect once all three are written.

## The standings

From the previous season's file. An unfinished season (games not played) is `WARN <file>: Season not finished: <n> game(s) not played.`, and the run goes on with the games played; a new league with no game played is ordered by the coin toss.

- Overall order (the 1-18 ranks, and the 1-9 conference ranks the difficulty line uses): playoff finish first (champion, runner-up, then the round each team went out in, then the teams that missed the playoffs), then win percentage, then strength of schedule (opponents' combined record that season, tougher first), then the previous season's division finish (the team's place in the division it played in, ranked as below), then point differential, then a coin toss. This reproduces the PNFL's own published order.
- Each division's finish order (the same-place pairs): the upcoming division's members ranked by their previous season the way the game ranks a finished season (win percentage, then the manual's tie-breakers under the previous season's divisions, then the coin toss; the lge library's `ranked`), so a division whose membership changed still gets an order.
- The coin toss is one shuffle of the previous season's teams drawn from the run's seed; no file's team order breaks a tie.

## Teams that moved

A team is matched to its previous season by name, so a team that moved keeps its previous record, games and playoff finish. Two cases:

- Renamed, same division: list it under `[renames.<season>]` and it keeps its division place under the new name (2048: `Baltimore = "Los Angeles"`).
- In a different division (or conference): that division's finish order is its upcoming members ranked on their previous seasons, so the other members' places shift around the newcomer; the overall 1-18 order is unchanged.

2047 AFC East: Miami (11-5 as Houston) and Jacksonville (5-11) came over from the West, Buffalo (10-6) and New England (3-13) stayed, so the East's finish order became Miami, Buffalo, Jacksonville, New England.

## League shapes

| | With divisions (the PNFL) | Conferences only (the PCFL) |
|---|---|---|
| League file | two or more divisions in a conference | one division per conference |
| Weeks | 16 (`[league] weeks`, the default) | 12 |
| Same-conference games | division rivals twice, rest of the conference once | every conference team once |
| Non-conference | same-place pairs fixed, rest by the difficulty line | the cross-conference rivalry fixed, rest by the line |
| Season shape | NFL-style rules ([phase 2](scheduler-phase-2-schedule.md)) | opening non-conference weeks, conference-sequence cap, rivalry week last |

Conferences and divisions go by their position in the league file (names may be empty or repeat); division sizes are their team counts. Shipped files, in `config/dev/` and `config/release/`: `leagues\PNFL\` and `leagues\PCFL\`, each with its `scheduler.toml`.

## Design

- [Phase 1 — matchups](scheduler-phase-1-matchups.md)
- [Phase 2 — schedule placement](scheduler-phase-2-schedule.md)
- [Prior art — the current NFL formula](research/nfl-formula.md) — background, not what athc uses
- [Research — NFL schedule patterns](research/nfl-schedules.md) — provenance of the phase-2 rules
- [Research — CP-SAT rule design patterns](research/cpsat-rule-patterns.md) — hard/soft rules, preventing solver anomalies

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

One test suite runs every league: two divisional standings variants and the conference league. The league-file loader is tested on the PNFL's real 2046-2048 files. Solver-backed tests are `slow` and skipped by default.

## How it works

Two phases. Phase 1 picks every matchup: league structure fixes the same-conference games, the same-place rule and any cross-conference rivalry fix some non-conference games, and CP-SAT picks the rest along a configurable difficulty line. Phase 2 places the matchups into weeks with CP-SAT. The same code serves every league: the upcoming season's league file gives the structure, the previous season's the standings, the rules file the amounts.

### Module layout

```
src/athc/scheduler/                 # subsystem source
├── __init__.py
├── main.py                         # generate_schedule() orchestration
├── config.py                       # SchedulerConfig, load_scheduler_config() ([renames] included), rules path
├── league_files.py                 # load_league(): the League from the previous and upcoming .lge files
├── cpu.py                          # this CPU's name and fast threads (Windows), for solver_workers = "auto"
├── domain/
│   ├── league.py                   # League, Conference, Division, Team; build_league()
│   └── schedule.py                 # Schedule, Game
├── schedulers/
│   ├── scheduler.py                # the scheduler entry: phase 1 then phase 2
│   ├── matchup_builder.py          # phase 1: MatchupBuilder (structure, same-place pairs, rivalries, CP-SAT line)
│   ├── schedule_builder.py         # phase 2: ScheduleBuilder (CP-SAT week placement)
│   ├── types.py                    # MatchupPlan, SchedulerResult, get_scheduler
│   ├── utils.py                    # make_solver, resolve_workers, run_solver, write_hold: the CP-SAT setup both phases share, and Ctrl+C
│   └── errors.py                   # SchedulerError
└── writers/
    ├── writer.py                   # ScheduleWriter protocol + factory
    ├── html_writer.py              # HTML schedule (titled by league)
    ├── txt_writer.py               # plain-text schedule
    └── report.py                   # HtmlReportWriter + build_schedule_report

src/athc/cli/generate_schedule.py   # Click command (lazy solver import)
```

### What this package does

- Provides a CLI: `athc generate-schedule [OPTIONS]`, with `--season YEAR` (required), `--previous FILE`, `--upcoming FILE`, `--seed NUMBER`, `--time-limit LIMIT` and `--league NAME`
- Resolves the league (`--league` → `[athc] league`) with the shared `athc.config.load_league_config`; `--upcoming` defaults to `<league>.lge` in the league's `path`, and `--previous` to the upcoming file
- Reads the previous season's `.lge` file (standings), then the upcoming season's (conferences, divisions, names), through `fbpro98_lge`, matches the teams by name with `[renames.<season>]` (none when one file gives both), ranks the previous season and builds the `League` (`league_files.py`); loads `scheduler.toml` (optional amounts and the renames) from the league's folder first
- Solves the schedule in two CP-SAT phases
- Writes `schedule_<season>_<timestamp>.txt` / `.html` and `_report.html` to the current folder, titled by league

### What this package enforces

CLI-level (Click → exit 2):
- `--season` provided; `--seed` an integer from 0 to 2147483647 (`must be 0 to 2147483647, got -1.`); `--time-limit` an integer of 1 or more (`must be 1 or more, got 0.`). The bounds are athc callbacks raising Click's `BadParameter`, so a non-integer keeps Click's `is not a valid integer.`

Config (`ConfigFileError`, `LeagueError` → `FAIL`, exit 2) — found via `config_dir()` / `ATHC_CONFIG_DIR`, no `--config` flag:
- The league (`--league`, else `[athc] league`) must have a folder `leagues\<NAME>\`; without `--upcoming`, its `league.toml` must set `path`, else `League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.`
- `leagues\<NAME>\scheduler.toml` is **optional**; every key defaults; invalid TOML or a bad value is an error. `[solver] time_limit` and `phase1_time_limit` must be positive numbers (`Must be a positive number.`). `[renames.<season>]` keys are season years, values team names; a rename must name a previous-season team and an upcoming-season team, and not a name another previous-season team keeps.
- League-resolved rules: `weeks` must fit the league, `opening_nonconference_weeks` must leave room for every same-conference game, `[rivalries]` must name every team once with exactly one cross-conference pair.

League files (`OSError`, `InvalidLgeError`, `SchedulerError` → `FAIL`, exit 2), each line naming the file:
- Both `.lge` files must exist and parse; a missing one is Windows' own phrase.
- An unfinished previous season is a `WARN`, not an error: `Season not finished: N game(s) not played.`, and the standings come from the games played.
- A team name must not repeat in a file; every previous-season team must match an upcoming one by (renamed) name and vice versa (`Team(s) not in <file>: ...`, with the `[renames.<season>]` hint); no playoff game may be tied.

Domain (`ValueError`, surfaced as `SchedulerError` naming the upcoming file):
- Exactly two conferences of nine teams; no team twice; each division's finish lists exactly its members.

Solver (`SchedulerError` → `FAIL`, exit 2):
- No feasible inventory or schedule within the limits is a one-line error, not a traceback.

### The standings

`league_files.py` ranks the previous season: playoff finish (the last round's winner first, then its loser, then each earlier round's losers; a bye costs nothing), then win percentage, then strength of schedule (opponents' combined regular-season record as a win percentage), then the previous season's division finish (the team's place in the division it played in, ranked with `ranked` and the coin toss last), then point differential, then the coin toss. Each upcoming division's finish is its members ranked by the previous season with the lge library's `ranked` (the game's own order: win percentage, the manual's tie-breakers under the previous season's divisions, then the given order, which is the coin toss). The coin toss is one `random.Random(seed)` shuffle of the previous season's teams, drawn from the run's seed, so no file's team order breaks a tie and a seed reproduces its standings. A league whose conferences each hold one division is the conference-only shape. Conferences and divisions carry their file position as `number`: the identity and sort key, since the PNFL's conference names are empty and both conferences have an `East`. The same order is the standings library's `scheduler` method; the rules beside the game's and the NFL's: [standings-tie-breakers.md](research/standings-tie-breakers.md).

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Done** — schedule (and report) written. |
| `2` | **Error** — a `FAIL` line: league, config, no feasible schedule, I/O, or missing solver (ortools); or usage, bad `--season` / `--seed` / `--time-limit` (Click). |
| `130` | **Interrupted** — Ctrl+C, `FAIL Interrupted.`: nothing written, or all three files when pressed while they are written. |

The shared scheme: [architecture.md](architecture.md#console-run-log-and-errors).

### The scheduler

Two-phase CP-SAT. Phase 1 ([scheduler-phase-1-matchups.md](scheduler-phase-1-matchups.md)) builds the matchup inventory: structure fixes the same-conference games; the same-place rule (each division place plays the same place in every other-conference division that has that place) and any cross-conference rivalry fix some non-conference games; one CP-SAT solve picks the rest along the `spread` line. Phase 2 ([scheduler-phase-2-schedule.md](scheduler-phase-2-schedule.md)) places the inventory into weeks.

### Solver & reproducibility

Both phases run CP-SAT the same way, through one shared setup (`make_solver`): **interleave search** — parallel but reproducible. Two rules make a seed's matchups and schedule identical across runs and machines:

- **Same worker count.** Interleave results change with the number of workers, so both phases run one count from `solver_workers`: a number, or `"auto"` (the default) = this CPU's fast threads minus 2 — the threads on its highest-efficiency-class cores (the P-cores on Intel hybrid CPUs, every core on most AMD CPUs), from Windows' `GetLogicalProcessorInformationEx`. `"auto"` varies by machine, so the report shows the CPU and thread count; setting that number reproduces a seed anywhere. Not CLI-overridable.
- **Deterministic-time budget.** Each solve stops on its own limit — `phase1_time_limit` (default 120) for phase 1, `time_limit` (default 300) for phase 2 — measured in CP-SAT *deterministic time*, so a slow or fast machine reaches the same stopping point.

Also required: the model is built in canonical team order (never Python `set` iteration order). The model checksum test and the golden regression test guard both.

Ctrl+C: `make_solver` turns CP-SAT's own handling off (`catch_sigint_signal = False`). With it on, a press ends the process at once with no line: OR-Tools keeps its handler on the solving thread, and Windows runs the Ctrl+C handler on a thread of its own. With it off alone, Python hears the press only when the solve returns, up to the whole budget later. So both builders solve through `run_solver`, which installs a console control handler (`SetConsoleCtrlHandler`) for the length of the solve: a press calls `stop_search()`, and `KeyboardInterrupt` follows once the solve returns, which the one place prints as `FAIL Interrupted.`, exit 130. Outside a solve, Python's own handler does the same. The three output files are written inside `write_hold`, whose handler only records a press, so a press there takes effect once all three are written. The best schedule found so far is not kept.

### Testing

One suite in `tests/unit/scheduler/`, parametrized over every league case (two divisional standings variants, the conference league in an even season, an odd season, and with rotation off):

- `test_matchups` (phase 1; matrix in [test-matrix-phase-1-matchups.md](../tests/unit/scheduler/test-matrix-phase-1-matchups.md)), `test_schedule_builder` (phase-2 model wiring), `test_utils` (the shared solver setup, the Ctrl+C solve and the write hold), `test_cpu` (fast-thread count and CPU name) and `test_schedule_rules` (every rule on a solved schedule, through the shared validator; matrix in [test-matrix-phase-2-schedule.md](../tests/unit/scheduler/test-matrix-phase-2-schedule.md)).
- `test_cli` / `test_config` (CLI, the rules file and `[renames]`, every shipped `config/dev/` and `config/release/` rules file; matrix in [test-matrix-config-loading.md](../tests/unit/scheduler/test-matrix-config-loading.md)), `test_league_files` (the League from two `.lge` files: the PNFL's real 2047 -> 2048 files reproduce the league's published 2048 order, 2046 -> 2047 covers a realignment with four renames, built `LgeFile`s cover every error and ranking rule), `test_league` (domain), `test_report` (matrix in [test-matrix-report.md](../tests/unit/scheduler/test-matrix-report.md)), `test_writers`.
- `test_model_checksum` pins both CP-SAT models per league; re-pin only with that league's goldens.

The rule validator is `tests/integration/schedule_validation.py`: it checks every rule that applies to a league and its config, with every amount from the config and the league. The golden regression test ([tests/integration/test_generate_schedule.py](../tests/integration/test_generate_schedule.py)) runs the CLI per league at a fixed seed, validates the output, and byte-compares the three files to the frozen goldens. The divisional case is the real 2048 PNFL season (`PNFL-2047-after-super-bowl.lge`, `PNFL-2048-after-week1.lge`); the conference case's league files are built by [tests/integration/league_files.py](../tests/integration/league_files.py) from the test league's tables. Regenerate the built files and both golden sets with `python -m tests.integration.test_generate_schedule --bless`. Solver-backed tests are `slow`.
