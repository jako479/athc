# config CLI plan

`athc config` gains `get`, a FILE argument (`athc.ini` or `league.toml`) on `path`, `edit` and `reveal`, and `--league NAME` on every verb, with the help, keys and lines below; the functional changes are in config-behavior.md.

Depends on cli-help.md landing first.

## Decisions

- `config` stays a group of verbs on the settings files; a bare `athc config` prints the group's help on stderr, exit 2, as every athc group.
- Five verbs: `path`, `edit`, `reveal`, `get`, `set`; `get` is new.
- No `list` verb.
- No `unset` verb; a coach who means it deletes the line in `edit`.
- No verb lists the league folders.
- Names stay: `path`, `reveal`, `get`, `set`.
- Summaries, placeholders, usage lines, hints, help blocks and tests are in cli-help.md's form and no other; its general fixes (uppercase placeholders, `[OPTIONS]`, the Positional arguments section) are not repeated here.
- `path`, `edit` and `reveal` take FILE, `athc.ini` or `league.toml`, as a positional argument; no second flag such as `--league-file`.
- FILE's two names are lowercase literals, matched without case in an athc callback on the optional `file` argument.
- FILE carries no metavar, so usage reads `[FILE]`; the callback raises `click.BadParameter(..., param_hint="'FILE'")`, so the hint reads `'FILE'`, never `'[FILE]'`, as convert-pdb-cli.md's `_ext` will.
- A FILE word that is neither name gets Click's `Choice` wording: `Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.`
- FILE defaults to `athc.ini`; when `--league NAME` is given and FILE is not, it defaults to `league.toml`.
- `--league NAME` is on `path`, `edit`, `reveal`, `get` and `set`, with its required value and cli-help.md's shared `--league NAME` text, resolution and errors, as on every league-aware command.
- `edit` and `reveal` print nothing on success.
- `get league` prints the league the tools will use, the name alone on stdout, through `resolve_league(league)`: with `--league NAME`, that name after the folder check.
- `get league` unset or blank is `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.`; a name whose folder is gone is `FAIL League 'X' not found. ...`; both exit 2, never 1 (1 is findings, for checkers and finders only).
- `get` prints paths through `LeagueConfig.path()`, so a relative `ppp_path` prints resolved against the league folder, and `team` as written through `LeagueConfig.string()` (check-ppp-cli.md adds it).
- `get team` is not matched against the `.lge`; `check-ppp` reports a bad team.
- `get` of a required key with no value (`path`, `play_path`, `team`) is `FAIL <league.toml>:` and the key's not-set line, exit 2: the tools' lines for the same key, with no alternative.
- `get ppp_path` unset is not a failure and never tells the coach to set it: nothing on stdout, `WARN <league.toml>: Game plan and profile folder is not set; using the folders the league file names.` on stderr, exit 0.
- `WARN` never changes the exit code.
- A key written as an array is `LeagueConfig.path()`'s existing `[league] <key>: Expected a string, got an array.`
- The rule arrays and athc-admin's keys are not `get` keys; they are edited in the file.
- KEY is matched without case against the known keys, `league`, `path`, `play_path`, `team` and `ppp_path`, for `set` as for `get`; the match hands `set` the canonical spelling to write.
- The KEY match is an athc callback on a plain `key` argument, not a Click `Choice` type; the argument carries no metavar, so usage shows `KEY` and the hint `'KEY'`.
- An unknown KEY gets Click's `Choice` wording, `Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.`, replacing the hand-written `unknown key` text.
- KEY's help line lists the keys.
- `set league` still checks the folder before writing; its error keeps Click's frame with Click's quoted hint: `Invalid value for 'VALUE': league 'PCLF' not found. No folder <leagues>\PCLF. Available: PCFL, PNFL.` (the lowercase `for value:` goes).
- `set` prints `OK   <file>: <key> = <value>`, as `OK   <athc.ini>: league = PCFL` or `OK   <league.toml>: team = Denver`, through the console's `ok` kind, replacing `Set league = X`.
- The other `athc.ini` sections (`[autocontinue]`, `[convert-pdb]`) stay out of `set`; `edit` opens them.
- `path`, `edit`, `reveal`, `get` and `set` read `[athc] league` when they need the league in use (FILE `league.toml` or a league key, without `--league`); `get league` reads it; `set league` reads `athc.ini` to rewrite it.
- A malformed `athc.ini` is `FAIL <athc.ini>: Not valid INI: ...` (2) on every verb that reads it.
- `get` and `set` are the only verbs that read `league.toml`'s contents; `path`, `edit` and `reveal` only locate it.
- Every league-aware command's `League is not set` error names `athc config set league NAME`; `get league` prints the same `FAIL` line when nothing is set.
- The tools' not-set lines say what is not set in plain words, then the `athc config set` command that sets it, as `League is not set. Run 'athc config set league NAME' or pass --league.` does: `League files folder is not set. Run 'athc config set path FOLDER' ...`, `Team is not set. Run 'athc config set team NAME' ...`, `Plays folder is not set. Run 'athc config set play_path FOLDER' ...`.
- A missing file or folder that a setting names ends `Run 'athc config set <key> FOLDER'.`
- Each command's own alternative (`or pass the folder`, `--path`, `a .pln file`) goes in through the gameplan, profile, convert-pdb, check-ppp, playpool and generate-schedule plans.
- check-ppp-cli.md's path sources, default team, `-r` and four-file rule do not apply to `config`.
- The period on `Got unexpected extra argument (x).` comes from the shared usage-error rendering in `src/athc/cli/__init__.py` (convert-pdb-cli.md); this plan raises no copy of its own.

