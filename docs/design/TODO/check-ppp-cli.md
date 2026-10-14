# check-ppp CLI plan

**Goal:** `athc check-ppp` with nothing after it checks your team's profiles and game plans (its PPP files) where the league file puts them; a path points it at a folder or at one pair instead; the league manager runs it over every team, in the league's folders or in a folder of handed-in files. `gameplan check` and `profile check` stay as the checkers for files of one kind.

**Status:** proposal, 2026-10-13; nothing changed yet. Every choice is decided below, with its reason next to it. Reviewed in rounds for workflow gaps and codebase fit; the findings are folded in.

## 1. Today

- `athc check-ppp PATH [PATH]`: one `.prf` and one `.pln` in either order, or one folder (`-r` for its tree). In a folder, every pair the league's `.lg2` names, for any team, matched by file name in each folder; a pair with a file missing is skipped silently, and so is a file no pair names. When one file of a pair cannot be read, the other is still checked alone, without the cross-check, and the unreadable one counts as checked and failed; a missing file reads as an unreadable one.
- A bare `athc check-ppp` is a usage error. Nothing knows which team is yours, and nothing checks the files where the league file puts them; a season's folders are reached only through a tree walk, which also walks the older seasons under `path`.
- `gameplan check [PATH]...` and `profile check [PATH]...` take files of one kind, folders, trees and wildcards; no path means the current folder. `playpool check [play_dir]` takes no argument for the league's `play_path`, or a folder instead: the in-house precedent for "nothing means the configured place".
- The `.lg2` lists each team's eight files, each as a folder relative to the game folder plus a file name; the `.lge` beside it holds the team names and nicknames in the same team order. The lg2 and lge libraries read both from `path`, the folder that holds the league's files (`read_lg2(league, dir)`, `read_lge(league, dir)`); the lge library has no flat team list yet, only conferences, divisions and teams.
- The real league today: 18 teams, one folder each (`PNFL\2048\Plans\<Team (Coach)>`), file names of every shape (`DEN-OGP1.pln`, `LAC OFF1.prf`, `packersoff1.pln`), all distinct across teams; four teams use one game plan for both halves.

## 2. Who runs it, for what

