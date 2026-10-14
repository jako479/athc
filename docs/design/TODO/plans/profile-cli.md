# profile CLI plan

`athc profile check`, `diff` and `copy` accept `off1`, `def1`, `off2` and `def2` for your team's profiles and gain `--team`; `copy` takes one or more targets; `--substitutions` replaces `--sub-percent`.

Depends on cli-help.md landing first.

## Decisions

- The three commands stay; no command takes the team's four profiles as a set (that is `check-ppp`); a coach names the ones wanted.
- `check` keeps the current folder as its no-PATH default; `.` and an explicit path behave as today and as in `check-ppp`.
- Every `.prf` operand may be `off1`, `def1`, `off2` or `def2`: your team's 1st-half offense, 1st-half defense, 2nd-half offense or 2nd-half defense profile, in `check`'s PATH, `diff`'s PROFILE1 and PROFILE2, and `copy`'s SOURCE and TARGET.
- The four names: one spelling, lowercase in help and docs; matched after casefolding (`OFF1` works); no synonyms (`o1`, `offense-1`).
- Help calls them profile keys: operands say "or a profile key"; a "Profile keys" block above Examples gives each one's meaning.
- An operand that exists on disk, file or folder, is a path whatever it is called; an operand with an extension or a folder separator is a path too (`off1.prf`, `.\off1`); else one of the four words is the team's file; else it is a missing path with today's line.
- A folder named `off1` in the current folder is that folder: `check off1` checks its `.prf` files (or `WARN off1: No .prf files.`), `copy new.prf off1 --stop-clock` edits every same-side `.prf` in it, `diff off1 try.prf` is `FAIL off1: Access is denied.`.
- Existence is tested against the current folder; run from another folder, `off1` is the word; `.\off1` always means the path.
- A file named `off1` is a path: on `check`'s PATH and `copy`'s TARGET it is `FAIL off1: Not a .prf file.`; on `diff` and `copy`'s SOURCE it reaches the reader, which gives its own line.
- A name resolves to the file's `.lg2` name in `ppp_path`, else the league location (`path` joined with the file's `.lg2` folder and name).
- The team is `team` in league.toml or `--team NAME`, matched by the `.lge` names (name, nickname or both, without case, exactly one match). No new keys.
- `ppp_path` applies only to the team `team` names: `--team` naming that same team goes through it; `--team` naming another team, or `--team` with `team` unset or unresolvable, uses the league locations.
- `--team NAME` and `--league NAME` sit on all three commands; no `--all-teams`.
- `--team` without one of the four names among the operands is Click's usage error `Error: --team requires a profile key (off1, def1, off2 or def2).`, exit 2; `check` with no PATH counts too; the same rule on every command, `gameplan check` included.
- `--league NAME` is never a contradiction: a named league must exist (today's `League 'NOPE' not found` line from `league_dir`); the league's files are read only when something needs them.
- `check` reads the league on every run for its rules; `diff` and `copy` read `league.toml`, the `.lg2` and the `.lge` only when an operand is a name, and with plain files and no `--league` read no config at all.
- `diff` takes exactly two operands; none is Click's `Missing argument` line; folders are not operands.
- `copy` takes `SOURCE TARGET...`: one source, one or more targets, each a `.prf` file, a folder, a wildcard or a name; targets collected in order, each file once, as `check`'s paths are.
- `copy` with no SOURCE or no TARGET is Click's `Missing argument` line; TARGET is `nargs=-1, required=True`.
- 1st half to 2nd half is `copy off1 off2 ...` and `copy def1 def2 ...`.
- Offense to defense stays one `SKIP <file>: defense profile` per wrong-side target, exit 0, whether the target came from a folder or by name; any change to that is TODO.md's 2.0.0 item "profile: revisit edit\copy options".
- A source that is also a target (`copy off1 off1`) is today's `SKIP <file>: the source profile`.
- `--substitutions` replaces `--sub-percent`; the `OK` line's label is `updated (substitutions)`; the usage error lists the new name; the writer's keyword `copy_sub_percent` keeps its name.
- The other copy options stay: `--stop-clock`, `--field-goal-range`, `--fourth-down`, `--goal-line`, `--pat-logic`; at least one copy option is required, as today.
- No `--dry-run` and no backup.
- `-r` keeps today's meaning on `check` (a PATH folder's tree) and `copy` (a TARGET folder's tree), help "Include subfolders."; ignored for files and names.
- Whether a name's file exists is decided when the name is resolved, before anything reads it; the resolver builds the line itself: `FAIL <path>: The system cannot find the file specified.` (the path phrase when its folder is missing too, `missing_reason`).
- At the league location, when the team is the one `team` names, that line adds `Run 'athc config set ppp_path FOLDER' or pass a .prf file.`; for another team, or in `ppp_path`, it adds nothing.
- A missing name file: for `diff` and `copy`'s SOURCE nothing runs (2); in `check` and among `copy`'s targets it counts as failed and the run continues.
- Setup order: the arguments (Click, the `--team`-with-a-path error included); `--league` resolved whenever given; when a name is present, `league.toml` read for `team` alone (a missing `team` shows before a missing `path`), then `path`, the `.lg2` with its stock check, the `.lge`, the team counts and the team match; then `check`'s rules; then the files.
- The lines stay the three commands' lines; new ones are the setup lines, `copy`'s renamed label and `diff`'s `-o` extension line; codes stay 0 / 1 / 2.
- Help text: the blocks below, as in cli-help.md; the arguments carry no metavar, so Click derives `PROFILE1`, `PROFILE2`, `SOURCE` and `TARGET...` from the dests for the usage line and the error hints.
- `check` otherwise unchanged: no PATH is the current folder; each file's lines, the tally and the codes as today.
- `check` order: PATH order, a folder's files sorted; a name takes its place in the order like a file.
- `diff`'s report names each file by the operand's resolved path (`<path> -> <path>`).
- `copy` order: targets in TARGET order, a folder's files sorted, each file once (its first mention); then the blank line and the tally, as today.
- A missing `copy` SOURCE stops the run before any target is touched, as today.
- `check-ppp` shares `team`, `ppp_path`, `path`, the team resolver and the lines; `gameplan` takes the same four names (`.lg2` entries 2, 4, 6 and 8) with the same `--team` and resolver.
- `profile check`'s help and README point at `check-ppp`; `profile copy` points at `profile check` for the check afterward; `profile diff` is the preview before a copy.

### Where an operand's file comes from

- A path that exists, or one with an extension or a folder separator: that file (a folder or a wildcard where the command allows one); needs nothing.
- A name (any case), `ppp_path` set, the team `team` names (by default or with `--team` naming it): `<ppp_path>\<its .lg2 name>`; needs `path`, the `.lg2` and `.lge`, `team`.
- A name, no `ppp_path`, the same team: `<path>\<its .lg2 folder>\<its .lg2 name>`; needs the same.
- A name, another team with `--team`, or `--team` with `team` unset or unresolvable: `<path>\<its .lg2 folder>\<its .lg2 name>`, `ppp_path` not used; needs `path`, the `.lg2` and `.lge`.
- A name, `team` unset or unresolvable, no `--team`: nothing is located; the "Team is not set" line, or the no-match / two-match line; needs `league.toml`.
- Anything else: a missing path, today's line; needs nothing.
- `.lg2` file entries: `off1` is entry 1 (1st-half offense profile), `def1` entry 3, `off2` entry 5, `def2` entry 7.

## Help

### profile

```
Usage: athc profile [OPTIONS] COMMAND [ARGS]...

  Check and edit coaching profiles (.prf).

Options:
  -h, --help  Show this message and exit.

Commands:
  check  Check profiles against the league's rules.
  copy   Copy settings from one profile to others.
  diff   Show differences between two profiles.
```

### profile check

```
Usage: athc profile check [OPTIONS] [PATH]...

  Check profiles against the league's rules.

  Each profile prints OK or its violations. To check a profile with its game
  plan, run athc check-ppp.

Positional arguments:
  PATH  .prf files, folders, wildcards or profile keys (default: current
        folder).

Options:
  -r, --recursive  Include subfolders.
  --team NAME      Team the profile keys refer to (default: team in
                   league.toml).
  --league NAME    League to use (default: the one set with athc config set
                   league).
  -h, --help       Show this message and exit.

  Profile keys, for your team's profiles:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc profile check
    athc profile check off2
    athc profile check drafts\*OFF*.prf
```

### profile diff

```
Usage: athc profile diff [OPTIONS] PROFILE1 PROFILE2

  Show differences between two profiles.

  Compares situations, PAT situations, substitutions, field-goal range and
  audibles; only what changed is shown. Both must be the same side.

Positional arguments:
  PROFILE1  A .prf file or a profile key.
  PROFILE2  The profile to compare it with, named the same way.

Options:
  -o, --output FILE  Write the report to FILE instead of the console (.txt, or
                     .csv for Excel).
  --team NAME        Team the profile keys refer to (default: team in
                     league.toml).
  --league NAME      League to use (default: the one set with athc config set
                     league).
  -h, --help         Show this message and exit.

  Profile keys, for your team's profiles:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc profile diff off1 off2
    athc profile diff off1 try.prf -o changes.csv
```

### profile copy

```
Usage: athc profile copy [OPTIONS] SOURCE TARGET...

  Copy settings from one profile to others.

  Pick the settings with one or more options. Targets of the other side are
  skipped. Rules are not checked; run athc profile check afterward.

Positional arguments:
  SOURCE  Profile to copy from: a .prf file or a profile key.
  TARGET  Profiles to copy into: .prf files, folders, wildcards or profile
          keys.

Options:
  -r, --recursive     Include subfolders.
  --stop-clock        Copy the stop-clock setting of every situation.
  --substitutions     Copy the substitution percentages.
  --field-goal-range  Copy the field-goal range.
  --fourth-down       Copy every 4th-down situation.
  --goal-line         Copy every goal-line situation (inside the 5).
  --pat-logic         Copy the PAT table (60 situations).
  --team NAME         Team the profile keys refer to (default: team in
                      league.toml).
  --league NAME       League to use (default: the one set with athc config set
                      league).
  -h, --help          Show this message and exit.

  Profile keys, for your team's profiles:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense

  Examples:

    athc profile copy off1 off2 --stop-clock --substitutions
    athc profile copy new.prf off1 off2 --substitutions
```

## Settings

In `league.toml`, under `[league]`: the keys check-ppp-cli.md adds, nothing new; the `path` and `team` comment text is check-ppp-cli.md's:

```toml
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# Your team: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

- `check` reads `profile.toml` (or `profile_rules`) as today; `diff` and `copy` read no rules.
- `ppp_path` applies only to the team `team` names.
- `<league>.lg2` and `<league>.lge` are read from `path` only when an operand is one of the four names.

## Lines and exit codes

New or changed lines; everything else prints as today.

| When | Line | Code |
|---|---|---|
| bare `athc profile` | the group help, on stderr | 2 |
| a name, no `team`, no `--team` | `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or a .prf file.` | 2 |
| `team` matches no team, two teams, or is an array | check-ppp's lines (one shared resolver) | 2 |
| `--team` matches no team or two teams | check-ppp's `Error: Invalid value for '--team': ...` lines | 2 |
| `--team` with no name among the operands (a path, a wildcard, or `check` with no PATH) | `Error: --team requires a profile key (off1, def1, off2 or def2).` | 2 |
| `--league NOPE`, whatever the operands | `FAIL League 'NOPE' not found. No folder <leagues>\NOPE. Available: PCFL, PNFL.` (today's `league_dir` line) | 2 |
| a name, no `path` | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass a .prf file.` | 2 |
| `.lg2` or `.lge` missing or bad, a stock league, team counts that differ | the libraries' and check-ppp's lines | 2 |
| `ppp_path` missing on disk, or a file | check-ppp's line | 2 |
| a team file missing at the league location, the team is the one `team` names | `FAIL <path>\PNFL\2048\Plans\Denver (Brian)\DEN-OFF2.prf: The system cannot find the file specified. Run 'athc config set ppp_path FOLDER' or pass a .prf file.` (the path phrase when the folder is missing) | `diff`, `copy` SOURCE: 2; `check`, `copy` TARGET: counted failed, 2 at the end |
| a team file missing at the league location, another team | the same line without the hint | the same |
| a team file missing in `ppp_path` | `FAIL <ppp_path>\DEN-OFF2.prf: The system cannot find the file specified.` | the same |
| a file named like one of the four names on `check`'s PATH or among `copy`'s TARGETs | `FAIL off1: Not a .prf file.` (`collect_files`, as today) | counted failed, 2 at the end |
| a folder as `diff`'s operand or `copy`'s SOURCE | `FAIL off1: Access is denied.` (`named_file`, as today) | as today |
| a folder `off1` with no `.prf` on `check` | `WARN off1: No .prf files.` | as today |
| `diff` with no operand, or one | `Error: Missing argument 'PROFILE1'.` / `Error: Missing argument 'PROFILE2'.` (Click) | 2 |
| `diff` with three operands | `Error: Got unexpected extra argument (<x>).` (Click's text, athc's period added in `src/athc/cli/__init__.py`) | 2 |
| `diff -o` with another extension | `Error: Invalid value for '-o' / '--output': must have a .txt or .csv extension.` (was `Error: Invalid value for --output: the format comes from the extension: use .txt or .csv.`) | 2 |
| `copy` with no SOURCE or no TARGET | `Error: Missing argument 'SOURCE'.` / `Error: Missing argument 'TARGET...'.` (Click) | 2 |
| `copy` without a copy option | `Error: At least one copy option is required (--stop-clock, --substitutions, --field-goal-range, --fourth-down, --goal-line, --pat-logic).` | 2 |
| `copy --sub-percent` | Click's `No such option` | |
| `copy` updated a target's substitutions | `OK   <file>: updated (substitutions)` (was `sub-percent`) | |
| `copy` target of the other side | `SKIP <file>: defense profile` (one per wrong-side target) | 0 |
| `copy` target that is the source | `SKIP <file>: the source profile` | 0 |

- `--league` with plain files is resolved and nothing else is read.
- `check`: 0 clean / 1 violations / 2 error.
- `diff`: 0 identical / 1 different / 2 error.
- `copy`: 0 done (skips included) / 2 error.

## Files to change

- `src/athc/cli/__init__.py`: `team_option(head)` beside `league_option`, the `--team NAME` decorator joining the command's head to the fixed tail `(default: team in league.toml).` (profile's head "Team the profile keys refer to", gameplan's "Team the game plan keys refer to"); athc's period added once to Click's `Got unexpected extra argument (x)` where usage errors are rendered.
- `src/athc/cli/_team.py` (new, beside `_files.py`): the team layer shared by `check-ppp`, `gameplan` and `profile`, moved out of `check_ppp.py`: `TEAM_FILE_NAMES = ("off1", "def1", "off2", "def2")`; `TEAM_KEY = "team"`, `PPP_PATH_KEY = "ppp_path"`, `LEAGUE_PATH_KEY` imported from `src/athc/config.py`; `load_league_files(league, league_dir)` (the `.lg2` with its stock check, the `.lge`, the team counts compared); `resolve_team(name, lge)` with its two error lines; `team_files(team, kind)`, the team's four `(name, file)` pairs of one kind in `.lg2` order with a shared file repeated (profile's callers drop repeats by resolved path); `locate(file, ppp_path, league_path) -> Located(path, exists, source)`, existence decided before any read.
- `src/athc/cli/profile/_common.py`: `expand_names(operands, *, team, league) -> Expanded(paths, errors)` (an operand that exists, has an extension or a separator, or is not a name passes through as a path string; a name goes through `_team`; a missing located file becomes a `FAIL` line in `errors`, with the hint for the league location and the `team` team, never a path for `collect_files`; `--team` with no name raises the `UsageError`; `--league` resolved first when given; `league.toml` and the league files loaded once, only when a name is present); `one_profile(raw, *, team, league) -> Path` (`named_file` for a path; for a name the located path, raising `AthcError(reason with the hint, path)` when missing).
- `src/athc/cli/profile/check.py`: `team_option`; the PATHs through `expand_names` before `collect_files`, its `errors` printed and counted with `collected.errors`.
- `src/athc/cli/profile/diff.py`: `team_option`, `league_option`; both operands through `one_profile`; dests `profile1` / `profile2`, no metavar; the `-o` extension check raises `click.BadParameter("must have a .txt or .csv extension.")`.
- `src/athc/cli/profile/copy.py`: dests `source` and `target` (`nargs=-1, required=True`), no metavar; `--substitutions` on the dest `copy_sub_percent`, label `substitutions`; the usage sentence; `team_option`, `league_option`; SOURCE through `one_profile`, the TARGETs through `expand_names`.
- `src/athc/cli/check_ppp.py`: its resolver, sources and keys import from `_team.py`; no behaviour change.
- `tests/integration/conftest.py`: check-ppp's fixtures move here; the league-folder builder `league` becomes `build_league`; `lg2_league`, `pnfl_league` and the `.lg2` team-record builder `team()` keep their names.

