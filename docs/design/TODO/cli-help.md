# athc CLI Help and Naming Plan

**Goal:** every athc command's usage and help text follow one mainstream, modern style.

**Status:** proposal, 2026-10-11, rules 16 to 28 added 2026-10-13; nothing changed yet.

## 1. CLI libraries

| Library | What it is | PyPI downloads, last month |
|---|---|---|
| Click 8.5 | Decorator-based | about 817 million |
| Typer 0.27 | Type-hint based; carries its own copy of Click since 0.26 | about 244 million |
| argparse | Standard library, nothing to install | not counted (ships with Python) |

- Typer is still pre-1.0 and made breaking changes in 0.26 (copied Click in) and 0.27 (help placeholders).
- Click 8.5 (August 2026) added help for arguments, shown in a "Positional arguments" section.

## 2. Recommended library

Stay on Click, and upgrade from 8.4.1 to 8.5 or later.

- It has over three times Typer's downloads, is stable at 8.x, and athc's plug-in command groups are plain Click.
- 8.5 adds the one thing athc's help lacks (argument help) with no custom code.
- Typer would mean rewriting every command in a different declaration style, while its help engine is still Click's.
- Turn off Click's Windows wildcard expansion; athc expands wildcards itself (rule 15). Click's expands every word before the command sees it, can't be limited to one argument and can't be escaped with quotes. Windows programs expand their own wildcards, per argument (`ren *.txt *.doc`; PowerShell's `-Path` vs `-LiteralPath`).

## 3. Mainstream help styles

| | Style A: Click / GNU | Style B: git / clap |
|---|---|---|
| Example | `cp [OPTION]... SOURCE DEST` | `git mv [-v] [-f] <source> <destination>` |
| Placeholders | UPPERCASE, with underscores | `<angle brackets>` |
| Options in usage | one `[OPTIONS]` | each option (git) or `[OPTIONS]` (uv) |
| Used by | Click, GNU coreutils | git, uv |

Both styles agree on:

- Long options in lowercase with hyphens (`--dry-run`); one-letter short options only for common flags.
- Standard flag meanings: `-h/--help`, `-o/--output`, `-q/--quiet`, `-f/--force`, `-n/--dry-run`, `--version`.
- Help content: a one-line summary, the usage line, arguments, options and a few examples.
- Command names: lowercase; groups are nouns, subcommands are verbs (`docker container create`).
- Joined words (`git worktree`, `git mergetool`) and hyphenated words (`git cherry-pick`) are both normal command names.

athc today writes placeholders in plain lowercase (`play replacement path`) and lists every option in the usage line. Plain lowercase reads like literal words; even argparse, which athc's usage line copies, capitalizes option values (`--league LEAGUE`).

## 4. Recommended athc style

Style A, which is Click's default:

```
Usage: athc gameplan replace-play [OPTIONS] PLAY REPLACEMENT...

  Replace one play with another in game plans.

  Each game plan gets the first REPLACEMENT not already in it with which it
  still passes athc gameplan check; the others are backups, tried in order.

Positional arguments:
  PLAY         Play to replace (any case).
  REPLACEMENT  Plays to put in its place, in order; each must be in the play
               pool.

Options:
  --path PATH      Game plans to edit: a .pln file, a folder, a wildcard, or
                   off1, def1, off2 or def2 (default: your team's game
                   plans).
  -r, --recursive  Include subfolders.
  --team NAME      Team whose game plans off1, def1, off2 and def2 name
                   (default: team in league.toml).
  --league NAME    League to use (default: the one set with athc config
                   set league).
  -h, --help       Show this message and exit.

  Examples:

    athc gameplan replace-play OLDRUN NEWRUN
    athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r
```

(The block is [gameplan-cli.md](gameplan-cli.md)'s replace-play; the command plans decide each command's arguments and options.)

Rules for every command and group:

1. **Usage line:** Click's own, `[OPTIONS]` then the arguments; groups end in `COMMAND [ARGS]...`.
2. **Placeholders:** UPPERCASE with underscores, for arguments and option values (`GAME_PLAN`, `--league NAME`).
3. **One name per kind of value:**
   - `PATH`: a file or a folder (or a wildcard, where rule 15 allows one)
   - `GAME_PLAN`: one .pln file
   - `PROFILE`: one .prf file
   - `FOLDER`: a folder only
   - `INPUT_FILE` / `OUTPUT_FILE`: play lists and reports (`-` means the console)
4. **Argument help:** every argument gets its own help line; the description stops explaining arguments.
5. **Placeholders in text:** the description names them in caps, like cp's "Copy SOURCE to DEST".
6. **One-line summary:** starts with a verb, fits the command list (55 characters or fewer), no game title (the root help names the game once).
7. **Verbs match commands:** `check` commands say "Check", not "Validate".
8. **Plain-English terms:** "game plan" and "play pool" in text; command names stay `gameplan` and `playpool`.
9. **Windows words for end users:** folder, subfolder, console, wildcard, File Explorer, Ctrl+C; never directory, stdout, glob, config dir.
10. **Shared options read the same everywhere:**
    - `-r, --recursive  Include subfolders.`
    - `--league NAME  League to use (default: the one set with athc config set league).`
11. **Short options:** one letter, standard meanings only (`-o` output, `-r` recursive); convert-pdb keeps its `-o`, `-o2`, `-d` and `-d2`.
12. **Long options:** spelled out (`--substitutions`, not `--sub-percent`).
13. **Description:** two to four lines; rule details belong in the tool's docs.
14. **Examples:** one or two real examples per command, in an "Examples" epilog.
15. **Wildcards:** athc expands them itself, only in these arguments, and their help says so: PATH in `gameplan check` and `profile check`; `--path PATH` in `gameplan find-play`, `gameplan replace-play` and `gameplan set-specials`; TARGET in `profile copy`. A name that exists is a name, never a wildcard, so a folder like `Season [2029]` works. Each of the six gets one CLI test with a wildcard.

Rules shared by the command plans ([autocontinue](autocontinue-cli.md), [check-ppp](check-ppp-cli.md), [config](config-cli.md), [convert-pdb](convert-pdb-cli.md), [gameplan](gameplan-cli.md), [generate-schedule](generate-schedule-cli.md), [playpool](playpool-cli.md), [profile](profile-cli.md)); each plan states them in its own words with its reasons:

16. **Path rule:** no path means the configured default (your team's files; the league's play pool), `.` the current folder, an explicit path overrides both. `gameplan check` and `profile check` default to the current folder, and a plan that prefers the current folder says why.
17. **The four names:** `off1`, `def1`, `off2`, `def2`, lowercase in help and docs (rule 2 reserves capitals for placeholders), matched without case, accepted wherever a game plan or profile file operand is (`check` PATH included): your team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense file of the command's kind, found in `ppp_path` by its `.lg2` name, else at the league location (`path` joined with the `.lg2` folder). An existing path wins over a name (rule 15). In text, "the four names". Every command that takes them lists them once: in the operand's help line, or in the description for option values.
18. **`--team NAME`:** on every command that accepts the four names, declared once as `team_option(head)` in `src/athc/cli/__init__.py` beside `league_option`; the help is a per-command head plus the shared tail `(default: team in league.toml).`. `--team` with no name among the operands is `Error: Cannot use --team with a path.`, exit 2. `ppp_path` applies only to the team `team` in `league.toml` resolves to; another team uses the league locations. The team resolver, the league-file loader and the file locator live in `src/athc/cli/_team.py`.
19. **`--league NAME`:** always a required value with rule 10's text; never a contradiction; a named league must exist (the existing not-found line, exit 2), and its files are read only when the run needs them.
20. **`--path`:** "where the game plans are" on every command that has it: `--path PATH` on `find-play`, `replace-play` and `set-specials` (a `.pln` file, a folder, a wildcard or one of the four names; default: your team's game plans), `--path FOLDER` on `convert-pdb` (a folder only; the team's four plans by their `.lg2` names, because the workbook has four slots).
21. **Hints:** `FAIL <league.toml>: No team for the league. Set team in this file, or pass --team or <alternative>.` and `FAIL <league.toml>: No path for the league. Set path in this file, or pass <alternative>.`, the alternative being the command's own path form (`--path`, `a .pln file`, `a .prf file`, `the folder`, `-o, -o2, -d and -d2 as .pln files`, check-ppp's `--all-teams`), or `--team` alone when the command's path form is already on the line (convert-pdb with `--path`). A team file missing at its league location, when the team is yours, adds `Set ppp_path in <league.toml>, or pass <the file|--path|the folder>.`. A folder named like one of the four names where one file is needed is `FAIL off1: Access is denied. Run from another folder to use your team's <game plan|profile>.`; on an operand that takes folders that folder is the folder, and a file named `off1` is `Not a .pln file.` / `Not a .prf file.`.
22. **No argument metavars:** Click derives the placeholder from the parameter name (`game_plan` gives `GAME_PLAN`, `output_file` gives `[OUTPUT_FILE]`, `play` with `nargs=-1, required=True` gives `PLAY...`), because an explicit metavar prints verbatim in the usage line and in Click's error hint. An argument's own validation is an athc callback raising `click.BadParameter(..., param_hint="'FILE'")`, so the hint reads `'FILE'`, never `'[FILE]'`.
23. **Usage-error period:** every command prints `Got unexpected extra argument (x).`; the period is added once in `src/athc/cli/__init__.py` where usage errors are rendered, and no command raises its own copy.
24. **No quiet flag:** no athc command has `-q/--quiet`; scripts use `> nul`, which hides the OK lines and keeps every FAIL on standard error.
25. **One form:** every command plan describes this plan's form only (`[OPTIONS]`, uppercase placeholders, a Positional arguments section, an Examples epilog) and says "Depends on cli-help.md landing first."; this plan lands before any of them.
26. **`FILE`** joins rule 3: a file named outright where none of the other names fits (`profile diff --output FILE`; `config path | edit | reveal FILE`, a choice of `athc.ini` or `league.toml`, lowercase literals matched without case).
27. **On/off pairs over an `athc.ini` boolean:** `--x/--no-x` with `default=None`, help `Overrides <key> in athc.ini (on by default).` (`autocontinue --hot-corner`, `convert-pdb --percentages`).
28. **Derived output:** an optional `OUTPUT_FILE` defaults to the input's name with the product's extension, beside the input; its help says `(default: <INPUT> with .<ext>, beside it)`; a binary product refuses `-` (rule 3's exception).

## 5. Issues and fixes

The command plans named above decide each command's arguments, options and lines; where a plan's "cli-help.md changes" subsection amends a line below, the plan wins.

### General (every command)

| # | Issue | Fix |
|---|---|---|
| G1 | Lowercase placeholders look like literal words (`play replacement path`, `--league name`) | Rule 2 |
| G2 | The usage line lists every option, using custom code | Rule 1; delete athc's custom usage code |
| G3 | No arguments section; arguments are explained only inside the description | Click 8.5 and rule 4 |
| G4 | Descriptions use placeholders as plain words ("from gameplan", "Set key to value") | Rule 5 |
| G5 | Summaries are cut off with "..." in command lists | Rule 6 |
| G6 | One thing, many names (`path`, `gameplan`, `pln_file`, `target`; `output_file`, `file`) | Rule 3 |
| G7 | Mixed terms: gameplan / game plan, stdout / console, glob / wildcard, directory / folder, config dir | Rules 8 and 9 |
| G8 | `-r` help is worded three ways; `--league` help names a path instead of saying what it does | Rule 10 |
| G9 | `check` commands say "Validate" | Rule 7 |
| G10 | No examples anywhere | Rule 14 |
| G11 | `--sort` shows `slot\|name\|category` in usage but `[slot\|name\|category]` under Options | Gone with G2 (choices show only under Options) |
| G12 | On Windows, Click expands wildcards in every word before athc sees it: `find-play`'s refusal never fires when files match, and `list-normals GP*.pln` with two matches writes the play list over the second game plan | Turn Click's expansion off; rule 15 |
| G13 | `set-specials` PATH, `replace-play` PATH and `profile copy` TARGET take wildcards, but their help never says so | Rule 15 |
| G14 | A real name containing `[` is taken as a wildcard: `find-play` refuses it, the others report no match | Rule 15 |
| G15 | No CLI test runs a wildcard through a command; the wildcard tests call the file helper directly | Rule 15 |

Project changes that come with the general fixes:

- `pyproject.toml` / `uv.lock`: Click 8.5 or later.
- `src/athc/cli/__init__.py`: Click's wildcard expansion off.
- `src/athc/cli/_files.py`: a path that exists is used as is, before any wildcard check.
- `docs/design/architecture.md`, CLI section: the usage-line and lowercase-placeholder rules are replaced by this style.
- `tests/integration/test_cli_root.py` (`test_usage_lists_each_option`) and its row in `tests/integration/README.md` pin the old usage line; they change with the approved style.

### athc (root)

- Usage becomes `athc [OPTIONS] COMMAND [ARGS]...`.
- Summaries of check-ppp, config, convert-pdb, gameplan and profile are cut off; each gets a new summary below.

### autocontinue

- Usage becomes `athc autocontinue [OPTIONS]`.
- "CTRL-C" becomes "Ctrl+C".
- `--hot-corner` help "(overrides config; default on)" becomes "Overrides hot_corner in athc.ini (on by default)."

### check-ppp

- Usage becomes `[OPTIONS] PATH [PATH]`; PATH help: "A .prf, a .pln, or a folder."
- Summary becomes "Check profiles against their game plans."
- The description is two dense paragraphs of rule logic; cut it to a few lines and move the rules to the tool's docs.
- "gameplan" and "directory" in text become "game plan" and "folder".

### config

- Summary becomes "Show or change athc settings (athc.ini)."
- `config reveal`: "file manager" becomes "File Explorer"; summary becomes "Show athc.ini in File Explorer."
- `config set`: usage becomes `[OPTIONS] KEY VALUE`; KEY help: "Setting to change: league."; VALUE help: "New value."
- `config set`: "Set key to value" becomes "Set a value in athc.ini."; "a folder under leagues\ in the config dir" becomes plain words.

### convert-pdb

- `-o`, `-o2`, `-d` and `-d2` (`--pln-off`, `--pln-off-2`, `--pln-def`, `--pln-def-2`) stay as they are.
- `--skip-calcs` becomes `--percentages/--no-percentages` (rule 27; [convert-pdb-cli.md](convert-pdb-cli.md)).
- Usage becomes `[OPTIONS] PDB_FILE OUTPUT_FILE`; PDB_FILE help: "WinLogStats .pdb file."; OUTPUT_FILE help: ".xlsx, or .xlsm to include sorting macros."
- Summary becomes "Convert a WinLogStats PDB to an Excel workbook."
- The description drops the game title.

### gameplan (group)

- Summary becomes "Check and edit game plans (.pln)."
- The summaries of check, find-play, list-specials, replace-play, set-normals and set-specials are cut off; each gets a new summary below.

### gameplan check

- Usage becomes `[OPTIONS] [PATH]...`; PATH help: ".pln files, folders or wildcards (default: current folder)."
- Summary becomes "Check game plans against the league's rules."
- "glob" and "directory" become "wildcard" and "folder".

### gameplan find-play

- What the last argument means depends on how many arguments there are (one is a play, two or more makes the last a path). Fix: make the location an option, `--path PATH` (default: current folder), so every argument is a play.
- `--path` refuses wildcards, as PATH does today; with Click's expansion off (G12), the refusal works.
- Summary becomes "Find plays by name in game plans."
- "(normal + custom-special slots)" becomes "Searches normal and special-teams slots."

### gameplan list-normals

- Usage becomes `[OPTIONS] GAME_PLAN [OUTPUT_FILE]`; both get help lines.
- The description explains each `--sort` value; move that into the `--sort` help.
- "gameplan" in text becomes "game plan".

### gameplan list-specials

- Usage becomes `[OPTIONS] GAME_PLAN [OUTPUT_FILE]`; both get help lines.
- Summary becomes "List the special-teams plays in a game plan."
- "in source order" becomes "in game plan order".

### gameplan replace-play

- Usage becomes `[OPTIONS] PLAY REPLACEMENT PATH`; each gets a help line (see the example in section 4).
- Summary becomes "Replace one play with another in game plans."
- "(unlike find-play, only one play)" is dropped; PLAY's help says it is one play.

### gameplan set-normals

- Usage becomes `[OPTIONS] GAME_PLAN INPUT_FILE`; INPUT_FILE help: "Play list, one name per line (- reads the console)."
- Summary becomes "Set the 64 normal plays from a play list."
- "`::` comment lines and ` ::` trailers are ignored" becomes "Lines starting with `::`, and text after ` ::`, are ignored."

### gameplan set-specials

- Usage becomes `[OPTIONS] PATH INPUT_FILE`; both get help lines; PATH help: "A .pln file, a folder or a wildcard."
- Summary becomes "Set the special-teams plays from a play list."
- "Merge semantics: unlisted special categories are preserved." becomes "Categories not in the list keep their plays."
- "(offense .pln are even-sized, defense odd)" is dropped.

### generate-schedule (hidden)

- Usage becomes `[OPTIONS]`; values become `--season YEAR`, `--seed NUMBER`, `--time-limit LIMIT`.
- "CP-SAT deterministic time" becomes plain words: the solver's own time units, not seconds.
- "directory" becomes "folder".

### playpool

- Group summary becomes "Check the play pool (.ply)."
- `playpool check`: usage becomes `[OPTIONS] [FOLDER]`; FOLDER help: "Play pool folder (default: the league's play_path)."
- `playpool check`: summary becomes "Check the play pool for problems."
- `playpool check`: the sentence about leagues lending category names to folders is rewritten in plain words, one idea per sentence.

### profile

- Group summary becomes "Check and edit coaching profiles (.prf)."
- `profile check`: same fixes as `gameplan check`; summary becomes "Check profiles against the league's rules."
- `profile copy`: usage becomes `[OPTIONS] SOURCE TARGET`; SOURCE help: "Profile to copy from."; TARGET help: "Profile, folder or wildcard to copy into."
- `profile copy`: summary becomes "Copy settings from one profile to others."
- `profile copy`: `--sub-percent` becomes `--substitutions`.
- `profile diff`: usage becomes `[OPTIONS] PROFILE1 PROFILE2`; both get help lines.
- `profile diff`: `--output file` becomes `--output FILE`; "instead of stdout" becomes "instead of the console".
- `profile diff`: summary becomes "Show differences between two profiles."

## Sources

- PyPI download counts: <https://pypistats.org/packages/click>, <https://pypistats.org/packages/typer>
- Click 8.5 argument help and placeholders: <https://click.palletsprojects.com/en/stable/documentation/>, <https://click.palletsprojects.com/en/stable/changes/>
- Typer releases: <https://pypi.org/project/typer/>, <https://typer.tiangolo.com/release-notes/>
- Command-line guidelines (help content, standard flags, noun-verb commands): <https://clig.dev/>
- POSIX utility syntax (single-letter options, synopsis notation): <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap12.html>
- Local help output: `cp --help` (GNU), `git mv -h`, `git help -a`, `uv add --help`, stock argparse and Click
- Click's Windows wildcard expansion: <https://click.palletsprojects.com/en/stable/faqs/>
- Windows programs expand their own wildcards: <https://learn.microsoft.com/en-us/cpp/c-language/expanding-wildcard-arguments>, <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ren>, <https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_wildcards>
- Windows removes quotes before a program sees its arguments: <https://learn.microsoft.com/en-us/cpp/c-language/parsing-c-command-line-arguments>
