# playpool CLI plan

**Goal:** `athc playpool check` with nothing after it checks the league's play pool where `league.toml` puts it (`play_path`); a folder points it at a folder of plays instead. No other command joins the group in this plan.

**Status:** proposal, 2026-10-13, written against main at ddae7a1 (play attributes from the play file; `playpool.toml` gone); nothing changed yet. Depends on cli-help.md landing first. Every choice is decided below, with its reason next to it. Reviewed for codebase fit and coach workflows; the findings are folded in.

## 1. Today

- `athc playpool check [play_dir]` (`src/athc/cli/playpool/check.py`, unchanged by ddae7a1): one optional folder. With none, the league's `play_path` from `league.toml`; a league that cannot be resolved is an error, and a league without `play_path` is `FAIL <league.toml>: No play_path for the league. Set play_path in this file.` (the command's own raise). With a folder, no league is needed, but a league named with `--league` must exist, and a league that resolves (named or configured) lends its category labels to the folder names; with no league, no folder name means a category. A broken `league.toml` fails the run even with a folder. After the league resolves (`check.py` lines 41 to 54), a given folder is checked for being there and being a folder (lines 56 to 59) before the pool is read.
- It reads the pool with `read_play_pool(play_dir, labels=labels)`, and the pool's issues are its findings: a play in a folder that contradicts its file, a duplicate name, an invalid or unreadable file. Since ddae7a1 there is no rules file for the pool: `playpool.toml`, `src/athc/playpool/rules.py` and the check of the names a rules file listed are gone, so `check` and every other pool consumer report the same set of problems with the same words (`docs/playpool/README.md`: "the same things pool loading checks for every other command, with the same messages", now true).
- The issues print one per line as results on stdout, then a blank line and the tally `<n> play(s) checked in '<folder>', <n> issue(s)`. Exit 0 clean, 1 issues, 2 error. A folder that does not exist is `FAIL <folder>: The system cannot find the path specified.` and a file in its place `FAIL <folder>: The directory name is invalid.`, in both modes, without the `Set play_path in <league.toml>.` hint that `play_dir()` in `src/athc/config.py` gives every other pool consumer through `build_pool`.
- The group (`src/athc/cli/playpool/__init__.py`) has `check` only. Usage today: `athc playpool check [-h] [--league name] [play_dir]`.
- The library (`src/athc/playpool/`, rewritten by ddae7a1): `read_play_pool(root_dir, *, labels=None)` walks `<root>/**/*.ply` in sorted path order, so a pool is always a whole tree; `PlayPool` holds the three side lists, `issues` and `find_by_name` (any case; a repeated name resolves to the last play loaded).
- The consumers: `gameplan check`, `set-normals`, `set-specials`, `replace-play`, `check-ppp` and `convert-pdb` all load the pool from `play_path`, look plays up with `find_by_name` and read the play attributes. The gameplan commands and `check-ppp` print every pool issue as a `WARN` line before their own work (`build_pool(play_path, labels, league_file)` in `src/athc/cli/gameplan/_common.py`: `play_dir()` for the hint, `read_play_pool`, one `console.warn` per issue; `docs/gameplan/README.md`: "`WARN` per play-pool issue"); `convert-pdb` gathers them as notices (`src/athc/pdbtoexcel/workbook_creator.py`) and prints them as `WARN` lines after the conversion (`src/athc/cli/convert_pdb.py`, `result.warnings`).
- The real pool today (the dev PNFL's `play_path`, `E:\SIERRA\FbPro98\PNFL`, counted 2026-10-13): `Offense` 2579 plays, `Defense` 2267, `Special` 309, `TestPlays` 4, 5159 in all; none at the root and none in the season folders `2043` to `2049`, which hold the teams' plans folders the `.lg2` names (`PNFL\2049\Plans\<Team>`). The pool root is the league's folder under the game folder, and a coach's plans folder sits inside it with no play in it.

## 2. Who runs it, for what

| # | Who | Wants to | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach | see why every gameplan command starts with `WARN` lines about the pool | `athc playpool check` | each issue once, on stdout, then the tally; exit 1 |
| 2 | Coach | know the league's pool is clean before building game plans | `athc playpool check` | `<n> play(s) checked in '<play_path>', 0 issue(s)`; exit 0 |
| 3 | Coach | check plays they made, before copying them into the pool | in that folder, `athc playpool check .`; or `athc playpool check newplays` | invalid files; duplicate names within the folder; wrong-folder plays when the folder uses the league's layout |
| 4 | Coach | check new plays against the whole pool after copying them in | `athc playpool check` | duplicate names across the pool |
| 5 | Coach | check a copy of the pool (a backup, another drive) | `athc playpool check D:\backup\PNFL` | that folder's plays |
| 6 | Coach | the pool of another league | rows 1, 2 and 4 with `--league PCFL`; with a FOLDER (rows 3 and 5) `--league` names the category folders only | |
| 7 | Coach | from a script | the exit code; `> out.txt` keeps the results, `2> errors.txt` the problem lines | |

## 3. What other tools do

- **Config names the default path, an argument wins, `.` is "here".** ruff's `check` lists its files argument as `[default: .]` ("Usage: ruff check [OPTIONS] [FILES]..."); pytest, mypy and pyright do the same (check-ppp-cli.md section 3); check-ppp-cli.md decision 3 fixes athc's rule: no path means the configured default, `.` the current folder, an explicit path overrides both.
- **A checker walks the whole tree.** ruff: "Ruff will automatically discover all Python files in that path"; athc's `read_play_pool` walks `**/*.ply`.
- **A checker of one thing takes a path to it.** helm lint: "helm lint PATH [flags]"; "This command takes a path to a chart and runs a series of tests to verify that the chart is well-formed"; its findings are "[ERROR]" and "[WARNING]" messages.
- **Standard shape and codes.** clig.dev: "Make the default the right thing for most users"; "Be consistent across subcommands"; "Use standard names for flags, if there is a standard"; "Return zero exit code on success, non-zero on failure"; and, on scope, "Rather than stuff more and more features into those programs", build small parts that work together.
- **Click.** An argument with no explicit metavar gets its placeholder from its name: `[FOLDER]` when optional (`Argument.make_metavar`, `click/core.py`); an explicit metavar prints verbatim in the usage line and in the error hint (`get_error_hint`), which is why today's `check.py` writes `metavar="[play_dir]"` by hand. `click.Path(exists=True, file_okay=False)` words a missing folder `Directory 'x' does not exist.` and a file `Directory 'x' is a file.` (`click/types.py`), not Windows' words. A second value for a one-value argument is Click's `Got unexpected extra argument (<value>)` (`click/core.py`); today the root shows it as Click wrote it (`error.show()`, `src/athc/cli/__init__.py`), and the period arrives with cli-help.md rule 23, added once where usage errors are rendered.
- **In-house.** `build_pool` prints every pool issue as `WARN <issue>` (an issue names the play's path itself where one is to blame) for `gameplan check`, `set-normals`, `set-specials`, `replace-play` and `check-ppp`; `playpool check` prints the pool's issues as results. The project's codes: 0 done, 1 findings, 2 error; a batch exits with the worst outcome (`docs/design/architecture.md`).

## 4. Decisions

1. **One command, `check`.** The group stays a group so later commands can join it; those are 2.0.0 items in TODO.md (`playpool find-play`, `playpool show`). TODO.md's two playpool-check ideas (2.0.0) stay there too: "check that each play's name matches its play category" is not covered, since `check` compares a play's folder with its file (`_folder_info` and `_warnings` in `src/athc/playpool/reader.py`), never its name; it would be a new `check` finding; "count plays by file name type" (STATUS.md: "Open: count plays by file name type") is a count over the whole pool, a report `check` does not give, and stays the 2.0.0 idea it is, a verb of its own if it comes, changing nothing in `check`. clig.dev: small parts that work together, not more features in one program.
2. **Usage `athc playpool check [OPTIONS] [FOLDER]`:** one optional folder, positional as in `gameplan check`, `profile check` and `check-ppp` (check-ppp-cli.md decision 16), named `FOLDER` because only a folder is accepted (cli-help.md rule 3). The argument carries no explicit metavar (cli-help.md rule 22): Click derives `[FOLDER]` from the parameter name, and an explicit one would print verbatim in the usage line and the error hint (section 3).
3. **No FOLDER means the league's pool; `.` the current folder; a FOLDER overrides**, the path rule of cli-help.md rule 16 and check-ppp-cli.md decision 3 (no path means the configured default, `.` the current folder, an explicit path overrides both; rule 16 names the league's play pool as such a default). The configured place, not the current folder, is the default because the pool is one fixed place per league that every pool consumer reads from `play_path`, and a coach's current folder is a plans folder, which holds game plans and no plays (section 1: no season folder holds a `.ply`); `gameplan check` and `profile check` default to the current folder because game plans and profiles live where the coach works. The coach's own play folder and the league's pool are told apart by the argument: nothing after `check` is the league's pool; anything after it (`.` included) is that folder. No team setting is read: plays are league-wide, so the default-team keys `team` and `ppp_path` of check-ppp-cli.md (decisions 4 and 15) have no part here.
4. **One folder, one check.** With no rules file left for the pool, the league's pool and a given folder are checked for the same things with the same code, so `check` never needs to recognize a FOLDER as the pool: `athc playpool check E:\SIERRA\FbPro98\PNFL` (the README's own example) and `athc playpool check` read the same folder and print the same findings. The two modes differ only in where the folder comes from and in the line for a configured folder that is missing (decision 7). The findings stay the pool's issues, nothing more: the other consumers show exactly these as `WARN` lines, and the README's promise of "the same things, with the same messages" holds as the code stands.
5. **No `-r`.** A pool is a tree by nature and `read_play_pool` always walks it (ruff discovers recursively too). The `-r` rule of check-ppp-cli.md decision 9, each folder of the tree on its own, would hide duplicate names across folders, which is the check's point. A league without the layout (a flat folder) is still one tree.
6. **`--league NAME`, the shared option with cli-help.md rule 10's text, always with a value (rule 19).** As today: a FOLDER needs no league; a league named with `--league` must exist even with a FOLDER (rule 19: a named league must exist, and its files are read only when the run needs them; `check.py` lines 41 to 45); a league that resolves lends its category labels to the folder names; a broken `league.toml` fails the run even with a FOLDER; with no league, no folder name means a category. A FOLDER run never reads `play_path`, as today.
7. **The configured pool missing on disk gets the hint, and the missing key names the way out.** With no FOLDER, a `play_path` that is not a folder is `play_dir()`'s line, `FAIL <play_path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` (`The directory name is invalid.` for a file), as every other pool consumer says it. A league without `play_path` says `FAIL <league.toml>: Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.`: cli-help.md rule 21's shape, a "... is not set" line naming the command's own path form, so a first-run coach sees the way out on the first line; `check.py` raises this line itself, so no other command's line changes. A given FOLDER keeps today's plain phrases: the user typed it, so a hint would be wrong.
8. **Argument errors stay athc's words, and come before the pool.** A given FOLDER is checked for being there and being a folder after the league resolves and before anything of the pool is read, as today, with Windows' phrases through athc's own checks instead of `click.Path(exists=True, file_okay=False)`, whose texts are not Windows' (section 3). A second FOLDER is Click's usage error, `Got unexpected extra argument (<folder>).`, with the period cli-help.md rule 23 adds once for every command. FOLDER is not a wildcard argument (cli-help.md rule 15): once Click's expansion is off, `plays*` is a folder that does not exist.
9. **`check`'s lines stay today's:** issues one per line, a blank line, the tally `<n> play(s) checked in '<folder>', <n> issue(s)`; the folder prints as typed (`'.'` for `.`), as `gameplan check` prints its paths. No per-play `OK` lines: the real pool has over five thousand plays.
10. **Help text is cli-help.md's:** the command summary "Check the play pool for problems.", the FOLDER help "Play pool folder (default: the league's play_path)." and the description below in plain words, one idea per sentence. Depends on cli-help.md landing first (its rule 25); the blocks below are that form.

