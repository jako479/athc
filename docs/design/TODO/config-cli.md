# config CLI plan

**Goal:** `athc config` keeps its four verbs on `athc.ini` (`path`, `edit`, `reveal`, `set`) and gains `get`, so a coach can ask which league the tools use, and what its folders and team are, as easily as set them. `path`, `edit` and `reveal` take a FILE argument, `athc.ini` (the default) or `league.toml`, since the league file holds everything a coach sets by hand (`path`, `play_path`, `team`, `ppp_path`) and sits in a hidden folder; `--league NAME` picks the league, as on every other command. `set` stays the one writer, writes `league` to `athc.ini` and `path`, `play_path`, `team` and `ppp_path` to the league's `league.toml`, and says which file it wrote.

**Status:** proposal, 2026-10-13; nothing changed yet. Every choice is decided below, with its reason next to it. Reviewed twice (coach workflows, codebase fit); the findings are folded in. Depends on cli-help.md landing first.

## 1. Today

- `athc config` is a group of four leaf commands in `src/athc/cli/config/` (`path.py`, `edit.py`, `reveal.py`, `set.py`; the group in `__init__.py`). None takes an option besides `-h`; none reads a league. A bare `athc config` prints the group's help on stderr and exits 2, as every athc group does (`no_args_is_help` is Click's default for a group; `_OnePlace.main` in `src/athc/cli/__init__.py` logs `no command given; help shown`).
- `config path` prints `config_file()` (`src/athc/config.py`: `%LOCALAPPDATA%\athc\athc.ini`, or `ATHC_CONFIG_DIR\athc.ini`) through `console.print`, whether or not the file exists.
- `config edit` creates the settings folder and an empty `athc.ini` when missing, then `click.launch(path)`: on Windows that is `os.startfile`, the app Windows associates with `.ini`. Click returns 127 when `os.startfile` raises, `edit` ignores the return value, so a broken association prints nothing and exits 0. `EDITOR` and `VISUAL` are ignored (`test_edit_ignores_editor_env` pins it).
- `config reveal` creates the settings folder when missing, then `click.launch(path, locate=True)` (`explorer /select, <athc.ini>`) when the file exists, else opens the folder. Nothing is printed.
- `config set KEY VALUE`: `KNOWN_KEYS = ("league",)`; another key is `Error: Invalid value for key: unknown key 'colour'. Known keys: league.` (2). `league` is checked with `league_dir(value)` first; a missing folder is `Error: Invalid value for value: league 'X' not found. No folder <leagues>\X. Available: PNFL.` (2). Then `set_config_value` rewrites `athc.ini` through ConfigUpdater, keeping comments and creating the file, the `[athc]` section (placed first) or the key as needed; a malformed file is `FAIL <athc.ini>: Not valid INI: ... (at line N).` (2) and the file is left as written. Success prints `Set league = X` through `console.result` (stdout, logged), exit 0. The usage line's placeholders are lowercase (`key value`), pinned by `test_help_uses_lowercase_names` in `tests/integration/test_cli_root.py` and by `packaging/sandbox-steps.ps1`, which asserts `Set league = TEST`.
- Nothing prints the league in use or a league's folders; a coach learns them by opening the files or from another command's `FAIL` line. Nothing opens or locates a league's `league.toml`: the release README says "open leagues\PNFL\league.toml in your settings folder", and the tools' lines name the file in full: `<league.toml>: No play_path for the league. Set play_path in this file.` (gameplan, convert-pdb and `playpool check`, `src/athc/gameplan/config.py`, `src/athc/pdbtoexcel/config.py`, `src/athc/cli/playpool/check.py`), `<league.toml>: No path for the league. Set path in this file.` (check-ppp, `src/athc/cli/check_ppp.py`), `<play_path>: The system cannot find the path specified. Set play_path in <league.toml>.` (`play_dir` in `src/athc/config.py`).
- `play_path` is read by gameplan, convert-pdb and `playpool check`; profile reads only its rules (`src/athc/profile/config.py`).
- Settings: the group reads none of its own; `set` reads `athc.ini` only to rewrite it. Docs: `docs/config/README.md`, `docs/config/ARCHITECTURE.md`, section 15 of `config/release/docs/COMMANDS.txt`, the Config bullet of `docs/design/architecture.md` ("thin wrappers over `click.launch` and ConfigUpdater"). Tests: `tests/integration/test_config.py` (`path`, `edit`, `reveal`; launches mocked), `tests/integration/test_config_set.py`, and the installer's sandbox test `packaging/sandbox-steps.ps1` (`config set league TEST`, `config path`, `config edit`, `config reveal`, every config verb with `-h`).

## 2. Who runs it, for what

| # | Who | Wants to | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach, first run | find the settings the installer seeded | `athc config reveal` | File Explorer on the settings folder, `athc.ini` selected, `leagues\` beside it |
| 2 | Coach, first run | set `play_path` (gameplan, convert-pdb and `playpool check` need it) | `athc config edit league.toml` | the league's `league.toml` open in Notepad |
| 3 | Coach | set `team` and `ppp_path` for check-ppp, or `path` | the same | the same file |
| 4 | Coach in two leagues | switch the league the tools use | `athc config set league PCFL` | `OK   <athc.ini>: league = PCFL` |
| 5 | Coach in two leagues | know which league the tools use now | `athc config get league` | `PNFL` |
| 6 | Coach | know which folder or team the tools will use (a relative `ppp_path`, a `team` typed weeks ago) | `athc config get play_path`, `athc config get team` | the resolved folder; the team as written |
| 7 | Coach | edit another league's file without switching to it | `athc config edit --league PCFL` | that file open |
| 8 | Coach | change a tool's default (`hot_corner`, the convert-pdb columns) | `athc config edit` | `athc.ini` open in Notepad, every setting documented inline |
| 9 | Coach | a file's path, to paste into a message or `type` it | `athc config path`, `athc config path league.toml` | the path |
| 10 | Coach | mistypes the league | `athc config set league PCLF` | the error, listing the league folders; nothing written |
| 11 | Coach | a league folder they copied, with no `league.toml` yet | `athc config edit --league NEW` | an empty `league.toml` created and opened; its help names the keys to add |
| 12 | Coach, from a script | the league in use | `for /f %i in ('athc config get league') do ...` | the bare name on stdout; exit 2 when none is set |