| # | Who | Wants to check | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach | this week's files, where the game reads them | `athc check-ppp` | the four pairs at their league locations |
| 2 | Coach | the same files, kept in a working folder | `ppp_path` set once, then `athc check-ppp`; or in that folder, `athc check-ppp .` | the four pairs found by name there |
| 3 | Coach | the files, with the league's files on this PC but the team's plans folder absent or empty | `athc check-ppp` before setting `ppp_path` | one `FAIL` naming the folder and telling them to set `ppp_path` or pass the folder |
| 4 | Coach | an archived week | `athc check-ppp plans\wk5` | that folder |
| 5 | Coach | every archived week | `athc check-ppp plans -r` | each week's folder on its own; a pair with one file gets a `WARN` for the other |
| 6 | Coach | a new game plan with the current profile, before renaming it | `athc check-ppp DEN-OFF1.prf try3.pln` | the pair |
| 7 | Coach | ten candidate game plans | `athc gameplan check *.pln` | each file |
| 8 | Coach | profiles after `profile copy` | `athc profile check profiles\` | each file |
| 9 | Manager | own team | as 1 to 6 | |
| 10 | Manager | everything handed in, in one folder or one subfolder per team | `athc check-ppp --all-teams handed-in` (`-r` for subfolders) | every file found; `WARN` lines for missing partners and for teams with nothing there |
| 11 | Manager | a coach who sent only the game plans | the same | the game plans checked alone, their profiles `WARN`ed as missing; the cross-check waits for row 13 |
| 12 | Manager | one coach's hand-in | `athc check-ppp --team Raiders handed-in` | that team's files found by name |
| 13 | Manager | the league's folders before the sim | `athc check-ppp --all-teams` | every file at its league location; a missing one is a `FAIL` |
| 14 | Manager | a late pair from an email | `athc check-ppp LVOFF1.prf RAIDEROFF.pln` | the pair |
| 15 | Manager | last season's folders | `athc check-ppp --all-teams E:\SIERRA\FbPro98\PNFL\2048\Plans -r` | each team's folder, by the current league file's names |
| 16 | Either | another league | any of these with `--league PCFL` | |
| 17 | Either | from a script | the exit code; `2> errors.txt` keeps the problem lines | |

## 3. What other tools do

- **Config names the default paths, arguments win, `.` is "here".** pytest's `testpaths`: "Directories to search for tests when no files or directories are given on the command line"; with neither, "pytest collects tests below the current working directory". mypy's `files`: "A comma-separated list of paths which should be checked by mypy if none are given on the command line". pyright's `include`: "If no paths are specified, pyright defaults to the directory that contains the config file". ruff's `check` lists its files argument as `[default: .]`.
- **A default scope in config, a flag for one other, a flag for all.** kubectl saves the namespace in the context (`kubectl config set-context --current --namespace=...`), `-n` picks one for a request, and `-A, --all-namespaces` lists "across all namespaces. Namespace in current context is ignored even if specified with --namespace". cargo: "By default ... only the package defined by the manifest", `-p` for others, `--workspace` for all. pre-commit: `run` takes the staged files, `--files` named ones, `--all-files` "all the files in the repo".
- **Standard flags and hints.** clig.dev: "Use standard names for flags, if there is a standard", listing `-a, --all`; "Make the default the right thing for most users"; "Be consistent across subcommands"; "Suggest commands the user should run".
- **A set checker beside the file checkers.** `helm lint` "takes a path to a chart and runs a series of tests to verify that the chart is well-formed"; the YAML files inside are yamllint's job. `cargo check` checks packages as their manifest defines them; one file is `rustc`'s. pre-commit runs the suite its config defines; each linter still runs on its own. docker keeps `docker inspect`, which "matches any type of object by either ID or name", beside `docker container inspect`.
- **Pointing elsewhere.** git's `-C <path>`: "Run as if git was started in <path> instead of the current working directory"; athc's check commands take the folder as an argument.
- **Names without case.** Click's `Choice(case_sensitive=False)`: "Set to false to make choices case insensitive"; docker finds objects "by either ID or name"; athc already pairs file names casefolded.
- **A named file that is missing is an error; a discovered one is not.** pytest: `file or directory not found: <arg>` for a command-line path, while a folder with nothing to collect is "no tests ran"; athc's own rules: a named file that does not exist is `FAIL <path>: The system cannot find the file specified.`, a folder with nothing matching is a `WARN`.

## 4. Decisions

1. **`gameplan check` and `profile check` stay, unchanged.** They check files of one kind by any name, many at once, with wildcards and trees (rows 7 and 8); check-ppp pairs files only as the league file names them. The split is helm lint beside yamllint and cargo check beside rustc, and each noun group keeps its verbs together, as docker's `container inspect` sits beside `docker inspect`. `profile copy` and `set-normals` keep pointing at their group's `check`.
2. **check-ppp checks PPP sets as the league file defines them, plus one pair given by hand.** One file alone is an error that names the command to run instead (clig.dev: suggest the command); check-ppp grows no one-file mode, so there is one way to check one file.
3. **Three sources for the files, in a fixed order:** PATH on the command line, else `ppp_path` in `league.toml` (your team only), else the league locations (`path` plus each file's `.lg2` folder). No PATH means the configured source; `.` means the current folder (pytest, mypy, pyright; athc's `playpool check`).
4. **The team comes from `team` in `league.toml`, `--team NAME` for one run, `-a, --all-teams` for every team** (kubectl's context namespace, `-n` and `-A`; cargo's package, `-p` and `--workspace`; `-a` is clig.dev's standard short flag for "all"). It is a league setting because a coach's team differs per league, as `play_path` does. "Your team" is the team `team` resolves to; `ppp_path` applies when the team being checked is that one, whether defaulted or named with `--team` (`--team Broncos` with `team = 'Denver'` goes through the same matcher). With `--team`, `team` is read only to decide that; when it is unset or does not resolve, the named team uses the league locations. `--all-teams` and another team always use the league locations.
5. **Team names are the `.lge`'s:** the team name, the nickname or both (`Denver`, `Broncos`, `Denver Broncos`), matched without case (Click's `Choice`), and exactly one team must match. No match, or two (two teams in one city), is an error that lists the league's teams by both names. A blank `team` is unset; an array is the `Expected a string, got an array.` error `path()` gives.
6. **Missing files.** Whether a file is there is decided before it is read; a file that is there but cannot be read is handled as today. At the league locations every file is named for the game, so a team none of whose files exist gets one `FAIL` per `.lg2` folder (Windows' path phrase when the folder is absent, `No Denver files.` when it holds none of them), with the `ppp_path` hint when the run checks your team alone; otherwise each missing file is a `FAIL` and its partner is checked alone without the cross-check (today's unreadable-partner behaviour); both count as failed. In a folder nothing has to be there (the rule behind today's exit 0 for "no pairs"): a pair with one file present has that file checked alone and the other noted as a `WARN`, counted as missing, not as checked or failed; a pair with neither file prints nothing; a team with no file at all in the scope (the folder, or the tree with `-r`) is one `WARN` naming the team, or with `--all-teams` one `WARN` listing every such team, since most teams send nothing in a given week. A `WARN` never changes the exit code; a hand-in folder is checked as it is, and the merged league folders are row 13's job.
7. **A found file prints its on-disk name; a missing one the league file's spelling.** The on-disk name is what File Explorer shows, and an existing test pins it.
8. **`-r` keeps today's meaning:** every folder of the tree on its own, since weeks and seasons reuse names; it applies to `ppp_path` like any folder, and is ignored for a pair (as today) and at the league locations, where the files are exact.
9. **The pair mode is unchanged.** `--team` or `--all-teams` with two files, or both flags together, is a contradiction, not a no-op, so it is a usage error (Click's `UsageError`, 2); a no-op flag such as `-r` with two files stays ignored, as today.
10. **The lines stay the two check commands' lines**, in `.lge` team order, each team's pairs in `.lg2` order, a tree's folders grouped as today. Identical pairs named by two teams are checked once, as today. The tally gains `missing` in a folder and `team(s) with no files` with `--all-teams`.
11. **Setup order: the arguments as today, then the league, the league files and the team, the rules and the play pool, then the files.** The league files are read as today's `load_lg2` does, the `.lg2` first with its stock check, then the `.lge`, then the team counts compared, then the team resolved, so a `--team` typo or a missing `team` shows before the pool's `WARN` lines instead of after them. The pair mode reads the rules, then the files, as today.
12. **The team modes need both league files** (`<league>.lg2` and `<league>.lge` in `path`); the pair mode reads neither, as today. Files with different team counts (a copied folder with a stale file) are one `FAIL` naming both.
13. **`team` and `ppp_path` are set with `athc config set`** (`athc config set team NAME`, `athc config set ppp_path FOLDER`), which writes them into `league.toml`, like `path` and `play_path`. The error for a missing `team` names the file and the command that sets it.
14. **Key names:** `team`, and `ppp_path` after its neighbours `path` and `play_path`; the pending `_dir` rename (TODO) covers all three.
15. **PATH stays positional,** as in `gameplan check`, `profile check` and `playpool check`: consistency across subcommands (clig.dev) outweighs its "prefer flags"; git's `-C` is the flag form athc does not take.
16. **Help text is today's style now and [cli-help.md](cli-help.md)'s when that lands:** the usage line below, lowercase placeholders, the shared `--league` text; under cli-help, `[OPTIONS] [PATH]...`, a PATH help line, `--team NAME`, and the summary "Check profiles against their game plans."

## 5. The command

```
Usage: athc check-ppp [-h] [-r] [--team name] [-a] [--league name] [path]...

  Check profiles with their game plans, as the league file pairs them.

  With no path, your team's files where the league file puts them (or in
  ppp_path). A folder is searched for the team's files instead (. is the
  current folder). One .prf and one .pln are checked as a pair.

