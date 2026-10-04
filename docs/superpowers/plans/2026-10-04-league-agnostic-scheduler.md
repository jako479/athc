# League-agnostic scheduler — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No league or division name in scheduler code or tests; `--league` picks `<league>.<season>.ini` and `rules/<league>.scheduler.toml`; one validator and one test suite serve every league.

**Architecture:** Conferences and divisions come from the standings file keys; the same-place rule replaces the fixed PNFL table; writers take the league name; one parametrized test suite over all league cases.

**Tech Stack:** Python 3.12, Click, OR-Tools CP-SAT, pytest.

**Spec:** `docs/superpowers/specs/2026-10-04-league-agnostic-scheduler-design.md`

## Global Constraints

- Python 3.12 idioms; ruff, pyright standard, coverage >= 92%.
- Every limit tested on both sides; never edit expected data or assertions to pass.
- Commits one line, prefixed `scheduler:`; no AI mention, no trailers.
- Text files UTF-8 CRLF with a final newline.
- PNFL CP-SAT model hashes and the PNFL schedule `.txt` golden must not change.

## Review Focus

- A standings key without an underscore in `[DivisionStandings]` → clear `ConfigError`, not a crash (Task 2).
- `--league` naming a league with no `[league.X]` section → exit 1 with a one-line message (Task 4).
- `--league` with no `<league>.<season>.ini` → exit 1 naming the expected path (Task 4).
- Solver infeasible → exit 1, not the generic exit 2 (Task 4).
- A rules file whose `weeks` or rivalries do not fit the shipped standings → test failure (Task 4).

## Assumption (design conflict)

The design wants the HTML schedule title to carry the league name and the golden league to be named `divisions`, and also wants the HTML golden byte-identical. Both cannot hold. Resolution: the `.txt` golden stays byte-identical (the schedule itself); the `.html` golden changes only in its two league-name title lines; the report golden changes in title and Scheduler line. Verified by diff in Task 7 and reported.

---

### Task 1: Same-place rule computed from divisions

**Files:** Modify `src/athc/scheduler/schedulers/fixed_cpsat_builder.py`, `tests/unit/scheduler/fixed_cpsat/test_fixed_cpsat_inventory.py`.

- [ ] Test: replace place-table tests with `_expected_same_place_pairs(league)` (each place vs the same place in every other-conference division that has it) and assert `plan.fixed_nonconference_pairs == expected` and `len == 17`.
- [ ] Code: `_same_place_pairs()` set comprehension over `league.division_standings`; delete `FIXED_NONCONF_PLACE_OPPONENTS`, `_validate_fixed_place_table`, `_PlaceSlot`.
- [ ] Run fast suite (fingerprint test proves the model is unchanged). Commit `scheduler: same-place non-conference games computed from the divisions`.

### Task 2: Conferences and divisions from the standings file

**Files:** Modify `src/athc/scheduler/domain/league.py`, `src/athc/scheduler/config.py`, tests referencing `AFC`/`AFC_EAST`… (`conftest.py`, `test_league.py`, `test_config.py`, `test_writers.py`, `test_schedule_builder.py`, `fixed_cpsat/*`), `tests/integration/schedule_validation.py`.

- [ ] Tests: `build_league(standings, overall, divisions=True/False)`; key `AFCEAST` rejected; 1 and 3 conferences rejected, 2 accepted; 8/10-team conference rejected, 9 accepted; division size from the file; duplicates rejected.
- [ ] Code: one `build_teams(standings, *, divisions)` and one `build_league(..., *, divisions)`; remove `AFC`, `NFC`, `AFC_EAST`…, `PNFL_DIVISIONS*`, `build_conference_teams`, `build_conference_league`; `load_league` passes `divisions=has_divisions`.
- [ ] Tests build divisions/conferences locally; validator uses `division.expected_size`.
- [ ] Fast suite green. Commit `scheduler: conferences and divisions come from the standings file`.

### Task 3: Writers take the league name

**Files:** Modify `writers/html_writer.py`, `writers/report.py`, `writers/writer.py`, `scheduler/main.py`, `test_writers.py`, `test_report.py`, `tests/unit/scheduler/conftest.py`.

- [ ] Tests: `HtmlScheduleWriter(path, league_name=...)` title contains the name; `HtmlReportWriter(path, league_name=...)` renders `<name> Schedule Report`; `get_writer(fmt, output, league_name)`.
- [ ] Code: required `league_name` fields; `main.generate_schedule(*, league: str, ...)` passes it.
- [ ] Commit `scheduler: writers take the league name`.

