# athc CLI help plan

Every athc command's usage and help text move to one mainstream, modern style; this plan lands before the command plans.

## Decisions (library, style)

- Library: Click, upgraded from 8.4.1 to 8.5 or later, with Click's Windows wildcard expansion turned off.
- Style: Click / GNU style, Click's default: one `[OPTIONS]` in the usage line, UPPERCASE placeholders with underscores.

## Rules (every command and group)

- Usage line: Click's own, `[OPTIONS]` then the arguments; groups end in `COMMAND [ARGS]...`.
- Placeholders: UPPERCASE with underscores, for arguments and option values (`GAME_PLAN`, `--league NAME`).
- One name per kind of value: `PATH` a file or a folder (or a wildcard, in the arguments where athc expands wildcards); `GAME_PLAN` one .pln file; `PROFILE` one .prf file; `FOLDER` a folder only; `INPUT_FILE` / `OUTPUT_FILE` play lists and reports (`-` means the console).
- `FILE` joins those names: a file named outright where none of the other names fits (`profile diff --output FILE`; generate-schedule's `--previous FILE` and `--upcoming FILE`, a `.lge` file; `config path | edit | reveal FILE`, a choice of `athc.ini` or `league.toml`, lowercase literals matched without case).
- Argument help: every argument gets its own help line; the description stops explaining arguments.
- Placeholders in text: the description names them in caps.
- One-line summary: starts with a verb, fits the command list (55 characters or fewer), no game title (the root help names the game once).
- Verbs match commands: `check` commands say "Check", not "Validate".
- Plain-English terms: "game plan" and "play pool" in text; command names stay `gameplan` and `playpool`.
- Windows words for end users: folder, subfolder, console, wildcard, File Explorer, Ctrl+C; never directory, stdout, glob, config dir.
- Shared options read the same everywhere: `-r, --recursive  Include subfolders.` and `--league NAME  League to use (default: the one set with athc config set league).`
- Short options: one letter, standard meanings only (`-o` output, `-r` recursive); convert-pdb keeps its `-o`, `-o2`, `-d` and `-d2`.
- Long options: spelled out (`--substitutions`, not `--sub-percent`).
- Description: two to four lines; rule details belong in the tool's docs.
- Examples: one or two real examples per command, in an "Examples" epilog.
- Wildcards: athc expands them itself, only in these arguments, and their help says so: PATH in `gameplan check` and `profile check`; `--path PATH` in `gameplan find-play`, `gameplan replace-play` and `gameplan set-specials`; TARGET in `profile copy`.
- A name that exists is a name, never a wildcard, so a folder like `Season [2029]` works.
- Path rule: no path means the configured default (your team's files; the league's play pool), `.` the current folder, an explicit path overrides both.
- `gameplan check` and `profile check` default to the current folder, and a plan that prefers the current folder says why.
- The four names: `off1`, `def1`, `off2`, `def2`, lowercase in help and docs, matched without case, accepted wherever a game plan or profile file operand is (`check` PATH included), except convert-pdb's `-o`, `-o2`, `-d` and `-d2`, which take `.pln` files only and never mix with the league file.
- The four names are your team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense file of the command's kind, found in `ppp_path` by its `.lg2` name, else at the league location (`path` joined with the `.lg2` folder).
- An existing path wins over a name.
- In docs, "the four names".
- Help calls them game plan keys (gameplan) and profile keys (profile): each operand or option that takes them says "or a game plan key" or "or a profile key" (or "keys").
- Every command that takes them ends its help with a `Game plan keys, for your team's league game plans:` or `Profile keys, for your team's profiles:` block above Examples, one meaning per key (1st-half offense, 1st-half defense, 2nd-half offense, 2nd-half defense).
- `--team NAME`: on every command that accepts the four names, declared once as `team_option(head)` in `src/athc/cli/__init__.py` beside `league_option`.
- `--team` help: a per-command head plus the shared tail `(default: team in league.toml).`; gameplan's head is `Team the game plan keys refer to` and profile's is `Team the profile keys refer to`.
- `--team` with no name among the operands: `Error: --team requires a game plan key (off1, def1, off2 or def2).` (gameplan) or `Error: --team requires a profile key (off1, def1, off2 or def2).` (profile), exit 2.
- On `find-play`, `replace-play` and `set-specials` it is `Error: --team requires --path to be a game plan key (off1, def1, off2 or def2) or left out.`
- On convert-pdb, `--team` with any of `-o`, `-o2`, `-d`, `-d2` is `Error: --team cannot be used with -o, -o2, -d or -d2.`
- `ppp_path` applies only to the team `team` in `league.toml` resolves to; another team uses the league locations.
- The team resolver, the league-file loader and the file locator live in `src/athc/cli/_team.py`.
- `--league NAME`: always a required value with the shared `--league` help text; never a contradiction; a named league must exist (the existing not-found line, exit 2), and its files are read only when the run needs them.
- `--path`: "where the game plans are" on every command that has it: `--path PATH` on `find-play`, `replace-play` and `set-specials` (a `.pln` file, a folder, a wildcard or one of the four names; default: your team's game plans), `--path FOLDER` on `convert-pdb` (a folder only; the team's four plans by their `.lg2` names).
- Hints: `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team.` and `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER'.`, each with the command's own ending.
- Team hint endings: ` or pass --team or --all-teams.` (check-ppp), ` or pass --team or --path.`, ` or pass --team or a .pln file.` or ` or pass --team or a .prf file.`, or `--team` alone when the command's path form is already on the line (convert-pdb with `--path`).
- Path hint endings: ` or pass --path.`, ` or pass --upcoming.`, ` or pass a .pln file.`, ` or pass a .prf file.`, ` or pass the folder.` or convert-pdb's ` or pass a game plan with -o, -o2, -d or -d2.`
- A team file missing at its league location, when the team is yours, adds `Run 'athc config set ppp_path FOLDER' or pass <a .pln file|a .prf file|--path|the folder>.`
- No argument metavars: Click derives the placeholder from the parameter name (`game_plan` gives `GAME_PLAN`, `output_file` gives `[OUTPUT_FILE]`, `play` with `nargs=-1, required=True` gives `PLAY...`).
- An argument's own validation is an athc callback raising `click.BadParameter(..., param_hint="'FILE'")`, so the hint reads `'FILE'`, never `'[FILE]'`.
- Usage-error period: every command prints `Got unexpected extra argument (x).`; the period is added once in `src/athc/cli/__init__.py` where usage errors are rendered, and no command raises its own copy.
- No quiet flag: no athc command has `-q/--quiet`; scripts use `> nul`, which hides the OK lines and keeps every FAIL on standard error.
- One form: every command plan describes this plan's form only (`[OPTIONS]`, uppercase placeholders, a Positional arguments section, an Examples epilog) and says "Depends on cli-help.md landing first."; this plan lands before any of them.
- On/off pairs over an `athc.ini` boolean: `--x/--no-x` with `default=None`, help `Overrides <key> in athc.ini (on by default).` (`autocontinue --hot-corner`, `convert-pdb --percentages`).
- Derived output: an optional `OUTPUT_FILE` defaults to the input's name with the product's extension, beside the input; its help says `(default: <INPUT> with .<ext>, beside it)`; a binary product refuses `-` (the exception to `-` meaning the console).

## Sample help screen

gameplan-cli.md's replace-play; the command plans decide each command's arguments and options.

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
  --path PATH      Game plans to edit: a .pln file, a folder, a wildcard or a
                   game plan key (default: your team's game plans).
  -r, --recursive  Include subfolders.
  --team NAME      Team the game plan keys refer to (default: team in
                   league.toml).
  --league NAME    League to use (default: the one set with athc config set
                   league).
  -h, --help       Show this message and exit.

  Game plan keys, for your team's league game plans:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc gameplan replace-play OLDRUN NEWRUN
    athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r
```

## Issues and fixes

The command plans decide each command's arguments, options and lines; where a plan's "cli-help.md changes" subsection amends a line below, the plan wins.

### General (every command)

- Lowercase placeholders look like literal words (`play replacement path`, `--league name`): UPPERCASE placeholders.
- The usage line lists every option, using custom code: Click's own usage line; delete athc's custom usage code.
- No arguments section; arguments are explained only inside the description: Click 8.5 argument help, one help line per argument.
- Descriptions use placeholders as plain words ("from gameplan", "Set key to value"): placeholders named in caps.
- Summaries are cut off with "..." in command lists: verb-first summaries of 55 characters or fewer.
- One thing, many names (`path`, `gameplan`, `pln_file`, `target`; `output_file`, `file`): one name per kind of value.
- Mixed terms: gameplan / game plan, stdout / console, glob / wildcard, directory / folder, config dir: plain-English terms and Windows words.
- `-r` help is worded three ways; `--league` help names a path instead of saying what it does: the shared `-r` and `--league` help text.
- `check` commands say "Validate": they say "Check".
- No examples anywhere: one or two examples per command in an Examples epilog.
- `--sort` shows `slot|name|category` in usage but `[slot|name|category]` under Options: gone with Click's own usage line (choices show only under Options).
- On Windows, Click expands wildcards in every word before athc sees it: `find-play`'s refusal never fires when files match, and `list-normals GP*.pln` with two matches writes the play list over the second game plan: turn Click's expansion off; athc expands wildcards itself, only in the wildcard arguments.
- `set-specials` PATH, `replace-play` PATH and `profile copy` TARGET take wildcards, but their help never says so: their help says so.
- A real name containing `[` is taken as a wildcard: `find-play` refuses it, the others report no match: a name that exists is a name, never a wildcard.
- No CLI test runs a wildcard through a command; the wildcard tests call the file helper directly: one CLI wildcard test per wildcard argument.

### athc (root)

- Usage becomes `athc [OPTIONS] COMMAND [ARGS]...`.
- Summaries of check-ppp, config, convert-pdb, gameplan and profile are cut off; each gets a new summary below.

### autocontinue

- Usage becomes `athc autocontinue [OPTIONS]`.
- "CTRL-C" becomes "Ctrl+C".
- `--hot-corner` help "(overrides config; default on)" becomes "Overrides hot_corner in athc.ini (on by default)."

### check-ppp

- Usage becomes `[OPTIONS] [PATH]...`; PATH help: "A .prf, a .pln, or a folder."
- Summary becomes "Check profiles against their game plans."
- The description is two dense paragraphs of rule logic; cut it to a few lines and move the rules to the tool's docs.
- "gameplan" and "directory" in text become "game plan" and "folder".

### config

- Summary becomes "Show or change athc settings (athc.ini, league.toml)."
- `config reveal`: "file manager" becomes "File Explorer"; summary becomes "Show athc.ini or league.toml in File Explorer."
- `config set`: usage becomes `[OPTIONS] KEY VALUE`; KEY help: "Setting to change: league, path, play_path, team or ppp_path."; VALUE help: "New value."
- `config set`: "Set key to value" becomes "Set a value in athc.ini or league.toml."; "a folder under leagues\ in the config dir" becomes plain words.

### convert-pdb

- `-o`, `-o2`, `-d` and `-d2` (`--pln-off`, `--pln-off-2`, `--pln-def`, `--pln-def-2`) stay as they are.
- `--skip-calcs` becomes `--percentages/--no-percentages` (an on/off pair over an `athc.ini` boolean; convert-pdb-cli.md).
- Usage becomes `[OPTIONS] PDB_FILE [OUTPUT_FILE]`; PDB_FILE help: "WinLogStats .pdb file."; OUTPUT_FILE help: ".xlsx, or .xlsm to include sorting macros (default: PDB_FILE with .xlsm, beside it)."
- Summary becomes "Convert a WinLogStats PDB to an Excel workbook."
- The description drops the game title.

### gameplan (group)

- Summary becomes "Check and edit game plans (.pln)."
- The summaries of check, find-play, list-specials, replace-play, set-normals and set-specials are cut off; each gets a new summary below.

### gameplan check

- Usage becomes `[OPTIONS] [PATH]...`; PATH help: ".pln files, folders, wildcards or game plan keys (default: current folder)."
- Summary becomes "Check game plans against the league's rules."
- "glob" and "directory" become "wildcard" and "folder".

### gameplan find-play

- What the last argument means depends on how many arguments there are (one is a play, two or more makes the last a path); make the location an option, `--path PATH` (default: your team's game plans), so every argument is a play.
- `--path` takes a .pln file, a folder, a wildcard or a game plan key; athc expands the wildcard itself.
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

- Usage becomes `[OPTIONS] PLAY REPLACEMENT...` with `--path PATH`; each argument gets a help line (see the sample help screen).
- Summary becomes "Replace one play with another in game plans."
- "(unlike find-play, only one play)" is dropped; PLAY's help says it is one play.

### gameplan set-normals

- Usage becomes `[OPTIONS] GAME_PLAN INPUT_FILE`; INPUT_FILE help: "Play list, one name per line (- reads the console)."
- Summary becomes "Set the 64 normal plays from a play list."
- "`::` comment lines and ` ::` trailers are ignored" becomes "Lines starting with `::`, and text after ` ::`, are ignored."

### gameplan set-specials

- Usage becomes `[OPTIONS] INPUT_FILE` with `--path PATH`; `--path` help: "Game plans to edit: a .pln file, a folder, a wildcard or a game plan key (default: your team's game plans)."
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
- `profile check`: same fixes as `gameplan check`, PATH help ".prf files, folders, wildcards or profile keys (default: current folder)."; summary becomes "Check profiles against the league's rules."
- `profile copy`: usage becomes `[OPTIONS] SOURCE TARGET...`; SOURCE help: "Profile to copy from: a .prf file or a profile key."; TARGET help: "Profiles to copy into: .prf files, folders, wildcards or profile keys."
- `profile copy`: summary becomes "Copy settings from one profile to others."
- `profile copy`: `--sub-percent` becomes `--substitutions`.
- `profile diff`: usage becomes `[OPTIONS] PROFILE1 PROFILE2`; both get help lines.
- `profile diff`: `--output file` becomes `--output FILE`; "instead of stdout" becomes "instead of the console".
- `profile diff`: summary becomes "Show differences between two profiles."

## Files to change

- `pyproject.toml` / `uv.lock`: Click 8.5 or later.
- `src/athc/cli/__init__.py`: Click's wildcard expansion off.
- `src/athc/cli/_files.py`: a path that exists is used as is, before any wildcard check.

## Tests

- One CLI test with a wildcard for each of the six wildcard arguments: PATH in `gameplan check` and `profile check`; `--path PATH` in `gameplan find-play`, `gameplan replace-play` and `gameplan set-specials`; TARGET in `profile copy`.
- `tests/integration/test_cli_root.py` (`test_usage_lists_each_option`): pins the old usage line; changes with the approved style.
- Summary limit: every command and group summary is 55 characters or fewer; the check passes a 55-character summary and fails a 56-character one.
- Description range: every command's description is two to four lines; the check fails 1 line, passes 2 and 4, and fails 5.
- Examples range: every command has one or two examples; the check fails 0, passes 1 and 2, and fails 3.

## Docs and meta

- `docs/design/architecture.md`, CLI section: the usage-line and lowercase-placeholder rules are replaced by this style.
- `tests/integration/README.md`: the `test_usage_lists_each_option` row changes with the approved style.
- check-ppp's docs: take the rule logic cut from its help description.
