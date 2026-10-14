# check-ppp CLI plan

`athc check-ppp` with no path checks your team's profiles and game plans where the league file puts them (or in `ppp_path`); a path points it at a folder or one pair; `--team` and `--all-teams` pick other teams.

## Decisions

- `gameplan check` and `profile check` stay unchanged: `[OPTIONS] [PATH]...`, files of one kind, folders, trees, wildcards, the current folder by default.
- `profile copy` and `set-normals` keep pointing at their group's `check`.
- check-ppp checks PPP sets as the league file defines them, plus one pair given by hand; it grows no one-file mode.
- One file alone is an error that names the command to run instead.
- Three sources for the files, in a fixed order: PATH on the command line, else `ppp_path` in `league.toml` (your team only), else the league locations (`path` plus each file's `.lg2` folder).
- No PATH means the configured source; `.` means the current folder.
- The team comes from `team` in `league.toml`, `--team NAME` for one run, `-a, --all-teams` for every team.
- `team` is a league setting, as `play_path` is.
- "Your team" is the team `team` resolves to; `ppp_path` applies when the team being checked is that one, whether defaulted or named with `--team` (`--team Broncos` with `team = 'Denver'` goes through the same matcher).
- With `--team`, `team` is read only to decide that; when it is unset or does not resolve, the named team uses the league locations.
- `--all-teams` and another team always use the league locations.
- Team names are the `.lge`'s: the team name, the nickname or both (`Denver`, `Broncos`, `Denver Broncos`), matched without case; exactly one team must match.
- No match, or two (two teams in one city), is an error that lists the league's teams by both names.
- A blank `team` is unset; an array is the `Expected a string, got an array.` error `path()` gives.
- Whether a file is there is decided before it is read; a file that is there but cannot be read is handled as today.
- League locations: a team none of whose files exist gets one `FAIL` per `.lg2` folder (Windows' path phrase when the folder is absent, `No Denver files.` when it holds none of them), with the `ppp_path` hint when the run checks your team alone.
- League locations: otherwise each missing file is a `FAIL` and its partner is checked alone without the cross-check; both count as failed.
- Folder: nothing has to be there; a pair with one file present has that file checked alone and the other noted as a `WARN`, counted as missing, not as checked or failed.
- Folder: a pair with neither file prints nothing.
- Folder: a team with no file at all in the scope (the folder, or the tree with `-r`) is one `WARN` naming the team, or with `--all-teams` one `WARN` listing every such team.
- A `WARN` never changes the exit code; a hand-in folder is checked as it is.
- A found file prints its on-disk name; a missing one the league file's spelling.
- `-r` keeps today's meaning: every folder of the tree on its own; it applies to `ppp_path` like any folder, and is ignored for a pair (as today) and at the league locations.
- The pair mode is unchanged.
- `--team` or `--all-teams` with two files, or both flags together, is a usage error (Click's `UsageError`, 2); a no-op flag such as `-r` with two files stays ignored, as today.
- The lines stay the two check commands' lines, in `.lge` team order, each team's pairs in `.lg2` order, a tree's folders grouped as today.
- Identical pairs named by two teams are checked once, as today.
- The tally gains `missing` in a folder and `team(s) with no files` with `--all-teams`.
- Setup order: the arguments as today, then the league, the league files and the team, the rules and the play pool, then the files.
- The league files are read as today's `load_lg2` does: the `.lg2` first with its stock check, then the `.lge`, then the team counts compared, then the team resolved.
- The pair mode reads the rules, then the files, as today.
- The team modes need both league files (`<league>.lg2` and `<league>.lge` in `path`); the pair mode reads neither, as today.
- Files with different team counts are one `FAIL` naming both.
- `team` and `ppp_path` are set with `athc config set` (`athc config set team NAME`, `athc config set ppp_path FOLDER`), which writes them into `league.toml`, like `path` and `play_path`.
- The error for a missing `team` names the file and the command that sets it.
- Key names: `team`, and `ppp_path` after its neighbours `path` and `play_path`; the pending `_dir` rename covers all three.
- PATH stays positional, as in `gameplan check`, `profile check` and `playpool check`.
- Help text is today's style now (the usage line below, lowercase placeholders, the shared `--league` text) and [cli-help.md](cli-help.md)'s when that lands: `[OPTIONS] [PATH]...`, a PATH help line, `--team NAME`, and the summary "Check profiles against their game plans."

Modes:

| path | Team | Files come from | What is missing |
|---|---|---|---|
| none, `ppp_path` set | your team (`team`, or `--team` naming it) | that folder, each file by its `.lg2` name; with `-r`, each folder of its tree on its own | a partner: `WARN`, counted as missing; a whole pair: nothing; the team's every file: one `WARN` |
| none | `team`, `--team` or `--all-teams` | the league locations: `path` joined with each file's `.lg2` folder | a file: `FAIL`, counted as failed; the team's every file: one `FAIL` per folder, absent or empty |
| a folder | `team`, `--team` or `--all-teams` | that folder; with `-r`, each folder of its tree on its own | as the first row |
| one `.prf` and one `.pln` | none | the two files | `FAIL`, as today |

- League locations: `path` may point at a copy of the league's files; the `.lg2` folders resolve under it.
- Folder: each file is looked up by its `.lg2` name without case; folder modes always use the current league file's names, so an archived season of a renamed team shows as "no files".
- Order: folders top first, then subfolders by name; inside a folder, teams in `.lge` order, each team's four pairs in `.lg2` order (1st-half offense, 1st-half defense, 2nd-half offense, 2nd-half defense); a missing file's `WARN` or `FAIL` sits where its report would.
- A game plan two pairs share is reported once, its missing-file `WARN` or `FAIL` included; each profile gets its own cross-check; identical pairs once, as today.
- The "no files" lines come after the folders' lines; then the blank line and the tally.

## Help

### athc check-ppp

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

## Settings

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

## Lines and exit codes

New lines; everything else prints as today.

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
| three or more paths | `Error: Got unexpected extra argument (<path>).` (Click's phrase, athc's period; `arguments (<a> <b>)` for two extra) | 2 |
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

- The hint at the league locations, when the run checks your team alone: `Run 'athc config set ppp_path FOLDER' or pass the folder.`
- A folder beside a file, two files of a kind, or another extension are `FAIL` lines as today, and nothing is checked.
- Team labels are the `.lge` team name (`Denver`), whichever form `team` was written in; the no-match and two-match lines show both names.
- A "no files" `FAIL` counts as one failed item.
- `missing` counts a pair's other file only; a whole pair absent prints nothing and counts nowhere.
- Today's `No profile and gameplan pairs from the league file in directory` line goes; the per-team lines replace it.
- Codes stay 0 done (warnings included), 1 violations, 2 error; a batch runs every pair and exits with the worst outcome.

## Files to change

- `src/athc/cli/check_ppp.py`: path as `nargs=-1`, with the third-path `UsageError` in Click's words; `--team` and `-a/--all-teams`; a team resolver over the `.lge` names; the three sources; per-team pairs from the `.lg2` (today's `league_pairs`, per team, keeping the folders for the league locations); the folder lookup.
- `src/athc/cli/check_ppp.py`: a missing file decided by `exists()` before any read; at the league locations a team with none found gets the one `FAIL` line and no reads, and a missing file otherwise goes through today's unreadable-file path (`check_files` checks the partner alone, `summarize` prints and counts the `(-1, line)` report).
- `src/athc/cli/check_ppp.py`: in a folder a missing file is a third report kind, `missing`, that `summarize` prints through `console.warn` and counts in `missing`, outside `checked` and `failed`.
- `src/athc/cli/check_ppp.py`: the "no files" lines; the team-count check; the tally fields; keys `TEAM_KEY = "team"` and `PPP_PATH_KEY = "ppp_path"` beside `LEAGUE_PATH_KEY`.
- `src/athc/config.py`: `LeagueConfig.string(key)` beside `path(key)`: the string value, `None` when absent or blank, the array error otherwise; `team` reads through it, `ppp_path` through `path()`.
- `src/athc/fbpro98_lge/model.py`: `LgeFile.teams`, the teams flat in file order (team numbers 1..N), as `Lg2File.teams` is.
- `config/release/leagues/*/league.toml`, `config/dev/leagues/*/league.toml`: the two keys.

## Tests

`tests/integration/test_check_ppp.py`, new:

- Fixtures: `lg2_league` writes a `.lge` beside the `.lg2` with real team names, through a shared builder module also used by `tests/unit/fbpro98_lge/conftest.py`.
- Fixtures: `pnfl_league` copies `tests/unit/fbpro98_lge/data/PNFL.lge` beside `PNFL.lg2`.
- Fixtures: the `team()` helper's never-on-disk filler names stay (a pair with neither file prints nothing).
- Team resolution: name, nickname, both, mixed case; no match; two matches (a built `.lge`); blank; an array; `--team` beats `team`; `--team` with `team` unset or unresolvable; neither set.
- Team match count: one match accepted, zero and two rejected.
- Sources: no path with `ppp_path`; no path without it; `.`; a folder; `ppp_path` used for `--team` naming your team, skipped for another team and `--all-teams`; a relative `ppp_path`; `ppp_path` missing on disk and a file.
- League locations: every file at its folder; one missing (`FAIL`, partner checked alone, counted as failed); none of a team's files (one line: the path phrase for an absent folder, the no-files line for an empty one; the hint only when checking your team alone, not with `--all-teams`); a shared game plan missing once; `-r` ignored.
- Folder: a missing partner (`WARN`, partner checked alone, counted as missing, code unchanged); a shared game plan missing once; a whole pair missing (nothing).
- Folder: a team with no files (one team: the names hint, other teams' files present or not; `--all-teams`: the one-line list).
- Folder: found files in on-disk spelling, missing ones in the league file's; the tally fields; `-r` with the tree as the scope; `--all-teams` in `.lge` order.
- League files: `.lge` missing; the `.lg2` errors still come first.
- League file team counts: equal accepted; `.lg2` one fewer and one more than the `.lge` rejected.
- Usage: `--team` with `--all-teams`; a team flag with two files; one file of each kind with its hint; a missing single path keeps the path phrase.
- Path count: two paths accepted, three rejected (Click's phrase with the period).

`tests/integration/test_check_ppp.py`, changed:

- `test_cli_requires_a_path`: a bare command now gives the "Team is not set" error.
- `test_cli_one_file_is_an_error`: the hints.
- `test_dir_half_a_pair_is_skipped`: now a `WARN` and the partner checked.
- `test_dir_subfolders_are_not_searched`, `test_dir_empty`, `test_dir_unreadable_directory_has_no_pairs`, `test_tree_pair_split_across_folders_is_not_found`: the per-team lines.
- `test_dir_unlisted_files_are_ignored`, `test_dir_checks_each_pair_in_league_file_order`, `test_dir_clean_exit_0`, `test_dir_teams_in_league_file_order`, `test_dir_expected_error_in_a_pair_is_its_fail_line`, `test_dir_side_mismatch_is_that_pairs_error`, `test_dir_unreadable_file`: the exact tallies gain the new fields.
- `test_dir_first_setup_error_stops_the_run`: now sees the "League files folder is not set" error first.
- `test_dir_relative_path_is_in_the_league_folder`: an `.lge` beside its hand-built `.lg2`.
- Every directory and tree test passes `--all-teams`.
- `test_real_tree_checks_every_team_folder`, `test_real_tree_reads_as_two_file_mode`: run with `--all-teams`.
- `test_real_team_folder_alone`: runs with `--team Denver`.
- `test_league_flag_picks_the_league_file`: `.lge`s beside its `.lg2`s and a team flag.
- `test_cli_rejects_a_third_path`, `test_cli_one_missing_path`, `test_dir_names_ignore_case`, `test_dir_league_file_missing`, `test_dir_bad_league_file`, `test_dir_stock_league_file`: keep passing unchanged.

Other files:

- `tests/integration/test_cli_root.py`: check-ppp's usage line and metavars.
- `tests/unit/fbpro98_lge/test_model.py`: `teams` order against the nested walk.
- `tests/integration/test_config.py`: `LeagueConfig.string()` for a value, blank, absent and an array.

## Docs and meta

- `docs/check_ppp/README.md`: rewritten around the modes, settings, lines and codes above, saying what `missing` counts.
- `docs/gameplan/README.md`: the sentence pointing at check-ppp for pairs (profile's README already has it).
- `docs/fbpro98_lge/README.md`: `teams`.
- `docs/config/README.md`: as config-cli.md lists (`config set` now writes `team` and `ppp_path`).
- `docs/design/architecture.md`, Config: `team` and `ppp_path` in the `[league]` list.
- `docs/design/installer.md`: the `path` sentence gains `team`.
- [cli-help.md](cli-help.md), check-ppp: the usage and options above.
- `config/release/athc.ini`, `config/release/docs/README.txt`: the check-ppp setup notes name `path` and `team`.
- `config/release/docs/COMMANDS.txt` section 11, saying what `missing` counts.
- `tests/integration/README.md`.
- `CHANGELOG.md`, `STATUS.md`, `TODO.md`.
- Examples for the docs:

```
athc check-ppp
athc check-ppp .
athc check-ppp --all-teams handed-in -r
athc check-ppp --team "Las Vegas" handed-in
athc check-ppp DEN-OFF1.prf DEN-OGP1.pln
```