## Tests

New tests in `tests/integration/test_profile_check.py`, `test_profile_diff.py`, `test_profile_copy.py` and a new `tests/integration/test_team.py` for the shared resolver, building leagues with `build_league`, `lg2_league` and `team()` from `tests/integration/conftest.py`.

Resolver, tested once for every command:

- Each of the four names, in mixed case.
- `off`, `o1`, `off0` and `off3` are not names (a missing-path `FAIL`).
- A file named `off1` on disk wins over the word.
- A folder named `off1` in the current folder wins: `check off1` checks it, `copy new.prf off1` edits its files, `diff off1 x.prf` and `copy off1 x.prf` are `Access is denied.`.
- A file named `off1` is `Not a .prf file.` on `check` and among `copy`'s targets, and reaches the reader on `diff` and as `copy`'s source.
- The same word run from another folder is the name.
- `off1.prf` and `.\off1` are plain paths.
- `ppp_path` set and unset; a relative `ppp_path`.
- `ppp_path` used for `--team` naming the `team` team; skipped for another team and for `--team` with `team` unset.
- The file missing at the league location for the `team` team (the hint), for another team (no hint), and in `ppp_path` (no hint).
- `team` unset with and without `--team`; the "Team is not set" line before any `path` check.
- `--team` beats `team`.
- No `path` (the line with the alternative).
- The `.lge` missing; a stock `.lg2`.
- `--team` with a path, a wildcard and no operand (the usage error).
- `--league NOPE` with plain files (the not-found line) and with a name.
- No league configured, plain files: the command runs.
- Team-name matching limits (one match accepted, zero and two rejected) stay check-ppp's tests of the same resolver.

