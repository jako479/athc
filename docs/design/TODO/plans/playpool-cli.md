# playpool CLI plan

`athc playpool check` with no FOLDER checks the league's `play_path` with the `athc config set play_path` hint lines, a FOLDER checks that folder instead, and the help takes cli-help.md's form; no other command joins the group.

Depends on cli-help.md landing first.

## Decisions

- One command, `check`; the group stays a group.
- `playpool find-play` and `playpool show` stay 2.0.0 items in TODO.md.
- TODO.md's two playpool-check ideas stay 2.0.0: "check that each play's name matches its play category" would be a new `check` finding; "count plays by file name type" would be a verb of its own, changing nothing in `check`.
- Usage `athc playpool check [OPTIONS] [FOLDER]`: one optional positional folder, named `FOLDER`.
- The argument carries no explicit metavar; Click derives `[FOLDER]` from the parameter name.
- No FOLDER means the league's pool (`play_path`); `.` means the current folder; a FOLDER overrides both.
- Nothing after `check` is the league's pool; anything after it (`.` included) is that folder.
- No team setting is read: `team` and `ppp_path` play no part.
- The league's pool and a given folder are checked for the same things with the same code; `check` never recognizes a FOLDER as the pool.
- The two modes differ only in where the folder comes from and in the line for a configured folder that is missing.
- The findings are the pool's issues, nothing more (the same ones the other pool consumers show as `WARN` lines).
- No `-r`: the folder is always read as one whole tree; a flat folder is still one tree.
- `--league NAME`, the shared option with cli-help.md's text, always with a value.
- A FOLDER needs no league; a league named with `--league` must exist even with a FOLDER.
- A league that resolves (named or configured) lends its category labels to the folder names; with no league, no folder name means a category.
- A broken `league.toml` fails the run even with a FOLDER.
- A FOLDER run never reads `play_path`.
- No FOLDER, `play_path` not a folder: `play_dir()`'s line with the `Run 'athc config set play_path FOLDER'.` hint, as every other pool consumer says it.
- No FOLDER, no `play_path`: the "... is not set" line naming the command's own path form; `check.py` raises it itself, so no other command's line changes.
- A given FOLDER keeps today's plain phrases, no hint.
- A given FOLDER is checked for being there and being a folder after the league resolves and before anything of the pool is read, with Windows' phrases through athc's own checks, not `click.Path(exists=True, file_okay=False)`.
- A second FOLDER is Click's usage error, with the period cli-help.md adds once for every command.
- FOLDER is not a wildcard argument: once Click's expansion is off, `plays*` is a folder that does not exist.
- Output stays today's: issues one per line in the reader's order (the plays' sorted path order), a blank line, then the tally; a clean run prints the tally alone.
- The tally's folder prints as typed (`'.'` for `.`).
- No per-play `OK` lines.
- Help text is cli-help.md's: the command summary, the FOLDER help, and the description in plain words, one idea per sentence.
- `gameplan check`, `set-normals`, `set-specials`, `replace-play`, `check-ppp` and `convert-pdb` keep printing each pool issue as a `WARN` line; their output does not change.
- No new option or key.

| FOLDER | Plays come from | League | Missing folder |
|---|---|---|---|
| none | the league's `play_path` | required, with `play_path` | `play_dir()`'s line with the `Run 'athc config set play_path FOLDER'` hint |
| a folder, `.` included | that folder, the whole tree | optional; one named must exist; one that resolves names the category folders | Windows' path phrase, no hint |

## Help

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

### cli-help.md changes

- `playpool check`: no change; the usage, summary and FOLDER help are the ones cli-help.md lists, and the description above is the plain-words rewrite it asks for.

## Settings

In `league.toml`, under `[league]`, as shipped (the config plan owns the comment's wording):

```toml
[league]
# The folder that holds this league's plays (.ply files).
play_path = 'C:\SIERRA\FBPRO98\PNFL'
```

- `play_path`: the pool; `check` reads it with no FOLDER only; a relative value resolves against the league folder (`LeagueConfig.path`).
- `[categories.offense]` / `[categories.defense]`: the folder names that mean a category.
- `--league NAME` picks the league; else `[athc] league` in `athc.ini`.
- No new keys, and no rules file for the pool: the attributes come from the play files. `team` and `ppp_path` are never read.

## Lines and exit codes

| When | Line | Code |
|---|---|---|
| no FOLDER, `play_path` missing on disk | `FAIL <play_path>: The system cannot find the path specified. Run 'athc config set play_path FOLDER'.` | 2 |
| no FOLDER, `play_path` is a file | `FAIL <play_path>: The directory name is invalid. Run 'athc config set play_path FOLDER'.` | 2 |
| no FOLDER, no `play_path` in `league.toml` | `FAIL <league.toml>: Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.` | 2 |
| a FOLDER that does not exist (unchanged) | `FAIL <folder>: The system cannot find the path specified.` | |
| a FOLDER that is a file (unchanged) | `FAIL <folder>: The directory name is invalid.` | |
| a second FOLDER | Click's usage text ending `Error: Got unexpected extra argument (<folder>).` | 2 |
| each issue (unchanged) | the reader's wording (`src/athc/playpool/reader.py`) | |
| the tally (unchanged) | `<n> play(s) checked in '<folder>', <n> issue(s)` | |

- Nothing is checked after any argument error.
- Codes stay 0 done, 1 findings, 2 error.

## Files to change

- `src/athc/cli/playpool/check.py`: the argument renamed `folder`, declared without a metavar (today's `metavar="[play_dir]"` goes), with cli-help.md's help.
- `src/athc/cli/playpool/check.py`: the docstring's summary and description become the help text above.
- `src/athc/cli/playpool/check.py`: order as today: the league resolves (a `LeagueError` is swallowed when a FOLDER is given and no `--league`); a given FOLDER goes through today's two checks (`exists()` for the path phrase, `is_dir()` for the directory phrase).
- `src/athc/cli/playpool/check.py`: with no FOLDER, `play_dir(play_path, league_file)` replaces the two checks and gives the hint.
- `src/athc/cli/playpool/check.py`: the command's own `No play_path` line becomes `Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.`
- `src/athc/cli/playpool/check.py`: the pool is read with `read_play_pool(folder, labels=labels)`; the issues and the tally print as today.
- `src/athc/playpool/`: no change.
- The usage line, argument help and `--league` text come with cli-help.md's general changes (Click 8.5, `[OPTIONS]` usage, argument help); no playpool-specific code.

## Tests

In `tests/integration/test_playpool_check.py`, with the `make_league` / `write_config` fixtures:

- No FOLDER, `play_path` missing on disk: the hint line, exit 2, stdout empty.
- No FOLDER, `play_path` a file: the hint line, exit 2, stdout empty.
- No FOLDER, no `play_path`: the `Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.` line, exit 2.
- A FOLDER run never reads `play_path`: a league whose `play_path` is missing on disk, or written as an array, with a clean FOLDER given: exit 0, no `FAIL`.
- Argument count at the limit: one FOLDER is accepted (today's tests).
- Argument count one past: two FOLDERs are Click's usage error with the period, exit 2, nothing checked.
- A wildcard FOLDER (`plays*`), once cli-help.md turns Click's expansion off: `FAIL plays*: The system cannot find the path specified.`
- Change `test_league_without_play_path_exit_2`: the line becomes `Plays folder is not set. Run 'athc config set play_path FOLDER' or pass the folder.`
- Change `tests/integration/test_cli_root.py::test_usage_lists_each_option`, rows `playpool` and `playpool check`: `athc playpool [OPTIONS] COMMAND [ARGS]...`, `athc playpool check [OPTIONS] [FOLDER]` (cli-help.md already changes them with the style).
- Every other playpool test keeps passing unchanged: `test_read_error_exit_2`'s stub still matches `read_play_pool(folder, labels=labels)`; `test_default_is_current_league_play_path` and `test_league_option_picks_another_league` have `play_path` on disk.
- `tests/unit/playpool/`: nothing.

## Docs and meta

- `docs/playpool/README.md`: the CLI section covers `check` (`[OPTIONS] [FOLDER]`, the two modes, the hint line and the `or pass the folder` line, the examples below); `check`'s exit table's error row names the hint.
- `docs/playpool/ARCHITECTURE.md`: nothing.
- `docs/gameplan/README.md` (its `check` row) and the other pool consumers' READMEs where they describe the pool's `WARN` lines: one sentence saying `athc playpool check` lists the same problems on their own, with an exit code.
- `config/release/docs/COMMANDS.txt`: section 12 (`playpool check`) gets the two modes, the hint and the `.` example.
- `STATUS.md`: the playpool section gains the hint; its "Open: count plays by file name type (TODO)." line stays.
- `CHANGELOG.md`, top of `## athc`: "playpool: `check` says to set `play_path` or pass the folder when the pool is unset or missing".
- `TODO.md`: the 1.0.0 playpool item is ticked when this work lands.
- `tests/integration/README.md`: the `athc playpool check` intro paragraph ("`play_dir` defaults to the league's `play_path`") rewritten for FOLDER, and a row per new case.

Examples for the docs:

```
athc playpool check
athc playpool check .
athc playpool check newplays
athc playpool check --league PCFL
```