### Which file

- `path`, `edit`, `reveal`, no FILE, no `--league`: `athc.ini` in the settings folder; no league read.
- No FILE, `--league NAME`: `leagues\NAME\league.toml`; the league is the name.
- `athc.ini`, no `--league`: `athc.ini`; no league read.
- `athc.ini`, `--league NAME`: `athc.ini`; the named league must exist, as on every command; the name is checked only, not read further.
- `league.toml`, no `--league`: `leagues\<league>\league.toml`, the league in use, from `[athc] league` in `athc.ini`.
- `league.toml`, `--league NAME`: `leagues\NAME\league.toml`; the league is the name.
- `get`: `league` reads `athc.ini` (or prints the `--league` name after its folder check); the other keys read the `league.toml` of the league in use, or of `--league NAME`.
- `set`: `league` writes `athc.ini`; the other keys write the `league.toml` of the league in use, or of `--league NAME`.
- The settings folder is `config_dir()`: `%LOCALAPPDATA%\athc`, or `ATHC_CONFIG_DIR` (dev and tests).
- The league folder must exist; the file need not: `--league NAME`, and the league in use for `league.toml`, go through `resolve_league()` and `league_dir()`, and a wrong name is `FAIL League 'NOPE' not found. ...`, 2.
- A missing `league.toml` is printed by `path` and stood in for by its folder in `reveal`, as for `athc.ini`; `edit` fails on it with `set`'s line, `FAIL <league.toml>: The system cannot find the file specified.`, exit 2, and creates nothing.

## Help

### config

```
Usage: athc config [OPTIONS] COMMAND [ARGS]...

  Show or change athc settings (athc.ini, league.toml).

  athc.ini holds the league in use and each tool's app-wide settings. A
  league's league.toml holds its path, play_path, team and ppp_path. Both live
  in your settings folder, %LOCALAPPDATA%\athc.

Options:
  -h, --help  Show this message and exit.

Commands:
  edit    Open athc.ini or league.toml in its default app.
  get     Print a setting.
  path    Print the path of athc.ini or league.toml.
  reveal  Show athc.ini or league.toml in File Explorer.
  set     Set a value in athc.ini or league.toml.

  Examples:

    athc config set league PCFL
    athc config edit league.toml
```

### config path

```
Usage: athc config path [OPTIONS] [FILE]

  Print the path of athc.ini or league.toml.

  The file need not exist yet.

Positional arguments:
  FILE  athc.ini or league.toml (default: athc.ini, or league.toml when
        --league is given).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config path
    athc config path league.toml
```

### config edit

```
Usage: athc config edit [OPTIONS] [FILE]

  Open athc.ini or league.toml in its default app.

  league.toml holds the league's path, play_path, team and ppp_path. A missing
  athc.ini is created empty first. Windows picks the app: Notepad, unless you
  changed it.

Positional arguments:
  FILE  athc.ini or league.toml (default: athc.ini, or league.toml when
        --league is given).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config edit
    athc config edit league.toml
    athc config edit --league PCFL
```

### config reveal

```
Usage: athc config reveal [OPTIONS] [FILE]

  Show athc.ini or league.toml in File Explorer.

  Opens the file's folder with the file selected, or just the folder when the
  file is missing.

Positional arguments:
  FILE  athc.ini or league.toml (default: athc.ini, or league.toml when
        --league is given).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config reveal
    athc config reveal league.toml
```

