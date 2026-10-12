# athc CLI Help and Naming Plan

**Goal:** every athc command's usage and help text follow one mainstream, modern style.

**Status:** proposal, 2026-10-11; nothing changed yet.

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
Usage: athc gameplan replace-play [OPTIONS] PLAY REPLACEMENT PATH

  Replace one play with another in game plans.

  Rules are not checked; run `athc gameplan check` afterward.

Positional arguments:
  PLAY         Play to replace (any case).
  REPLACEMENT  Play to put in its place; must be in the play pool.
  PATH         A .pln file or a folder.

Options:
  -r, --recursive  Include subfolders.
  --league NAME    League to use (default: the one set with `athc config
                   set league`).
  -h, --help       Show this message and exit.

  Examples:

    athc gameplan replace-play "Old Play" "New Play" .
```

Rules for every command and group:

1. **Usage line:** Click's own, `[OPTIONS]` then the arguments; groups end in `COMMAND [ARGS]...`.
2. **Placeholders:** UPPERCASE with underscores, for arguments and option values (`GAME_PLAN`, `--league NAME`).
3. **One name per kind of value:**
   - `PATH`: a file or a folder
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
11. **Short options:** one letter, standard meanings only (`-o` output, `-q` quiet, `-r` recursive).
12. **Long options:** spelled out (`--skip-calculations`, not `--skip-calcs`).
13. **Description:** two to four lines; rule details belong in the tool's docs.
14. **Examples:** one or two real examples per command, in an "Examples" epilog.

## 5. Issues and fixes

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

Project changes that come with the general fixes:

- `pyproject.toml` / `uv.lock`: Click 8.5 or later.
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

- `-o` means "output" elsewhere (`profile diff`, and the standard); `-o2` and `-d2` are not single letters. Replace with long options only: `--offense`, `--offense-2`, `--defense`, `--defense-2`, each taking `GAME_PLAN`.
- `--skip-calcs` becomes `--skip-calculations`.
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

- Usage becomes `[OPTIONS] PATH INPUT_FILE`; both get help lines.
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
- `profile copy`: usage becomes `[OPTIONS] SOURCE TARGET`; SOURCE help: "Profile to copy from."; TARGET help: "Profile or folder to copy into."
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