Options:
  -r, --recursive  Recurse into subdirectories of a directory path.
  --team name      Team to check (default: team in league.toml).
  -a, --all-teams  Every team in the league.
  --league name    League name (a folder under leagues\ in the config dir).
  -h, --help       Show this message and exit.
```

Examples for the docs:

```
athc check-ppp
athc check-ppp .
athc check-ppp --all-teams handed-in -r
athc check-ppp --team "Las Vegas" handed-in
athc check-ppp DEN-OFF1.prf DEN-OGP1.pln
```

### Modes

| path | Team | Files come from | What is missing |
|---|---|---|---|
| none, `ppp_path` set | your team (`team`, or `--team` naming it) | that folder, each file by its `.lg2` name; with `-r`, each folder of its tree on its own | a partner: `WARN`, counted as missing; a whole pair: nothing; the team's every file: one `WARN` |
| none | `team`, `--team` or `--all-teams` | the league locations: `path` joined with each file's `.lg2` folder | a file: `FAIL`, counted as failed; the team's every file: one `FAIL` per folder, absent or empty |
| a folder | `team`, `--team` or `--all-teams` | that folder; with `-r`, each folder of its tree on its own | as the first row |
| one `.prf` and one `.pln` | none | the two files | `FAIL`, as today |

- **League locations:** `path` may point at a copy of the league's files; the `.lg2` folders resolve under it, the way the game resolves them under its own folder. When the run checks your team alone, that one line adds `Run 'athc config set ppp_path FOLDER' or pass the folder.`
- **Folder:** each file is looked up by its `.lg2` name without case. Folder modes always use the current league file's names, so an archived season of a renamed team shows as "no files".
- **Order:** folders top first, then subfolders by name; inside a folder, teams in `.lge` order, each team's four pairs in `.lg2` order (1st-half offense, 1st-half defense, 2nd-half offense, 2nd-half defense); a missing file's `WARN` or `FAIL` sits where its report would. A game plan two pairs share is reported once, its missing-file `WARN` or `FAIL` included; each profile gets its own cross-check; identical pairs once, as today. The "no files" lines come after the folders' lines, since they are known only after the walk; then the blank line and the tally.
- **Argument errors:** a third path is Click's own phrase, `Got unexpected extra argument (<path>).` (`arguments (<a> <b>)` for two), raised by the command since `nargs=-1` accepts any count, with the period athc's usage errors end in; one path that does not exist keeps today's path phrase, since one path is a folder; a folder beside a file, two files of a kind, or another extension are `FAIL` lines as today, and nothing is checked.

## 6. Settings

In `league.toml`, under `[league]`:

```toml
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# Your team: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

