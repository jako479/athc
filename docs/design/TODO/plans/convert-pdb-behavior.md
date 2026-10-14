# convert-pdb behavior plan

With no game plan option, the team's four game plans fill the Slot columns; plan options and the league file never mix; a shared plan is read once; each Slot column hides by its own plan; plan sides are checked; a missing defaulted plan is a `WARN`.

Depends on cli-help.md landing first. Options, settings, team resolution and the full list of lines: convert-pdb-cli.md.

## Decisions

- With no game plan option, your team's four game plans fill the Slot columns: Slot 1 from the 1st-half plan, Slot 2 from the 2nd-half plan, per side.
- The `.lg2` entry order is 1st-half offense, 1st-half defense, 2nd-half offense, 2nd-half defense (the four names `off1`, `def1`, `off2`, `def2`).
- Without a team (`team` unset, no `--team`) and with no `--path` asked for, nothing changes from today: the Slot columns are hidden and no line says so.
- The Slot columns say where each play sits in your plans, whoever ran it: a play another team ran that is in your plan shows its slot.
- There is no off switch for the default.
- The game plan options and the league file never mix: with any of `-o`, `-o2`, `-d` and `-d2`, the run uses only the files given; each fills its own slot, the slots not given are hidden, and the league file is not read.
- With none, the team's four plans come from the league file.
- A typed `.pln` path gets no progress line.
- Two typed `.pln` paths to one file are used as given: two columns.
- A shared plan is given once: two resolved slots that land on one file are read once and fill Slot 1 alone, and Slot 2 is hidden; the progress line is `<path>: Las Vegas offense, both halves, Slot 1`.
- If that one shared file is missing or unreadable, one `WARN` names it, not two: `WARN <path>: The system cannot find the file specified. Offense Slot 1 is hidden.` (Slot 2 is hidden with it).
- A defaulted plan that is missing is a `WARN` and its column is hidden; a named one is a `FAIL`, as today: `FAIL <path>: The system cannot find the file specified.`, exit 2.
- A defaulted plan missing in `--path` or `ppp_path`: `WARN <path>: The system cannot find the file specified. Offense Slot 2 is hidden.`, exit 0.
- A defaulted plan missing at the league locations carries the hint as its last sentence: `WARN <path>: The system cannot find the file specified. Offense Slot 2 is hidden. Run 'athc config set ppp_path FOLDER' or pass --path.`, exit 0; in `ppp_path` or `--path` there is no hint.
- A defaulted plan that cannot be read gets the same treatment, with the game plan library's reason: `WARN <path>: <the game plan library's reason> Offense Slot 2 is hidden.`, exit 0.
- A team whose `.lg2` folder is absent or holds none of its plans gets one `WARN` per folder instead of four; the line covers every Slot column of that side or team at once.
- None of the team's plans in the folder (`--path`, `ppp_path`): `WARN <folder>: No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, DEN-OGP2.pln, DEN-DGP2.pln.` (each name once), exit 0.
- None of the team's plans at a league location, folder present: `WARN <folder>: No Denver game plans. Run 'athc config set ppp_path FOLDER' or pass --path.`, exit 0.
- None of the team's plans at a league location, folder absent: `WARN <folder>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER' or pass --path.`, exit 0.
- A Slot column is hidden when its own plan is absent, not when the count is short.
- Slot positions stay fixed: Slot 1 is the 1st-half plan, Slot 2 the 2nd-half plan, whichever is present.
- The side is checked: a defense plan under `-o`/`-o2`, or an offense plan under `-d`/`-d2`, is `FAIL <path>: Not an offense game plan.` (`Not a defense game plan.` under `-d`/`-d2`), exit 2.
- A defaulted plan on the wrong side is the same text as a `WARN`, with the column hidden: `WARN <path>: Not an offense game plan. Offense Slot 1 is hidden.`, exit 0.
- A `WARN` never changes the code.

Modes, per run:

- Any game plan option: the files given fill their slots, the slots not given hidden, nothing else read; a missing file is `FAIL`, exit 2, as today.
- No game plan option, a team: the team's four plans; a missing one is a `WARN`, its column hidden.
- No game plan option, no team, no `--path`: the Slot columns hidden; no line.

## Files to change

- `src/athc/cli/convert_pdb.py`: for each resolved plan, checks `exists()` before any read, reads with `read_gameplan`, checks the side, collapses two resolved slots that name one file; a problem with a resolved plan is a `console.warn` line and `None` for that slot; a plan given as a path is read with `read_gameplan` and side-checked, a wrong side raises `AthcError(reason, path)`; the command passes the `Config` and four `GamePlan | None` on.
- `src/athc/pdbtoexcel/main.py`: `convert_pdb()` takes the four plans as `GamePlan | None` (`pln_offense`, `pln_offense_2`, `pln_defense`, `pln_defense_2`); full signature in convert-pdb-cli.md.
- `src/athc/pdbtoexcel/workbook_creator.py`: `from_config` takes the four `GamePlan | None` instead of file names and reads none; `create_workbook` passes each slot's presence to the workbook instead of a count.
- `src/athc/pdbtoexcel/excel_workbook.py`: `__init__` takes which Slot columns have a plan (per side, per slot); `_slot_options` hides a column whose plan is absent.

## Tests

- `tests/integration/test_convert_pdb.py`, with the shared fixtures convert-pdb-cli.md lists:
- Game plan options: `-o try3.pln` with `team` set fills offense Slot 1 from the file, hides the other three columns and prints no progress line; any plan option reads no league files (a league without `path` still converts); `-o2` alone fills and shows offense Slot 2.
- Team mode at the league locations: the four plans found, the Slot columns filled and visible; a missing plan is a `WARN` with the `ppp_path` hint, its column hidden, exit 0; a missing 1st-half plan with the 2nd-half present fills Slot 2 and shows it; a shared plan gives Slot 1 and hides Slot 2; a shared plan missing is one `WARN`; a team folder absent is one `WARN` with the path phrase and the hint, every Slot column hidden; a folder present with none of the plans is the one "No Denver game plans" line with the hint; a wrong-side plan is a `WARN`; an unreadable plan is a `WARN`.
- Folder limit: a folder holding one of Denver's four plans gives one `WARN` per missing plan and no "No Denver game plans" line.
- `--path FOLDER`: a missing plan `WARN`s without the hint; none of the plans is "No Denver game plans" with the league file's names and without the `ppp_path` hint.
- `ppp_path`: a missing plan `WARN`s without the hint.
- Explicit mode: a wrong-side plan under `-o` and under `-d` is a `FAIL`, exit 2, nothing written.
- `tests/unit/pdbtoexcel/test_workbook_creation.py`: `_slot_options` by presence: plan 1 only, plan 2 only, both, neither (0, 1 and 2 plans; Slot 2 visible with plan 2 alone); `test_slot_column_from_gameplan` keeps passing (it passes a `GamePlan` to `__init__`).

## Docs and meta

- `docs/pdbtoexcel/README.md`: the Command section covers the game plan options' rule, the team mode and its sources, and the side check.
- `docs/pdbtoexcel/ARCHITECTURE.md`: "What it does" gains the team default, the side check and hiding by presence.
- `config/release/docs/COMMANDS.txt` section 13: the game plan options' rule and the team default.
- `config/release/docs/README.txt`: the convert-pdb troubleshooting line for a missing game plan adds the team default ("or fix path, team or ppp_path in league.toml").
- `CHANGELOG.md`, `STATUS.md`: this change.