### config get

```
Usage: athc config get [OPTIONS] KEY

  Print a setting.

  league is read from athc.ini and checked against the league folders. path,
  play_path, team and ppp_path are read from the league's league.toml; a
  relative path is resolved against the league folder.

Positional arguments:
  KEY  Setting to print: league, path, play_path, team or ppp_path.

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config get league
    athc config get play_path
```

### config set

```
Usage: athc config set [OPTIONS] KEY VALUE

  Set a value in athc.ini or league.toml.

  league goes in athc.ini, the other keys in the league's league.toml.

Positional arguments:
  KEY    Setting to change: league, path, play_path, team or ppp_path.
  VALUE  New value.

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config set league PCFL
    athc config set play_path C:\SIERRA\FBPRO98\PNFL
    athc config set team Denver
```

## Settings

In `athc.ini`, under `[athc]`:

```ini
[athc]
; league used when --league is not given; change it with
;   athc config set league NAME
league = PNFL
```

In `league.toml`, under `[league]`, the keys `get` reads and `set` writes (set with `athc config set KEY VALUE`, or by hand with `athc config edit league.toml`):

```toml
# Open this file with: athc config edit league.toml

[league]
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# The folder that holds this league's plays (.ply files).
play_path = 'C:\SIERRA\FBPRO98\PNFL'
# Your team: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

- `get league` reads `[athc] league`; `set league` writes it; `path`, `edit`, `reveal`, `get` and `set` read it for the league in use.
- `get path | play_path | team | ppp_path` read the league file; `set` of the same keys writes it (config-behavior.md).
- check-ppp-cli.md owns the `path`, `team` and `ppp_path` comments; this plan owns the `play_path` comment and the header line.
- `athc.ini`'s header names `athc config edit league.toml` beside `play_path`.
- Each `league.toml` gains the first line above (`config/release/leagues/*/league.toml`; `config/dev/` mirrors).
- Each comment says what the value is, never which commands read it.

## Lines and exit codes

Click's usage errors print the `Usage:` line, `Try 'athc config <verb> --help' for help.`, then the `Error:` line, exit 2. Everything not listed prints unchanged.

| When | Line | Code |
|---|---|---|
| `set league PCFL` written | `OK   <athc.ini>: league = PCFL` (stdout, logged) | 0 |
| `set play_path C:\SIERRA\FBPRO98\PNFL` written | `OK   <league.toml>: play_path = C:\SIERRA\FBPRO98\PNFL` (stdout, logged); `path`, `team` and `ppp_path` the same way | 0 |
| `set` of a `league.toml` key, the file missing or with no `[league]` | `FAIL <league.toml>: The system cannot find the file specified.`, nothing written | 2 |
| `edit league.toml`, the file missing | `FAIL <league.toml>: The system cannot find the file specified.`, nothing created | 2 |
| `set` of a `league.toml` key, the file malformed | its parse error line, as every reader prints it; nothing written | 2 |
| `set league X --league Y` | `Error: --league cannot be used with set league.` | 2 |
| `set league` with no folder of that name | `Error: Invalid value for 'VALUE': league 'PCLF' not found. No folder <leagues>\PCLF. Available: PCFL, PNFL.` | 2 |
| `set league ""` | the same line with the blank name | 2 |
| `set league` without a value | `Error: Missing argument 'VALUE'.` | 2 |
| `set` or `get` with nothing | `Error: Missing argument 'KEY'.` | 2 |
| `get league`, set and its folder present | `PNFL` (stdout, not logged) | 0 |
| `get league --league PCFL` | `PCFL` | 0 |
| `get league`, unset or blank | `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.` | 2 |
| `get league`, folder gone | `FAIL League 'PCLF' not found. No folder <leagues>\PCLF. Available: PNFL.` | 2 |
| `get play_path`, `path`, `ppp_path` set | the resolved folder, as `LeagueConfig.path()` gives it (stdout) | 0 |
| `get team` set | the value as written (stdout) | 0 |
| `get path` with no value in `league.toml` | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER'.` | 2 |
| `get play_path` with no value | `FAIL <league.toml>: Plays folder is not set. Run 'athc config set play_path FOLDER'.` | 2 |
| `get team` with no value | `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME'.` | 2 |
| `get ppp_path` with no value | nothing on stdout; `WARN <league.toml>: Game plan and profile folder is not set; using the folders the league file names.` | 0 |
| `get <key>` written as an array | `FAIL <league.toml>: [league] play_path: Expected a string, got an array.` (unchanged) | 2 |
| `get` or `set` with an unknown key | `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` | 2 |
| `path`, `edit`, `reveal`, `get` or `set --league NOPE` | `FAIL League 'NOPE' not found. No folder <leagues>\NOPE. Available: PCFL, PNFL.` | 2 |
| `path`, `edit` or `reveal league.toml`, or `get` or `set` of a league key, with no league set | `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.` | 2 |
| FILE neither name, a league name typed there included | `Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.` | 2 |
| a third word to `set`, a second to `get`, `path`, `edit` or `reveal` | `Error: Got unexpected extra argument (x).` | 2 |
| `--league` without a name, on any verb that has it | `Error: Option '--league' requires an argument.` | 2 |
| `edit`, no app for the file | `FAIL <athc.ini>: No application is associated with the specified file for this operation.` (any other Windows text the same way) | 2 |
| any verb reading a malformed `athc.ini` | `FAIL <athc.ini>: Not valid INI: No [section] header above it (at line 1).` (as `set` prints it now) | 2 |
| `path` | the path (stdout, not logged), unchanged | 0 |
| `edit`, `reveal` done | nothing, unchanged | 0 |
| bare `athc config` | the group's help on stderr, unchanged | 2 |

- The `Error:` lines keep Click's frame; athc's part after `Invalid value for 'VALUE':` starts lowercase.
- Codes stay 0 done, 2 error; no config verb uses 1.

## Files to change

- `src/athc/cli/config/__init__.py`: register `get`; `KEYS = ("league", "path", "play_path", "team", "ppp_path")`, shared by `get` and `set`; `key_callback` for the `key` argument (casefold match returns the canonical spelling, else `click.BadParameter` with Click's `Choice` wording; Click attaches `'KEY'`); `FILE_NAMES = ("athc.ini", "league.toml")` and `file_callback` for the optional `file` argument (`None` passes through; a casefold match returns the canonical name; else `click.BadParameter("'<word>' is not one of 'athc.ini', 'league.toml'.", param_hint="'FILE'")`); no metavar on either argument, so Click renders `KEY` and `[FILE]`; `settings_file(file: str | None, league: str | None) -> Path` for `path`, `edit` and `reveal`: `config_file()` for `athc.ini`, `league_file(league)` (config-behavior.md) for `league.toml`, the FILE default above, and `resolve_league(league)` for a named league with `athc.ini`.
- `src/athc/config.py`: `LeagueConfig.string(key)` as check-ppp-cli.md describes it (whichever plan lands first adds it).
- `src/athc/cli/config/path.py`, `edit.py`, `reveal.py`: the optional `file` argument with `file_callback` and the shared `league_option` from `athc.cli`; `path` prints `settings_file(...)`; `edit` creates the parent folder and the empty file when `athc.ini` is missing, and raises the `FAIL <league.toml>: The system cannot find the file specified.` error, creating nothing, when `league.toml` is missing; `reveal` creates the parent folder when missing (`config_dir()`; a league folder already exists), then `click.launch(locate=True)` on the file or `click.launch` on the folder.
- `src/athc/cli/config/get.py` (new): the `key` argument with `key_callback` and `league_option`; `league` prints `resolve_league(league)`; the other keys load `load_league_config(league)` and print `path(key)` or `string(key)`; a `None` value raises a `ConfigFileError` with `cfg.dir / LEAGUE_FILE` and the key's not-set line for `path`, `play_path` and `team`, and for `ppp_path` goes through `console.warn` with the `Game plan and profile folder is not set` line and returns normally.
- `src/athc/cli/config/set.py`: the `key` argument with `key_callback` and `league_option`; for `league`, the folder check with `param_hint="'VALUE'"`, then `set_config_value`; `console.ok(f"{written}: {key} = {value}")` with the path either write returns.
- Every config verb: the help texts above.

## Tests

`tests/integration/test_config.py` (`path`, `edit`, `reveal`, `get`) and `tests/integration/test_config_set.py` (`set`); no new fixtures (`config_dir`, `write_config` and `make_league` in `tests/conftest.py` cover it).

- `get league`, set with its folder present: the name on stdout, stderr empty, 0.
- `get league --league PCFL`: that name, 0.
- `get league` unset: `League is not set`, the folders listed, 2.
- `get league` with a blank value: the same.
- `get league`, folder gone: `not found`, 2.
- `get League` and `get LEAGUE` accepted.
- `get colour` rejected with the exact line `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` (the known keys accepted, one past them rejected).
- `get` with no KEY: `Error: Missing argument 'KEY'.`
- `get league` with a malformed `athc.ini`: the INI line, 2.
- `get league --league NOPE`: `not found`, 2.
- `get path` and `get play_path` absolute: printed as written.
- `get ppp_path` relative: printed resolved against the league folder.
- `get team`: printed as written.
- `get path`, `get play_path`, `get team` unset: each key's `... is not set. Run 'athc config set <key> ...'.` line naming `league.toml`, stdout empty, 2.
- `get ppp_path` unset: stdout empty, the `WARN ... Game plan and profile folder is not set; using the folders the league file names.` line, 0.
- `get` of a key written as an array: the `Expected a string` line, 2.
- `get <key> --league NAME` reads that league's file.
- `get` of a league key with no league set and no `--league`: `League is not set`, 2.
- `get` of a league key in a league folder without `league.toml`: the unset lines.
- `set League PCFL` writes `league = PCFL` once, in the canonical spelling; the `OK` line names `athc.ini` and the pair.
- `set` of a league key: the `OK` line names `league.toml` and the pair.
- `set Play_Path` writes `play_path`.
- `set` KEY: the five keys accepted (the writes above); `set colour x` rejected with the exact line `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.`
- `set league` with a missing folder: the `'VALUE'` hint.
- `set league` without VALUE: `Error: Missing argument 'VALUE'.`
- `path`, `edit`, `reveal` with nothing: `athc.ini`.
- `league.toml` with `[athc] league` set: that league's file.
- `League.TOML` accepted.
- `PCFL` as FILE rejected with the exact line `Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.` (the hint reads `'FILE'`, not `'[FILE]'`).
- A word too many: `Got unexpected extra argument (x).`
- `--league PCFL` alone: PCFL's `league.toml`.
- `league.toml --league PCFL`: the same.
- `athc.ini --league PCFL`: `athc.ini`; `athc.ini --league NOPE` still fails.
- `league.toml` with nothing set: `League is not set`, 2.
- `--league NOPE`: `not found`, 2.
- `--league` with no name: `requires an argument`, 2.
- `league.toml` with a malformed `athc.ini`.
- `path league.toml` with the file missing: the path, 0.
- `edit league.toml` with the file missing: `FAIL <league.toml>: The system cannot find the file specified.`, 2, no file created, nothing opened.
- `edit league.toml` with the file present: opened, content kept.
- `reveal league.toml` with the file present: `locate=True` on it.
- `reveal league.toml` with the file missing: the league folder.
- Help: `config --help` lists `get`.
- Help: `--league NAME` shows on `path`, `edit`, `reveal`, `get` and `set`; FILE shows on the three.
- Limits: `config` has no numeric limits or ranges; the key list's (one for `get` and `set`) and FILE's accepted values and one past them are the tests above.
- `test_config_set.py`, `test_cli_sets_league`: stdout is the `OK` line naming `athc.ini`.
- `test_config_set.py`, `test_cli_rejects_unknown_league`: `Invalid value for 'VALUE':`.
- `test_config_set.py`, `test_cli_rejects_unknown_key`: Click's `'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` after `Invalid value for 'KEY':`.
- `test_config_set.py`: `test_cli_rejects_blank_league`, `test_cli_malformed_ini_is_clean_error`, `test_cli_help_lists_known_keys` and `test_group_lists_set` keep passing unchanged.
- `test_config.py`, `test_group_lists_subcommands`: also asserts `get`.
- `test_config.py`: `test_path_prints_config_file`, `test_reveal_selects_existing_file` and `test_reveal_opens_folder_when_absent` keep passing unchanged.
- `tests/integration/test_cli_root.py`, `test_help_uses_lowercase_names`: the `config set` row (`["key value"]` shown, `["KEY", "VALUE"]` hidden) goes, owned by this plan; cli-help.md's uppercase placeholders invert the whole test for every command, which cli-help.md does not yet list.
- `tests/integration/test_cli_root.py`: the config verbs are not added to `LEAGUE_COMMANDS`; their `--league` tests live in `test_config.py`.
- `tests/integration/test_cli_root.py`, `test_short_help_option_on_every_command`: picks up `get` by itself.
- `packaging/sandbox-steps.ps1`: the `config set league TEST` check asserts `OK` and `league = TEST` instead of `Set league = TEST`.
- `packaging/sandbox-steps.ps1`: `$commands` gains `config get`; a `config get league` check expects `TEST` on stdout, exit 0.
- `tests/integration/README.md`: the `athc config set` table's `CLI sets league` row (`stdout: Set league = <NAME>`) and `CLI unknown key` row ("names known keys") change.
- `tests/integration/README.md`: the `athc config` table's `Group lists subcommands` row (path / edit / reveal) changes.
- `tests/integration/README.md`: the root table's `Help uses lowercase names` row drops `config set`.
- `tests/integration/README.md`: both config tables gain the rows above.

## Docs and meta

- `docs/config/README.md`: rewritten around the five verbs, FILE, `--league NAME`, the lines and codes above; it names `set` (or `edit league.toml`) as the way to set `path`, `play_path`, `team` and `ppp_path`, and `get` as the way to read them.
- `docs/config/ARCHITECTURE.md`: "four thin commands" becomes five; the layout gains `get.py`; the exit table gains the `FAIL` cases for league errors, a malformed `athc.ini` and an unset key; Boundaries says `get` reads `league.toml`. (docs-layout.md folds the pair into one `config.md`; whichever lands first carries these changes.)
- `config/release/docs/COMMANDS.txt` section 15: `get`, `set`'s `league.toml` keys, FILE, `--league`, the `OK` line, the examples.
- `config/release/docs/README.txt`: "open leagues\PNFL\league.toml in your settings folder" becomes `athc config edit league.toml`.
- `config/release/docs/README.txt`: the "To open this folder" line keeps `athc config reveal`.
- `config/release/docs/README.txt`: the troubleshooting entries on `play_path` add `athc config get play_path` and `athc config edit league.toml`.
- `config/release/athc.ini` and `config/dev/athc.ini`: the header's `play_path` sentence names `athc config edit league.toml`.
- `config/release/leagues/*/league.toml` and the dev twins: the header line "Open this file with: athc config edit league.toml".
- `docs/design/architecture.md`, Config: the bullet becomes "`athc config path | edit | reveal | get | set` locate, open, reveal, read and write the settings files: `path`, `edit` and `reveal` take FILE (`athc.ini`, the default, or `league.toml`) and `--league NAME`; `get` reads `league` from `athc.ini` and `path`, `play_path`, `team`, `ppp_path` from the league's `league.toml`; `set` writes `league` to `athc.ini` through ConfigUpdater, validating the league folder first, and `path`, `play_path`, `team`, `ppp_path` to the league's `league.toml` through a TOML library that keeps comments (so comments survive in both); `edit` opens through `os.startfile`, `reveal` through `click.launch`".
- `docs/design/architecture.md`, CLI: the `--league` list gains `config path | edit | reveal | get | set`; its lowercase-placeholder rule (`metavar="pdb_file"`, never Click's capitals) changes with cli-help.md, not with this plan.
- `docs/design/installer.md`: "the only value a user must edit is `play_path` in `leagues\PNFL\league.toml`" gains "(`athc config edit league.toml` opens it)".
- `docs/design/installer.md`: the sandbox test description covers `config get`.
- cli-help.md, config: the group summary "Show or change athc settings (athc.ini, league.toml)." instead of "(athc.ini)".
- cli-help.md, config: `config get` is new; its block above.
- cli-help.md, config: `config path`, `edit`, `reveal` gain the FILE argument, the shared `--league NAME` option and the summaries above; the `reveal` summary "Show athc.ini in File Explorer." widens by the league file.
- cli-help.md, config: `config set` gets the summary "Set a value in athc.ini or league.toml.", the description above, KEY's help listing the five keys, and the shared `--league NAME` option; VALUE as cli-help.md has it.
- cli-help.md, config: the shared `--league NAME` text is used as written on `path`, `edit`, `reveal`, `get` and `set`.
- `CHANGELOG.md`: `config: get prints the league in use and a league's path, play_path, team and ppp_path; path, edit and reveal take league.toml as well as athc.ini; set writes path, play_path, team and ppp_path to the league's league.toml and says which file it wrote`.
- `STATUS.md`: an `athc config get` row; the "league in use" bullet gains `get` and the league file.
- `TODO.md`: this plan's entry, ticked when done.