- The team modes read `<league>.lg2` and `<league>.lge` from `path`; the pair mode needs neither `path` nor `team`.
- `ppp_path` applies to your team only; `--all-teams` and another team use the league locations.
- Shipped files: `team` and `ppp_path` commented out in `config/release/leagues/PNFL` and `PCFL`; the dev PNFL sets `team = 'Denver'`.

## 7. Lines and exit codes

New lines, in the project's wording; everything else prints as today.

| When | Line | Code |
|---|---|---|
| no `team`, no team flag, no pair | `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or --all-teams.` | 2 |
| `team` matches no team | `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: Jacksonville Jaguars, Buffalo Bills, ...` | 2 |
| `--team` matches no team | `Error: Invalid value for '--team': no team named 'Denvr'. Teams: Jacksonville Jaguars, Buffalo Bills, ...` | 2 |
| `team` matches two teams | `FAIL <league.toml>: [league] team: 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | 2 |
| `--team` matches two teams | `Error: Invalid value for '--team': 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | 2 |
| `team` is an array | `FAIL <league.toml>: [league] team: Expected a string, got an array.` | 2 |
| `--team` with `--all-teams` | `Error: --team and --all-teams cannot be used together.` | 2 |
| `--team` or `--all-teams` with two files | `Error: --team and --all-teams cannot be used with files.` | 2 |
| three or more paths | `Error: Got unexpected extra argument (<path>).` (Click's phrase, athc's period) | 2 |
| one `.pln` alone | `FAIL x.pln: No profile given. To check a game plan alone, run athc gameplan check.` | 2 |
| one `.prf` alone | `FAIL x.prf: No game plan given. To check a profile alone, run athc profile check.` | 2 |
| one path that does not exist | `FAIL <path>: The system cannot find the path specified.` (as today) | 2 |
| `ppp_path` missing on disk, or a file | `FAIL <ppp_path>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER'.` / `... The directory name is invalid. ...`, as `play_path`'s line | 2 |
| `.lge` missing or bad | the lge library's line, as the `.lg2`'s today | 2 |
| the two league files disagree | `FAIL <PNFL.lg2>: Lists 17 team(s), but PNFL.lge has 18.` | 2 |
| none of a team's files at the league locations, folder present | `FAIL <folder>: No Denver files.`; checking your team alone, `... Run 'athc config set ppp_path FOLDER' or pass the folder.` | 2 |
| none of a team's files at the league locations, folder absent | `FAIL <folder>: The system cannot find the path specified.`, with the same hint | 2 |
| a file missing at the league locations | `FAIL <folder>\DEN-OGP2.pln: The system cannot find the file specified.` | 2 |
| a pair's other file missing in a folder | `WARN <folder>\DEN-OGP2.pln: The system cannot find the file specified.` | 0 |
| a team with no file in the scope, one team, other teams' files present or not | `WARN <folder>: No Denver files. The league file names DEN-OFF1.prf, DEN-OGP1.pln, DEN-DEF1.prf, DEN-DGP1.pln, DEN-OFF2.prf, DEN-OGP2.pln, DEN-DEF2.prf, DEN-DGP2.pln.` (each name once) | 0 |
| teams with no file in the scope, `--all-teams` | `WARN <folder>: No files for 15 team(s): Buffalo, Miami, ...` | 0 |
| the tally, a folder | `<n> file(s) checked, <n> with violations, <n> failed, <n> missing` | |
| the tally, `--all-teams` | `..., <n> team(s) with no files` at the end, after `missing` in a folder; at the league locations it counts the one-line `FAIL`s above | |