`check`:

- `check off2` checks that file; `check off1 def1` two files.
- A name among paths keeps PATH order.
- A missing team file is counted failed and the run continues.
- No PATH is still the current folder.
- `--team` with a name; `--team` with no PATH is the usage error.

`diff`:

- `diff off1 off2`; `diff off1 <file>`, the report naming the resolved path.
- A missing team file is 2 with nothing on stdout.
- Limits: two operands accepted, one and three rejected (Click's phrases, the extra-argument one with athc's period).
- `--team` with two plain files is the usage error.
- A bad `-o` extension is the new `Invalid value for '-o' / '--output'` line.
- `--league` with two plain files resolves the league and reads nothing else.

`copy`:

- `copy off1 off2 --stop-clock`.
- `copy <file> off1 off2 --substitutions`: two targets and the label `substitutions`.
- `copy off1 def1 --stop-clock` is one `SKIP` and exit 0; `copy off1 def1 def2 --stop-clock` two.
- `copy off1 off1` is the source `SKIP`.
- A folder and a name together; a name repeated is processed once.
- Limits: one TARGET accepted, none rejected (`Missing argument 'TARGET...'.`).
- The usage sentence lists `--substitutions`; `--sub-percent` is Click's `No such option`.

Existing tests that change:

- `tests/integration/test_profile_copy.py`: `test_cli_no_copy_flag_is_a_sentence` (the new option name), `test_cli_copies_sub_percent` (passes `--substitutions`), `test_cli_help_uses_lowercase_names` (the usage shows `SOURCE TARGET...` in caps).
- `tests/integration/test_profile_diff.py`: the test that pins the `-o` extension error (the new line).
- `tests/integration/test_cli_root.py`: `LEAGUE_COMMANDS` gains `profile diff` and `profile copy`, with `_unknown_league_args` of `[str(OFF1), str(OFF1)]` and `[str(OFF1), str(OFF1), "--stop-clock"]`.
- `tests/integration/test_cli_root.py`: `USAGE_CASES`'s `profile diff` row reads `athc profile diff [OPTIONS] PROFILE1 PROFILE2`.
- `tests/integration/test_cli_root.py`: `test_help_uses_lowercase_names`'s `profile check` and `profile diff` rows change with cli-help.md's style, as that plan lists.
- `tests/integration/test_check_ppp.py`: imports and fixture names (`build_league`, `lg2_league`, `pnfl_league`) after the move to `conftest.py`.
- Keep passing unchanged: `test_cli_requires_two_paths`, `test_cli_usage_errors_exit_2`, `test_cli_single_wrong_side_target_skipped`, `test_cli_missing_source_exit_2`, `test_cli_missing_target_exit_2`; `tests/unit/profile/test_writer.py` (the keyword keeps its name).