## 5. The command

### `athc playpool` (group)

```
Usage: athc playpool [OPTIONS] COMMAND [ARGS]...

  Check the play pool (.ply).

Options:
  -h, --help  Show this message and exit.

Commands:
  check  Check the play pool for problems.
```

### `athc playpool check`

```
Usage: athc playpool check [OPTIONS] [FOLDER]

  Check the play pool for problems.

  Finds plays in the wrong folder, duplicate play names and invalid play
  files. With no FOLDER, the league's play pool is checked. Category folders
  go by the league's names; with no league, no folder name means a category.

Positional arguments:
  FOLDER  Play pool folder (default: the league's play_path).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc playpool check
    athc playpool check newplays
```

Examples for the docs:

```
athc playpool check
athc playpool check .
athc playpool check newplays
athc playpool check --league PCFL
```

#### Modes

| FOLDER | Plays come from | League | Missing folder |
|---|---|---|---|
| none | the league's `play_path` | required, with `play_path` | `play_dir()`'s line with the `Run 'athc config set play_path FOLDER'` hint |
| a folder, `.` included | that folder, the whole tree | optional; one named must exist; one that resolves names the category folders | Windows' path phrase, no hint |

- **Order:** the pool's issues in the reader's order (the plays' sorted path order), then the blank line and the tally. A clean run prints the tally alone.
- **Argument errors, checked after the league resolves and before anything of the pool is read:** a FOLDER that does not exist, `FAIL <folder>: The system cannot find the path specified.`; a file, `FAIL <folder>: The directory name is invalid.`; a second FOLDER, Click's usage text ending `Error: Got unexpected extra argument (<folder>).`; nothing is checked in any of these.

### cli-help.md changes

- `playpool check`: no change; the usage, summary and FOLDER help are the ones cli-help.md lists, and the description above is the plain-words rewrite it asks for.

## 6. Settings

In `league.toml`, under `[league]`, as shipped (the config plan owns the wording of this comment):

```toml
[league]
# The folder that holds this league's plays (.ply files).
play_path = 'C:\SIERRA\FBPRO98\PNFL'
```

- `play_path`: the pool. `check` reads it with no FOLDER only. A relative value resolves against the league folder (`LeagueConfig.path`).
- `[categories.offense]` / `[categories.defense]`: the folder names that mean a category.
- `--league NAME` picks the league; else `[athc] league` in `athc.ini`.
- No new keys, and no rules file for the pool: the attributes come from the play files. `team` and `ppp_path` are never read.

## 7. Lines and exit codes

New or changed lines, in the project's wording; everything else prints as today.

| When | Line | Code |
|---|---|---|
| `check`, no FOLDER, `play_path` missing on disk | `FAIL <play_path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` | 2 |
| `check`, no FOLDER, `play_path` is a file | `FAIL <play_path>: The directory name is invalid. Run 'athc config set play_path FOLDER'.` | 2 |
| `check`, no FOLDER, no `play_path` in `league.toml` | `FAIL <league.toml>: Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.` | 2 |
| `check`, a second FOLDER | Click's usage text, `Error: Got unexpected extra argument (<folder>).` (today's line; the period arrives with cli-help.md rule 23) | 2 |
| `check`, the tally | `<n> play(s) checked in '<folder>', <n> issue(s)`, unchanged | |