Team labels are the `.lge` team name (`Denver`), whichever form `team` was written in; the no-match and two-match lines show both names. A "no files" `FAIL` counts as one failed item. `missing` counts a pair's other file only; a whole pair absent prints nothing and counts nowhere, which the README and COMMANDS.txt say. Today's `No profile and gameplan pairs from the league file in directory` line goes; the per-team lines replace it. Codes stay 0 done (warnings included), 1 violations, 2 error; a batch runs every pair and exits with the worst outcome.

## 8. gameplan check and profile check

Unchanged: `[OPTIONS] [PATH]...`, files of one kind, folders, trees, wildcards, the current folder by default. Their docs say what check-ppp is for (profile's already does; gameplan's gets the same sentence), and check-ppp's one-file errors point back at them.

## 9. Code

- `src/athc/cli/check_ppp.py`: path as `nargs=-1`, with the third-path `UsageError` in Click's words; `--team` and `-a/--all-teams`; a team resolver over the `.lge` names; the three sources; per-team pairs from the `.lg2` (today's `league_pairs`, per team, keeping the folders for the league locations); the folder lookup. A missing file is decided by `exists()` before any read: at the league locations a team with none found gets the one `FAIL` line and no reads, and a missing file otherwise goes through today's unreadable-file path (`check_files` already checks the partner alone and `summarize` prints and counts the `(-1, line)` report); in a folder it becomes a third report kind, `missing`, that `summarize` prints through `console.warn` and counts in `missing`, outside `checked` and `failed`. The "no files" lines; the team-count check; the tally fields. Keys `TEAM_KEY = "team"` and `PPP_PATH_KEY = "ppp_path"` beside `LEAGUE_PATH_KEY`.
- `src/athc/config.py`: `LeagueConfig.string(key)` beside `path(key)`: the string value, `None` when absent or blank, the array error otherwise; `team` reads through it, `ppp_path` through `path()`.
- `src/athc/fbpro98_lge/model.py`: `LgeFile.teams`, the teams flat in file order (team numbers 1..N), as `Lg2File.teams` is; its README line.
- `config/release/leagues/*/league.toml`, `config/dev/leagues/*/league.toml`: the two keys.

