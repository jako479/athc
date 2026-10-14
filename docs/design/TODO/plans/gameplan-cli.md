# gameplan CLI plan

`find-play`, `replace-play` and `set-specials` default to your team's four game plans; every game plan operand, `check` included, also takes `off1`, `def1`, `off2` or `def2`; a path still points at a file, a folder or a wildcard; `check` keeps the current folder as its default.

Depends on cli-help.md landing first.

## Decisions

- Scope rule for the group: no path means the command's default scope, `.` means the current folder, an explicit path overrides both.
- Default scope: your team's game plans for `find-play`, `replace-play` and `set-specials`; the current folder for `check`.
- The scope of the three batch commands is an option, `--path PATH`; `gameplan check` keeps PATH positional.
- `--path` takes a `.pln` file, a folder, a wildcard or one of the four names, the same on all three.
- A wildcard counts as a folder (a tally, misses silent); find-play no longer refuses one.
- A wildcard in `--path` reaches the command whole (Click's own Windows expansion off), like `check`'s.
- The three batch commands act on every game plan they find in `--path`.
- Your team's four game plans are named `off1`, `def1`, `off2`, `def2`: the 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense game plan the `.lg2` names for your team (its entries 2, 4, 6 and 8), in that order, matched without case.
- In prose they are "the four names"; help calls them game plan keys.
- An existing path always wins: a file or folder named `off1` in the current folder is that file or folder.
- Two names that resolve to one file (a game plan shared across halves) are the same file.
- The profile commands use the same four words for the four `.prf`.
- The four names are accepted wherever a game plan operand is: `GAME_PLAN` on `list-normals`, `list-specials` and `set-normals`, `--path` on the batch three, `PATH` on `check`.
- No `GAME_PLAN` stays Click's `Missing argument 'GAME_PLAN'.` (exit 2); there is no default game plan.
- The `GAME_PLAN` help line names the four words.
- No explicit metavars: the parameters are named `game_plan`, `input_file`, `output_file`, `play`, `replacement` and, on `check`, `path`, so Click derives `GAME_PLAN`, `INPUT_FILE`, `[OUTPUT_FILE]`, `PLAY...`, `REPLACEMENT...` and `[PATH]...` for the usage line and the `Missing argument` hints.
- `--team NAME` on every gameplan subcommand: `team` in `league.toml` by default, `--team` for one run; the `.lge`'s names (team, nickname or both) matched without case, exactly one match, check-ppp's lines.
- `--team` with no name among the operands is a usage error, `Error: --team requires a game plan key (off1, def1, off2 or def2).` (`Error: --team requires --path to be a game plan key (off1, def1, off2 or def2) or left out.` on `find-play`, `replace-play` and `set-specials`): a `--path`, `GAME_PLAN` or `PATH` that is a real path, and `check --team X` with no PATH.
- `--team` only reads `team` to tell whether `ppp_path` applies.
- No `--all-teams`.
- `--league NAME` is never a contradiction; it always takes a value, with the shared `--league` help text.
- Every subcommand resolves `--league` when given (a named league must exist: the existing `League '<name>' not found` line, exit 2) and reads the league's files only when the run needs them.
- What each command reads from the league: `find-play` and `list-specials` with a path, nothing; `check`, its rules on every run; `replace-play`, `set-normals` and `set-specials`, the pool on every run; `list-normals`, the category labels.
- `find-play` and `list-specials` with an explicit path read no league files, pool or rules; `--league` on such a run is resolved and nothing is read from it; with the default scope, a name or `--team` they read `league.toml`, the `.lg2` and the `.lge`.
- `find-play` and `list-specials` gain `--league`.
- Three sources for the files, in this order: the path on the command line; else `ppp_path` under `[league]` (your team's files found there by their `.lg2` names, without case; with `-r`, each folder of its tree on its own); else the league locations (`path` joined with each file's `.lg2` folder and name, exact).
- `ppp_path` applies only to the team `team` in `league.toml` resolves to: `--team` naming that team goes through it; `--team` naming another team, or `--team` with `team` unset or unresolvable, uses the league locations.
- `-r` is ignored for a file, a name and the league locations.
- At the league locations a missing game plan is a `FAIL` counted as failed; a team none of whose game plans exists gets one `FAIL` per `.lg2` folder, counted as one failed item.
- The `Run 'athc config set ppp_path FOLDER' ...` hint is added only when the run's team is the one `team` resolves to (defaulted, or `--team` naming it); another team's lines carry no hint.
- In `ppp_path` a batch command `WARN`s per missing game plan and goes on; when none of the four is in the scope (the folder, or the tree with `-r`) it prints one `WARN` for the scope naming the team and the four names; the code stays what the files found give.
- A one-file command, or `check` with a name, names one file: a missing one is the run's error (`FAIL`, exit 2) in either source.
- Whether a file is there is decided before anything reads it; a file that is there but cannot be read is handled as today.
- A game plan the `.lg2` names twice is processed once, in `.lg2` order (off1, def1, off2, def2); `team_files` returns both pairs and the command drops the repeat by resolved path.
- Tallies stay each command's: `find-play` and `replace-play` print one for a set (the four game plans, a folder, a tree, a wildcard) and none for one file (a `.pln` path or a name); `set-specials` prints its tally for one file too.
- Tally fields do not change; a `WARN`ed missing file counts nowhere.
- `-q/--quiet` goes and no athc command has a quiet flag; `-q` becomes Click's unknown-option error; the README and COMMANDS.txt say `> nul`.
- `replace-play` takes `PLAY` then `REPLACEMENT...`, nothing else positional; `split_args` and `_is_path` go.
- A replacement listed again, in any case, is tried once.
- One name alone is Click's `Missing argument 'REPLACEMENT...'.`.
- The 1.0.0 TODO item for a list of play/replacement pairs will arrive as an option that reads a file (`-` for the console); that change makes both positionals optional and checks by hand that either the two positionals or the option is present; the file's format belongs to that change.
- `check` keeps its default (the current folder) and its job (the any-name checker) and gains the four names and `--team`; its docs gain the sentence that check-ppp checks pairs.
- A written list lands beside its game plan by default: with `ppp_path` that is the coach's own folder; at the league locations the `OK` line names the full path; `OUTPUT_FILE` puts it anywhere.
- Two names for one shared game plan write the same file twice.
- Setup order: Click's argument parsing; `--league`, when given, resolved to an existing league folder (`resolve_league`, no file read) before any operand; the operands left to right as the usage line shows them; for a batch command with the default scope, `league.toml`, the team, the `.lg2` and `.lge`, the four located; the pool and rules; then the files are read.
- A game plan operand in that order: a path is checked to exist; a name reads `team` from `league.toml` (a missing one failing here), then loads the `.lg2` and `.lge`, matches the team against the `.lge` names and locates the file, which is checked to exist.
- A play list operand in that order is read, parsed and counted.
- `team` is read from `league.toml` alone before the league files are loaded: a missing `team` shows before a missing `path`, both before the pool's `WARN` lines.
- A stock league is `Stock league not supported.`, as in check-ppp.
- The order stays today's for every run that names paths, except that a wrong `--league` now fails before the operands; only a name adds the league reads in front of the file check.
- Lines are check-ppp-cli.md's where they say the same thing (team resolution, `path` and `ppp_path` problems, the league files, a missing file, a team with no files), with "game plans" where check-ppp says "files".
- The "Team is not set" and "League files folder is not set" lines keep check-ppp's shape and end with the command's own way out: `or pass --team or --path.` when the run used the default scope, `or pass --team or a .pln file.` when it used a name.
- The no-league line is the shared one from `src/athc/config.py`, reworded by config-cli.md to `League is not set. ...`; the help names `--path`.
- Keys: `team`, `ppp_path`, `path` under `[league]`, nothing new; set with `athc config set`, which writes them into the league's `league.toml`, like `play_path`.
- Help text is in cli-help.md's form: `[OPTIONS]`, UPPERCASE placeholders derived from the parameter names, a Positional arguments section, an Examples epilog, the shared `-r` and `--league` texts.
- Operands and `--path` say "or a game plan key"; a Keys block above Examples gives each key's meaning.
- The `--team` text is a per-command head and the shared tail: `Team the game plan keys refer to (default: team in league.toml).`
- A play list that cannot be read is one plain `FAIL <list>: Not a valid play list.` line, exit 2, not the unexpected-error line: the list reader turns `UnicodeDecodeError` into `AthcError("Not a valid play list.", path)`, naming the list, for `set-normals` and `set-specials`.
- A list from the console (`-`) is outside this change.

### Per command

- `gameplan`: summary "Check and edit game plans (.pln)."; bare `athc gameplan` prints its help on standard error and exits 2, as today.
- `check`: a name is one file in the batch, found as the one-file modes say (a missing one is a `FAIL` counted as failed, with the hint when the team is yours); lines, order and codes are today's.
- `check`: a folder named `off1` in the current folder is searched like any folder; a file named `off1` is `FAIL off1: Not a .pln file.`, as `collect_files` says today.
- `check`: `--team` with paths only, or with no PATH at all, is `Error: --team requires a game plan key (off1, def1, off2 or def2).`; `--league` is read for the rules as today.
- `find-play`: every argument is a play; lines are today's; the four game plans are a set (the blank line and the per-play tallies); `--path off1` or `--path x.pln` is one file, no tally.
- `find-play`: order is the four in `.lg2` order, a shared game plan once; in a folder or tree, `collect_files`' order as today.
- `find-play`: exit 0 a play found anywhere, 1 none, 2 any failed file.
- `replace-play`: lines, order and codes as today; the four game plans are a set (tally, misses silent), a name or a `.pln` one file (`not found` line, no tally).
- `set-specials`: with the default scope an offense list updates off1 and off2 and prints `SKIP <path>: defense gameplan` for def1 and def2; the tally reads `4 file(s) processed, 2 updated, 2 skipped, 0 failed` (`2 ... 1 updated, 1 skipped` for a team with one game plan per side).
- `set-specials`: one file (`--path try3.pln` or a name) gets its tally too; exit 2 any failed file, else 0.
- `list-normals`, `list-specials`: write beside the file they read; `-` prints.

### Batch modes (find-play, replace-play, set-specials)

| `--path` | Team | Files come from | What is missing |
|---|---|---|---|
| none, `ppp_path` set | `team`, or `--team` naming it | that folder, each of the four by its `.lg2` name without case; with `-r`, each folder of its tree on its own | a game plan: `WARN`, not counted; all four, in the whole scope: one `WARN` naming the team and the names |
| none | `team`, or `--team` naming it, with `ppp_path` unset; `--team` naming another team, or with `team` unset, always | the league locations: `path` joined with each game plan's `.lg2` folder and name | a game plan: `FAIL`, counted as failed; all four: one `FAIL` per folder, absent or empty, counted as one failed item, with the `ppp_path` hint when the team is yours and none for another team |
| `off1`, `def1`, `off2` or `def2` | as the two rows above | that one file, from `ppp_path` when it applies, else its league location | `FAIL`, exit 2 (one file was named) |
| a `.pln`, a folder, a wildcard, `.` | none (`--team` is a usage error; `--league` must name an existing league and is otherwise not read) | as today | as today |

- A folder named `off1` in the current folder is a folder, so `--path off1` searches it; a file named `off1` is `FAIL off1: Not a .pln file.`; the four names mean your team's file only when no such path exists.

### One-file modes (list-normals, list-specials, set-normals)

| `GAME_PLAN` | Team | The file | What is missing |
|---|---|---|---|
| `off1`, `def1`, `off2` or `def2`, `ppp_path` set | `team`, or `--team` naming it | `<ppp_path>\<its .lg2 name>`, matched without case | `FAIL <ppp_path>\<name>: The system cannot find the file specified.`, 2 |
| one of the four names | `team`, or `--team` naming it, with `ppp_path` unset; `--team` naming another team, or with `team` unset, always | its league location | the same `FAIL`, with the `ppp_path` hint when the team is yours and none for another team, 2 |
| a path | none (`--team` is a usage error; `--league` must name an existing league; `list-normals` reads it for its labels and `set-normals` for the pool, `list-specials` reads nothing from it) | that file, as today | as today |

- An existing path named `off1` is that path: a folder named `off1` gives `named_file`'s `FAIL off1: Access is denied.`, as any folder does.
- A name the `.lg2` knows nothing of (`off3`) is a path like any other: today's missing-file `FAIL`.

## Help

### gameplan

```
Usage: athc gameplan [OPTIONS] COMMAND [ARGS]...

  Check and edit game plans (.pln).

Options:
  -h, --help  Show this message and exit.

Commands:
  check          Check game plans against the league's rules.
  find-play      Find plays by name in game plans.
  list-normals   List the 64 normal plays in a game plan.
  list-specials  List the special-teams plays in a game plan.
  replace-play   Replace one play with another in game plans.
  set-normals    Set the 64 normal plays from a play list.
  set-specials   Set the special-teams plays from a play list.
```

### check

```
Usage: athc gameplan check [OPTIONS] [PATH]...

  Check game plans against the league's rules.

  With no PATH, every .pln in the current folder is checked. To check your
  team's game plans with their profiles, run athc check-ppp.

Positional arguments:
  PATH  .pln files, folders, wildcards or game plan keys (default: current
        folder).

Options:
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

    athc gameplan check
    athc gameplan check off1
    athc gameplan check plans -r
```

### find-play

```
Usage: athc gameplan find-play [OPTIONS] PLAY...

  Find plays by name in game plans.

  Searches the normal and special-teams slots of your team's game plans, or of
  the game plans --path names, and lists each play's slots per game plan.

Positional arguments:
  PLAY  Plays to find (any case).

Options:
  --path PATH      Game plans to search: a .pln file, a folder, a wildcard or
                   a game plan key (default: your team's game plans).
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

    athc gameplan find-play OR45RL01
    athc gameplan find-play OR45RL01 BCFGPAT --path plans -r
```

### replace-play

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

### set-specials

```
Usage: athc gameplan set-specials [OPTIONS] INPUT_FILE

  Set the special-teams plays from a play list.

  The list's side picks the game plans: files of the other side are skipped.
  Categories not in the list keep their plays.

Positional arguments:
  INPUT_FILE  Play list, one name per line (- reads the console).

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

    athc gameplan set-specials spec.txt
    athc gameplan set-specials spec.txt --path plans -r
```

### list-normals

```
Usage: athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT_FILE]

  List the 64 normal plays in a game plan.

  Writes them to OUTPUT_FILE, or to <name>.normals.txt beside the game plan;
  an existing file is replaced.

Positional arguments:
  GAME_PLAN    A .pln file or a game plan key.
  OUTPUT_FILE  Where to write the list (default: GAME_PLAN with .normals.txt,
               beside it; - prints it).

Options:
  --sort [slot|name|category]  slot keeps slot order (empty slots blank); name
                               sorts by name; category groups by category
                               under :: headers with the league's names.
                               [default: slot]
  --team NAME                  Team the game plan keys refer to (default: team
                               in league.toml).
  --league NAME                League to use (default: the one set with athc
                               config set league).
  -h, --help                   Show this message and exit.

  Game plan keys, for your team's league game plans:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc gameplan list-normals off1
    athc gameplan list-normals DEN-OGP1.pln plays.txt --sort category
```

### list-specials

```
Usage: athc gameplan list-specials [OPTIONS] GAME_PLAN [OUTPUT_FILE]

  List the special-teams plays in a game plan.

  Writes them, in game plan order, to OUTPUT_FILE, or to <name>.specials.txt
  beside the game plan; an existing file is replaced.

Positional arguments:
  GAME_PLAN    A .pln file or a game plan key.
  OUTPUT_FILE  Where to write the list (default: GAME_PLAN with .specials.txt,
               beside it; - prints it).

Options:
  --team NAME    Team the game plan keys refer to (default: team in
                 league.toml).
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Game plan keys, for your team's league game plans:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc gameplan list-specials def1 -
    athc gameplan list-specials DEN-DGP1.pln spec.txt
```

### set-normals

```
Usage: athc gameplan set-normals [OPTIONS] GAME_PLAN INPUT_FILE

  Set the 64 normal plays from a play list.

  Lines starting with ::, and text after " ::", are ignored. The league's play
  pool resolves names; run athc gameplan check afterward.

Positional arguments:
  GAME_PLAN   A .pln file or a game plan key.
  INPUT_FILE  Play list, one name per line (- reads the console).

Options:
  --team NAME    Team the game plan keys refer to (default: team in
                 league.toml).
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Game plan keys, for your team's league game plans:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc gameplan set-normals off1 plays.txt
    athc gameplan set-normals DEN-OGP1.pln -
```

## Settings

In `league.toml`, under `[league]`, the keys check-ppp-cli.md adds; this plan adds none. The comment text for `path` and `team` is the shipped text check-ppp-cli.md owns:

```toml
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# Your team: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

- `find-play`, `replace-play` and `set-specials` read `path`, `team` and `ppp_path` when `--path` is absent or one of the four names; `check`, `list-normals`, `list-specials` and `set-normals` when an operand is one of the four names; every command when `--team` is given. With paths only none of the three keys is read.
- `--league` is accepted on every subcommand and the named league must exist (today's `League '<name>' not found` line otherwise); `find-play` and `list-specials` read the league's files only when the run needs them (the default scope, a name, `--team`); `check` reads its rules, and `replace-play`, `set-normals` and `set-specials` the pool, on every run.
- `replace-play`, `set-normals` and `set-specials` read `play_path` and (`replace-play`) the gameplan rules as today; `list-normals` the category labels as today; `check` its rules and pool as today.
- The run log gets the same lines as the console, as everywhere.

## Lines and exit codes

New or changed lines; everything else prints as today. Team labels are the `.lge` team name (`Denver`); a found file prints its on-disk name, a missing one the league file's spelling.

| When | Line | Code |
|---|---|---|
| bare `athc gameplan` | its help, on standard error | 2 |
| no league set, default scope or a name (`find-play`, `list-specials` included, which need none for a path) | `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.` (the shared line from `src/athc/config.py`, as config-cli.md words it) | 2 |
| `--league` names a league with no folder (any subcommand, path or not) | `FAIL League 'NOPE' not found. No folder <leagues>\NOPE. Available: PCFL, PNFL.` (the shared line, unchanged; `_available()` sorts the names) | 2 |
| no `team`, no `--team`, default scope (batch) | `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or --path.` | 2 |
| no `team`, no `--team`, a name given (`--path off1`, `GAME_PLAN`, `check`'s PATH) | `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or a .pln file.` | 2 |
| `team` matches no team | `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: Jacksonville Jaguars, Buffalo Bills, ...` | 2 |
| `--team` matches no team | `Error: Invalid value for '--team': no team named 'Denvr'. Teams: Jacksonville Jaguars, Buffalo Bills, ...` | 2 |
| `team` matches two teams | `FAIL <league.toml>: [league] team: 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | 2 |
| `--team` matches two teams | `Error: Invalid value for '--team': 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | 2 |
| `team` is an array | `FAIL <league.toml>: [league] team: Expected a string, got an array.` | 2 |
| `--team` with paths only, or `check --team X` with no PATH (`check`, `list-normals`, `list-specials`, `set-normals`) | `Error: --team requires a game plan key (off1, def1, off2 or def2).` | 2 |
| `--team` with a `--path` that is not a key (`find-play`, `replace-play`, `set-specials`) | `Error: --team requires --path to be a game plan key (off1, def1, off2 or def2) or left out.` | 2 |
| bare `find-play` | `Error: Missing argument 'PLAY...'.` | 2 |
| bare `replace-play` | `Error: Missing argument 'PLAY'.` | 2 |
| `replace-play OLD` | `Error: Missing argument 'REPLACEMENT...'.` | 2 |
| bare `set-specials`; `set-normals off1` | `Error: Missing argument 'INPUT_FILE'.` | 2 |
| bare `list-normals`, `list-specials`, `set-normals` | `Error: Missing argument 'GAME_PLAN'.` | 2 |
| `set-normals -q` | Click's unknown-option error | 2 |
| an extra positional (`set-specials spec.txt extra`, `set-normals off1 plays.txt extra`, `list-normals off1 out.txt extra`) | `Error: Got unexpected extra argument (extra).` (Click's text, athc's period added once in `src/athc/cli/__init__.py`) | 2 |
| a `.pln`, or any file that is not UTF-8 text, as `INPUT_FILE` | `FAIL <list>: Not a valid play list.` (today: the "Unexpected error" line) | 2 |
| no `path` in `league.toml`, default scope (batch) | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass --path.` | 2 |
| no `path` in `league.toml`, a name given | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass a .pln file.` | 2 |
| `ppp_path` missing on disk, or a file | `FAIL <ppp_path>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER'.` / `... The directory name is invalid. ...` | 2 |
| `.lg2` or `.lge` missing or bad | the library's line (`FAIL <PNFL.lge>: ...`) | 2 |
| a stock league | `FAIL <PNFL.lg2>: Stock league not supported.` | 2 |
| the two league files disagree | `FAIL <PNFL.lg2>: Lists 17 team(s), but PNFL.lge has 18.` | 2 |
| league location, a game plan missing (batch) | `FAIL <folder>\DEN-OGP2.pln: The system cannot find the file specified.`, counted as failed | 2 |
| league location, none of the four, folder present (batch, your team) | `FAIL <folder>: No Denver game plans. Run 'athc config set ppp_path FOLDER' or pass --path.`, counted as one failed item | 2 |
| league location, none of the four, folder present (batch, `--team` naming another team) | `FAIL <folder>: No Las Vegas game plans.`, counted as one failed item, no hint | 2 |
| league location, none of the four, folder absent (batch, your team) | `FAIL <folder>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER' or pass --path.`, counted as one failed item | 2 |
| league location, none of the four, folder absent (batch, another team) | `FAIL <folder>: The system cannot find the path specified.`, counted as one failed item, no hint | 2 |
| league location, the named game plan missing (one file, or `check` with a name; your team) | `FAIL <folder>\DEN-OGP1.pln: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .pln file.` (the path phrase when the folder is absent) | 2 |
| league location, the named game plan missing (another team) | `FAIL <folder>\RAIDEROFF.pln: The system cannot find the file specified.`, no hint | 2 |
| `ppp_path`, a game plan missing (batch) | `WARN <ppp_path>\DEN-OGP2.pln: The system cannot find the file specified.` | unchanged |
| `ppp_path`, none of the four in the scope (batch) | `WARN <ppp_path>: No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, DEN-OGP2.pln, DEN-DGP2.pln.` (each name once; one line for the scope, tree included) | `find-play` 1, `replace-play` 1, `set-specials` 0 |
| `ppp_path`, the named game plan missing (one file, or `check` with a name) | `FAIL <ppp_path>\DEN-OGP1.pln: The system cannot find the file specified.` | 2 |
| a file named like one of the four is given on `check` PATH or `--path` | `FAIL off1: Not a .pln file.` (`collect_files`, as today) | 2 |
| a folder named like one of the four is given as `GAME_PLAN` | `FAIL off1: Access is denied.` (`named_file`, as any folder) | as today |
| `set-specials`, default scope, an offense list | `SKIP <path>: defense gameplan` for def1 and def2; tally `4 file(s) processed, 2 updated, 2 skipped, 0 failed` | 2 any failed file, else 0 |
| the tallies | unchanged; the four count as the files found | |

- A batch runs every file it found and exits with the worst outcome, as today: error beats findings beats clean; a `WARN` never changes the code.

## Files to change

- `src/athc/cli/_team.py` (new, beside `_files.py`; profile-cli.md and convert-pdb-cli.md use the same): the team layer moved out of `check_ppp.py`: `TEAM_FILE_NAMES = ("off1", "def1", "off2", "def2")`; `load_league_files(league, league_dir)` (the `.lg2` with its stock check, then the `.lge`, then the team counts compared); `resolve_team(name, lge)` (team, nickname or both, without case, exactly one; check-ppp's two error lines); `team_files(team, kind)` (the four `(name, file)` pairs of one kind in `.lg2` order, a shared file repeated); `locate(file, ppp_path, league_path) -> Located(path, exists, source)` (the three sources, existence decided before any read); `TEAM_KEY = "team"` and `PPP_PATH_KEY = "ppp_path"`, with `LEAGUE_PATH_KEY` imported from `src/athc/config.py` and re-exported, not defined twice, read through `LeagueConfig.string` and `LeagueConfig.path`.
- `src/athc/cli/__init__.py`: `team_option` beside `league_option`, the per-command head passed in and the shared tail fixed.
- `src/athc/cli/gameplan/_common.py`: `scope(path, team, league, *, recursive) -> Collected` (a real path through `collect_files` as today; `None` or one of the four names through `_team`, the missing-file `WARN` / `FAIL` lines as `Collected.warnings` / `errors`, the `--team`-with-a-path `UsageError`).
- `src/athc/cli/gameplan/_common.py`: `one_game_plan(raw, team, league) -> Path` (`named_file` for a path, the folder hint added when `raw` is one of the four; the resolver for a name).
- `src/athc/cli/gameplan/_common.py`: `read_play_list(path) -> str` (`named_file(...).read_text(encoding="utf-8-sig")` with `UnicodeDecodeError` turned into `AthcError("Not a valid play list.", path)`), used by `set-normals` and `set-specials`.
- `src/athc/cli/gameplan/check.py`: the argument `path` (`nargs=-1`, no metavar: `[PATH]...`); entries that are one of the four names resolved through `_team` before `collect_files`; `team_option`; a usage error with no name among the entries, no PATH at all included; help text.
- `src/athc/cli/gameplan/find_play.py`: the argument `play` (`nargs=-1, required=True`, no metavar: `PLAY...`), `--path`, `team_option`, `league_option`; the single-argument split and the wildcard refusal go; `single_path` becomes "the scope is one file".
- `src/athc/cli/gameplan/replace_play.py`: the arguments `play` and `replacement` (`nargs=-1, required=True`), no metavars (`PLAY REPLACEMENT...`, hint `'REPLACEMENT...'`), `--path`, `team_option`; `split_args` and `_is_path` go; the repeat-dropping moves into the command.
- `src/athc/cli/gameplan/set_specials.py`: the one argument `input_file` (no metavar: `INPUT_FILE`), `--path`, `team_option`; the list through `read_play_list`.
- `src/athc/cli/gameplan/set_normals.py`: `-q/--quiet` removed; the arguments `game_plan` and `input_file` (no metavars); `game_plan` through `one_game_plan`; the list through `read_play_list`; `team_option`.
- `src/athc/cli/gameplan/list_normals.py`, `list_specials.py`: the arguments `game_plan` and `output_file` (no metavars: `GAME_PLAN [OUTPUT_FILE]`); `game_plan` through `one_game_plan`; `team_option`; `list_specials.py` gains `league_option`.
- `src/athc/cli/gameplan/__init__.py`: help text only.
- `src/athc/config.py`: `LeagueConfig.string(key)` (`LgeFile.teams` already exists).
- `src/athc/cli/check_ppp.py`: its resolver, league-file loader and sources import from `_team.py`; no behaviour change.
- `config/release/leagues/*/league.toml`, `config/dev/leagues/*/league.toml`: the comments above `path` name the gameplan commands too.

## Tests

New, in `tests/integration/test_gameplan_check.py`, `test_gameplan_find_play.py`, `test_gameplan_replace_play.py`, `test_gameplan_set_specials.py`, `test_gameplan_list.py` and `test_gameplan_set_normals.py`:

- Fixtures in `tests/integration/conftest.py` (profile-cli.md and convert-pdb-cli.md use the same names): `build_league` (a league folder with `path` and `team`), `lg2_league` (a built league with `.lg2` and `.lge` beside `league.toml`), `pnfl_league` (the real `tests/integration/data/PNFL.lg2` with a `PNFL.lge` beside it, over `data/ppp`: Denver's four files, Las Vegas's one game plan per side), the `team()` builder (one team's eight names), with the `.lg2`/`.lge` builders.
- The four names: each maps to its `.lg2` entry (off1 = 1st-half offense game plan, def1, off2, def2); any case; a shared game plan once for the batch commands and the same file for two names.
- An existing path named `off1` wins: a `.pln` file is used; a folder on a one-file command gives the `Access is denied.` line; a folder on `check` PATH or `--path` is searched; a file named `off1` on `check` PATH or `--path` gives `Not a .pln file.`.
- `off3` is today's missing-file `FAIL`.
- `check off1` checks that file; `check off1 x.pln` checks both.
- Limits: the four names accepted, a fifth rejected.
- Sources: default scope with `ppp_path`; without it; `--path .`; `--path <folder>`; `--path <wildcard>` on all three (find-play's new one).
- Sources: a relative `ppp_path`; `ppp_path` missing on disk and a file; `-r` over a `ppp_path` tree (the no-game-plans `WARN` once for the tree); `-r` ignored at the league locations.
- Team: `team`; `--team` by name, nickname, both, mixed case; no match and two matches (a built `.lge`); blank; an array; `--team` beats `team`.
- Team: `--team` naming your team goes through `ppp_path`; naming another team, or with `team` unset, uses the league locations.
- Team: neither set gives the two "Team is not set" hints.
- `--team` with paths only is a usage error on a batch command, a one-file command and `check`; `check --team X` with no PATH too.
- `--league` with a path on `find-play` and `list-specials`: an existing league is resolved and nothing read from it; `--league NOPE` fails with the no-such-league line even with a path; no `--league` with no `athc.ini` at all still works.
- Limits: one team match accepted, zero and two rejected.
- Missing files: league locations, one game plan missing (`FAIL`, counted failed, exit 2, the others processed).
- Missing files: league locations, none of the four, folder present and absent (one line, one failed item in the tally; the `ppp_path` hint for your team, none for `--team` naming another team).
- Missing files: `ppp_path`, one missing (`WARN`, code unchanged); none of the four (the names line; `find-play` 1, `replace-play` 1, `set-specials` 0).
- Limits: none of the four present gives the one scope line; exactly one present gives no scope line, in `ppp_path` and at the league locations.
- Missing files: a one-file command's named file missing in each source; `check off1` with the file missing.
- League files: no `path` (the two hints); `.lg2` or `.lge` missing; a stock league; no league selected on `find-play` with the default scope and on `list-specials off1`.
- Limits: team counts equal accepted, off by one rejected.
- Setup order: a missing `team` shows before a missing `path`; a `--team` typo shows before the pool's `WARN` lines.
- Setup order: a too-long list fails before any league read on `set-specials` and on `set-normals` with a path; `set-normals off1 <too long list>` reads the league first.
- `set-specials` over the four: the list's side updated, the other side `SKIP`ped, the tally; one file keeps its tally.
- `find-play` and `replace-play` over the four: `.lg2` order, a tally, a shared game plan once.
- `replace-play`: bare is `Missing argument 'PLAY'.`, `OLD` alone `Missing argument 'REPLACEMENT...'.`; a repeated replacement tried once (CLI, replacing the `split_args` unit tests).
- Bare `find-play` and bare `set-specials` give their `Missing argument` lines.
- `set-normals -q` rejected.
- A `.pln` as `INPUT_FILE` is `FAIL <list>: Not a valid play list.` on `set-normals` and `set-specials`, the game plan untouched.
- `tests/integration/test_cli_root.py`: `LEAGUE_COMMANDS` gains `find_play`, `list_normals` and `list_specials`; `_unknown_league_args` gives `find_play` `["Some Play", "--path", str(GP_OFFENSE)]`, `list_specials` `[str(GP_OFFENSE)]`, `list_normals` `[str(GP_OFFENSE)]`, `replace_play` `["Old Play", "New Play", "--path", str(GP_OFFENSE)]`, `set_specials` `[str(plays), "--path", str(GP_OFFENSE)]`; `--league NOPE` fails at `resolve_league` before any team or league file is needed; the test's `make_league()` is fixture enough.
- Help: every screen above, in cli-help.md's help tests.

Existing tests that change:

- `test_gameplan_find_play.py`: `test_cli_single_arg_searches_current_directory` becomes the default-scope test (the current folder is `--path .`).
- `test_gameplan_find_play.py`: `test_cli_single_arg_recursive` and `test_cli_single_arg_empty_directory_exit_1` take `--path .`.
- `test_gameplan_find_play.py`: `test_cli_two_args_last_is_the_path` becomes the "every argument is a play" test.
- `test_gameplan_find_play.py`: `test_cli_wildcard_path_is_rejected` changes (a wildcard now works like a folder).
- `test_gameplan_find_play.py`: the path moves from the last argument to `--path` in `test_cli_single_file_hit`, `test_cli_single_file_miss_exit_1`, `test_cli_single_file_case_insensitive`, `test_cli_finds_custom_special`, `test_cli_multiple_plays_all_hit`, `test_cli_one_play_found_exit_0`, `test_cli_no_play_found_exit_1`, `test_cli_directory_reports_hit_and_miss_per_file`, `test_cli_directory_misses_are_reported`, `test_cli_verbose_option_is_rejected`, `test_cli_directory_summary_counts_multiple_hits`, `test_cli_directory_per_play_summary`, `test_cli_recursive_finds_in_subdir`, `test_cli_missing_path_exit_2`, `test_cli_malformed_pln_exit_2`; `test_cli_requires_args` keeps passing.
- `test_gameplan_replace_play.py`: the `split_args` tests go (`test_split_one_name_is_usage_error`, `test_split_play_and_replacement`, `test_split_play_and_folder_only_is_usage_error`, `test_split_last_existing_folder_is_path`, `test_split_last_existing_file_is_path`, `test_split_path_looking_name_is_path`, `test_split_plain_names_are_replacements`, `test_split_folder_named_like_play_is_the_folder`); `test_split_drops_repeated_replacements` becomes a CLI test.
- `test_gameplan_replace_play.py`: `test_cli_one_name_is_usage_error` asserts `"Missing argument 'REPLACEMENT...'." in result.stderr`.
- `test_gameplan_replace_play.py`: `test_cli_path_left_out_uses_current_folder` becomes the default-scope test.
- `test_gameplan_replace_play.py`: the path moves from the last argument to `--path` in `test_cli_every_replacement_must_be_in_pool`, `test_cli_no_quiet_option`, `test_cli_replacement_not_in_pool_exit_2`, `test_cli_replacement_case_insensitive`, `test_cli_single_file_replaces_normal`, `test_cli_play_in_several_slots_not_replaced`, `test_cli_output_uses_game_names_without_league_labels`, `test_cli_single_file_replaces_special`, `test_cli_single_file_target_case_insensitive`, `test_cli_single_file_miss_exit_1`, `test_cli_backup_used_when_first_already_in_plan`, `test_cli_backup_used_when_first_breaks_rule`, `test_cli_rollout_cap_uses_the_play_file`, `test_cli_cross_category_swap_within_limits`, `test_cli_cross_category_swap_leaves_losing_category_short`, `test_cli_no_valid_replacement_single_file`, `test_cli_directory_counts_not_replaced`, `test_cli_refused_later_replacement_names_it`, `test_cli_wildcard_path_works_like_a_folder`, `test_cli_bad_rules_file_exit_2`, `test_writes_no_backup`, `test_no_backup_option_removed`, `test_cli_directory_updates_matching_files`, `test_cli_directory_leaves_other_side_untouched`, `test_cli_directory_no_hits_exit_1`, `test_cli_recursive_replaces_in_subdir`, `test_cli_replacement_special_for_normal_fails`, `test_cli_replacement_wrong_side_fails`, `test_cli_replacement_wrong_special_category_fails`, `test_cli_missing_path_exit_2`, `test_cli_malformed_pln_exit_2`, `test_cli_invalid_play_path_exit_2`, `test_cli_play_path_option_removed`, `test_cli_continues_past_failed_file`; `test_cli_requires_args` and the `pick_replacement`, `replace_in_gameplan` and `format_replacement_lines` tests keep passing.
- `test_gameplan_set_specials.py`: `test_requires_path` becomes "requires INPUT_FILE".
- `test_gameplan_set_specials.py`: `test_requires_play_list` becomes the `Not a valid play list.` test (a `.pln` as the only argument, exit 2, the game plan untouched).
- `test_gameplan_set_specials.py`: the game plan moves from the first argument to `--path` in `test_no_quiet_option`, `test_removed_options_rejected`, `test_writes_special_from_file`, `test_a_list_saved_with_a_bom_reads_its_first_play`, `test_merge_preserves_other_categories`, `test_writes_no_backup`, `test_skips_and_strips_comments`, `test_dash_reads_from_console`, `test_dash_input_errors_name_no_file`, `test_gameplan_problem_names_the_gameplan_and_the_list_line`, `test_gameplan_problem_from_the_console`, `test_rejects_normal_play`, `test_rejects_duplicate_play`, `test_as_many_plays_as_slots_pass_the_count`, `test_too_many_plays_rejected`, `test_missing_target`, `test_missing_play_list`, `test_invalid_play_path`, `test_directory_top_level_only`, `test_directory_recursive`, `test_offense_input_skips_defense_files`, `test_continues_past_failed_file`.
- `test_gameplan_set_normals.py`: `test_quiet_still_updates` becomes the "-q is rejected" test (exit 2, Click's unknown-option text); the rest keeps passing.
- `test_gameplan_list.py`: `test_normals_help_uses_lowercase_names` and `test_specials_help_uses_lowercase_names` change with cli-help.md's style (that plan's change); the rest keeps passing.
- `test_gameplan_check.py`: gains the name, `--team` and hint tests above.
- `test_cli_root.py`: `LEAGUE_COMMANDS` and `_unknown_league_args` as above.
- `test_cli_root.py`: after cli-help.md rewrites its rows, the `test_help_uses_lowercase_names` rows change: `gameplan find-play` shown `PLAY...`, `--path PATH`, `--team NAME`, `--league NAME`, hidden `PLAYS`, `[PATH]`; `gameplan replace-play` shown `PLAY REPLACEMENT...`, `--path PATH`, `--team NAME`, hidden `PATH]`; `gameplan set-specials` shown `INPUT_FILE`, `--path PATH`, `--team NAME`, hidden `PATH INPUT_FILE`; `gameplan check`, `set-normals` and `list-normals` add `--team NAME` to their shown lists.
- `test_cli_root.py`: the `test_usage_lists_each_option` rows for `gameplan find-play` (`Usage: athc gameplan find-play [OPTIONS] PLAY...`) and `gameplan list-normals` (`Usage: athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT_FILE]`) keep cli-help.md's values and wait on cli-help.md alone.
- `test_check_ppp.py`: its `league`, `lg2_league`, `team` and `pnfl_league` fixtures and the `.lg2`/`.lge` builders move to `tests/integration/conftest.py`; `league` becomes `build_league`, the others keep their names, and its tests take the new name.
- `tests/integration/README.md`: the rows of every test named above.

## Docs and meta

- `docs/gameplan/README.md`: the CLI section rewritten around the scope rule, the four names, `--path`, `--team`, the sources and the lines above; the `set-normals` row loses `-q` and the section says `> nul` hides the `OK` lines; a sentence pointing at check-ppp for pairs.
- `docs/gameplan/ARCHITECTURE.md`: the check, find-play, set-normals / set-specials and replace-play sections (arguments, `--path`, the names, no `split_args`, `read_play_list`), the layout (`_team.py` shared); the exit-code paragraph unchanged.
- `docs/design/architecture.md`: CLI section: `--team NAME` as a shared decorator beside `--league`, on every command that resolves a team's files; the `--league` command list gains `find-play` and `list-specials`; Config: `team` and `ppp_path` are shared by check-ppp, gameplan and profile.
- check-ppp-cli.md amendments (the one list; profile-cli.md and convert-pdb-cli.md point here):
  - its team resolver, league-file loader and sources move to `src/athc/cli/_team.py`, with `team_files(team, kind)` returning the four `(name, file)` pairs, a shared file repeated (check-ppp drops repeats by resolved path), `locate(...) -> Located(path, exists, source)`, the key constants `TEAM_KEY` and `PPP_PATH_KEY`, and `LEAGUE_PATH_KEY` imported from `src/athc/config.py`;
  - its `--team` becomes the shared `team_option("Team to check")` in `src/athc/cli/__init__.py`;
  - its fixtures move to `tests/integration/conftest.py` as `build_league`, `lg2_league`, `pnfl_league` and `team()`;
  - `LgeFile.teams` exists since dade898, so that code item is done; `LeagueConfig.string` stays to add;
  - its own `Got unexpected extra argument` raise and its row for that line go once `src/athc/cli/__init__.py` adds the period for every command;
  - its "No path" line becomes `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass the folder.`;
  - `team` is read from `league.toml` before the league files, so `test_dir_first_setup_error_stops_the_run` sees the "Team is not set" error first instead of "League files folder is not set";
  - its help block becomes the cli-help.md form (`[OPTIONS] [PATH]...`, a PATH help line, `--team NAME`, the shared `-r` and `--league` texts);
  - it owns the shipped `league.toml` comment text for `path` and `team`, quoted in Settings here.
- cli-help.md changes:
  - find-play's `--path` default becomes your team's game plans and takes a wildcard and the four names; the command gains `--team` and `--league`;
  - the wildcard rule lists `--path` in `find-play`, `replace-play` and `set-specials` instead of their PATH, drops "find-play --path refuses them", and its wildcard CLI tests become six;
  - replace-play's usage is `[OPTIONS] PLAY REPLACEMENT...` and it gains `--team`;
  - set-specials' usage is `[OPTIONS] INPUT_FILE` and it gains `--team`;
  - check's PATH help gains the four names and the command `--team`;
  - list-normals, list-specials and set-normals get the `GAME_PLAN` help line above and `--team`, and list-specials `--league`;
  - set-normals loses `-q`;
  - the `GAME_PLAN` placeholder entry reads "one .pln file, or one of your team's four names (off1, def1, off2, def2)";
  - `--team NAME` is cli-help.md's shared `--team` (per-command head, shared tail).
- `config/release/docs/COMMANDS.txt`: sections 1 to 7 rewritten (examples above; the `-q` example gone, `> nul` in its place; section 1 gains the names and the check-ppp sentence).
- `config/release/docs/README.txt`: FIRST-TIME SETUP names `team` beside `path` for check-ppp and the gameplan commands.
- `config/release/athc.ini`: the header comment names `team` beside `path` likewise.
- `CHANGELOG.md` (athc section, top): `gameplan: find-play, replace-play and set-specials work on your team's game plans by default; --path points them at a file, a folder, a wildcard or one game plan`.
- `CHANGELOG.md`: `gameplan: every subcommand takes off1, def1, off2 or def2 for one of your team's game plans`.
- `CHANGELOG.md`: `gameplan: set-normals dropped -q; redirect with > nul instead`.
- `CHANGELOG.md`: `gameplan: find-play's --path takes a wildcard`.
- `CHANGELOG.md`: `gameplan: a play list that cannot be read is one FAIL line (Not a valid play list.), not an unexpected error`.
- `STATUS.md`: the gameplan section gains the scope rule, the four names and `--team`.
- `STATUS.md`: the Decisions list gains "No athc command has a quiet flag" and "The team's game plans are the default scope of the gameplan batch commands; check keeps the current folder".
- `STATUS.md`: the "Wildcards stay, expanded by athc" entry loses "`find-play` refuses one".
- `TODO.md`: the `set-normals -q` item is ticked when this lands; the check-ppp item's keys serve this plan too; the `replace-play` pairs item stays open, with the file-option shape and the both-positionals-optional note above.
- `tests/integration/README.md`: the rows named in Tests.
