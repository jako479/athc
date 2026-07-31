# athc — Status

Updated 2026-07-30. Task list: [TODO.md](TODO.md). Detail: [docs/](docs/).

All non-scheduler work was committed in one batch on 2026-07-19, so git dates lie — the
work itself is from early-to-mid June. Dates below are when the work happened.

## scheduler — `generate-schedule`

Working. Last worked 2026-07-25. Docs: [README](docs/scheduler/README.md) ·
[phase 1](docs/scheduler/phase-1-matchups-fixed-cpsat.md) ·
[phase 2](docs/scheduler/phase-2-schedule.md)

### Done

- Rule overhaul from NFL data — hard rules, league-wide anti-pileup caps, soft objective
  with NFL-typical bands so seasons vary.
- Schedulers A, B, D removed. Just "the scheduler" now — no `--scheduler` flag.
- Multithreaded phase 2. `solver_workers = 8` is a reproducibility contract: config-only,
  change it and every seed re-rolls. Stops on deterministic time, not wall-clock.
- league.ini simplified — `[DivisionStandings]` + `[OverallStandings]` only.
- Golden integration test for `generate-schedule` (3 files byte-compared, `--bless` to reset).

### Next

**1. Simplify the ruleset.** 50 `[phase2]` keys + 6 fixed rules, never pruned. Some are
redundant by construction (a 9-week density cap forces the 10-week one). Too big to hold in
your head, hard to blame when a solve is slow or infeasible, and probably why every season
comes out more uniform than a real one.
Plan: drop rules implied by others; turn each remaining one off and see if the schedule
actually degrades; add a simple/full ruleset switch (toggles already exist for two rules);
watch solve time.

**2. Quirk budget.** Proposal only — [quirk-budget.md](docs/design/quirk-budget.md). Real NFL
seasons have a few rare one-offs; athc bans them all. A league-wide budget (default 2) raises
one team's cap one step; `0` = today's behavior. Do this *after* #1 — it adds rules.

**3. Delete** `TEST_DATA/scheduler_integration/` (workspace root, untracked) — obsolete
scheduler C/D output, replaced by the golden test.

## gameplan — `check` `list-normals` `list-specials` `set-normals` `set-specials` `find-play` `replace-play`

Working. Validates and edits .pln game plans. Docs: [README](docs/gameplan/README.md) ·
[rules](docs/gameplan/RULES_PNFL.md)

Latest (June): added `find-play` (search by play name across files/trees; reads the category
straight from the .pln, no pool setup) and `replace-play` (swap one play across .pln files).
Writes back up first (`file.YYYY-MM-DD-HHMM.bak`, `--no-backup` to skip). Renamed the
`Play` API to `PlayRef`/`CustomPlay`/`StockPlay`.

Open: `check` should take a profile and confirm it's valid for the gameplan's categories ·
`replace-play` should accept a list of plays for bulk swaps.

## profile — `check` `copy` `diff`

Working. Validates and compares .prf coaching profiles. Docs:
[README](docs/profile/README.md) · [rules](docs/profile/RULES_PNFL.md)

Latest (June): expanded `check`'s gameplan-compatibility checks and validators (reverse
warnings, FG/PAT specials). `diff` was built this cycle — one line per differing situation
showing situation #, game state, and stop-clock; `--output` infers CSV from the file
extension. Tests were restructured to sit under the package being tested and to compare
written .prf output against known expected files.

Open: revisit `edit`/`copy` options.

## playpool (library)

Working. Backs `gameplan` and `convert-pdb`; not a subcommand. Docs:
[ARCHITECTURE](docs/playpool/ARCHITECTURE.md). Rules: `rules/PNFL.playpool.toml`.

Latest (June): renamed the `PlayRecord` family to `Play`; play attributes now come from the
pool's folder categories, with the user category treated as authoritative. `pool.py` was
split up and its over-long comments cut.

## convert-pdb (pdbtoexcel)

Working. Extracts a WinLogStats database into an Excel workbook. Docs:
[README](docs/pdbtoexcel/README.md) · [ARCHITECTURE](docs/pdbtoexcel/ARCHITECTURE.md)

Latest (June): rules paths are now config-relative, resolved against the config dir.
Note: a standalone port lives outside this repo at `E:\PNFL\__My Projects\PdbToExcel_2.0`
for testers — re-sync it by hand when this package changes.

## autocontinue

Working. Docs: [README](docs/autocontinue/README.md) ·
[ARCHITECTURE](docs/autocontinue/ARCHITECTURE.md)

Latest (June): hot-corner toggle, focus checks, halftime assets added.

Open: halftime handling itself.

## config — `path` `edit` `reveal`

Working, untouched since June. Docs: [README](docs/config/README.md). `reveal` opens the
config dir in Explorer — named `reveal`, not `explorer`.

## install / release

`install.bat` + a wheel in a zip; uv installs it and pulls deps from PyPI. Python is no
longer a prerequisite — uv downloads a managed one (2026-07-23).
Docs: [installer.md](docs/design/installer.md)

Open: on 2026-07-29 you reopened whether this is the right shape for non-dev users —
PyInstaller `.exe` plus a real Windows installer, versus today's uv prerequisite. Research
only; nothing decided, no code changed. Key point from it: a bundled exe can only carry a
read-only config template, so the editable config still has to be written to a real folder
on first run.