## 10. Tests

`tests/integration/test_check_ppp.py`:

- Fixtures: `lg2_league` writes a `.lge` beside the `.lg2` with real team names, through a shared builder module used by `tests/unit/fbpro98_lge/conftest.py` (today's builder names teams `T1`/`N1`); `pnfl_league` copies `tests/unit/fbpro98_lge/data/PNFL.lge` beside `PNFL.lg2` (its 18 teams line up with the `.lg2`'s 2049 folders; Denver is team 5 in both). The `team()` helper's never-on-disk filler names stay: a pair with neither file prints nothing.
- Team resolution: name, nickname, both, mixed case; no match; two matches (a built `.lge`, since the real league has none); blank; an array; `--team` beats `team`; `--team` with `team` unset or unresolvable; neither set. Limits: one match accepted, zero and two rejected.
- Sources: no path with `ppp_path`; no path without it; `.`; a folder; `ppp_path` used for `--team` naming your team, skipped for another team and `--all-teams`; a relative `ppp_path`; `ppp_path` missing on disk and a file.
- League locations: every file at its folder; one missing (`FAIL`, partner checked alone, counted as failed); none of a team's files (one line: the path phrase for an absent folder, the no-files line for an empty one; the hint only when checking your team alone, not with `--all-teams`); a shared game plan missing once; `-r` ignored.
- Folder: a missing partner (`WARN`, partner checked alone, counted as missing, code unchanged); a shared game plan missing once; a whole pair missing (nothing); a team with no files (one team: the names hint, other teams' files present or not; `--all-teams`: the one-line list); found files in on-disk spelling, missing ones in the league file's; the tally fields; `-r` with the tree as the scope; `--all-teams` in `.lge` order.
- League files: `.lge` missing; team counts equal accepted, off by one rejected; the `.lg2` errors still come first.
- Usage: `--team` with `--all-teams`; a team flag with two files; two paths accepted and three rejected (Click's phrase with the period); one file of each kind with its hint; a missing single path keeps the path phrase.
- Existing tests that change: `test_cli_requires_a_path` (a bare command now needs a team: the "Team is not set" error); `test_cli_one_file_is_an_error` (the hints); `test_dir_half_a_pair_is_skipped` (now a `WARN` and the partner checked); `test_dir_subfolders_are_not_searched`, `test_dir_empty`, `test_dir_unreadable_directory_has_no_pairs` and `test_tree_pair_split_across_folders_is_not_found` (the per-team lines); the exact tallies in `test_dir_unlisted_files_are_ignored`, `test_dir_checks_each_pair_in_league_file_order`, `test_dir_clean_exit_0`, `test_dir_teams_in_league_file_order`, `test_dir_expected_error_in_a_pair_is_its_fail_line`, `test_dir_side_mismatch_is_that_pairs_error` and `test_dir_unreadable_file` gain the new fields; `test_dir_first_setup_error_stops_the_run` now sees the "League files folder is not set" error first (decision 11); `test_dir_relative_path_is_in_the_league_folder` gets an `.lge` beside its hand-built `.lg2`; every directory and tree test passes `--all-teams` (today's any-team behaviour); `test_real_tree_checks_every_team_folder` and `test_real_tree_reads_as_two_file_mode` run with `--all-teams`, `test_real_team_folder_alone` with `--team Denver`; `test_league_flag_picks_the_league_file` gets `.lge`s beside its `.lg2`s and a team flag; `test_cli_rejects_a_third_path`, `test_cli_one_missing_path`, `test_dir_names_ignore_case`, `test_dir_league_file_missing`, `test_dir_bad_league_file` and `test_dir_stock_league_file` keep passing by design; `test_cli_root.py`'s usage line and metavars for check-ppp.
- `tests/unit/fbpro98_lge/test_model.py`: `teams` order against the nested walk. `tests/integration/test_config.py`, where `LeagueConfig` is tested: `string()` for a value, blank, absent and an array.

## 11. Docs and meta

- `docs/check_ppp/README.md`: rewritten around the modes, settings, lines and codes above, saying what `missing` counts.
- `docs/gameplan/README.md`: the sentence pointing at check-ppp for pairs. `docs/fbpro98_lge/README.md`: `teams`. `docs/config/README.md`: as config-cli.md lists (`config set` now writes `team` and `ppp_path`).
- `docs/design/architecture.md`, Config: `team` and `ppp_path` in the `[league]` list; `docs/design/installer.md`: the `path` sentence gains `team`.
- `docs/design/TODO/cli-help.md`, check-ppp: the usage and options above.
- `config/release/athc.ini` and `config/release/docs/README.txt`: the check-ppp setup notes name `path` and `team`; `config/release/docs/COMMANDS.txt` section 11; `tests/integration/README.md`.
- `CHANGELOG.md`, `STATUS.md`, `TODO.md`.

## Sources

- pytest `testpaths` help text and `file or directory not found`: `_pytest/main.py` in the venv; the current-directory fallback: <https://docs.pytest.org/en/stable/reference/customize.html>
- mypy `files`: <https://mypy.readthedocs.io/en/stable/config_file.html>
- pyright `include`: <https://github.com/microsoft/pyright/blob/main/docs/configuration.md>
- ruff `check` `[default: .]`: <https://docs.astral.sh/ruff/configuration/>
- kubectl `-n`, `-A`: <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/>; the saved namespace: <https://kubernetes.io/docs/reference/kubectl/quick-reference/>
- cargo package selection: <https://doc.rust-lang.org/cargo/commands/cargo-check.html>; workspaces: <https://doc.rust-lang.org/cargo/reference/workspaces.html>
- pre-commit `run`, `--files`, `--all-files`: <https://pre-commit.com/>
- clig.dev: <https://clig.dev/>
- helm lint: <https://helm.sh/docs/helm/helm_lint/>
- docker inspect and container inspect: <https://docs.docker.com/reference/cli/docker/inspect/>, <https://docs.docker.com/reference/cli/docker/container/inspect/>
- git `-C`: <https://git-scm.com/docs/git>
- Click `Choice(case_sensitive)`, `UsageError` (exit 2) and the extra-argument text: `click/types.py`, `click/exceptions.py`, `click/core.py` in the venv
- athc: `src/athc/cli/check_ppp.py`, `src/athc/cli/playpool/check.py`, `src/athc/cli/_files.py`, `src/athc/config.py`, `src/athc/errors.py`, `docs/fbpro98_lg2/specs/lg2.md`, `docs/fbpro98_lge/README.md`, `tests/integration/test_check_ppp.py`; the real `PNFL.lg2` and `PNFL.lge` read on 2026-10-13
