# Scheduler: league-agnostic code, config layout and one test suite — design

Date: 2026-10-04. Status: approved by the user; ready for the implementation plan.

## Goal

No league name or division name anywhere in scheduler code or tests. The PNFL
and the PCFL are clones that differ only in their standings file and rules
file; both run through the same command, the same two builders, the same
validator and the same tests. Fixed structure stays fixed: 18 teams, two
conferences of nine.

## Current state (branch `worktree-league-agnostic`, on main 385a6b2)

- The PCFL work is merged (47f083a): one matchup builder and one schedule
  builder serve both leagues, driven by `League` (from the standings file) and
  the rules file (`[league] weeks`, `[phase2]` keys, `[rivalries]`).
- Still league-specific: file resolution (`rules/PNFL.scheduler.toml`,
  `<season>.league.ini`, no `--league`), the PNFL division constants and the
  same-place table in `fixed_cpsat_builder.py`, the writers' "PNFL" titles,
  module/class names, and two test folders (`fixed_cpsat/`, `conference_league/`)
  with league-specific test data and names.
- The PCFL data files sit at `dev/leagues/PCFL/...`, a layout the user did not
  want; main's layout is `dev/rules/<League>.<tool>.toml` and season files in
  `dev/`.

## Config layout (the user's decision)

- Standings: `<league>.<season>.ini`, no `.league` segment, INI as today:
  `dev/PNFL.2045.ini` … `PNFL.2049.ini`, `dev/PCFL.2029.ini`; the same in
  `release/` plus `release/PCFL.2029.ini`.
- Rules: `dev/rules/PCFL.scheduler.toml` (moved from `dev/leagues/PCFL/rules/
  scheduler.toml`, `phase1_time_limit = 180`) and a copy in `release/rules/`.
  Delete `dev/leagues/`.
- `[league.PCFL]` in `dev/athc.ini` and `release/athc.ini` with
  `play_path = E:\SIERRA\FbPro98\PCFL` and
  `db_path = E:\PNFL\Game Log Database\49W4\pcfl_athc.db` (no playpool rules).
- `release/release-build.ps1` stages `*.*.ini` instead of `*.league.ini`.
- Code resolves `rules/<league>.scheduler.toml` and `<league>.<season>.ini`
  in the config dir.

## Command

- `generate-schedule` takes the shared `--league` option from
  `athc.cli.league_option`; the name resolves through `athc.config.load_league`
  (option → `ATHC_LEAGUE` → `[athc] default_league`; `LeagueError` if none).
- The league name flows to `main.generate_schedule` and into both writer titles
  (`<league> Schedule Report`, the HTML schedule title).
- A solver `SchedulerError` ("no feasible schedule", from either phase) exits 1
  with a one-line message like config errors do; today it falls through to the
  generic "unexpected error" exit 2. Add a CLI test for it. No per-rule
  "force a violation and expect infeasible" tests (the user declined them).

## League-agnostic domain

- Conferences and divisions come from the standings file. `[DivisionStandings]`
  keys are `<CONFERENCE>_<DIVISION>` (split on the first underscore; this is
  already the file format): `AFC_EAST` → conference `AFC`, division `AFC_EAST`.
  `[ConferenceStandings]` keys are conference names. Division sizes come from
  the file.
- Remove `AFC`, `NFC`, `AFC_EAST`…, `PNFL_DIVISIONS`, `PNFL_DIVISIONS_BY_NAME`;
  one `build_teams` and one `build_league` for either section.
- Same-place non-conference games become a structural rule: each place in a
  division plays the same place in every other-conference division that has
  that place. For the PNFL this reproduces today's 17 fixed pairs (places 1-4
  get two games, the two 5th places play each other). The `FIXED_NONCONF_
  PLACE_OPPONENTS` table and its validation go away.
- Phase-2 rule keys named by division size (`four_team_…`, `five_team_…`) stay;
  they are size-based, not league-based.

## Renames