Codes stay 0 done, 1 findings, 2 error. The issue wording is the reader's (`src/athc/playpool/reader.py`) and does not change.

## 8. Related commands

- `gameplan check`, `set-normals`, `set-specials`, `replace-play`, `check-ppp` and `convert-pdb` keep printing each pool issue as a `WARN` line when they load the pool; their output does not change. Their docs say `athc playpool check` lists the same problems on their own, with an exit code (clig.dev: suggest the command to run).
- `check-ppp-cli.md` names `playpool check` as the precedent for "nothing means the configured place"; this plan keeps that behavior.
- TODO.md's 2.0.0 playpool ideas: settled in decision 1; none changes `check`'s usage.

## 9. Code

- `src/athc/cli/playpool/check.py`: the argument renamed `folder` and declared without a metavar, so Click derives `[FOLDER]` from the name (today's `metavar="[play_dir]"` goes), with cli-help.md's help; the docstring's summary and description become section 5's text (cli-help.md line 248 marks the description rewrite as playpool-specific). Order as today: the league resolves (a `LeagueError` is swallowed when a FOLDER is given and no `--league`); a given FOLDER goes through today's two checks (`exists()` for the path phrase, `is_dir()` for the directory phrase, lines 56 to 59); with no FOLDER, `play_dir(play_path, league_file)` replaces the two checks and gives the hint, and the command's own `No play_path` line becomes `Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.` The pool is read with `read_play_pool(folder, labels=labels)` as today; the issues and the tally print as today.
- The library does not change.
- The usage line, argument help and `--league` text come with cli-help.md's general changes (Click 8.5, `[OPTIONS]` usage, argument help); no playpool-specific code for them.

## 10. Tests

`tests/integration/test_playpool_check.py`, with the `make_league` / `write_config` fixtures:

- No FOLDER, `play_path` missing on disk, and a file: the two hint lines, exit 2, stdout empty.
- No FOLDER, no `play_path`: the `Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.` line, exit 2.
- A FOLDER run never reads `play_path`: a league whose `play_path` is missing on disk, or written as an array, with a clean FOLDER given: exit 0, no `FAIL`.
- Argument count, at the limit and one past: one FOLDER is accepted (today's tests); two FOLDERs are Click's usage error with the period, exit 2, nothing checked.
- A wildcard FOLDER (`plays*`), once cli-help.md turns Click's expansion off: `FAIL plays*: The system cannot find the path specified.`
- Existing tests that change: `tests/integration/test_playpool_check.py::test_league_without_play_path_exit_2` (the line becomes `Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.`); `tests/integration/test_cli_root.py::test_usage_lists_each_option`, rows `playpool` and `playpool check` (`athc playpool [OPTIONS] COMMAND [ARGS]...`, `athc playpool check [OPTIONS] [FOLDER]`, which cli-help.md already changes with the style). Every other playpool test keeps passing by design: the FOLDER mode is unchanged, `test_read_error_exit_2`'s stub still matches `read_play_pool(folder, labels=labels)`, and the pool-mode tests (`test_default_is_current_league_play_path`, `test_league_option_picks_another_league`) have `play_path` on disk.
- `tests/unit/playpool/`: nothing; the library does not change.

## 11. Docs and meta

- `docs/playpool/README.md`: the CLI section covers `check` (`[OPTIONS] [FOLDER]`, the two modes, the hint line and the `or pass the folder` line, the examples above); `check`'s exit table's error row names the hint.
- `docs/playpool/ARCHITECTURE.md`: nothing; it describes the library, which does not change.
- `docs/gameplan/README.md` (its `check` row names the pool's `WARN` lines) and the other pool consumers' READMEs where they describe those lines: one sentence pointing at `athc playpool check`.
- `config/release/docs/COMMANDS.txt`: section 12 (`playpool check`) gets the two modes, the hint and the `.` example.
- `STATUS.md`: the playpool section gains the hint; its "Open: count plays by file name type (TODO)." line stays.
- `CHANGELOG.md`, top of `## athc`: "playpool: `check` says to set `play_path` or pass the folder when the pool is unset or missing". `TODO.md`: the `playpool: CLI plan (...)` line under 1.0.0 is ticked when this work lands, with its text as the one-liner below.
- `tests/integration/README.md`: the `athc playpool check` intro paragraph ("`play_dir` defaults to the league's `play_path`") rewritten for FOLDER, and a row per new case.

TODO.md one-liner: `playpool: CLI plan (check [FOLDER], athc config set play_path in its not-set lines); see docs/design/TODO/playpool-cli.md`.

## Shared vocabulary

- `FOLDER`: a folder only, here the play pool or a folder of plays; cli-help.md rule 3's name, nothing new.
- "The league's play pool": the folder `play_path` names.
- Rules applied from cli-help.md, in words: no path means the configured default, `.` the current folder, an explicit path overrides both (rule 16; check-ppp-cli.md decision 3), here with the pool as the configured default for the reason in decision 3; `--league NAME` with a required value and rule 10's text, and a named league must exist even when the command needs no league (rule 19; today's `check.py`); arguments carry no explicit metavar (rule 22; Click's `Argument.make_metavar` and `get_error_hint`); Click's extra-argument error gets athc's period once in `src/athc/cli/__init__.py` (rule 23); a "... is not set" line names the command's own path form (rule 21); no quiet flag (rule 24; none proposed here); the cli-help.md form only (rule 25); Windows words in help and lines (rule 9); athc's lines and codes (`docs/design/architecture.md`).
- Not taken, with the reasons in decisions 3 and 5: `-r` (check-ppp-cli.md decision 9's rule, each folder on its own) and the default-team keys `team` and `ppp_path` (check-ppp-cli.md decisions 4 and 15). No new option or key.

## Sources

- ruff `check` usage, `[default: .]` and file discovery: <https://docs.astral.sh/ruff/configuration/>
- helm lint: <https://helm.sh/docs/helm/helm_lint/>
- clig.dev: <https://clig.dev/>
- Click `Argument.make_metavar`, `get_error_hint` and the extra-argument text: `click/core.py`; the `Path` type's texts: `click/types.py` (Click 8.4.1 in the venv)
- athc at main ddae7a1: `src/athc/cli/playpool/check.py`, `src/athc/cli/playpool/__init__.py`, `src/athc/playpool/reader.py`, `src/athc/playpool/model.py`, `src/athc/playpool/__init__.py`, `src/athc/cli/gameplan/_common.py` (`build_pool`), `src/athc/cli/convert_pdb.py`, `src/athc/cli/__init__.py`, `src/athc/pdbtoexcel/workbook_creator.py`, `src/athc/config.py` (`play_dir`, `LeagueConfig`), `src/athc/errors.py`, `src/athc/console.py`, `src/athc/fbpro98_play/labels.py`, `docs/playpool/README.md`, `docs/playpool/ARCHITECTURE.md`, `docs/fbpro98_play/README.md`, `docs/gameplan/README.md`, `docs/design/architecture.md`, `docs/design/TODO/check-ppp-cli.md`, `docs/design/TODO/cli-help.md`, `config/release/leagues/PNFL/league.toml`, `config/release/docs/COMMANDS.txt`, `STATUS.md`, `TODO.md`, `tests/integration/test_playpool_check.py`, `tests/integration/test_cli_root.py`, `tests/integration/README.md`, `tests/integration/conftest.py`, `tests/unit/playpool/README.md`; the real pool under the dev PNFL's `play_path` (`E:\SIERRA\FbPro98\PNFL`), counted 2026-10-13