## Docs and meta

- `docs/profile/README.md`: the four names, `--team` and the `--league` rule in each command's section; `copy`'s `SOURCE TARGET...` and `--substitutions`; its sentence "Exit 0 (ok), 1 (a target failed), or 2" corrected to 0 / 2.
- `docs/profile/ARCHITECTURE.md`: the same for its Copy paragraph and exit line; `_common.py`'s line; the shared resolver.
- `docs/design/TODO/plans/check-ppp-cli.md`: amended as gameplan-cli.md lists (the `_team.py` move, `team_option`, the fixtures, the comment text and the rest); this plan adds nothing to that list.
- `docs/design/architecture.md`, CLI: `--team NAME` as a shared option (`team_option` beside `league_option`), the four-names rule and the existing-path rule, `profile diff` and `profile copy` in the `--league` list; Config: `team` and `ppp_path`, which check-ppp-cli.md already adds.
- `docs/design/TODO/plans/cli-help.md`: `profile copy` usage `[OPTIONS] SOURCE TARGET...` with TARGET help "Profiles, folders or wildcards to copy into."; `--team NAME` on `profile check`, `diff` and `copy`; `--league NAME` on `diff` and `copy`; its `PROFILE` placeholder gains "or one of the four names"; the argument help lines of the blocks above.
- `config/release/docs/COMMANDS.txt` sections 8 to 10: the names, `--team`, `copy`'s targets and `--substitutions`.
- `config/release/docs/README.txt` and `config/release/athc.ini`: the `team` setup note covers gameplan and profile as well as check-ppp.
- `tests/integration/README.md`: the new rows; the `profile copy` row "Copy sub-percent / field-goal-range" (`test_cli_copies_sub_percent`) renamed with the option.
- `CHANGELOG.md`: `profile:` lines.
- `STATUS.md`: the profile section and its "revisit edit/copy options" note.
- `TODO.md`.