## 3. What other tools do

- **Every config command pairs a getter with its setter, and most add edit.** git: `git config list`, `get`, `set`, `unset`, `edit`; gh ("Display or change configuration settings for gh"): `get`, `set`, `list`, `clear-cache`; npm: `set`, `get`, `delete`, `list`, `edit`, `fix`; pip ("Manage local and global configuration"): `list`, `edit`, `get`, `set`, `unset`, `debug`; kubectl: `view`, `set`, `unset`, `use-context`, `current-context` ("Display the current-context") and more.
- **A getter prints the bare value and reads the file the scope names.** gh `config get`: "Print the value of a given configuration key"; git `get`: "Returns error code 1 if key is not present", and `--global`, `--local`, `--file` apply "For reading options" as well as writing; kubectl `current-context` prints the context name alone.
- **A scope picks the file; the user's own file is the default.** git writes to the repository file by default, and `--global`, `--system`, `--worktree` or `--file <config-file>` pick another; `git config edit` "Opens an editor to modify the specified config file; either --system, --global, --local (default), --worktree, or --file". pip: "If none of --user, --global and --site are passed" a virtual environment's file is used "if one is active and the file exists. Otherwise, all modifications happen to the user file by default." npm's `--location` is "global", "user" or "project", default "user".
- **A flag that names something takes a value; a flag that picks a mode is plain.** git's `--global`, `--local` and pip's `--user`, `--site` are plain; git's `--file <config-file>`, `-C <path>`, gh's `--host <string>`, npm's `--location`, kubectl's `--kubeconfig string` all take one. clig.dev: "If a flag can accept an optional value, allow a special word like "none"." and "Don't just use a blank value, this can make it ambiguous whether arguments are flag values or arguments." Click's parser hands the next word to such a flag whenever one is there (`_get_value_from_state` in `click/parser.py`), and `Option '--league' requires an argument.` is what a required value prints when the word is missing.
- **Windows commands take the file as the argument.** `type [<drive>:][<path>]<filename>` "displays the contents of a text file"; `notepad <file>` the same. VS Code's menu item for the native file manager is "Reveal in File Explorer" on Windows ("Reveal in Finder" on macOS, "Open Containing Folder" on Linux).
- **Edit opens the file in an editor; Windows tools use the file association.** winget: "The settings command will launch your default JSON editor. Windows by default will launch Notepad as an option." npm's editor is "The EDITOR or VISUAL environment variables, or '%SYSTEMROOT%\notepad.exe' on Windows"; pip's `--editor` "Uses VISUAL or EDITOR environment variables if not provided". Python's `os.startfile` "acts like double-clicking the file in Windows Explorer, or giving the file name as an argument to the start command"; it calls `ShellExecute`, whose return codes include `SE_ERR_NOASSOC`, "There is no application associated with the given file name extension", with "Call GetLastError for extended error information"; the system error `ERROR_NO_ASSOCIATION` (1155) reads "No application is associated with the specified file for this operation."
- **Where the file is.** pip `config debug`: "List the configuration files and values defined under them"; git `--show-origin` adds "the actual origin (config file path, ref, or blob id if applicable)"; kubectl documents its default, "Otherwise, ${HOME}/.kube/config is used".
- **Tell the user what changed; suggest the command.** clig.dev: "If you change state, tell the user"; "When a command changes the state of a system, it's especially valuable to explain what has just happened"; "Suggest commands the user should run"; "Make the default the right thing for most users"; "Use the same flag names for the same things"; "Don't have ambiguous or similarly-named commands".
- **Keys without case.** configparser: "By default, section names are case sensitive but keys are not"; `optionxform` "converts the name to lowercase. This also means that when a configuration file gets written, all keys will be lowercase." ConfigUpdater's `optionxform` "By default ... uses str.lower". Click's `Choice(case_sensitive=False)` matches without case, returns the choice's own spelling, and its error reads `'colour' is not 'league'.` for one choice, `'x' is not one of 'a', 'b'.` for several.
- **Writing TOML needs a library the standard library lacks.** Python's `tomllib`: "This module does not support writing TOML."; its docs point at Tomli-W, and at TOML Kit as "a style-preserving TOML library with both read and write capability ... recommended ... for editing already existing TOML files." athc rewrites `athc.ini` with ConfigUpdater for the same reason (comments survive).
- **Removing a key is its own verb where it matters.** git `unset`, npm `delete` (and `set` with no value: "the key will be removed from your config file entirely"), pip `unset`, kubectl `unset`. npm's `get` with no key "behaves the same as npm config list"; the other getters require the key.

## 4. Decisions

