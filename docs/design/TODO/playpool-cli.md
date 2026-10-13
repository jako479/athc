# playpool CLI plan

**Goal:** `athc playpool check` with nothing after it checks the league's play pool where `league.toml` puts it (`play_path`); a folder points it at a folder of plays instead. `athc playpool show PLAY...` looks plays up in that pool and tells a coach each one's side, category, attributes (from the play file; `screen` from a `Screens` folder) and file, the way the gameplan commands see them. `athc playpool list [CATEGORY]...` lists a category's plays with the same attributes, one line each, in the shape `set-normals` reads. Nothing else joins the group.

**Status:** proposal, 2026-10-13, written against main at ddae7a1 (play attributes from the play file; `playpool.toml` gone); nothing changed yet. Depends on cli-help.md landing first. Every choice is decided below, with its reason next to it. Reviewed for codebase fit and coach workflows; the findings are folded in.

## 1. Today

- `athc playpool check [play_dir]` (`src/athc/cli/playpool/check.py`, unchanged by ddae7a1): one optional folder. With none, the league's `play_path` from `league.toml`; a league that cannot be resolved is an error, and a league without `play_path` is `FAIL <league.toml>: No play_path for the league. Set play_path in this file.` (the command's own raise). With a folder, no league is needed, but a league named with `--league` must exist, and a league that resolves (named or configured) lends its category labels to the folder names; with no league, no folder name means a category. A broken `league.toml` fails the run even with a folder. After the league resolves (`check.py` lines 41 to 54), a given folder is checked for being there and being a folder (lines 56 to 59) before the pool is read.
- It reads the pool with `read_play_pool(play_dir, labels=labels)`, and the pool's issues are its findings: a play in a folder that contradicts its file, a duplicate name, an invalid or unreadable file. Since ddae7a1 there is no rules file for the pool: `playpool.toml`, `src/athc/playpool/rules.py` and the check of the names a rules file listed are gone, so `check` and every other pool consumer report the same set of problems with the same words (`docs/playpool/README.md`: "the same things pool loading checks for every other command, with the same messages", now true).
- The issues print one per line as results on stdout, then a blank line and the tally `<n> play(s) checked in '<folder>', <n> issue(s)`. Exit 0 clean, 1 issues, 2 error. A folder that does not exist is `FAIL <folder>: The system cannot find the path specified.` and a file in its place `FAIL <folder>: The directory name is invalid.`, in both modes, without the `Set play_path in <league.toml>.` hint that `play_dir()` in `src/athc/config.py` gives every other pool consumer through `build_pool`.
- The group (`src/athc/cli/playpool/__init__.py`) has `check` only. Usage today: `athc playpool check [-h] [--league name] [play_dir]`.
- The library (`src/athc/playpool/`, rewritten by ddae7a1): `read_play_pool(root_dir, *, labels=None)` walks `<root>/**/*.ply` in sorted path order, so a pool is always a whole tree; `PlayPool` holds the three side lists, `issues` and `find_by_name` (any case; a repeated name resolves to the last play loaded). Each `Play` carries `name`, `file_path`, `category` and `play_file`; an `OffensivePlay` adds `screen` (from a `Screens` folder, the one attribute the bytes cannot carry), `rollout`, `qb_run` and `pass_logic` (`Timed` or `Check Receivers`), a `DefensivePlay` adds `defensive_front` (`3-4`, `4-3`, `2-DL` or none), those four read from the play file's players and their logic (`docs/playpool/README.md`, "How athc reads a play": a rollout is a QB who gets beyond 100 units outside the outermost offensive lineman before he passes; a timed pass is a QB who throws a Timed pass; a QB run is a QB who runs the ball; 3-4 and 4-3 are Run Left, Middle and Right defenses with 3 or 4 down linemen; 2-DL a pass defense with 2). `PassLogic` lives in `athc.playpool`, `DefensiveFront` in `athc.fbpro98_play`.
- The consumers: `gameplan check`, `set-normals`, `set-specials`, `replace-play`, `check-ppp` and `convert-pdb` all load the pool from `play_path`, look plays up with `find_by_name` and read the play attributes. The gameplan commands and `check-ppp` print every pool issue as a `WARN` line before their own work (`build_pool(play_path, labels, league_file)` in `src/athc/cli/gameplan/_common.py`: `play_dir()` for the hint, `read_play_pool`, one `console.warn` per issue; `docs/gameplan/README.md`: "`WARN` per play-pool issue"); `convert-pdb` gathers them as notices (`src/athc/pdbtoexcel/workbook_creator.py`) and prints them as `WARN` lines after the conversion (`src/athc/cli/convert_pdb.py`, `result.warnings`).
- Nothing looks a play up or lists plays for a coach. The attributes come from the players' logic inside the play file (the QB's spot and commands, the count of down linemen), and "a play's folder doesn't count, except `Screens`" (the README), so no name or folder tells a coach whether a play is a rollout, a timed pass, a QB run or a 2-DL; the layout's category folders answer the category only. The cap violations of `gameplan check` print counts only, under the game's category name (`Offensive category 'Pass Short Right' has 3 of 5 timed passes; allows at most 1/2.`, `tests/integration/expected/offense.report.txt`; the rules keep `member.long` as a category's name, `src/athc/gameplan/rules.py`; the same shape for `QB runs`, `rollouts` and the defense `2-DL plays`, `src/athc/gameplan/validators.py`), never the plays. `gameplan list-normals --sort category` groups a game plan's plays by the categories in the `.pln` bytes, with no attribute. `replace-play` says only `Replacement play 'X' not found in the play pool.` `convert-pdb`'s Type column says `QB run` and the front (CHANGELOG.md) but needs a stats `.pdb`. A play list for `set-normals` is "one play name per line; `::` comment lines and ` ::` trailers are ignored" (`parse_play_list` in `src/athc/cli/gameplan/_common.py`), and `list-normals --sort category` writes `:: <label>` header lines in that shape.
- The real pool today (the dev PNFL's `play_path`, `E:\SIERRA\FbPro98\PNFL`, counted 2026-10-13): `Offense` 2579 plays, `Defense` 2267, `Special` 309, `TestPlays` 4, 5159 in all; none at the root and none in the season folders `2043` to `2049`, which hold the teams' plans folders the `.lg2` names (`PNFL\2049\Plans\<Team>`). The pool root is the league's folder under the game folder, and a coach's plans folder sits inside it with no play in it. With 2579 offense plays over 17 categories, a category holds about 150 plays.

## 2. Who runs it, for what

| # | Who | Wants to | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach | see why every gameplan command starts with `WARN` lines about the pool | `athc playpool check` | each issue once, on stdout, then the tally; exit 1 |
| 2 | Coach | know the league's pool is clean before building game plans | `athc playpool check` | `<n> play(s) checked in '<play_path>', 0 issue(s)`; exit 0 |
| 3 | Coach | check plays they made, before copying them into the pool | in that folder, `athc playpool check .`; or `athc playpool check newplays` | invalid files; duplicate names within the folder; wrong-folder plays when the folder uses the league's layout |
| 4 | Coach | know whether a new play's name is already taken in the pool | `athc playpool show NewPlay` | `NewPlay: not in the play pool`, exit 1, so the name is free; else the play that has it |
| 5 | Coach | check new plays against the whole pool after copying them in | `athc playpool check` | duplicate names across the pool |
| 6 | Coach | check a copy of the pool (a backup, another drive) | `athc playpool check D:\backup\PNFL` | that folder's plays |
| 7 | Coach | know a play's category and whether the game counts it as a timed pass, a rollout or a QB run, before putting it in a plan | `athc playpool show AF1AwagR` | one headline: side, category, attributes; its file under it |
| 8 | Coach | see which plays made `gameplan check` flag a cap (`3 of 5 timed passes`) | the cap line names them (section 8); `athc playpool show` with those names shows each one's attributes | the plays, and what each is |
| 9 | Coach | find a Pass Short Right play that is not a timed pass, to swap in with `replace-play` | `athc playpool list PSR`, or `athc playpool list PSR \| findstr /v timed` | the category's plays, one line each with their attributes; with `findstr /v`, only those without `timed` |
| 10 | Coach | pick a category's plays for a new game plan's normals | `athc playpool list PSL PSM PSR > picks.txt`, trim the file to the 64 names, then `athc gameplan set-normals GP.pln picks.txt` | a play list `set-normals` reads as it is: `::` headers and ` ::` trailers are ignored |
| 11 | Coach | see the whole pool as the game sees it, side by side with its attributes | `athc playpool list > pool.txt` | every play under its category header |
| 12 | Coach | the pool of another league | rows 1, 2, 4, 5 and 7 to 11 with `--league PCFL`; with a FOLDER (rows 3 and 6) `--league` names the category folders only | |
| 13 | Coach | from a script | the exit code; `> out.txt` keeps the results, `2> errors.txt` the problem lines | |

## 3. What other tools do

- **Config names the default path, an argument wins, `.` is "here".** ruff's `check` lists its files argument as `[default: .]` ("Usage: ruff check [OPTIONS] [FILES]..."); pytest, mypy and pyright do the same (check-ppp-cli.md section 3); check-ppp-cli.md decision 3 fixes athc's rule: no path means the configured default, `.` the current folder, an explicit path overrides both.
- **A checker walks the whole tree.** ruff: "Ruff will automatically discover all Python files in that path"; athc's `read_play_pool` walks `**/*.ply`.
- **A checker of one thing takes a path to it.** helm lint: "helm lint PATH [flags]"; "This command takes a path to a chart and runs a series of tests to verify that the chart is well-formed"; its findings are "[ERROR]" and "[WARNING]" messages.
- **A lookup verb beside the checker, taking one or more names.** pip: "Show information about one or more installed packages." (`pip show [options] <package> ...`); docker: "Display detailed information on one or more images" (`docker image inspect [OPTIONS] IMAGE [IMAGE...]`); winget's `show` "displays details for the specified application" (`winget show [[-q] <query>] [<options>]`). In-house: `gameplan find-play` prints its hits and its `<file>: '<play>' not found` lines through `console.result` and exits 1 when no play was found anywhere; architecture.md reserves code 1 for findings, "a play found nowhere" among them.
- **A list verb, narrowed by an optional argument.** docker: "List images", `docker image ls [OPTIONS] [REPOSITORY[:TAG]]`, where the optional argument "restricts the list to images" of that repository; pip: "List installed packages, including editables." (`pip list [options]`). Windows narrows a listing further with findstr ("Searches for patterns of text in files."; `/v` "Prints only lines that don't contain a match."; `/i` "Ignores the case of the characters when searching for the string."). In-house: `gameplan list-normals --sort category` prints `:: <label>` headers over the names, sorted without case under `--sort name`, and `set-normals` reads that shape back (`parse_play_list` drops `::` lines and ` ::` trailers).
- **Standard shape and codes.** clig.dev: "Make the default the right thing for most users"; "Be consistent across subcommands"; "Use standard names for flags, if there is a standard"; "Return zero exit code on success, non-zero on failure"; and, on scope, "Rather than stuff more and more features into those programs", build small parts that work together.
- **Click.** An argument with no explicit metavar gets its placeholder from its name: `[FOLDER]` when optional, `PLAY...` for a required list, `[CATEGORY]...` for an optional one (`Argument.make_metavar`, `click/core.py`); an explicit metavar prints verbatim in the usage line and in the error hint (`get_error_hint`), which is why today's `check.py` writes `metavar="[play_dir]"` by hand. `click.Path(exists=True, file_okay=False)` words a missing folder `Directory 'x' does not exist.` and a file `Directory 'x' is a file.` (`click/types.py`), not Windows' words. A second value for a one-value argument is Click's `Got unexpected extra argument (<value>)` (`click/core.py`); today the root shows it as Click wrote it (`error.show()`, `src/athc/cli/__init__.py`), and the period arrives with cli-help.md rule 23, added once where usage errors are rendered. A required argument left out is `Missing argument 'PLAY...'.` (`MissingParameter.format_message`, `click/exceptions.py`). A `click.BadParameter(..., param_hint="'CATEGORY'")` renders `Error: Invalid value for 'CATEGORY': ...` (cli-help.md rule 22's callback shape).
- **In-house.** `build_pool` prints every pool issue as `WARN <issue>` (an issue names the play's path itself where one is to blame) for `gameplan check`, `set-normals`, `set-specials`, `replace-play` and `check-ppp`; `set-normals` loads its config with `load_config(league, rule_files=())` ("no gameplan rules needed"); `playpool check` prints the pool's issues as results; `check-ppp` imports `build_pool` across groups already; `collect_files` turns a folder with nothing to do into a `WARN <dir>: No .pln files.` and code 0. The project's codes: 0 done, 1 findings, 2 error; a batch exits with the worst outcome (`docs/design/architecture.md`).

## 4. Decisions

1. **Three commands: `check`, `show` and `list`.** The commands that use the pool need one thing from it, a play by name with its side, category and attributes (`find_by_name`), and nothing lets a coach ask the same questions: since ddae7a1 the attributes are read from the players' logic inside the file, which no name or folder shows (section 1), `gameplan check`'s cap lines count plays without naming them, `list-normals` shows no attribute, and `replace-play` only says a name is not in the pool. `show` answers for named plays, from the pool the gameplan commands load, through the same code, and tells whether a name is taken (rows 4, 7 and 8); pip, docker and winget put the same verb beside their other commands. `list` answers for a category: the layout's folders answer the category only, so a coach who must swap a timed Pass Short Right for one that is not (row 9) has about 150 plays to look through with nothing to tell them apart; `list PSR` prints them with their attributes, and findstr narrows the lines (docker's `image ls` narrows by an argument the same way). The two verbs stay apart because a play name and a category name in one argument would be the shape cli-help.md removed from `find-play`, and pip and docker split them too (`show` / `list`, `inspect` / `ls`). TODO.md's two playpool ideas (2.0.0) settle the same way: "check that each play's name matches its play category" is not covered, since `check` compares a play's folder with its file (`_folder_info` and `_warnings` in `src/athc/playpool/reader.py`), never its name; it would be a new `check` finding; "count plays by file name type" (STATUS.md: "Open: count plays by file name type") is a count over the whole pool, a report none of the three verbs gives, and stays the 2.0.0 idea it is, a verb of its own if it comes, changing nothing in `check`, `show` or `list`. clig.dev: small parts that work together, not more features in one program.
2. **Usage `athc playpool check [OPTIONS] [FOLDER]`:** one optional folder, positional as in `gameplan check`, `profile check` and `check-ppp` (check-ppp-cli.md decision 16), named `FOLDER` because only a folder is accepted (cli-help.md rule 3). The argument carries no explicit metavar (cli-help.md rule 22): Click derives `[FOLDER]` from the parameter name, and an explicit one would print verbatim in the usage line and the error hint (section 3).
3. **No FOLDER means the league's pool; `.` the current folder; a FOLDER overrides**, the path rule of cli-help.md rule 16 and check-ppp-cli.md decision 3 (no path means the configured default, `.` the current folder, an explicit path overrides both; rule 16 names the league's play pool as such a default). The configured place, not the current folder, is the default because the pool is one fixed place per league that every pool consumer reads from `play_path`, and a coach's current folder is a plans folder, which holds game plans and no plays (section 1: no season folder holds a `.ply`); `gameplan check` and `profile check` default to the current folder because game plans and profiles live where the coach works. The coach's own play folder and the league's pool are told apart by the argument: nothing after `check` is the league's pool; anything after it (`.` included) is that folder. No team setting is read: plays are league-wide, so the default-team keys `team` and `ppp_path` of check-ppp-cli.md (decisions 4 and 15) have no part here.
4. **One folder, one check.** With no rules file left for the pool, the league's pool and a given folder are checked for the same things with the same code, so `check` never needs to recognize a FOLDER as the pool: `athc playpool check E:\SIERRA\FbPro98\PNFL` (the README's own example) and `athc playpool check` read the same folder and print the same findings. The two modes differ only in where the folder comes from and in the line for a configured folder that is missing (decision 7). The findings stay the pool's issues, nothing more: the other consumers show exactly these as `WARN` lines, and the README's promise of "the same things, with the same messages" holds as the code stands.
5. **No `-r`.** A pool is a tree by nature and `read_play_pool` always walks it (ruff discovers recursively too). The `-r` rule of check-ppp-cli.md decision 9, each folder of the tree on its own, would hide duplicate names across folders, which is the check's point. A league without the layout (a flat folder) is still one tree.
6. **`--league NAME`, the shared option with cli-help.md rule 10's text, always with a value (rule 19).** As today: a FOLDER needs no league; a league named with `--league` must exist even with a FOLDER (rule 19: a named league must exist, and its files are read only when the run needs them; `check.py` lines 41 to 45); a league that resolves lends its category labels to the folder names; a broken `league.toml` fails the run even with a FOLDER; with no league, no folder name means a category. A FOLDER run never reads `play_path`, as today.
7. **The configured pool missing on disk gets the hint, and the missing key names the way out.** With no FOLDER, a `play_path` that is not a folder is `play_dir()`'s line, `FAIL <play_path>: The system cannot find the path specified. Set play_path in <league.toml>.` (`The directory name is invalid.` for a file), as every other pool consumer says it. A league without `play_path` says `FAIL <league.toml>: No play_path for the league. Set play_path in this file, or pass the folder.`: cli-help.md rule 21's shape, a "No ... for the league" line naming the command's own path form, so a first-run coach sees the way out on the first line; `check.py` raises this line itself, so no other command's line changes. A given FOLDER keeps today's plain phrases: the user typed it, so a hint would be wrong.
8. **Argument errors stay athc's words, and come before the pool.** A given FOLDER is checked for being there and being a folder after the league resolves and before anything of the pool is read, as today, with Windows' phrases through athc's own checks instead of `click.Path(exists=True, file_okay=False)`, whose texts are not Windows' (section 3). A second FOLDER is Click's usage error, `Got unexpected extra argument (<folder>).`, with the period cli-help.md rule 23 adds once for every command. FOLDER is not a wildcard argument (cli-help.md rule 15): once Click's expansion is off, `plays*` is a folder that does not exist.
9. **`check`'s lines stay today's:** issues one per line, a blank line, the tally `<n> play(s) checked in '<folder>', <n> issue(s)`; the folder prints as typed (`'.'` for `.`), as `gameplan check` prints its paths. No per-play `OK` lines: the real pool has over five thousand plays.
10. **Usage `athc playpool show [OPTIONS] PLAY...`:** one or more play names, matched without case as every pool consumer matches them (`find_by_name`), in argument order; the argument `play` carries no metavar (cli-help.md rule 22), so Click derives `PLAY...` and refuses none. No folder argument: names are looked up where the gameplan commands resolve them, the league's pool; a trailing optional folder after a list of names is the shape cli-help.md removed from `find-play`; a folder of new plays is `check`'s job (row 3), and a name's availability is answered against the pool (row 4).
11. **`show` and `list` load the pool exactly as the gameplan commands do:** `load_config(league, rule_files=())` from `athc.gameplan.config` (as `set-normals` does) and `build_pool(config.play_path, config.categories, config.league_file)`, so the league, `play_path` and its hint behave as in `set-normals`, and the pool's issues print as `WARN` lines first, as there. The answer is then what `set-normals` and `replace-play` would make of the names; a repeated name shows the play the pool resolves, the last loaded, and `check` is where the duplicate is reported.
12. **`show`'s lines:** per PLAY, a headline `<name>: <side>, <category>[, <attributes>]` through `console.result` (logged, as `find-play` prints its hits and as a finding's headline prints, so the run log holds what was asked and answered) and, indented under it, the play's file through `console.print`, both on stdout (the headline-and-detail shape of `gameplan check`); `<name>` in the pool's spelling; `<side>` is `offense` or `defense`, or `special teams` for a special-teams play; `<category>` is the league's label with the game name in parentheses (`PSL (Pass Short Left)`), or the game name alone when the league has no label for it (special teams always); the attributes are the record's: from the play file, for an offense pass play `timed` or `check receivers` (`PassLogic`, always one of the two) then `rollout` when set, for an offense run play `QB run` when set, for a defense play `3-4 front`, `4-3 front` or `2-DL front` when the file gives one (`DefensiveFront`; a Run Left, Middle or Right defense with 3 or 4 down linemen, a pass defense with 2; nothing otherwise); and from the folder, `screen` for an offense play under `Screens`; a special-teams play has none. A name not in the pool is the result line `<name>: not in the play pool` (`find-play`'s shape), and the run exits 1 when any PLAY is missing, the batch rule (worst outcome) rather than `find-play`'s grep rule, since a lookup of named items fails for each name a coach asked about. No tally: a lookup of named items is not a folder run.
13. **Usage `athc playpool list [OPTIONS] [CATEGORY]...`:** zero or more categories, each the league's label or the game's name, matched without case (`psr`, `PSR`, `"pass short right"`), in argument order; no CATEGORY means every category (pip and docker list everything by default; docker's optional argument narrows). The argument `category` carries no metavar (cli-help.md rule 22), so Click derives `[CATEGORY]...`. A game name both sides use (Run Left, Run Middle, Run Right, Goal Line Run, Goal Line Pass) lists the offense category, then the defense one; a label is one side's. A name that is no category is `Error: Invalid value for 'CATEGORY': no category named 'PSX'. Use the league's name or the game's name, like "Pass Short Right".`, a `click.BadParameter` with `param_hint="'CATEGORY'"` raised after the league loads, since the labels come from it (rule 22's shape; athc's part continues Click's sentence in lowercase and ends with a period, architecture.md). No folder argument, for decision 10's reasons.
14. **`list`'s lines are a play list `set-normals` reads.** Per category, a header `:: <label> (<game name>)` (the game name alone when the league has no label; the `::` header `list-normals --sort category` writes), then one line per play, names sorted without case (`list-normals --sort name`'s order): `<name> :: <attributes>` with the attribute words of decision 12, or the name alone when the play has none (special teams; a defense with no front). The ` ::` trailer and the `::` headers are what `parse_play_list` drops, so `athc playpool list PSL > picks.txt` is a file `set-normals` takes once the coach trims it (row 10), and `findstr` narrows the lines by an attribute word (row 9). With no CATEGORY the categories come in the game's order (the enums' order: offense, defense, special teams kicking, then receiving), empty ones skipped, as `list-normals` skips an empty category; a CATEGORY given that holds no play is `WARN No PSR plays in the play pool.` and a pool with no play at all `WARN No plays in the play pool.`, both code 0 (`collect_files`'s rule for a folder with nothing to do). All lines are results through `console.print` (the command's product, as `list-normals` prints to the console); no tally, so the output stays a play list. Codes: 0 listed (warnings included), 2 error (league, `play_path`, pool, an unknown category); never 1, as `list-normals` never (a list is not a finder). No file argument: the product has no input file to sit beside (cli-help.md rule 28's derived output does not apply), so the console and `>` serve, as for pip and docker.
15. **Help text is cli-help.md's:** the command summary "Check the play pool for problems.", the FOLDER help "Play pool folder (default: the league's play_path)." and the description below in plain words, one idea per sentence; `show`, `list` and the group summary are new entries (section 5). Depends on cli-help.md landing first (its rule 25); the blocks below are that form.

## 5. The command

### `athc playpool` (group)

```
Usage: athc playpool [OPTIONS] COMMAND [ARGS]...

  Check the play pool, show and list its plays (.ply).

Options:
  -h, --help  Show this message and exit.

Commands:
  check  Check the play pool for problems.
  list   List the play pool's plays by category.
  show   Show a play's category and attributes.
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
| none | the league's `play_path` | required, with `play_path` | `play_dir()`'s line with the `Set play_path` hint |
| a folder, `.` included | that folder, the whole tree | optional; one named must exist; one that resolves names the category folders | Windows' path phrase, no hint |

- **Order:** the pool's issues in the reader's order (the plays' sorted path order), then the blank line and the tally. A clean run prints the tally alone.
- **Argument errors, checked after the league resolves and before anything of the pool is read:** a FOLDER that does not exist, `FAIL <folder>: The system cannot find the path specified.`; a file, `FAIL <folder>: The directory name is invalid.`; a second FOLDER, Click's usage text ending `Error: Got unexpected extra argument (<folder>).`; nothing is checked in any of these.

### `athc playpool show`

```
Usage: athc playpool show [OPTIONS] PLAY...

  Show a play's category and attributes.

  Looks each PLAY up in the league's play pool, as the gameplan commands do
  (any case). Shows its side, its category, what the play file makes it
  (timed pass or check receivers, rollout, QB run, defensive front), screen
  when it sits in a Screens folder, and its file.

Positional arguments:
  PLAY  Play name (any case).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc playpool show AF1AwagR
    athc playpool show AF1AwagR GP5Xtop1
```

Output, in argument order (the values illustrate the shape):

```
AF1AwagR: offense, PSL (Pass Short Left), check receivers, rollout
  E:\SIERRA\FbPro98\PNFL\Offense\PSL\AF1AwagR.ply
CC31rl5m: defense, RunLeft (Run Left), 3-4 front
  E:\SIERRA\FbPro98\PNFL\Defense\34RunLeft\CC31rl5m.ply
KO1: special teams, Kickoff
  E:\SIERRA\FbPro98\PNFL\Special\KO1.ply
NewPlay: not in the play pool
```

- **Before the results:** the pool's issues as `WARN` lines on stderr, as `set-normals` prints them.
- **Argument errors:** no PLAY is Click's usage text ending `Error: Missing argument 'PLAY...'.`; nothing is read.

### `athc playpool list`

```
Usage: athc playpool list [OPTIONS] [CATEGORY]...

  List the play pool's plays by category.

  Lists every play of each CATEGORY, one line each: the name, then :: and
  what the play file makes it (timed pass or check receivers, rollout, QB
  run, defensive front), with screen for a Screens folder. The output is a
  play list for gameplan set-normals. A category is the league's name or the
  game's, any case.

Positional arguments:
  CATEGORY  Category to list, the league's name or the game's (default:
            every category).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc playpool list PSR
    athc playpool list PSL PSM PSR > picks.txt
```

Output (the values illustrate the shape):

```
:: PSR (Pass Short Right)
AF3ArshZ :: timed, rollout
GP3Xcrs1 :: check receivers
GP5Xtop1 :: timed
:: RunLeft (Run Left)
CC31rl5m :: 3-4 front
DD40rlZ
:: Kickoff
KO1
```

- **Before the results:** the pool's issues as `WARN` lines on stderr, as `set-normals` prints them.
- **Order:** categories in argument order, or with no CATEGORY in the game's order (offense, defense, special teams kicking, then receiving), empty ones skipped; names sorted without case within a category.
- **Argument errors:** a name that is no category, `Error: Invalid value for 'CATEGORY': no category named 'PSX'. Use the league's name or the game's name, like "Pass Short Right".`, exit 2, nothing listed. There is no second-argument error: any number of categories is taken.

### cli-help.md changes

- playpool (group): the summary becomes "Check the play pool, show and list its plays (.ply)." (54 characters, rule 6), since the group gains two verbs.
- `playpool check`: no change; the usage, summary and FOLDER help are the ones cli-help.md lists, and the description above is the plain-words rewrite it asks for.
- `playpool show`, new: usage `[OPTIONS] PLAY...`; PLAY help "Play name (any case)."; summary "Show a play's category and attributes."; the description above; `--league` with rule 10's text; the two examples.
- `playpool list`, new: usage `[OPTIONS] [CATEGORY]...`; CATEGORY help "Category to list, the league's name or the game's (default: every category)."; summary "List the play pool's plays by category."; the description above; `--league` with rule 10's text; the two examples. `CATEGORY` joins rule 3's names: a play category, by the league's label or the game's name.

## 6. Settings

In `league.toml`, under `[league]`, as shipped (the config plan owns the wording of this comment):

```toml
[league]
# REQUIRED for gameplan/profile/convert-pdb -- your FbPro98 league plays folder.
play_path = 'C:\SIERRA\FBPRO98\PNFL'
```

- `play_path`: the pool. `check` reads it with no FOLDER only; `show` and `list` always read it. A relative value resolves against the league folder (`LeagueConfig.path`).
- `[categories.offense]` / `[categories.defense]`: the folder names that mean a category, the labels `show` and `list` print, and the names `list` accepts.
- `--league NAME` picks the league; else `[athc] league` in `athc.ini`.
- No new keys, and no rules file for the pool: the attributes come from the play files. `team` and `ppp_path` are never read.

## 7. Lines and exit codes

New or changed lines, in the project's wording; everything else prints as today.

| When | Line | Code |
|---|---|---|
| `check`, no FOLDER, `play_path` missing on disk | `FAIL <play_path>: The system cannot find the path specified. Set play_path in <league.toml>.` | 2 |
| `check`, no FOLDER, `play_path` is a file | `FAIL <play_path>: The directory name is invalid. Set play_path in <league.toml>.` | 2 |
| `check`, no FOLDER, no `play_path` in `league.toml` | `FAIL <league.toml>: No play_path for the league. Set play_path in this file, or pass the folder.` | 2 |
| `check`, a second FOLDER | Click's usage text, `Error: Got unexpected extra argument (<folder>).` (today's line; the period arrives with cli-help.md rule 23) | 2 |
| `check`, the tally | `<n> play(s) checked in '<folder>', <n> issue(s)`, unchanged | |
| `show`, a play found | `<name>: offense, PSL (Pass Short Left), check receivers, rollout` then `  <file>` (stdout; the attribute words of decision 12) | 0 |
| `show`, a special-teams play | `<name>: special teams, Kickoff` then `  <file>` | 0 |
| `show`, a name not in the pool | `<name>: not in the play pool` (stdout, a result line, logged) | 1 |
| `show`, no PLAY | Click's usage text, `Error: Missing argument 'PLAY...'.` | 2 |
| `list`, a category header | `:: PSR (Pass Short Right)`, or `:: Kickoff` with no label (stdout) | 0 |
| `list`, a play | `AF3ArshZ :: timed, rollout`; a play with no attribute, its name alone | 0 |
| `list`, a CATEGORY with no play | `WARN No PSR plays in the play pool.` (the label as the coach typed it is resolved to the league's label) | 0 |
| `list`, no CATEGORY, an empty pool | `WARN No plays in the play pool.` | 0 |
| `list`, a name that is no category | `Error: Invalid value for 'CATEGORY': no category named 'PSX'. Use the league's name or the game's name, like "Pass Short Right".` | 2 |
| `show` and `list`, league, `play_path` or pool problems | the gameplan commands' lines through `load_config` and `build_pool` (`FAIL No league selected...`, `FAIL <league.toml>: No play_path for the league. Set play_path in this file.`, the hint line above) | 2 |
| `show` and `list`, pool issues | `WARN <issue>` on stderr, as `set-normals` prints them | unchanged |

Codes stay 0 done, 1 findings, 2 error; `show` exits 1 when any PLAY is not in the pool; `list` never exits 1. The issue wording is the reader's (`src/athc/playpool/reader.py`) and does not change.

## 8. Related commands

- `gameplan check`, `set-normals`, `set-specials`, `replace-play`, `check-ppp` and `convert-pdb` keep printing each pool issue as a `WARN` line when they load the pool; their output does not change. Their docs say `athc playpool check` lists the same problems on their own, with an exit code (clig.dev: suggest the command to run).
- `replace-play`'s `Replacement play 'X' not found in the play pool.` and the play-list errors of `set-normals` / `set-specials` are where a coach meets a name the pool lacks; `athc playpool show X` is the command to find out why, and `athc playpool list <category>` the one that finds a replacement; their docs say so, and `set-normals`'s docs say `playpool list` writes a play list it reads.
- **What gameplan-cli.md must add** (handed to its author; not edited here): `gameplan check`, no change to its usage; each attribute-cap violation names the plays it counted, in slot order, in parentheses after the count, lists reading `A, B, C` (architecture.md's plain-values rule): `Offensive category 'Pass Short Right' has 3 of 5 timed passes (AF3ArshZ, PSRlob1, PSRfadeT); allows at most 1/2.` (the game's category name, as today's line has it; the play names illustrate the shape), and the same for the `QB runs`, `rollouts` and defense `2-DL plays` lines (`_validate_offense` / `_validate_defense` in `src/athc/gameplan/validators.py`; `RuleName.CATEGORY_MAX_QB_RUNS`, `CATEGORY_MAX_ROLLOUTS`, `CATEGORY_MAX_TIMED`, `CATEGORY_MAX_TWO_DL`). The tests that pin a cap line change with it: the golden reports `tests/integration/expected/*.report.txt`, compared by `tests/integration/test_gameplan_check.py` and by `tests/integration/test_check_ppp.py`, and `tests/integration/test_gameplan_replace_play.py::test_cli_rollout_cap_uses_the_play_file`, which pins `[Pass Short Left] Offensive category 'Pass Short Left' has 1 of 1 rollouts; allows at most 0.`; `docs/gameplan/README.md`'s `check` row and `config/release/docs/COMMANDS.txt` section 1 describe the named plays. Reason: the moment a cap is flagged is the moment the coach needs the names, the line already holds them, and since ddae7a1 nothing outside the play file tells which plays they are (row 8); `playpool show` then tells what each play is, and `playpool list` finds the replacement (row 9).
- `check-ppp-cli.md` names `playpool check` as the precedent for "nothing means the configured place"; this plan keeps that behavior.
- TODO.md's 2.0.0 playpool ideas: settled in decision 1; neither changes the three commands' usage.

## 9. Code

- `src/athc/cli/playpool/check.py`: the argument renamed `folder` and declared without a metavar, so Click derives `[FOLDER]` from the name (today's `metavar="[play_dir]"` goes), with cli-help.md's help; the docstring's summary and description become section 5's text (cli-help.md line 248 marks the description rewrite as playpool-specific). Order as today: the league resolves (a `LeagueError` is swallowed when a FOLDER is given and no `--league`); a given FOLDER goes through today's two checks (`exists()` for the path phrase, `is_dir()` for the directory phrase, lines 56 to 59); with no FOLDER, `play_dir(play_path, league_file)` replaces the two checks and gives the hint, and the command's own `No play_path` line gains `, or pass the folder`. The pool is read with `read_play_pool(folder, labels=labels)` as today; the issues and the tally print as today.
- `src/athc/cli/playpool/_common.py`, new (the gameplan and profile groups keep their shared helpers in a `_common.py` the same way): `load_pool(league)` (`load_config(league, rule_files=())` from `athc.gameplan.config`, then `build_pool(config.play_path, config.categories, config.league_file)` from `athc.cli.gameplan._common`, returning the pool and the labels); `attribute_words(play)` (the `PassLogic` value lowercased, `rollout`, `screen`, `QB run`, the `DefensiveFront` value as it is plus ` front`; `DefensiveFront` from `athc.fbpro98_play`); `category_text(category, labels)` (`<label> (<game name>)`, or the game name alone); `match_category(text, labels)` (the categories a label or game name means, without case, offense before defense, over the four category enums; empty when none).
- `src/athc/cli/playpool/show.py`, new: `@playpool.command(name="show", context_settings=CONTEXT_SETTINGS)` (every command passes it, architecture.md; `check.py` does), the argument `play` as `nargs=-1, required=True` without a metavar, so Click derives `PLAY...` from the name, with its help; `@league_option`, `@click.pass_context`; `load_pool`; per name `pool.find_by_name`, the headline and the not-found line through `console.result`, the file line through `console.print`; `ctx.exit(1 if missing else 0)`.
- `src/athc/cli/playpool/list_plays.py`, new (named like `gameplan/list_normals.py`, since a module called `list` would shadow the builtin): `@playpool.command(name="list", context_settings=CONTEXT_SETTINGS)`, the argument `category` as `nargs=-1` without a metavar, so Click derives `[CATEGORY]...`, with its help; `@league_option`, `@click.pass_context`; `load_pool`; each CATEGORY through `match_category`, a miss raising `click.BadParameter("no category named '<text>'. Use the league's name or the game's name, like \"Pass Short Right\".", param_hint="'CATEGORY'")`; no CATEGORY means the four enums in order; per category the header and the sorted lines through `console.print`, the plays taken from the pool's side lists by `category`; the two `WARN` lines through `console.warn`; no tally, `ctx.exit(0)`.
- `src/athc/cli/playpool/__init__.py`: the group docstring (the new summary) and `from athc.cli.playpool import list_plays as list_plays` and `show as show` beside the `check` import; leaves register by import, so no entry-point change.
- The library does not change: `show` and `list` read what `Play`, `OffensivePlay` and `DefensivePlay` already carry.
- The usage line, argument help and `--league` text come with cli-help.md's general changes (Click 8.5, `[OPTIONS]` usage, argument help); no playpool-specific code for them.

## 10. Tests

`tests/integration/test_playpool_check.py`, with the `make_league` / `write_config` fixtures:

- No FOLDER, `play_path` missing on disk, and a file: the two hint lines, exit 2, stdout empty.
- No FOLDER, no `play_path`: the line with `, or pass the folder.`, exit 2.
- A FOLDER run never reads `play_path`: a league whose `play_path` is missing on disk, or written as an array, with a clean FOLDER given: exit 0, no `FAIL`.
- Argument count, at the limit and one past: one FOLDER is accepted (today's tests); two FOLDERs are Click's usage error with the period, exit 2, nothing checked.
- A wildcard FOLDER (`plays*`), once cli-help.md turns Click's expansion off: `FAIL plays*: The system cannot find the path specified.`

`tests/integration/test_playpool_show.py`, new, on the curated pool (`tests/integration/data/plays` and the PNFL labels from `tests/conftest.py`):

- One PLAY found: `AF1AwagR` (`Offense\PSL`, the rollout that `test_cli_rollout_cap_uses_the_play_file` relies on) prints `offense, PSL (Pass Short Left)`, its pass logic as the file gives it, and `rollout`, then its file; `GP5Xtop1` (`Offense\PMM`, a timed pass per the recorded plan of ddae7a1) prints `timed`; `TT10draw` (`Offense\RR`, a QB run) prints `QB run`; `CC31rl5m` (`Defense\34RunLeft`, a defensive Run Left) prints `defense, RunLeft (Run Left)` and the front its down linemen give; a play from `Special\` prints `special teams, <category>` and no attribute; with a `league.toml` that has no `[categories]` tables (as `test_gameplan_replace_play.py::test_cli_output_uses_game_names_without_league_labels` builds one) the game name prints alone.
- `screen`: a pass play copied into `Screens\` of a tmp pool (`test_playpool_check.py`'s `copy_play`; the curated pool has no `Screens` folder) prints `screen` after its pass logic; the same play copied loose does not.
- A pass play prints exactly one of `timed` and `check receivers`; a run play prints neither.
- Any case: `af1awagr` finds the play and prints the pool's spelling.
- Several PLAYs print in argument order; one missing among them prints its not-found line in place and the run exits 1; all found exits 0.
- A repeated name shows the play the pool resolves (the last in sorted path order), on a tmp pool with one play copied into two folders (`copy_play`), since the curated pool repeats no name.
- Argument count, at the limit and one past: one PLAY is accepted; none is Click's `Missing argument 'PLAY...'.`, exit 2.
- Setup errors through the shared loaders: no league (`no_league_selected`), no `play_path`, `play_path` missing on disk (the hint line), each exit 2 with stdout empty; pool issues (a misfiled play in a tmp pool) print as `WARN` lines on stderr while the results stay on stdout.

`tests/integration/test_playpool_list.py`, new, on the same pool:

- One CATEGORY by label (`PSL`): the header `:: PSL (Pass Short Left)`, then every `Offense\PSL` play sorted without case, `AF1AwagR :: <pass logic>, rollout` among them; the same by game name (`"Pass Short Left"`) and in another case (`psl`).
- Two CATEGORYs print in argument order; a game name both sides use (`"Run Left"`) prints the offense category, then the defense one; a defense play prints its front or its name alone; a special-teams category prints names alone.
- No CATEGORY: every category of the pool in the game's order, empty categories skipped, offense before defense before special teams.
- The output is a play list: `parse_play_list` on the captured stdout returns the play names and nothing else.
- `screen`: a pass play under `Screens\` of a tmp pool prints `:: <pass logic>, screen`.
- A CATEGORY with no play (a label of the league the pool has no play for): the `WARN No <label> plays in the play pool.` line, exit 0, nothing else; a pool with no play and no CATEGORY: `WARN No plays in the play pool.`, exit 0.
- A name that is no category: the `Invalid value for 'CATEGORY'` line, exit 2, stdout empty; one good and one bad name: the error alone, nothing listed.
- Setup errors and pool issues as for `show`. The argument has no upper limit, so no count test beyond zero and one accepted.
- Existing tests that change: `tests/integration/test_playpool_check.py::test_league_without_play_path_exit_2` (the line gains `, or pass the folder`); `tests/integration/test_cli_root.py::test_usage_lists_each_option`, rows `playpool` and `playpool check` (`athc playpool [OPTIONS] COMMAND [ARGS]...`, `athc playpool check [OPTIONS] [FOLDER]`, which cli-help.md already changes with the style) plus new rows `athc playpool show [OPTIONS] PLAY...` and `athc playpool list [OPTIONS] [CATEGORY]...`; `test_short_help_option_on_every_command` is parametrized over every command path and picks `show` and `list` up by itself. Every other playpool test keeps passing by design: the FOLDER mode is unchanged, `test_read_error_exit_2`'s stub still matches `read_play_pool(folder, labels=labels)`, and the pool-mode tests (`test_default_is_current_league_play_path`, `test_league_option_picks_another_league`) have `play_path` on disk.
- `tests/unit/playpool/`: nothing; the library does not change.

## 11. Docs and meta

- `docs/playpool/README.md`: the CLI section covers `check` (`[OPTIONS] [FOLDER]`, the two modes, the hint line and the `or pass the folder` line, the examples above), `show` (usage, lines, codes, the attribute words against "How athc reads a play") and `list` (usage, the play-list shape, the `findstr` and `set-normals` examples, codes); `check`'s exit table's error row names the hint.
- `docs/playpool/ARCHITECTURE.md`: nothing; it describes the library, which does not change.
- `docs/gameplan/README.md` (its `check` row names the pool's `WARN` lines) and the other pool consumers' READMEs where they describe those lines: one sentence pointing at `athc playpool check`; where they describe a name not in the pool, one pointing at `athc playpool show` and `athc playpool list`; `set-normals`'s play-list paragraph names `athc playpool list` as a source of one.
- `config/release/docs/COMMANDS.txt`: section 12 (`playpool check`) gets the two modes, the hint and the `.` example; new sections `13) playpool show` and `14) playpool list` follow it, the later sections renumber; the EXIT CODES paragraph lists `playpool show` among the commands that use code 1.
- `STATUS.md`: the playpool section gains `show`, `list` and the hint; its "Open: count plays by file name type (TODO)." line stays.
- `docs/design/architecture.md`: the project layout block lists `_common.py`, `list_plays.py` and `show.py` beside `check.py` under `cli/playpool/`; the `--league` list gains `playpool show` and `playpool list`; the exit-code table's code 1 gains `playpool show` among the commands that use it.
- `docs/design/TODO/cli-help.md`: the four entries of section 5 above.
- `CHANGELOG.md`, top of `## athc`: "playpool: `list` lists a category's plays with their attributes, as a play list for `set-normals`", "playpool: `show` looks plays up in the pool: side, category, attributes and file" and "playpool: `check` says to set `play_path` or pass the folder when the pool is unset or missing". `TODO.md`: the `playpool: CLI plan (...)` line under 1.0.0 is ticked when this work lands, with its text as the one-liner below.
- `tests/integration/README.md`: the `athc playpool check` intro paragraph ("`play_dir` defaults to the league's `play_path`") rewritten for FOLDER, a row per new case, and new `athc playpool show` and `athc playpool list` tables.

TODO.md one-liner: `playpool: CLI plan (check [FOLDER] with pass-the-folder hints; new show PLAY... for a play's side, category, attributes and file; new list [CATEGORY]... listing a category's plays with their attributes as a set-normals play list); see docs/design/TODO/playpool-cli.md`.

## Shared vocabulary

- `FOLDER`: a folder only, here the play pool or a folder of plays; cli-help.md rule 3's name, nothing new.
- `PLAY...`: one or more play names, any case; cli-help.md's `PLAY` (replace-play's "Play to replace (any case)") used for a list, as `find-play`'s plays are.
- `CATEGORY`: new; a play category by the league's label or the game's name, any case, for cli-help.md rule 3's list.
- `show`: the lookup verb for the pool, as pip, docker and winget use it; `gameplan find-play` stays the search of game plans. `list`: the listing verb, as pip and docker use it; `gameplan list-normals` and `list-specials` stay the listings of a game plan, and `list`'s output is their `::` play-list shape.
- "The league's play pool": the folder `play_path` names.
- Rules applied from cli-help.md, in words: no path means the configured default, `.` the current folder, an explicit path overrides both (rule 16; check-ppp-cli.md decision 3), here with the pool as the configured default for the reason in decision 3; `--league NAME` with a required value and rule 10's text, and a named league must exist even when the command needs no league (rule 19; today's `check.py`); arguments carry no explicit metavar, and an argument's own validation is a `click.BadParameter` with the `'CATEGORY'` hint (rule 22; Click's `Argument.make_metavar` and `get_error_hint`); Click's extra-argument error gets athc's period once in `src/athc/cli/__init__.py` (rule 23); a "No ... for the league" line names the command's own path form (rule 21); no quiet flag (rule 24; none proposed here); the cli-help.md form only (rule 25); Windows words in help and lines (rule 9); athc's lines and codes (`docs/design/architecture.md`).
- Not taken, with the reasons in decisions 3, 5 and 14: `-r` (check-ppp-cli.md decision 9's rule, each folder on its own), the default-team keys `team` and `ppp_path` (check-ppp-cli.md decisions 4 and 15), and an output file for `list` (rule 28's derived output has no input file here). No new option or key.

## Sources

- ruff `check` usage, `[default: .]` and file discovery: <https://docs.astral.sh/ruff/configuration/>
- helm lint: <https://helm.sh/docs/helm/helm_lint/>
- pip show: <https://pip.pypa.io/en/stable/cli/pip_show/>; pip list: <https://pip.pypa.io/en/stable/cli/pip_list/>
- docker image inspect: <https://docs.docker.com/reference/cli/docker/image/inspect/>; docker image ls: <https://docs.docker.com/reference/cli/docker/image/ls/>
- winget show: <https://learn.microsoft.com/en-us/windows/package-manager/winget/show>
- findstr: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/findstr>
- clig.dev: <https://clig.dev/>
- Click `Argument.make_metavar`, `get_error_hint` and the extra-argument text: `click/core.py`; `MissingParameter.format_message` and `BadParameter`: `click/exceptions.py`; the `Path` type's texts: `click/types.py` (Click 8.4.1 in the venv)
- athc at main ddae7a1: `src/athc/cli/playpool/check.py`, `src/athc/cli/playpool/__init__.py`, `src/athc/playpool/reader.py`, `src/athc/playpool/model.py`, `src/athc/playpool/__init__.py`, `src/athc/fbpro98_play/model.py` (`DefensiveFront`, the attribute properties), `src/athc/cli/gameplan/_common.py` (`build_pool`, `parse_play_list`, `_category_lines`, `emit_play_list`), `src/athc/cli/gameplan/set_normals.py`, `src/athc/cli/gameplan/replace_play.py`, `src/athc/cli/gameplan/find_play.py`, `src/athc/cli/convert_pdb.py`, `src/athc/cli/__init__.py`, `src/athc/pdbtoexcel/workbook_creator.py`, `src/athc/gameplan/config.py`, `src/athc/gameplan/rules.py`, `src/athc/gameplan/validators.py` (the cap lines), `src/athc/config.py` (`play_dir`, `LeagueConfig`), `src/athc/cli/_files.py`, `src/athc/errors.py`, `src/athc/console.py`, `src/athc/fbpro98_play/labels.py`, `docs/playpool/README.md` ("How athc reads a play"), `docs/playpool/ARCHITECTURE.md`, `docs/fbpro98_play/README.md`, `docs/gameplan/README.md`, `docs/design/architecture.md`, `docs/design/TODO/check-ppp-cli.md`, `docs/design/TODO/cli-help.md`, `docs/superpowers/plans/2026-10-12-play-attributes-from-data.md`, `config/release/leagues/PNFL/league.toml`, `config/release/docs/COMMANDS.txt`, `CHANGELOG.md`, `STATUS.md`, `TODO.md`, `tests/integration/test_playpool_check.py`, `tests/integration/test_gameplan_replace_play.py`, `tests/integration/test_cli_root.py`, `tests/integration/expected/offense.report.txt`, `tests/integration/README.md`, `tests/integration/conftest.py`, `tests/conftest.py`, `tests/integration/data/plays` (the curated pool), `tests/unit/playpool/README.md`; the real pool under the dev PNFL's `play_path` (`E:\SIERRA\FbPro98\PNFL`), counted 2026-10-13