| Old | New |
|---|---|
| `schedulers/fixed_cpsat_builder.py`, `FixedCpsatMatchupBuilder`, `_FixedCpsatNonConferenceModel` | `schedulers/matchup_builder.py`, `MatchupBuilder`, `_NonConferenceModel` |
| `schedulers/fixed_cpsat_scheduler.py` | `schedulers/scheduler.py` |
| `SCHEDULER_DESCRIPTION = "fixed-place + CP-SAT"` | `"two-phase CP-SAT"` (printed in the report, so the PNFL golden report is re-frozen; the schedule `.txt`/`.html` goldens must stay byte-identical) |
| `HtmlScheduleWriter.league_name = "PNFL"` default, `"PNFL Schedule Report"` | league name required, used in both titles |
| `docs/scheduler/phase-1-matchups-fixed-cpsat.md` | `docs/scheduler/phase-1-matchups.md` |
| `tests/unit/scheduler/fixed_cpsat/` + `conference_league/` | gone; one suite in `tests/unit/scheduler/` |
| `test_fixed_cpsat_inventory.py` + `conference_league/test_inventory.py` | `test_matchups.py` |
| `fixed_cpsat/test_schedule_rules.py` + `test_schedule_structure.py` + `conference_league/test_schedule_rules.py` | `test_schedule_rules.py` |
| `test_pnfl_model_fingerprint.py` | `test_model_checksum.py` (one pinned checksum per league; the PNFL hashes must not change) |
| `LEAGUE_5_SLOTS`, `LEAGUE_7_SLOTS` (drop `LEAGUE_6_SLOTS`) | `ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION`, `THREE_PLAYOFF_TEAMS_FROM_4_TEAM_DIVISION`; ids `one-playoff-team-from-4-team-division`, `three-playoff-teams-from-4-team-division` |
| `PCFL_LEAGUE`, `PCFL_WEST/EAST/OVERALL/RIVALRIES/CONFIG/AMOUNTS` | `CONFERENCES_LEAGUE`, `CONFERENCES_WEST`, … (named by structure) |
| fixtures `pcfl_even/odd/free/result` | `solved_even_season`, `solved_odd_season`, `solved_no_rotation`, `solved` |
| tests named `…_pnfl_…`, `…_pcfl_…` | `…_divisional_…`, `…_conferences_…`, `…_shipped_files` |
| golden inputs `tests/integration/data/league.ini`, `PNFL.scheduler.toml` | `divisions.2026.ini` + `divisions.scheduler.toml`, `conferences.2029.ini` + `conferences.scheduler.toml`; test league names `divisions` / `conferences` |
| `test-matrix-phase-1-matchups-fixed-cpsat.md`, `test-matrix-conference-league.md` | `test-matrix-phase-1-matchups.md`; conference rows fold into the phase-2 matrix |

Shipped data keeps the real league names (`dev/PNFL.2049.ini`,
`dev/rules/PCFL.scheduler.toml`, `[league.PCFL]`): those are the leagues'
files, not code.

## One test suite

- One rule validator (`tests/integration/schedule_validation.py`) takes the
  schedule, its league and its config and checks every rule that applies:
  structural rules always; divisional rules when the league has divisions; the
  toggled or configured rules (six-week window, streak caps, season-end mixing,
  opening non-conference weeks, conference-sequence cap, rivalry week and
  hosting parity) when the config turns them on. Amounts and counts come from
  the config and the league (weeks, games per team, hosting halves), never
  literals.
- One `test_schedule_rules.py`: the solved-schedule fixture is parametrized over
  every league case (two divisional variants, the conference league in an even
  season, an odd season, and with rotation off) and runs the validator. Solved
  fixtures are built once per case by setup code and shared; the report test
  reads the shared result instead of solving its own. Solver-backed tests stay
  `slow`.
- Golden CLI test: the same test parametrized per league, one frozen output set
  each (`schedule_2026.*` for divisions, a new set for conferences), validated
  with the same validator. `--bless` regenerates both.
- Shipped-file tests parametrized over every `dev/` and `release/` league and
  rules file.
- Test-league comment (use verbatim):

```python
# Two test leagues: same teams and divisions, different standings. They differ
# in how many of each conference's four playoff teams came from the 4-team
# division: 1 or 3. With three, it's harder to find a schedule that meets all the
# league rules, as well as, to stay close to the strength-of-schedule targets.
```

  The design doc explains the rest: the names came from the original
  playoff-based rules, where each playoff team had non-conference games left
  over for the other conference's non-playoff teams (one per 5-team-division
  playoff team, two per 4-team-division playoff team), so 4 + the count above
  gave the old "5/6/7 free slots" labels; the current scheduler uses only the
  overall order and each division's finish order.

## Facts the implementer needs

- OR-Tools 9.15's `CpModel.proto` has no `SerializeToString`; the checksum test
  hashes the bytes `export_to_file` writes.
- PCFL phase 2 has no objective and solves in ~30 s; PNFL phase 2 runs to its
  deterministic-time limit. PCFL phase 1 at `spread = 0.0` takes ~27 s to prove
  optimal (spread 2.5: under a second), so matchup tests use spread 2.5 by
  default and the flat case is `slow`.
- The PNFL CP-SAT models must stay byte-identical (the checksum test and the
  schedule goldens prove it); only the report's "Scheduler" line changes.
- Text files are UTF-8 with CRLF line endings and a final newline.
- Docs: very simple, clear, high-level; new CHANGELOG/STATUS/WORKLOG entries at
  the top of their section; `TODO.md` is the user's.
- Commits one line, prefixed `scheduler:`, no AI mention, no trailers; hand-off
  ends with the two separate code blocks (squash-merge + commit; worktree
  removal + branch deletion) after leaving the worktree.