1. **`config` stays a group of verbs on the settings files, and a bare `athc config` keeps the project's rule:** help on stderr, exit 2, as every athc group (architecture.md, CLI). The group is the shape of git, gh, npm, pip and kubectl.
2. **Five verbs: `path`, `edit`, `reveal`, `get`, `set`.** `get` is new: every precedent pairs a getter with its setter, and nothing in athc prints the league in use or a league's folders (rows 5 and 6). No `list`: `athc.ini` is one file with no cascade or merged scopes, the shipped file documents every setting inline, so `edit` shows it all and `path` with `type` prints it; git, gh, npm and pip have `list` because they merge several files. No `unset`: every key `set` writes is one the tools need, so unsetting it only produces its "is not set" error; a coach who means it deletes the line in `edit`.
3. **`set` writes `league` to `athc.ini`, and `path`, `play_path`, `team` and `ppp_path` to the league's `league.toml`, the league in use or `--league NAME`.** This reverses check-ppp-cli.md decision 14, which kept `team` and `ppp_path` edited by hand in `league.toml`. These five are the keys the tools tell the coach to set (`Run 'athc config set league NAME'`, `Run 'athc config set play_path FOLDER'` and the rest). `set path`, `set play_path` and `set ppp_path` take a FOLDER, written as supplied (no folder check, nothing resolved); `set team` a NAME. A missing `league.toml`, or one with no `[league]` section, is Windows' `FAIL <league.toml>: The system cannot find the file specified.` and nothing is written: athc does not repair a broken install. A malformed `league.toml` is its parse error line, as every reader prints it, and nothing is written. `--league` is not valid with `set league`: `Error: --league cannot be used with set league.` (decided 2026-10-13). `league.toml` is written through a TOML library that keeps comments (the standard library's `tomllib` cannot write TOML), so its comments and other lines stay as they were, as ConfigUpdater keeps them in `athc.ini`. The other `athc.ini` sections (`[autocontinue]`, `[convert-pdb]`) stay out of `set`: they are their tools' settings, each read with typed defaults ("`athc.ini` values come back as strings, so type conversion is the tool's job", architecture.md) and documented in the shipped file, which `edit` opens.
4. **`get` reads both files.** `league` comes from `athc.ini`; `path`, `play_path`, `team` and `ppp_path` come from the league's `league.toml`, the league in use or `--league NAME`. git's `get` reads whichever file its scope option names; a coach can then ask what the tools will use: paths through `LeagueConfig.path()`, so a relative `ppp_path` prints resolved against the league folder, `team` as written through `LeagueConfig.string()` (check-ppp-cli.md section 9 adds it). `team` is not matched against the `.lge`: that matcher is check-ppp's (`_team.py`), and `get` reads a file, it does not check a league; `check-ppp` reports a bad team. A required key with no value (`path`, `play_path`, `team`) is `FAIL <league.toml>:` and the key's not-set line, exit 2: `League files folder is not set. Run 'athc config set path FOLDER'.`, `Plays folder is not set. Run 'athc config set play_path FOLDER'.`, `Team is not set. Run 'athc config set team NAME'.`; the tools' lines for the same key, with no alternative, since `get` takes none. `ppp_path` is optional (check-ppp-cli.md decision 3: no `ppp_path` means the league locations; its section 6 ships it commented out), so an unset `ppp_path` is not a failure and must not tell the coach to set it: `get ppp_path` prints nothing on stdout and `WARN <league.toml>: Game plan and profile folder is not set; using the folders the league file names.` on stderr, exit 0. `WARN` is the console's "noted, nothing failed" kind and never changes the code (architecture.md); stdout stays empty so a script reads the true value, nothing, as git's `get` prints nothing for an unset key. A key written as an array is `LeagueConfig.path()`'s existing `[league] <key>: Expected a string, got an array.` The rule arrays and athc-admin's keys are not `get` keys: they are edited in the file.
5. **KEY is matched without case against the known keys,** `league`, `path`, `play_path`, `team` and `ppp_path`, for `set` as for `get`. INI keys are case-insensitive (configparser), so `League` must mean `league`, and the match hands `set` the canonical spelling to write. The match is an athc callback on a plain `key` argument, not a Click `Choice` type: a `Choice` would print `{league}` as the placeholder, and arguments carry no explicit metavar (an explicit one prints verbatim in the usage line and in Click's error hint, `Argument.make_metavar` and `get_error_hint` in `click/core.py`), so the argument name gives `KEY` in usage and `'KEY'` in the hint. The callback uses Click's `Choice` wording, `Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.`, replacing today's hand-written `unknown key` text; the help line lists the keys, as cli-help.md prescribes.
6. **`set league` still checks the folder before writing** (architecture.md: "`set league` validates the folder first"), so `get league` never meets a name with no folder behind it unless the file was edited by hand. The error keeps Click's frame with Click's quoted hint, `Invalid value for 'VALUE': league 'PCLF' not found. No folder <leagues>\PCLF. Available: PCFL, PNFL.`; today's `for value:` follows the lowercase metavar that cli-help.md retires.
7. **`set` prints `OK   <file>: <key> = <value>`,** as `OK   <athc.ini>: league = PCFL` or `OK   <league.toml>: team = Denver`. The console's "one item done" kind is `ok`, and "a line about a file starts with its path, once" (architecture.md); the editing commands print theirs the same way: `set-normals` `OK   <path>: <n> normal play(s)` (`src/athc/cli/gameplan/set_normals.py`), `set-specials` `OK   <path>: updated (<n> special play(s))` and `profile copy` `OK   <path>: updated (...)` (`set_specials.py`, `profile/copy.py`). Naming the file matters here because it sits in a hidden folder: the first `set` also shows where the settings live. clig.dev: "If you change state, tell the user." Today's `Set league = X` goes through `result`, the tally kind.
8. **`get league` prints the league the tools will use,** the name alone on stdout (gh: "Print the value of a given configuration key"; kubectl `current-context`), so a script can read it. It goes through `resolve_league(league)`: with `--league NAME` it is that name after the folder check; otherwise unset or blank is `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.`, and a name whose folder is gone is `FAIL League 'X' not found. ...`, both exit 2. Exit 2, not git's 1: in athc 1 means findings and belongs to the checkers and finders only (architecture.md, Exit codes), and a `get` with nothing to print could not do its job. The `FAIL` line carries the fix and the choices (clig.dev: suggest the command), which serves a coach better than git's silence.
9. **`path`, `edit` and `reveal` take FILE, `athc.ini` or `league.toml`, and `--league NAME` picks the league.** `--league NAME` keeps its required value and cli-help.md rule 10's text everywhere, and a shape of its own on three verbs would break "Use the same flag names for the same things" and clig.dev's "Don't just use a blank value" (Click's parser would take the next word as the value). Of the two shapes left for picking the file, a positional or a plain flag, the positional wins: the argument is the file's real name, as `type <filename>` and `notepad <file>` take it, so `athc config edit league.toml` reads as a coach thinks of it, while a second flag beside `--league` (`--league-file`) would be two similarly named flags on one command (clig.dev). The two names are lowercase literals, as cli-help.md rule 2 reserves capitals for placeholders, matched without case in an athc callback on the optional `file` argument (no metavar: Click renders `[FILE]` in usage from the name; the callback raises `click.BadParameter(..., param_hint="'FILE'")`, so the hint reads `'FILE'`, never `'[FILE]'`, as [convert-pdb-cli.md](convert-pdb-cli.md)'s `_ext` will; today's `_ext` passes no `param_hint`). A word that is neither name gets Click's `Choice` wording: `Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.` FILE defaults to `athc.ini`; when `--league NAME` is given and FILE is not, it defaults to `league.toml`, because `athc.ini` has nothing per league, so a coach who names a league means that league's file (clig.dev: "Make the default the right thing for most users"; pip's default scope likewise depends on context). `--league NAME` is resolved on every form, so a named league must exist even with `athc.ini` (`playpool check` with an explicit folder does the same today, `src/athc/cli/playpool/check.py`); it is not read further for `athc.ini`.
10. **The league folder must exist; the file need not.** `--league NAME`, and the league in use for `league.toml`, go through `resolve_league()` and `league_dir()` (a wrong name is `FAIL League 'NOPE' not found. ...`, 2), since a missing folder is a typo, never a request for a new league (`set league` refuses the same name). `path league.toml` prints the path whether or not the file exists, as `path` does for `athc.ini`; `edit league.toml` creates an empty `league.toml` when missing, as `edit` does for `athc.ini` (an empty file reads as no values, which `load_league_config` already allows for a missing one); `reveal league.toml` selects the file, or opens the league folder when the file is missing, as `reveal` does for `athc.ini`.
11. **`edit` opens the file with `os.startfile` directly, so a failure reaches `main`.** `click.launch` swallows the `OSError` and returns 127, which `edit` ignores, so a coach whose `.ini` association is broken sees nothing and exit 0. Called directly, the error carries the Windows error and the file name (checked on 2026-10-13 with a missing file: `FileNotFoundError`, `winerror 2`, Windows' text, the file name), so `main` prints `FAIL <file>: <Windows' text>` and exits 2; for a file with no associated app, `ShellExecute` reports `SE_ERR_NOASSOC` and the system error is 1155, `No application is associated with the specified file for this operation.` That case was not run; the line is Windows' text for that error, as the Wording rule asks. `EDITOR` and `VISUAL` stay ignored: winget opens the default editor, npm's Windows default is Notepad, and the association is what the coach set in Windows. `reveal` keeps `click.launch`: File Explorer is always present, so there is no association to break.
12. **`edit` and `reveal` print nothing on success,** as today and as `git config edit` and `winget settings`; the window that opens is the result.
13. **Names stay:** `path` (it prints a file's path, not a folder), `reveal` (VS Code's Windows menu item is "Reveal in File Explorer"; STATUS.md's decision not to call it `explorer`), `get` and `set` (git, gh, npm, pip). Summaries and placeholders follow cli-help.md rules 1 to 15.
14. **Settings read:** `path`, `edit`, `reveal`, `get` and `set` read `[athc] league` when they need the league in use (FILE `league.toml` or a league key, without `--league`); `get league` reads it; `set league` reads `athc.ini` to rewrite it, and `set` of a league key reads `league.toml` to rewrite it. A malformed `athc.ini` is `FAIL <athc.ini>: Not valid INI: ...` (2) in each case, as `load_config` reports it today. `get` and `set` are the only verbs that read `league.toml`'s contents; `path`, `edit` and `reveal` only locate it.
15. **Order of checks in `set`:** KEY (Click); for `league`, VALUE (the folder), then `athc.ini` (parse, write); for a league key, the league (decision 10), then `league.toml` (parse, write); then the `OK` line. A usage error never touches the file, and a malformed file is reported before anything is written, as `test_cli_malformed_ini_is_clean_error` pins today.
16. **No verb lists the league folders.** The leagues are folders under `leagues\`, which `reveal` shows in File Explorer beside `athc.ini`, and which the coach made by copying one (README.txt: "To add another league, copy a league folder and rename it"), so the names are the coach's own; every wrong or missing name already lists them (`Available: PCFL, PNFL.`, `src/athc/config.py`), so a guess costs one command. kubectl needs `get-contexts` because contexts live inside one file where nothing else shows them.
17. **The tools' not-set lines name the `athc config set` command (decided 2026-10-13).** Each says what is not set in plain words, then the command that sets it, as the existing `League is not set. Run 'athc config set league NAME' or pass --league.` does: `League files folder is not set. Run 'athc config set path FOLDER' ...`, `Team is not set. Run 'athc config set team NAME' ...`, `Plays folder is not set. Run 'athc config set play_path FOLDER' ...`; a missing file or folder that a setting names ends `Run 'athc config set <key> FOLDER'.` (cli-help.md rule 21).
18. **check-ppp-cli.md's path sources (decision 3), default team (decisions 4 and 5), `-r` (decision 9) and the four-file rule do not apply:** `config` has no PATH, no team, no tree and no game files; its files are fixed by the settings folder and the league name. `--league NAME` follows cli-help.md rule 10 as written.
19. **Everything below is the cli-help.md form.** cli-help.md lands first (Status), so the usage lines, placeholders, hints, help blocks and tests here are written in its style and in no other; its general fixes (uppercase placeholders, `[OPTIONS]`, the Positional arguments section) are not repeated here.

## 5. The command

Help in cli-help.md's style (Click 8.5: `[OPTIONS]`, uppercase placeholders, a Positional arguments section, an Examples epilog), as it will render.

### config

```
Usage: athc config [OPTIONS] COMMAND [ARGS]...

  Show or change athc settings (athc.ini, league.toml).

  athc.ini holds the league in use and each tool's app-wide settings. A
  league's league.toml holds its path, play_path, team and ppp_path. Both
  live in your settings folder, %LOCALAPPDATA%\athc.

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

  league.toml holds the league's path, play_path, team and ppp_path. A
  missing file is created empty first. Windows picks the app: Notepad,
  unless you changed it.

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

  league, kept in athc.ini, is the league used when a command is not given
  --league; VALUE is the name of a folder under leagues\ in your settings
  folder. path, play_path, team and ppp_path go in the league's league.toml;
  VALUE is a folder, or your team's name for team. Comments and other lines in
  both files are kept.

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

### Which file

For `path`, `edit` and `reveal`:

| FILE | `--league` | File | League read from |
|---|---|---|---|
| omitted | omitted | `athc.ini` in the settings folder | nothing |
| omitted | NAME | `leagues\NAME\league.toml` | the name |
| `athc.ini` | omitted | `athc.ini` | nothing |
| `athc.ini` | NAME | `athc.ini`; the named league must exist, as on every command | the name, checked only |
| `league.toml` | omitted | `leagues\<league>\league.toml`, the league in use | `[athc] league` in `athc.ini` |
| `league.toml` | NAME | `leagues\NAME\league.toml` | the name |

For `get`: `league` reads `athc.ini` (or prints the `--league` name after its folder check); the other keys read the `league.toml` of the league in use, or of `--league NAME`. For `set`: `league` writes `athc.ini`; the other keys write the `league.toml` of the league in use, or of `--league NAME`.

- The settings folder is `config_dir()`: `%LOCALAPPDATA%\athc`, or `ATHC_CONFIG_DIR` (dev and tests).
- The league folder must exist (decision 10); `league.toml` is created by `edit`, printed by `path` and stood in for by its folder in `reveal` when missing.

### Argument errors

Click's usage errors, as Click prints them: the `Usage:` line, `Try 'athc config <verb> --help' for help.`, then the `Error:` line, exit 2.

- `config set league` without a value: `Error: Missing argument 'VALUE'.`
- `config set` or `config get` with nothing: `Error: Missing argument 'KEY'.`
- A third word to `set`, a second to `get`, `path`, `edit` or `reveal`: `Error: Got unexpected extra argument (x).` The period is added once, where `src/athc/cli/__init__.py` renders usage errors, so every command prints it (convert-pdb-cli.md names the mechanism); this plan raises no copy of its own.
- A FILE that is neither name, a league name typed there included: `Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.`
- `--league` with no name, on any verb that has it: `Error: Option '--league' requires an argument.`

### cli-help.md changes

- Group summary: "Show or change athc settings (athc.ini, league.toml)." instead of "(athc.ini)".
- `config get` is new; its block above.
- `config path`, `edit`, `reveal`: the FILE argument, the shared `--league NAME` option, and the summaries above; cli-help.md's `reveal` summary "Show athc.ini in File Explorer." widens by the league file.
- `config set`: the summary "Set a value in athc.ini or league.toml.", the description above, KEY's help listing the five keys, and the shared `--league NAME` option; VALUE as cli-help.md has it.
- Rule 10's `--league NAME` text is used as written on `path`, `edit`, `reveal`, `get` and `set`.

## 6. Settings

In `athc.ini`, under `[athc]`:

```ini
[athc]
; league used when --league is not given; change it with
;   athc config set league NAME
league = PNFL
```

In `league.toml`, under `[league]`, the keys `get` reads and `set` writes (set with `athc config set KEY VALUE`, or by hand with `athc config edit league.toml`), as the shipped file will read with check-ppp-cli.md's section 6 comments for `path`, `team` and `ppp_path` (that plan owns those three) and this plan's `play_path` comment:

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
- `get path | play_path | team | ppp_path` read the league file; `set` of the same keys writes it (decision 3).
- The shipped headers point the coach at the commands: `athc.ini`'s header names `athc config edit league.toml` beside `play_path`, and each `league.toml` gains the first line above (`config/release/leagues/*/league.toml`; `config/dev/` mirrors). Each comment says what the value is, never which commands read it.

## 7. Lines and exit codes

New or changed lines, in the project's wording; everything else prints as today.

| When | Line | Code |
|---|---|---|
| `set league PCFL` written | `OK   <athc.ini>: league = PCFL` (stdout, logged) | 0 |
| `set play_path C:\SIERRA\FBPRO98\PNFL` written | `OK   <league.toml>: play_path = C:\SIERRA\FBPRO98\PNFL` (stdout, logged); `path`, `team` and `ppp_path` the same way | 0 |
| `set` of a `league.toml` key, the file missing or with no `[league]` | `FAIL <league.toml>: The system cannot find the file specified.`, nothing written | 2 |
| `set` of a `league.toml` key, the file malformed | its parse error line, as every reader prints it; nothing written | 2 |
| `set league X --league Y` | `Error: --league cannot be used with set league.` | 2 |
| `set league` with no folder of that name | `Error: Invalid value for 'VALUE': league 'PCLF' not found. No folder <leagues>\PCLF. Available: PCFL, PNFL.` | 2 |
| `set league ""` | the same line with the blank name | 2 |
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
| `get <key>` written as an array | `FAIL <league.toml>: [league] play_path: Expected a string, got an array.` (as today) | 2 |
| `get` or `set` with an unknown key | `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` | 2 |
| `path`, `edit`, `reveal`, `get` or `set --league NOPE` | `FAIL League 'NOPE' not found. No folder <leagues>\NOPE. Available: PCFL, PNFL.` | 2 |
| `path`, `edit` or `reveal league.toml`, or `get` or `set` of a league key, with no league set | `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.` | 2 |
| FILE neither name | `Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.` | 2 |
| a word too many | `Error: Got unexpected extra argument (x).` (the period from the shared change in `src/athc/cli/__init__.py`) | 2 |
| `--league` without a name | `Error: Option '--league' requires an argument.` | 2 |
| `edit`, no app for the file | `FAIL <athc.ini>: No application is associated with the specified file for this operation.` (any other Windows text the same way) | 2 |
| any verb reading a malformed `athc.ini` | `FAIL <athc.ini>: Not valid INI: No [section] header above it (at line 1).` (as `set` today) | 2 |
| `path` | the path (stdout, not logged), as today | 0 |
| `edit`, `reveal` done | nothing, as today | 0 |
| bare `athc config` | the group's help on stderr, as today | 2 |

The `Error:` lines are Click's usage errors and keep Click's frame (architecture.md, Wording); athc's part after `Invalid value for 'VALUE':` continues Click's sentence, so it starts lowercase, as today. Codes stay 0 done, 2 error; no config verb uses 1.

## 8. Related commands

- Every league-aware command's `League is not set` error names `athc config set league NAME` (`resolve_league` in `src/athc/config.py`); `get league` is its counterpart and prints the same `FAIL` line when nothing is set.
- The tools' not-set lines and their fix sentences name `athc config set` (decision 17; cli-help.md rule 21), with each command's own alternative (`or pass the folder`, `--path`, `a .pln file`) through the gameplan, profile, convert-pdb, check-ppp, playpool and generate-schedule plans; `athc config get <key>` shows what they read.
- `check-ppp`, `playpool check` and the other league-aware commands take `--league NAME` to run against a league; `config`'s verbs take the same option, with the same text, resolution and errors, to pick a league's file or setting.

## 9. Code

- `src/athc/cli/config/__init__.py`: register `get`; `KEYS = ("league", "path", "play_path", "team", "ppp_path")`, shared by `get` and `set`; `key_callback`, the Click callback for the `key` argument (casefold match, returns the canonical spelling, else `click.BadParameter` with Click's `Choice` wording; Click attaches the required argument's own hint, `'KEY'`); `FILE_NAMES = ("athc.ini", "league.toml")` and `file_callback` for the optional `file` argument (`None` passes through; a casefold match returns the canonical name; else `click.BadParameter("'<word>' is not one of 'athc.ini', 'league.toml'.", param_hint="'FILE'")`); neither argument carries a metavar, so Click renders `KEY` and `[FILE]`; a `settings_file(file: str | None, league: str | None) -> Path` helper for `path`, `edit` and `reveal`: `config_file()` for `athc.ini`, `league_file(league)` for `league.toml`, the default by decision 9, and `resolve_league(league)` for a named league with `athc.ini`.
- `src/athc/config.py`: `league_file(league: str | None) -> Path`: `league_dir(resolve_league(league)) / LEAGUE_FILE`, raising `LeagueError` as those two do; `LeagueConfig.string(key)` as check-ppp-cli.md section 9 describes it (whichever plan lands first adds it); `set_league_value(league: str | None, key: str, value: str) -> Path`: writes `key = value` under `[league]` in `league_file(league)` through a TOML library that keeps comments, so its comments and other lines stay, and returns the path written (the library is not picked yet; it is added with `uv add`). `check_ppp.py` and `play_dir` keep building the path from `LeagueConfig.dir`, unchanged.
- `src/athc/cli/config/path.py`, `edit.py`, `reveal.py`: the optional `file` argument with `file_callback` and the shared `league_option` from `athc.cli`; `path` prints `settings_file(...)`; `edit` creates the parent folder and the empty file when missing, then `os.startfile(path)`, its `OSError` left to `main`; `reveal` creates the parent folder when missing (today's `config_dir()`; a league folder already exists), then `click.launch(locate=True)` on the file or `click.launch` on the folder, as today.
- `src/athc/cli/config/get.py` (new): the `key` argument with `key_callback` and `league_option`; `league` prints `resolve_league(league)`; the other keys load `load_league_config(league)` and print `path(key)` or `string(key)`; a `None` value raises a `ConfigFileError` with `cfg.dir / LEAGUE_FILE` and the key's not-set line (section 7) for `path`, `play_path` and `team`, and for `ppp_path` goes through `console.warn` with the `Game plan and profile folder is not set` line and returns normally.
- `src/athc/cli/config/set.py`: the `key` argument with `key_callback` and `league_option`; for `league`, the folder check with `param_hint="'VALUE'"`, then `set_config_value`; for a league key, `set_league_value(league, key, value)`; `console.ok(f"{written}: {key} = {value}")` with the path either returns. The help texts of section 5 everywhere.
- Tests need no new fixtures: `config_dir`, `write_config` and `make_league` in `tests/conftest.py` cover it.

## 10. Tests

`tests/integration/test_config.py` (`path`, `edit`, `reveal`, `get`) and `tests/integration/test_config_set.py` (`set`):

- `get league`: set with its folder present (the name on stdout, stderr empty, 0); `--league PCFL` (that name, 0); unset (`League is not set`, the folders listed, 2); blank value (the same); folder gone (`not found`, 2); `get League` and `get LEAGUE` accepted; `get colour` rejected with the exact line `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` (the known keys accepted, one past them rejected); no KEY (`Error: Missing argument 'KEY'.`); malformed `athc.ini` (the INI line, 2); `--league NOPE` (`not found`, 2).
- `get` of a league key: `path` and `play_path` absolute, printed as written; a relative `ppp_path` printed resolved against the league folder; `team` as written; `path`, `play_path` and `team` unset (each key's `... is not set. Run 'athc config set <key> ...'.` line naming `league.toml`, stdout empty, 2); `ppp_path` unset (stdout empty, the `WARN ... Game plan and profile folder is not set; using the folders the league file names.` line, 0); a key written as an array (the `Expected a string` line, 2); `--league NAME` reads that league's file; no league set and no `--league` (`League is not set`, 2); a league folder without `league.toml` (the unset lines).
- `set`: `set League PCFL` writes `league = PCFL` once, in the canonical spelling; the `OK` line names `athc.ini` and the pair; `set path`, `set play_path` and `set ppp_path` with a folder and `set team Denver` write the key under `[league]` in the `league.toml` of the league in use, the `OK` line names `league.toml` and the pair, and every comment and other line of the file is kept; `set Play_Path` writes `play_path`; `--league PCFL` writes PCFL's `league.toml`; a league key with no league set and no `--league` (`League is not set`, 2); `--league NOPE` (`not found`, 2); KEY: the five keys accepted (the writes above), `set colour x` rejected with the exact line `Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.`; the `'VALUE'` hint on a missing folder; `set league` without VALUE (`Error: Missing argument 'VALUE'.`).
- FILE and `--league` on `path`, `edit` and `reveal`: nothing (`athc.ini`); `league.toml` with `[athc] league` set (that league's file); `League.TOML` accepted; `PCFL` rejected with the exact line `Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.ini', 'league.toml'.` (the hint reads `'FILE'`, not `'[FILE]'`); a word too many (`Got unexpected extra argument (x).`); `--league PCFL` alone (PCFL's `league.toml`); `league.toml --league PCFL` (the same); `athc.ini --league PCFL` (`athc.ini`, and `--league NOPE` still fails); `league.toml` with nothing set (`League is not set`, 2); `--league NOPE` (`not found`, 2); `--league` with no name (`requires an argument`, 2); `league.toml` with a malformed `athc.ini`; `path league.toml` with the file missing (the path, 0); `edit league.toml` with the file missing (created empty, opened) and present (opened, content kept); `reveal league.toml` with the file present (`locate=True` on it) and missing (the league folder).
- `edit`: `os.startfile` monkeypatched; a stub raising `OSError` with `winerror=1155`, Windows' text and the file name gives `FAIL <athc.ini>: No application is associated with the specified file for this operation.` and exit 2.
- Help: `config --help` lists `get`; `--league NAME` shows on `path`, `edit`, `reveal`, `get` and `set`; FILE shows on the three.
- Limits: `config` has no numeric limits or ranges; the key list's (one for `get` and `set`) and FILE's accepted values and one past them are the tests above.
- Existing tests that change: `tests/integration/test_config_set.py`: `test_cli_sets_league` (stdout is the `OK` line naming `athc.ini`), `test_cli_rejects_unknown_league` (`Invalid value for 'VALUE':`), `test_cli_rejects_unknown_key` (Click's `'colour' is not one of 'league', 'path', 'play_path', 'team', 'ppp_path'.` after `Invalid value for 'KEY':`); `test_cli_rejects_blank_league`, `test_cli_malformed_ini_is_clean_error`, `test_cli_help_lists_known_keys` and `test_group_lists_set` keep passing by design. `tests/integration/test_config.py`: `test_edit_opens_associated_app`, `test_edit_ignores_editor_env` and `test_edit_preserves_existing_file` monkeypatch `os.startfile` instead of `click.launch`; `test_group_lists_subcommands` also asserts `get`; `test_path_prints_config_file`, `test_reveal_selects_existing_file` and `test_reveal_opens_folder_when_absent` keep passing by design. `tests/integration/test_cli_root.py`: the `config set` row of `test_help_uses_lowercase_names` (`["key value"]` shown, `["KEY", "VALUE"]` hidden) fails as soon as `set`'s placeholders read `KEY VALUE` (Click's own, once the lowercase `metavar="key"` / `"value"` go), so this plan owns it: the row goes with them (cli-help.md rule 2 inverts the whole test's premise for every command, which cli-help.md does not yet list); the config verbs are not added to `LEAGUE_COMMANDS` (their `--league` tests live in `test_config.py`, and `_unknown_league_args` would need entries for them), `test_short_help_option_on_every_command` picks up `get` by itself. `packaging/sandbox-steps.ps1` (the installer's release gate, `docs/design/installer.md`): the `config set league TEST` check asserts `OK` and `league = TEST` instead of `Set league = TEST`; `$commands` gains `config get`; a `config get league` check expects `TEST` on stdout, exit 0. `tests/integration/README.md`: the `athc config set` table's `CLI sets league` row (`stdout: Set league = <NAME>`) and `CLI unknown key` row ("names known keys") change; the `athc config` table's `Group lists subcommands` row (path / edit / reveal) and the `edit` rows (`launch(<athc.ini>)`) change; the root table's `Help uses lowercase names` row drops `config set`; both tables gain the rows above.

## 11. Docs and meta

- `docs/config/README.md`: rewritten around the five verbs, FILE, `--league NAME`, the lines and codes above; it names `set` (or `edit league.toml`) as the way to set `path`, `play_path`, `team` and `ppp_path`, and `get` as the way to read them. `docs/config/ARCHITECTURE.md`: "four thin commands" becomes five, the layout gains `get.py`, `edit` is `os.startfile`, the exit table gains the `FAIL` cases (league errors, an unassociated file, a malformed `athc.ini`, an unset key), Boundaries says `get` reads and `set` writes `league.toml`. (docs-layout.md folds the pair into one `config.md`; whichever lands first carries these changes.)
- `config/release/docs/COMMANDS.txt` section 15: `get`, `set`'s `league.toml` keys, FILE, `--league`, the `OK` line, the examples. `config/release/docs/README.txt`: "open leagues\PNFL\league.toml in your settings folder" becomes `athc config edit league.toml`; the "To open this folder" line keeps `athc config reveal`; the troubleshooting entries on `play_path` add `athc config get play_path` and `athc config edit league.toml`.
- `config/release/athc.ini` and `config/dev/athc.ini`: the header's `play_path` sentence names `athc config edit league.toml`. `config/release/leagues/*/league.toml` and the dev twins: the header line "Open this file with: athc config edit league.toml".
- `docs/design/architecture.md`, Config: the bullet becomes "`athc config path | edit | reveal | get | set` locate, open, reveal, read and write the settings files: `path`, `edit` and `reveal` take FILE (`athc.ini`, the default, or `league.toml`) and `--league NAME`; `get` reads `league` from `athc.ini` and `path`, `play_path`, `team`, `ppp_path` from the league's `league.toml`; `set` writes `league` to `athc.ini` through ConfigUpdater, validating the league folder first, and `path`, `play_path`, `team`, `ppp_path` to the league's `league.toml` through a TOML library that keeps comments (so comments survive in both); `edit` opens through `os.startfile`, `reveal` through `click.launch`". The CLI section's `--league` list gains `config path | edit | reveal | get | set`; its lowercase-placeholder rule (`metavar="pdb_file"`, never Click's capitals) changes with cli-help.md, not with this plan. `docs/design/installer.md`: "the only value a user must edit is `play_path` in `leagues\PNFL\league.toml`" gains "(`athc config edit league.toml` opens it)"; the sandbox test description covers `config get`.
- `docs/design/TODO/cli-help.md`, config: the changes in section 5.
- `CHANGELOG.md`: `config: get prints the league in use and a league's path, play_path, team and ppp_path; path, edit and reveal take league.toml as well as athc.ini; set writes path, play_path, team and ppp_path to the league's league.toml and says which file it wrote` and `config: edit reports a file Windows cannot open instead of doing nothing`. `STATUS.md`: an `athc config get` row; the "league in use" bullet gains `get` and the league file. `TODO.md`: this plan's entry, ticked when done.

## Shared vocabulary

- `KEY`, `VALUE`: a setting's name and its new value (cli-help.md's placeholders); KEY is a case-insensitive choice of the known keys, `league`, `path`, `play_path`, `team`, `ppp_path`, for `get` and `set`.
- `get KEY` and `set KEY VALUE`: the read and write verbs, as git, gh, npm and pip name them.
- `FILE` on `config path`, `edit` and `reveal`: one of the two settings file names, `athc.ini` or `league.toml`, lowercase literals matched without case; default `athc.ini`, or `league.toml` when `--league NAME` is given. `FILE` is cli-help.md rule 26's name for it.
- `--league NAME`: cli-help.md rule 10's option, required value, same text; on `config` it picks the league whose file or setting the verb reads or writes.

## Sources

- git config (subcommands, scope options for reading and writing, `edit`, `--show-origin`, exit codes): <https://git-scm.com/docs/git-config>; `-C <path>`: <https://git-scm.com/docs/git>
- gh config: <https://cli.github.com/manual/gh_config>, <https://cli.github.com/manual/gh_config_get>
- npm config (`get` with no key, `edit` and the Windows editor default, `--location`, `set` with no value): <https://docs.npmjs.com/cli/v10/commands/npm-config>
- pip config (scope options and the user-file default, `--editor`, `debug`): <https://pip.pypa.io/en/stable/cli/pip_config/>
- kubectl config (subcommands, `current-context`, `--kubeconfig`, the default path): <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_config/>
- winget settings (opens the default editor, Notepad by default): <https://learn.microsoft.com/en-us/windows/package-manager/winget/settings>
- Windows `type` (the file as the argument): <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/type>
- clig.dev (optional flag values and blank values, tell the user, suggest commands, defaults, same flag names, unambiguous names): <https://clig.dev/>
- Click: `click/parser.py` (`_get_value_from_state`: the next word is a flag's value; `requires an argument`), `click/core.py` (`Group` `no_args_is_help` default, `Parameter.make_metavar`, `Argument.get_error_hint`), `click/types.py` (`Choice`: `case_sensitive`, `convert`, `get_metavar`, `get_invalid_choice_message`), `click/exceptions.py` (`BadParameter`, `MissingParameter`, `NoSuchOption`, `NoArgsIsHelpError`), `click/termui.py` and `click/_termui_impl.py` (`launch`, `open_url`: `os.startfile`, 127 on `OSError`), all in the venv
- configparser key case and `optionxform`: <https://docs.python.org/3/library/configparser.html>; ConfigUpdater's `optionxform` in the venv, `configupdater/document.py`
- tomllib does not write TOML: <https://docs.python.org/3/library/tomllib.html>
- `os.startfile` (associated application, `ShellExecute`): <https://docs.python.org/3/library/os.html>; its `OSError` fields checked on 2026-10-13 with a missing file (`FileNotFoundError`, `winerror`, `strerror`, `filename`); the no-association case was not run
- ShellExecuteW return codes (`SE_ERR_NOASSOC`, `GetLastError`): <https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutew>; Windows error 1155, `ERROR_NO_ASSOCIATION`: <https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299->
- VS Code, "Reveal in File Explorer": <https://code.visualstudio.com/docs/getstarted/userinterface>
- athc: `src/athc/cli/config/__init__.py`, `path.py`, `edit.py`, `reveal.py`, `set.py`; `src/athc/config.py`; `src/athc/errors.py`; `src/athc/console.py`; `src/athc/cli/__init__.py`; `src/athc/cli/check_ppp.py`; `src/athc/cli/playpool/check.py`; `src/athc/gameplan/config.py`; `src/athc/pdbtoexcel/config.py`; `src/athc/profile/config.py`; `docs/config/README.md`, `ARCHITECTURE.md`; `docs/design/architecture.md`; `docs/design/installer.md`; `docs/design/TODO/check-ppp-cli.md` (decisions 3, 4, 5, 9, 14, section 9); `docs/design/TODO/cli-help.md`; `docs/design/TODO/docs-layout.md`; `config/release/athc.ini`; `config/release/leagues/PNFL/league.toml`, `PCFL/league.toml`; `config/release/docs/COMMANDS.txt`, `README.txt`; `packaging/sandbox-steps.ps1`; `STATUS.md`; `tests/conftest.py`; `tests/integration/test_config.py`, `test_config_set.py`, `test_cli_root.py`, `README.md`; `athc config` and each verb's `--help` run on 2026-10-13