### Task 4: `--league`, file resolution, shipped files

**Files:** Modify `src/athc/config.py` (`resolve_league`), `scheduler/config.py` (`scheduler_rules_path(league)`, `find_league_path(league, season)`, `load_scheduler_config(path, *, required=True)`), `cli/generate_schedule.py`, `scheduler/main.py`; rename `dev/<s>.league.ini` → `dev/PNFL.<s>.ini`, same in `release/`; move `dev/leagues/PCFL/...` → `dev/PCFL.2029.ini`, `dev/rules/PCFL.scheduler.toml`, copies in `release/`; delete `dev/leagues/`; `[league.PCFL]` in both `athc.ini`; `release-build.ps1` and `install.bat` stage `*.*.ini`; `docs/design/installer.md`; research script path strings. Tests: `test_cli.py`, `test_config.py` (unit), `tests/integration/test_config.py`.

- [ ] Tests: `resolve_league` arg/env/default/none/unknown; rules path and standings path per league; `load_scheduler_config` missing → error, `required=False` → defaults; CLI: no league → 1, missing standings → 1, `SchedulerError` → 1, `--league` resolves both files; shipped standings and rules files parametrized over `dev/` and `release/`; `[league.PCFL]` loads from `release/athc.ini`.
- [ ] Code + file moves as above.
- [ ] Commit `scheduler: --league selects <league>.<season>.ini and rules/<league>.scheduler.toml; PCFL files ship in dev/ and release/`.

### Task 5: Renames

**Files:** `git mv fixed_cpsat_builder.py matchup_builder.py`, `fixed_cpsat_scheduler.py scheduler.py`; classes `MatchupBuilder`, `_NonConferenceModel`; `SCHEDULER_DESCRIPTION = "two-phase CP-SAT"`; `git mv docs/scheduler/phase-1-matchups-fixed-cpsat.md phase-1-matchups.md` + links; `git mv test_pnfl_model_fingerprint.py test_model_checksum.py` parametrized per league (PNFL hashes unchanged; conferences hash pinned once computed) using golden inputs `tests/integration/data/divisions.2026.ini`, `divisions.scheduler.toml`, `conferences.2029.ini`, `conferences.scheduler.toml` (conferences rules mirror the PCFL file but `spread = 2.5` so the fast suite stays fast).

- [ ] Commit `scheduler: league-neutral module, class and doc names; model checksum per league`.

### Task 6: One validator, one test suite

**Files:** Rewrite `tests/integration/schedule_validation.py` (`validate_schedule(schedule, league, config, *, season)`); `tests/unit/scheduler/conftest.py` (league cases, `solved*` fixtures, shared cache); new `test_matchups.py`, `test_schedule_rules.py`; delete `fixed_cpsat/`, `conference_league/`; `test_report.py` reads the shared result; matrices (`test-matrix-phase-1-matchups.md`, phase-2 matrix absorbs conference rows; delete the conference matrix).

- [ ] Fast suite green. Commit `scheduler: one rule validator and one test suite parametrized over every league`.

### Task 7: Golden CLI test per league

**Files:** `tests/integration/test_generate_schedule.py` parametrized (divisions 2026 seed 0; conferences 2029 seed 0); goldens `expected/schedule_2026.*` re-blessed, `expected/schedule_2029.*` new; `tests/integration/README.md`.

- [ ] Run `--bless`; verify `schedule_2026.txt` unchanged in `git diff`, `.html` differs only in the two title lines, report only in title + Scheduler line.
- [ ] Commit `scheduler: golden CLI test per league`.

### Task 8: Docs and meta

**Files:** `docs/scheduler/README.md`, `ARCHITECTURE.md`, `phase-1-matchups.md`, `phase-2-schedule.md`, `docs/design/config.md`, `docs/design/cli.md`, `release/docs/SCHEDULER-COMMANDS.txt`, `STATUS.md`, `WORKLOG.md`, `CHANGELOG.md`; CRLF for the spec and this plan.

- [ ] Commit `scheduler: docs and meta for the league-agnostic scheduler`.

### Finish

- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` (one per call), then `uv run pytest -m slow`.
- [ ] One whole-branch reviewer; fix findings.
- [ ] finishing-a-development-branch: leave the worktree; two code blocks (squash-merge + commit; worktree removal + branch deletion).
