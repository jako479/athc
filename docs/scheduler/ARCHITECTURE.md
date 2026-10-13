# scheduler — Architecture

CLI tool that generates a league's season schedule with OR-Tools constraint programming, writes it as `.txt` and `.html`, and emits a companion sortable HTML report. No league name or division name lives in the code: both come from the league's game files.

## Module layout

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
│   ├── utils.py                    # make_solver, resolve_workers: the CP-SAT solver setup both phases share
│   └── errors.py                   # SchedulerError
└── writers/
    ├── writer.py                   # ScheduleWriter protocol + factory
    ├── html_writer.py              # HTML schedule (titled by league)
    ├── txt_writer.py               # plain-text schedule
    └── report.py                   # HtmlReportWriter + build_schedule_report

src/athc/cli/generate_schedule.py   # Click command (lazy solver import)
```

## What this package does

- Provides a CLI: `athc generate-schedule [--league name] --season year --previous folder [--upcoming folder] [--seed number] [--time-limit number]`
- Resolves the league (`--league` → `[athc] league`) with the shared `athc.config.load_league_config`; `--upcoming` defaults to the league's `path`
- Reads the previous season's `<league>.lge` (standings) and the upcoming season's (conferences, divisions, names) through `fbpro98_lge`, matches the teams by name with `[renames.<season>]`, ranks the previous season and builds the `League` (`league_files.py`); loads `scheduler.toml` (optional amounts and the renames) from the league's folder
- Solves the schedule in two CP-SAT phases
- Writes `schedule_<season>_<timestamp>.txt` / `.html` and `_report.html` to the current directory, titled by league

## What this package enforces

CLI-level (Click → exit 2):
- `--season` and `--previous` provided; `--time-limit` an integer

Config (`ConfigFileError`, `LeagueError` → `FAIL`, exit 2) — found via `config_dir()` / `ATHC_CONFIG_DIR`, no `--config` flag:
- The league (`--league`, else `[athc] league`) must have a folder `leagues\<NAME>\`; without `--upcoming`, its `league.toml` must set `path`.
- `leagues\<NAME>\scheduler.toml` is **optional**; every key defaults; invalid TOML or a bad value is an error. `[renames.<season>]` keys are season years, values team names; a rename must name a previous-season team and an upcoming-season team, and not a name another previous-season team keeps.
- League-resolved rules: `weeks` must fit the league, `opening_nonconference_weeks` must leave room for every same-conference game, `[rivalries]` must name every team once with exactly one cross-conference pair.

League files (`OSError`, `InvalidLgeError`, `SchedulerError` → `FAIL`, exit 2), each line naming the file:
- Both `<league>.lge` files must exist and parse.
- The previous season must be finished: `Season not finished: N game(s) not played.`
- A team name must not repeat in a file; every previous-season team must match an upcoming one by (renamed) name and vice versa (`Team(s) not in <file>: ...`, with the `[renames.<season>]` hint); no playoff game may be tied.

Domain (`ValueError`, surfaced as `SchedulerError` naming the upcoming file):
- Exactly two conferences of nine teams; no team twice; each division's finish lists exactly its members.

Solver (`SchedulerError` → `FAIL`, exit 2):
- No feasible inventory or schedule within the limits is a one-line error, not a traceback.

## The standings

`league_files.py` ranks the previous season: playoff finish (the last round's winner first, then its loser, then each earlier round's losers; a bye costs nothing), then win percentage, then strength of schedule (opponents' combined regular-season record as a win percentage), then point differential, then file order. Each upcoming division's finish is its members ranked by the previous season with the lge library's `ranked` (the game's own order: win percentage, the manual's tie-breakers under the previous season's divisions, previous-file order). A league whose conferences each hold one division is the conference-only shape. Conferences and divisions carry their file position as `number`: the identity and sort key, since the PNFL's conference names are empty and both conferences have an `East`.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Done** — schedule (and report) written. |
| `2` | **Error** — a `FAIL` line: league, config, no feasible schedule, I/O, or missing solver (ortools); or usage, bad `--season` / `--time-limit` (Click). |

The shared scheme: [architecture.md](../design/architecture.md#console-run-log-and-errors).

## The scheduler

Two-phase CP-SAT. Phase 1 ([phase-1-matchups.md](phase-1-matchups.md)) builds the matchup inventory: structure fixes the same-conference games; the same-place rule (each division place plays the same place in every other-conference division that has that place) and any cross-conference rivalry fix some non-conference games; one CP-SAT solve picks the rest along the `spread` line. Phase 2 ([phase-2-schedule.md](phase-2-schedule.md)) places the inventory into weeks.

## Solver & reproducibility

Both phases run CP-SAT the same way, through one shared setup (`make_solver`): **interleave search** — parallel but reproducible. Two rules make a seed's matchups and schedule identical across runs and machines:

- **Same worker count.** Interleave results change with the number of workers, so both phases run one count from `solver_workers`: a number, or `"auto"` (the default) = this CPU's fast threads minus 2 — the threads on its highest-efficiency-class cores (the P-cores on Intel hybrid CPUs, every core on most AMD CPUs), from Windows' `GetLogicalProcessorInformationEx`. `"auto"` varies by machine, so the report shows the CPU and thread count; setting that number reproduces a seed anywhere. Not CLI-overridable.
- **Deterministic-time budget.** Each solve stops on its own limit — `phase1_time_limit` (default 120) for phase 1, `time_limit` (default 300) for phase 2 — measured in CP-SAT *deterministic time*, so a slow or fast machine reaches the same stopping point.

Also required: the model is built in canonical team order (never Python `set` iteration order). The model checksum test and the golden regression test guard both.

## Testing

One suite in `tests/unit/scheduler/`, parametrized over every league case (two divisional standings variants, the conference league in an even season, an odd season, and with rotation off):

- `test_matchups` (phase 1; matrix in [test-matrix-phase-1-matchups.md](../../tests/unit/scheduler/test-matrix-phase-1-matchups.md)), `test_schedule_builder` (phase-2 model wiring), `test_utils` (the shared solver setup), `test_cpu` (fast-thread count and CPU name) and `test_schedule_rules` (every rule on a solved schedule, through the shared validator; matrix in [test-matrix-phase-2-schedule.md](../../tests/unit/scheduler/test-matrix-phase-2-schedule.md)).
- `test_cli` / `test_config` (CLI, the rules file and `[renames]`, every shipped `config/dev/` and `config/release/` rules file; matrix in [test-matrix-config-loading.md](../../tests/unit/scheduler/test-matrix-config-loading.md)), `test_league_files` (the League from two `.lge` files: the PNFL's real 2047 -> 2048 files reproduce the league's published 2048 order, 2046 -> 2047 covers a realignment with four renames, built `LgeFile`s cover every error and ranking rule), `test_league` (domain), `test_report` (matrix in [test-matrix-report.md](../../tests/unit/scheduler/test-matrix-report.md)), `test_writers`.
- `test_model_checksum` pins both CP-SAT models per league; re-pin only with that league's goldens.

The rule validator is `tests/integration/schedule_validation.py`: it checks every rule that applies to a league and its config, with every amount from the config and the league. The golden regression test ([tests/integration/test_generate_schedule.py](../../tests/integration/test_generate_schedule.py)) runs the CLI per league at a fixed seed, validates the output, and byte-compares the three files to the frozen goldens. The divisional case is the real 2048 PNFL season (`PNFL-2047-after-super-bowl.lge`, `PNFL-2048-after-week1.lge`); the conference case's league files are built by [tests/integration/league_files.py](../../tests/integration/league_files.py) from the test league's tables. Regenerate the built files and both golden sets with `python -m tests.integration.test_generate_schedule --bless`. Solver-backed tests are `slow`.
