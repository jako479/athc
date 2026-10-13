# profile CLI plan

**Goal:** `athc profile` keeps its three commands. `check` checks `.prf` files of any name, the current folder by default, as today. `diff` and `copy` keep taking the files the coach names. New: every `.prf` operand of the three commands may also be one of four names, `off1`, `def1`, `off2` and `def2`, for one of your team's profiles where the league file puts them (or in `ppp_path`), so a coach compares or copies between halves without typing a path. `copy` takes one or more targets, and `--substitutions` replaces `--sub-percent`.

**Status:** proposal, 2026-10-13; nothing changed yet. Every choice is decided below, with its reason next to it. Reviewed twice (codebase fit, coach workflows) and passed for cross-command consistency; the findings and the rules shared with the gameplan and convert-pdb plans ([cli-help.md](cli-help.md) rules 16 to 28) are folded in. Depends on cli-help.md landing first.

## 1. Today

- `athc profile check [-h] [-r] [--league name] [path]...` (`src/athc/cli/profile/check.py`): each path is a `.prf` file, a folder (its tree with `-r`) or a wildcard; no path means the current folder (`paths = (".",)`). It needs the league's rules, `profile.toml` or the `profile_rules` array (`src/athc/profile/config.py`), so it reads the league on every run; none configured is `FAIL No rules configured. Add profile.toml to the league folder.`, exit 2. Per file `OK   <file>: <side>, FG range <n>`, or the headline `<file>: <n> violation(s) (<side>, FG range <n>)` with indented detail lines; a blank line; the tally `<n> file(s) checked, <n> with violations, <n> failed`; exit 2 when a file failed, 1 violations, 0 clean. A path that does not exist, a file of another kind and a folder with no `.prf` get `collect_files`'s lines (`src/athc/cli/_files.py`).
- `athc profile diff [-h] [-o file] file1 file2` (`src/athc/cli/profile/diff.py`): two `.prf` files, both required (`metavar="file1"`, `"file2"`), each through `named_file` (a missing one is `FAIL <path>: The system cannot find the file specified.`, 2; a folder is `FAIL <path>: Access is denied.`). Different sides: `FAIL Cannot compare <a> (offense) with <b> (defense).`, 2. The report goes to the console (`<a> -> <b>`, then `[profile]`, `[situations]`, `[pat]` and a summary line), or `<a> and <b> are identical.`; `-o FILE` writes `.txt` or `.csv` instead and prints `OK   <file>: written`, its missing folders created in full; another extension is `Error: Invalid value for --output: the format comes from the extension: use .txt or .csv.`, 2. Exit 0 identical, 1 different. No league and no rules are read: an empty config dir works (`test_entry_point_subprocess` in `tests/integration/test_profile_diff.py`).
- `athc profile copy [-h] [-r] [--stop-clock] [--sub-percent] [--field-goal-range] [--fourth-down] [--goal-line] [--pat-logic] source target` (`src/athc/cli/profile/copy.py`): `source` is one `.prf` (`named_file`, `metavar="source"`); `target` (`metavar="target"`) is one `.prf`, a folder (its tree with `-r`) or, under cli-help.md rule 15, a wildcard, collected like `check`'s paths. At least one copy option, else `Error: At least one copy option is required (--stop-clock, --sub-percent, --field-goal-range, --fourth-down, --goal-line, --pat-logic).`, 2. The source's side comes from reading it; a target's from its file size (even offense, odd defense, `_matches_side`; `docs/fbpro98_profile/specs/prf.md`). A target of the other side is `SKIP <file>: <side> profile`, the source itself `SKIP <file>: the source profile`. Each target is read, the chosen settings replaced (`ProfileWriter.apply`, `src/athc/profile/writer.py`, which refuses a side mismatch before any field) and the file written in place, no backup: `OK   <file>: updated (stop-clock, sub-percent, ...)`. Tally `<n> file(s) processed, <n> updated, <n> skipped, <n> failed`; exit 2 when a target failed, else 0 (one wrong-side target alone is a `SKIP` and 0, pinned by `test_cli_single_wrong_side_target_skipped`). No league and no rules are read.
- None of the three knows which team is yours or where the league file puts your profiles; the coach types every path. `check-ppp` is the only command that reads the `.lg2` (`src/athc/cli/check_ppp.py`); only `generate-schedule` reads the `.lge` (`src/athc/scheduler/league_files.py`, since main's dade898), and check-ppp's plan (`check-ppp-cli.md`) adds it there.
- The real league today (`PNFL.lg2` and `PNFL.lge` read 2026-10-13): 18 teams, one folder each (`PNFL\2048\Plans\<Team (Coach)>`), four distinct profiles per team. Every team's profile names carry the side and the half (`DEN-OFF1.prf`, `BUFdef2.prf`, `MIA-O1.prf`, `packersd1.prf`): 12 of 18 spell the side `off` / `OFF`, 11 `def` / `DEF`, the rest `O` / `D`. No team shares a profile across halves (four share a game plan). A team's league folder can hold other `.prf` files beside the four (older names, a stray `.prf`), and on this PC seven team folders are absent.
- The game's own stock profiles are `OFF1.PRF` and `DEF1.PRF` in an old stock league (`docs/fbpro98_lg2/specs/lg2.md` section 4.3; `docs/fbpro98_profile/README.md`) and `BILLSO1.PRF` in a modern one (section 3.3).

## 2. Who runs it, for what

| # | Who | Wants to | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach | check this week's drafts in a working folder | `athc profile check`, in that folder | every `.prf` there |
| 2 | Coach | check one draft | `athc profile check try.prf` | that file |
| 3 | Coach | check the 2nd-half offense profile the game will read | `athc profile check off2` | that file where the league file puts it, or in `ppp_path` |
| 4 | Coach | check every archived week | `athc profile check plans -r` | each file of the tree |
| 5 | Coach | check every offense draft | `athc profile check drafts\*OFF*.prf` | the matches |
| 6 | Coach | see how the 2nd half differs from the 1st | `athc profile diff off1 off2` | the report |
| 7 | Coach | see what a draft changes against the live profile | `athc profile diff off1 try.prf` | the report |
| 8 | Coach | compare the live profile with an archived week | `athc profile diff plans\wk5\DEN-OFF1.prf off1` | the report |
| 9 | Coach | keep a report for Excel | any `diff` with `-o changes.csv` | the file |
| 10 | Coach | carry 1st-half settings into the 2nd half | `athc profile copy off1 off2 --stop-clock --substitutions`, then the same with `def1 def2` | the 2nd-half files updated |
| 11 | Coach | put a tuned draft's substitutions into both halves | `athc profile copy new.prf off1 off2 --substitutions` | two targets updated |
| 12 | Coach | spread the live goal-line calls over every draft | `athc profile copy off1 drafts --goal-line` (`-r` for its tree, or `drafts\*.prf`) | each same-side file updated |
| 13 | Coach | copy stop-clock from the offense profile into both defense profiles, by mistake | `athc profile copy off1 def1 def2 --stop-clock` | two `SKIP <file>: defense profile` lines, nothing written, exit 0 |
| 14 | Coach | check what `copy` wrote | `athc check-ppp`, or `athc profile check off2` | the checks |
| 15 | Coach | run any of these before `team` is set in league.toml | the same with `--team Denver` | the same, from the league locations (`ppp_path` applies only once `team` names the team) |
| 16 | Coach | look at another team's published 2nd-half defense profile | `athc profile check --team Raiders def2` | that file at its league location |
| 17 | Coach | another league | the same with `--league PCFL` | |
| 18 | Coach | from a script | the exit code; `2> errors.txt` keeps the problem lines | |

## 3. What other tools do

- **Two operands name the two things compared; nothing is compared by default.** Windows `fc`: "Compares two files or sets of files and displays the differences between them."; "filename1 is required", "filename2 is required"; its exit codes are "0 Files are identical", "1 Files are different", "2 An error occurred during comparison", athc's own three. GNU `diff`: `Usage: diff [OPTION]... FILES`, "FILES are 'FILE1 FILE2' or 'DIR1 DIR2' or 'DIR FILE' or 'FILE DIR'", "Exit status is 0 if inputs are the same, 1 if different, 2 if trouble." git's `--no-index` form "is to compare the given two paths on the filesystem"; a bare `git diff` works only because git has a baseline, "the changes you made relative to the index".
- **Source first, then where it goes; one source into many files.** Windows `copy`: "Copies one or more files from one location to another.", `copy ... <source> ... [<destination> ...]`, both marked "Required". `tee`: `Usage: tee [OPTION]... [FILE]...`, "Copy standard input to each FILE". cli-help.md's model is `cp [OPTION]... SOURCE DEST`.
- **An existing path wins over a word.** athc's own rule: cli-help.md rule 15, "A name that exists is a name, never a wildcard", and `_is_path` in `src/athc/cli/gameplan/replace_play.py`, which tests "an existing file or folder (first, so a folder named like a play is the folder)", then a folder separator, a `.pln` extension or a wildcard, before taking the word as a play name.
- **The game's names for the four files.** Stock leagues ship `OFF1.PRF` and `DEF1.PRF` (old) and `BILLSO1.PRF` (modern); every PNFL team names its profiles the same way (section 1).
- **Literal words in lowercase, placeholders in caps.** cli-help.md rule 2 reserves UPPERCASE for placeholders; Click shows `Choice` values as given, so athc's own `list-normals` usage reads `[--sort slot|name|category]` (`tests/integration/test_cli_root.py`). Click's `Choice(case_sensitive=False)` matches after casefolding ("Set to false to make choices case insensitive", `click/types.py`); Windows file names and commands ignore case.
- **Standard flags, consistency, defaults.** clig.dev: "Prefer flags to args", but "Multiple arguments are fine for simple actions against multiple files"; "Make the default the right thing for most users"; "Be consistent across subcommands"; "Use standard names for flags, if there is a standard" (`-n, --dry-run`: "Do not run the command, but describe the changes that would occur if the command were run").
- **A required variadic argument.** Click makes an argument required by default only when "it has no explicit default value set and is setup to match at least one value" (`required = nargs > 0`, `click/core.py`), so `nargs=-1` needs `required=True`; an empty tuple is then missing and raises `MissingParameter`: `Missing argument '<hint>'.`, exit 2, where the hint is the argument's metavar as set, or Click's own `NAME...` built from the dest when none is set (`Argument.make_metavar`, `get_error_hint`; `MissingParameter.format_message`). A third operand of a fixed-count command is Click's `Got unexpected extra argument (<x>)`, no period.
- **A contradicting flag is an error; an unused one is not.** check-ppp decision 10: `--team` with two files "is a contradiction, not a no-op, so it is a usage error", while "a no-op flag such as `-r` with two files stays ignored". `playpool check` with an explicit folder needs no league, yet re-raises when a league the user named does not exist ("a league the user named must exist", `src/athc/cli/playpool/check.py`).

## 4. Decisions

1. **The three commands stay, and no command takes "the team's four profiles" as a set.** `check` checks files of one kind by any name (check-ppp decision 1 and section 8; STATUS.md); the four with their game plans are `check-ppp`'s job, and a coach who wants one or more of the four profiles alone names them (decision 3).
2. **`check` keeps the current folder as its no-PATH default,** a stated deviation from check-ppp decision 3's "no PATH means the configured source": it is the generic one-kind checker over drafts the league file never names (rows 1, 2, 5), the current folder is pytest's, ruff's and today's default, and the configured default (your team's files) belongs to `check-ppp`. `.` and an explicit path behave as today and as in `check-ppp`.
3. **Every `.prf` operand may be one of the four names, `off1`, `def1`, `off2` or `def2`:** the 1st-half offense, 1st-half defense, 2nd-half offense or 2nd-half defense profile of your team (`.lg2` file entries 1, 3, 5 and 7), in `check`'s PATH, `diff`'s PROFILE1 and PROFILE2, and `copy`'s SOURCE and TARGET. The words are the game's own stock names and the pattern every PNFL coach already uses; `gameplan`'s commands take the same four words for the game plans (entries 2, 4, 6 and 8). One spelling, lowercase, since cli-help.md rule 2 reserves caps for placeholders and Click shows choice values as given (`slot|name|category`); matched after casefolding, Click's `Choice(case_sensitive=False)` behaviour, so `OFF1` works; no synonyms (`o1`, `offense-1`), so the help lists all four.
4. **An existing path wins over a name** (cli-help.md rule 15; replace-play's `_is_path`, which puts "an existing file or folder" first). An operand that exists on disk, file or folder, is a path whatever it is called; an operand with an extension or a folder separator is a path too (`off1.prf`, `.\off1`); else one of the four words is the team's file; else it is a missing path and gets today's line. So a folder named `off1` in the current folder is that folder: `check off1` checks its `.prf` files (or `WARN off1: No .prf files.`), `copy new.prf off1 --stop-clock` edits every same-side `.prf` in it, and `diff off1 try.prf` is `FAIL off1: Access is denied. Run from another folder to use your team's profile.`, the one imperative hint sentence every one-file operand that takes a name adds (`diff`'s PROFILE1 and PROFILE2, `copy`'s SOURCE; `gameplan`'s line with "profile" for "game plan"; the project's hint shape, architecture.md Wording). `.\off1` always means the path; since existence is tested against the current folder, running from another folder yields the word. A file named `off1` is a path like any other: on `check`'s PATH and `copy`'s TARGET it is `FAIL off1: Not a .prf file.` (`collect_files`, as today); on `diff` and `copy`'s SOURCE it reaches the reader, which gives its own line.
5. **A name resolves through check-ppp decision 3's sources and decision 4's team:** the file's `.lg2` name in `ppp_path`, else the league location (`path` joined with the file's `.lg2` folder and name); the team is `team` in league.toml or `--team NAME`, matched by the `.lge` names as check-ppp decision 5 says (name, nickname or both, without case, exactly one match). No new keys.
6. **`ppp_path` applies only to the team `team` names** (check-ppp decision 4): `--team` naming that same team goes through it; `--team` naming another team, or `--team` with `team` unset or unresolvable, uses the league locations (rows 15 and 16).
7. **`--team NAME` and `--league NAME` sit on all three commands,** `--team` for a coach whose `team` is not set yet (row 15) and never `--all-teams` (coach commands only). `--team` without one of the four names among the operands is a contradiction, as `--team` with two files is in check-ppp decision 10: Click's usage error `Error: Cannot use --team with a path.`, exit 2; `check` with no PATH counts too, since the current folder names no team, and the rule is the same on every command, `gameplan check` included. `--league NAME` is never a contradiction: it is the shared option of every league command, a named league must exist (today's `League 'NOPE' not found` line from `league_dir` in `src/athc/config.py`, as `playpool check` with an explicit folder does), and the league's files are read only when something needs them. `check` reads the league on every run for its rules; `diff` and `copy` read `league.toml`, the `.lg2` and the `.lge` only when an operand is a name, and with plain files and no `--league` read no config at all (today's `test_entry_point_subprocess` runs `diff` with an empty config dir).
8. **`diff` takes exactly two operands, and no argument is a usage error,** Click's `Missing argument` line: `fc` and `diff` require both files, and athc has no one baseline a bare `diff` could mean (the other half, last week's file and the league copy are all plausible; git's bare form works only because the index is its baseline). Folders are not operands: one run is one report, so `-o` writes one file and exit 1 means "these two differ" (`fc`'s and `diff`'s codes).
9. **`copy` takes `SOURCE TARGET...`:** one source, one or more targets, each a `.prf` file, a folder, a wildcard or a name; targets are collected in order and each file once, as `check`'s paths are. `tee` is the shape (one input, each FILE); the common pair is the team's two same-side profiles (rows 10, 11). No TARGET or no SOURCE is Click's `Missing argument` line (Windows `copy`: source and destination "Required"); the argument is `nargs=-1, required=True`, since Click leaves a variadic argument optional by default.
10. **1st half to 2nd half is `copy off1 off2 ...` and `copy def1 def2 ...`; offense to defense stays one `SKIP <file>: defense profile` per wrong-side target, exit 0,** as today for one wrong-side target: the writer refuses any side mismatch before any field (`ProfileTypeMismatchError`, `src/athc/profile/writer.py`), `_matches_side` in `copy.py` skips a wrong-side target by its file-size parity (prf.md section 2.2's trailer), and the rule is one whether a target came from a folder or by name. Nothing is safe to carry across: `--substitutions` replaces the whole `SubstitutionSettings`, and while "All 32 bytes [are] physically present in both offense and defense profiles", "The UI exposes only the offense groups (OL, QB, RB, WR, K) when editing an offense profile and only the defense groups (DL, LB, DB) for defense" (prf.md section 2.2), so a cross-side copy would land the source's editable groups in the target's non-editable ones; the situation and PAT tables carry the side's own category codes (prf.md section 2.3.2). Any change to that is TODO.md's 2.0.0 item "profile: revisit edit\copy options". A source that is also a target (`copy off1 off1`) is today's `SKIP <file>: the source profile`.
11. **`--substitutions` replaces `--sub-percent`** (cli-help.md, profile copy); the `OK` line's label follows, `updated (substitutions)`, and the usage error lists the new name. The writer's keyword `copy_sub_percent` is tool logic and keeps its name.
12. **The other copy options stay:** `--stop-clock`, `--field-goal-range`, `--fourth-down`, `--goal-line`, `--pat-logic`; at least one is required, as today. No `--dry-run` and no backup: TODO.md defers "revisit edit\copy options" to 2.0.0, `diff` is the preview (`diff off1 try.prf` before `copy try.prf off1`), and architecture.md's in-place rule holds.
13. **`-r` keeps today's meaning** on `check` (a PATH folder's tree) and `copy` (a TARGET folder's tree), with cli-help.md rule 10's text (check-ppp decision 9); it is ignored for files and names.
14. **Missing team files.** Whether a name's file exists is decided when the name is resolved, before anything reads it (check-ppp decision 6), and the resolver builds the line itself: `FAIL <path>: The system cannot find the file specified.` (the path phrase when its folder is missing too, `missing_reason`). At the league location, when the team is the one `team` names, the line adds `Set ppp_path in <league.toml>, or pass the file.` (check-ppp's hint for your team's files, with "file" for "folder"); for another team, or in `ppp_path`, it adds nothing, since `ppp_path` cannot apply or is the coach's own choice. For `diff` and for `copy`'s SOURCE nothing runs (2); in `check` and among `copy`'s targets it counts as failed and the run continues, as a missing path does today.
15. **Setup order:** the arguments (Click, the `--team`-with-a-path error included); then `--league` resolved whenever it is given (decision 7); then, when a name is present, `league.toml` read for `team` alone (so a missing `team` shows before a missing `path`), then `path`, the `.lg2` with its stock check, the `.lge`, the team counts and the team match (check-ppp decision 12's order); then `check`'s rules; then the files. A `--team` typo shows before any file is read.
16. **The lines stay the three commands' lines;** the new ones are the setup lines and `copy`'s renamed label (section 7). Codes stay 0 / 1 / 2.
17. **Help text is cli-help.md's:** the blocks of section 5. The arguments carry no metavar; Click derives `PROFILE1`, `PROFILE2`, `SOURCE` and `TARGET...` from the dests, so the usage line and the error hints agree (cli-help.md's shared rule).

## 5. The commands

### Where an operand's file comes from

| Operand | Team | File | Needs |
|---|---|---|---|
| a path that exists, or one with an extension or a folder separator | none | that file (a folder or a wildcard where the command allows one) | nothing |
| `off1`, `def1`, `off2` or `def2` (any case), `ppp_path` set | the one `team` names, by default or with `--team` naming it | `<ppp_path>\<its .lg2 name>` | `path`, the `.lg2` and `.lge`, `team` |
| `off1`, `def1`, `off2` or `def2`, no `ppp_path` | the same | `<path>\<its .lg2 folder>\<its .lg2 name>` | the same |
| `off1`, `def1`, `off2` or `def2` | another team with `--team`, or `--team` with `team` unset or unresolvable | `<path>\<its .lg2 folder>\<its .lg2 name>`, `ppp_path` not used | `path`, the `.lg2` and `.lge` |
| `off1`, `def1`, `off2` or `def2` | `team` unset or unresolvable, no `--team` | nothing is located: section 7's "No team" line, or the no-match / two-match line | `league.toml` |
| anything else | none | a missing path, today's line | nothing |

The `.lg2` entries (`docs/fbpro98_lg2/specs/lg2.md` section 2.2): `off1` is file entry 1 (1st-half offense profile), `def1` entry 3, `off2` entry 5, `def2` entry 7.

### profile (group)

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

A bare `athc profile` prints this help on stderr and exits 2, as every bare group does (architecture.md, CLI; Click's `no_args_is_help` default for a group).

### profile check

```
Usage: athc profile check [OPTIONS] [PATH]...

  Check profiles against the league's rules.

  Each profile prints OK or its violations. To check a profile with its game
  plan, run athc check-ppp.

Positional arguments:
  PATH  .prf files, folders or wildcards, or off1, def1, off2 or def2 for one
        of your team's profiles (default: current folder).

Options:
  -r, --recursive  Include subfolders.
  --team NAME      Team whose profiles off1, def1, off2 and def2 name (default:
                   team in league.toml).
  --league NAME    League to use (default: the one set with athc config set
                   league).
  -h, --help       Show this message and exit.

  Examples:

    athc profile check
    athc profile check off2
    athc profile check drafts\*OFF*.prf
```

- Unchanged otherwise (check-ppp section 8): no PATH is the current folder; each file's lines, the tally and the codes as today.
- Order: PATH order, a folder's files sorted; a name takes its place in the order like a file.
- Argument errors: as today; `--team` with no name among the PATHs (none given included) is the usage error of decision 7; a name whose file is missing is a `FAIL` counted failed (decision 14).

### profile diff

```
Usage: athc profile diff [OPTIONS] PROFILE1 PROFILE2

  Show differences between two profiles.

  Compares situations, PAT situations, substitutions, field-goal range and
  audibles; only what changed is shown. Both must be the same side.

Positional arguments:
  PROFILE1  A .prf file, or off1, def1, off2 or def2 for one of your team's
            profiles.
  PROFILE2  The profile to compare it with, named the same way.

Options:
  -o, --output FILE  Write the report to FILE instead of the console (.txt, or
                     .csv for Excel).
  --team NAME        Team whose profiles off1, def1, off2 and def2 name
                     (default: team in league.toml).
  --league NAME      League to use (default: the one set with athc config set
                     league).
  -h, --help         Show this message and exit.

  Examples:

    athc profile diff off1 off2
    athc profile diff off1 try.prf -o changes.csv
```

- The report names each file by the operand's resolved path (`<path> -> <path>`), so a name shows the file it stood for.
- Argument errors: no operand is Click's `Error: Missing argument 'PROFILE1'.`, one operand `'PROFILE2'.`; three operands is `Error: Got unexpected extra argument (<x>).` (Click's text, athc's period added once in `src/athc/cli/__init__.py` where usage errors are rendered, the mechanism in convert-pdb-cli.md decision 22); `--team` with two paths is the usage error of decision 7; a folder named like one of the four names is the hinted `Access is denied.` line of decision 4; a bad `-o` extension as today.

### profile copy

```
Usage: athc profile copy [OPTIONS] SOURCE TARGET...

  Copy settings from one profile to others.

  Pick the settings with one or more options. Targets of the other side are
  skipped. Rules are not checked; run athc profile check afterward.

Positional arguments:
  SOURCE  Profile to copy from: a .prf file, or off1, def1, off2 or def2 for
          one of your team's profiles.
  TARGET  Profiles to copy into: .prf files, folders or wildcards, or off1,
          def1, off2 or def2.

Options:
  -r, --recursive     Include subfolders.
  --stop-clock        Copy the stop-clock setting of every situation.
  --substitutions     Copy the substitution percentages.
  --field-goal-range  Copy the field-goal range.
  --fourth-down       Copy every 4th-down situation.
  --goal-line         Copy every goal-line situation (inside the 5).
  --pat-logic         Copy the PAT table (60 situations).
  --team NAME         Team whose profiles off1, def1, off2 and def2 name
                      (default: team in league.toml).
  --league NAME       League to use (default: the one set with athc config set
                      league).
  -h, --help          Show this message and exit.

  Examples:

    athc profile copy off1 off2 --stop-clock --substitutions
    athc profile copy new.prf off1 off2 --substitutions
```

- Order: targets in TARGET order, a folder's files sorted, each file once (its first mention); then the blank line and the tally, as today.
- Argument errors: no SOURCE is Click's `Error: Missing argument 'SOURCE'.`, no TARGET `'TARGET...'.` (Click's own placeholders from the dests, section 9); no copy option is today's sentence with `--substitutions`; `--team` with no name among SOURCE and the TARGETs is the usage error of decision 7; a missing target is a `FAIL` counted failed; a missing SOURCE stops the run before any target is touched, as today.

## 6. Settings

In `league.toml`, under `[league]`: the keys check-ppp-cli.md adds, nothing new. The `path` and `team` comment text is the one check-ppp-cli.md section 6 owns, quoted here:

```toml
# Needed for check-ppp and generate-schedule, and for off1, def1, off2 and def2 in gameplan, profile and convert-pdb -- the folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# Your team, for the same commands: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

- `check` reads `profile.toml` (or `profile_rules`) as today; `diff` and `copy` read no rules.
- `ppp_path` applies only to the team `team` names (decision 6).
- `<league>.lg2` and `<league>.lge` are read from `path` only when an operand is one of the four names.

## 7. Lines and exit codes

New or changed lines, in the project's wording; everything else prints as today.

| When | Line | Code |
|---|---|---|
| a name, no `team`, no `--team` | `FAIL <league.toml>: No team for the league. Set team in this file, or pass --team or a .prf file.` | 2 |
| `team` matches no team, two teams, or is an array | check-ppp's lines (one shared resolver) | 2 |
| `--team` matches no team or two teams | check-ppp's `Error: Invalid value for '--team': ...` lines | 2 |
| `--team` with no name among the operands (a path, a wildcard, or `check` with no PATH) | `Error: Cannot use --team with a path.` | 2 |
| `--league NOPE`, whatever the operands | `FAIL League 'NOPE' not found. No folder <leagues>\NOPE. Available: PCFL, PNFL.` (today's `league_dir` line) | 2 |
| a name, no `path` | `FAIL <league.toml>: No path for the league. Set path in this file, or pass a .prf file.` | 2 |
| `.lg2` or `.lge` missing or bad, a stock league, team counts that differ | the libraries' and check-ppp's lines | 2 |
| `ppp_path` missing on disk, or a file | check-ppp's line | 2 |
| a team file missing at the league location, the team is the one `team` names | `FAIL <path>\PNFL\2048\Plans\Denver (Brian)\DEN-OFF2.prf: The system cannot find the file specified. Set ppp_path in <league.toml>, or pass the file.` (the path phrase when the folder is missing) | `diff`, `copy` SOURCE: 2; `check`, `copy` TARGET: counted failed, 2 at the end |
| a team file missing at the league location, another team | the same line without the hint | the same |
| a team file missing in `ppp_path` | `FAIL <ppp_path>\DEN-OFF2.prf: The system cannot find the file specified.` | the same |
| a folder named like one of the four names given as `diff`'s PROFILE1 or PROFILE2 or `copy`'s SOURCE | `FAIL off1: Access is denied. Run from another folder to use your team's profile.` | 2 |
| a file named like one of the four names on `check`'s PATH or among `copy`'s TARGETs | `FAIL off1: Not a .prf file.` (`collect_files`, as today) | counted failed, 2 at the end |
| `diff` with no operand, or one | `Error: Missing argument 'PROFILE1'.` / `'PROFILE2'.` (Click) | 2 |
| `diff` with three operands | `Error: Got unexpected extra argument (<x>).` (Click's text, athc's period from the shared change in `src/athc/cli/__init__.py`) | 2 |
| `copy` with no SOURCE or no TARGET | `Error: Missing argument 'SOURCE'.` / `'TARGET...'.` (Click) | 2 |
| `copy` without a copy option | `Error: At least one copy option is required (--stop-clock, --substitutions, --field-goal-range, --fourth-down, --goal-line, --pat-logic).` | 2 |
| `copy` updated a target's substitutions | `OK   <file>: updated (substitutions)` (was `sub-percent`) | |

`--league` with plain files is resolved and nothing else is read. Codes stay: `check` 0 clean / 1 violations / 2 error; `diff` 0 identical / 1 different / 2 error; `copy` 0 done (skips included) / 2 error.

## 8. Related commands

- `check-ppp` checks the four profiles with their game plans and is where a bare "check my files" goes; `profile check`'s help and README point at it, and `check-ppp`'s one-file error points back (its decision 2). It shares `team`, `ppp_path`, `path`, the team resolver and the lines.
- `gameplan` takes the same four names for a team's game plans, with the same `--team` and the same resolver.
- `profile copy` points at `profile check` and `check-ppp` for the check afterward; `profile diff` is the preview before a copy.

## 9. Code

- `src/athc/cli/__init__.py`: `team_option(head)` beside `league_option`, the `--team NAME` decorator that joins the command's head to the fixed tail `(default: team in league.toml).`; profile's head is "Team whose profiles off1, def1, off2 and def2 name". architecture.md's "What goes where" puts shared option decorators here. The same module adds athc's period to Click's `Got unexpected extra argument (x)` once, where usage errors are rendered (convert-pdb-cli.md decision 22).
- `src/athc/cli/_team.py` (new, beside `_files.py`): the team layer shared by `check-ppp`, `gameplan` and `profile`, moved out of `check_ppp.py` (check-ppp-cli.md section 9 is amended; section 11 here). `TEAM_FILE_NAMES = ("off1", "def1", "off2", "def2")`; the keys `TEAM_KEY = "team"`, `PPP_PATH_KEY = "ppp_path"`, `LEAGUE_PATH_KEY = "path"` (in `src/athc/config.py` since main's dade898; `_team.py` imports it); `load_league_files(league, league_dir)`, the `.lg2` with its stock check, then the `.lge`, then the team counts compared (check-ppp decision 12's order); `resolve_team(name, lge)`, check-ppp decision 5's matcher with its two error lines; `team_files(team, kind)`, the team's four `(name, file)` pairs of one kind in `.lg2` order with a shared file repeated, so a caller with fixed slots knows which slot each file fills, while profile's callers drop repeats by resolved path, as `collect_files` already does; `locate(file, ppp_path, league_path) -> Located(path, exists, source)`, check-ppp decision 3's sources with existence decided before any read.
- `src/athc/cli/profile/_common.py`: `expand_names(operands, *, team, league) -> Expanded(paths, errors)`: an operand that exists, has an extension or a separator, or is not one of the four names passes through as a path string; a name goes through `_team`, and a located file that does not exist becomes a `FAIL` line in `errors` (the hint when the source is the league location and the team is the one `team` names), never a path for `collect_files`; `--team` with no name raises the `UsageError`; `--league` is resolved first when given, and `league.toml` and the league files are loaded here once, only when a name is present. `one_profile(raw, *, team, league) -> Path`: `named_file` for a path, with the folder hint sentence of decision 4 added to its `Access is denied.` when the path is a folder spelled like one of the four names; for a name the located path, raising `AthcError(reason with the hint, path)` when it is missing.
- `src/athc/cli/profile/check.py`: `team_option`; the PATHs through `expand_names` before `collect_files`, its `errors` printed and counted with `collected.errors`.
- `src/athc/cli/profile/diff.py`: `team_option`, `league_option`; both operands through `one_profile`; the dests `profile1` / `profile2` with no metavar, so Click shows `PROFILE1 PROFILE2` and the missing-argument hint reads `'PROFILE1'` (cli-help.md's no-metavar rule).
- `src/athc/cli/profile/copy.py`: the dests `source` and `target`, the latter `nargs=-1, required=True`, no metavar, so Click builds `SOURCE` and `TARGET...` for the usage line and the hints `'SOURCE'` and `'TARGET...'` (a dest named `targets` would read `TARGETS...`). `--substitutions` on the dest `copy_sub_percent`, label `substitutions`; the usage sentence; `team_option`, `league_option`; SOURCE through `one_profile`, the TARGETs through `expand_names`.
- `src/athc/cli/check_ppp.py`: its resolver, sources and keys import from `_team.py`; no behaviour change.
- `tests/integration/conftest.py`: check-ppp's fixtures move here under the names every plan shares, since eight integration modules (`test_profile_check.py` among them) and `tests/unit/pdbtoexcel/test_config.py` define a fixture named `league` that would override a conftest one: the league-folder builder `league` becomes `build_league`, while `lg2_league` (a built league with its `.lg2` and `.lge` beside `league.toml`), `pnfl_league` (the real PNFL fixtures copied in) and the `.lg2` team-record builder `team()` keep their names (main's `tests/integration/league_files.py` module rules out a `league_files` fixture); `tests/integration/test_check_ppp.py` switches to these names.

## 10. Tests

New tests, in `tests/integration/test_profile_check.py`, `test_profile_diff.py`, `test_profile_copy.py` and a new `tests/integration/test_team.py` for the shared resolver, all building leagues with `build_league`, `lg2_league` and `team()` from `tests/integration/conftest.py`:

- Resolver, tested once for every command: each of the four names, in mixed case; `off`, `o1` and `off3` are not names (a missing-path `FAIL`); a file named `off1` on disk wins over the word; a folder named `off1` in the current folder wins too (`check off1` checks it, `copy new.prf off1` edits its files, `diff off1 x.prf` and `copy off1 x.prf` are `Access is denied. Run from another folder to use your team's profile.`), a file named `off1` is `Not a .prf file.` on `check` and among `copy`'s targets and reaches the reader on `diff` and as `copy`'s source, and the same word run from another folder is the name; `off1.prf` and `.\off1` are plain paths; `ppp_path` set and unset; a relative `ppp_path`; `ppp_path` used for `--team` naming the `team` team, skipped for another team and for `--team` with `team` unset; the file missing at the league location for the `team` team (the hint) and for another team (no hint), and in `ppp_path` (no hint); `team` unset with and without `--team`, the "No team" line before any `path` check; `--team` beats `team`; no `path` (the line with the alternative); the `.lge` missing; a stock `.lg2`; `--team` with a path, a wildcard and no operand (the usage error); `--league NOPE` with plain files (the not-found line) and with a name; no league configured, plain files: the command runs. Team-name matching limits (one match accepted, zero and two rejected) stay check-ppp's tests of the same resolver.
- `check`: `check off2` checks that file; `check off1 def1` two files; a name among paths keeps PATH order; a missing team file is counted failed and the run continues; no PATH is still the current folder; `--team` with a name; `--team` with no PATH is the usage error.
- `diff`: `diff off1 off2`; `diff off1 <file>`, the report naming the resolved path; a missing team file is 2 with nothing on stdout; limits: two operands accepted, one and three rejected (Click's phrases, the extra-argument one with athc's period); `--team` with two plain files is the usage error; `--league` with two plain files resolves the league and reads nothing else.
- `copy`: `copy off1 off2 --stop-clock`; `copy <file> off1 off2 --substitutions`, two targets and the label `substitutions`; `copy off1 def1 --stop-clock` is one `SKIP` and exit 0, `copy off1 def1 def2 --stop-clock` two; `copy off1 off1` is the source `SKIP`; a folder and a name together; a name repeated is processed once; limits: one TARGET accepted, none rejected (`Missing argument 'TARGET...'.`); the usage sentence lists `--substitutions`; `--sub-percent` is Click's `No such option`.
- Existing tests that change: `tests/integration/test_profile_copy.py`: `test_cli_no_copy_flag_is_a_sentence` (the new option name), `test_cli_copies_sub_percent` (passes `--substitutions`), `test_cli_help_uses_lowercase_names` (the usage shows `SOURCE TARGET...` in caps). `tests/integration/test_cli_root.py`: `LEAGUE_COMMANDS` gains `profile diff` and `profile copy`, with `_unknown_league_args` of `[str(OFF1), str(OFF1)]` and `[str(OFF1), str(OFF1), "--stop-clock"]` (a named league is resolved whatever the operands); `USAGE_CASES`'s `profile diff` row reads `athc profile diff [OPTIONS] PROFILE1 PROFILE2`; `test_help_uses_lowercase_names`'s `profile check` and `profile diff` rows change with cli-help.md's style, as that plan lists. `tests/integration/test_check_ppp.py`: imports and fixture names (`build_league`, `lg2_league`, `pnfl_league`) after the move to `conftest.py`. `test_cli_requires_two_paths`, `test_cli_usage_errors_exit_2`, `test_cli_single_wrong_side_target_skipped`, `test_cli_missing_source_exit_2` and `test_cli_missing_target_exit_2` keep passing by design. `tests/unit/profile/test_writer.py` is unchanged (the keyword keeps its name).

## 11. Docs and meta

- `docs/profile/README.md`: the four names, `--team` and the `--league` rule in each command's section; `copy`'s `SOURCE TARGET...` and `--substitutions`; its sentence "Exit 0 (ok), 1 (a target failed), or 2" corrected to the code's and its own table's 0 / 2 (architecture.md: a file that failed inside a batch is 2). `docs/profile/ARCHITECTURE.md`: the same for its Copy paragraph and exit line; `_common.py`'s line; the shared resolver.
- `docs/design/TODO/check-ppp-cli.md`: amended as gameplan-cli.md section 11 lists (the `_team.py` move, `team_option`, the fixtures, the comment text and the rest); this plan adds nothing to that list.
- `docs/design/architecture.md`, CLI: `--team NAME` as a shared option (`team_option` beside `league_option`), the four-names rule and the existing-path rule, `profile diff` and `profile copy` in the `--league` list; Config: `team` and `ppp_path`, which check-ppp-cli.md already adds.
- `docs/design/TODO/cli-help.md` changes: `profile copy` usage `[OPTIONS] SOURCE TARGET...` with TARGET help "Profiles, folders or wildcards to copy into."; `--team NAME` (rule 18) on `profile check`, `diff` and `copy`; `--league NAME` on `diff` and `copy`; rule 3's `PROFILE` gains "or one of the four names"; the argument help lines of section 5.
- `config/release/docs/COMMANDS.txt` sections 8 to 10: the names, `--team`, `copy`'s targets and `--substitutions`; `config/release/docs/README.txt` and `config/release/athc.ini`: the `team` setup note covers gameplan and profile as well as check-ppp.
- `tests/integration/README.md`: the new rows; the `profile copy` row "Copy sub-percent / field-goal-range" (`test_cli_copies_sub_percent`) renamed with the option.
- `CHANGELOG.md` (`profile:` lines), `STATUS.md` (the profile section and its "revisit edit/copy options" note), `TODO.md`.

## Shared vocabulary

- **The four names:** `off1`, `def1`, `off2`, `def2`, lowercase in help and docs, matched without case; the team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense file of the command's kind (`.prf` under `profile`, `.pln` under `gameplan`; `.lg2` entries 1 to 8 in that order), from `ppp_path` by `.lg2` name, else the league location. Accepted wherever a `.prf` operand is (PATH, PROFILE1, PROFILE2, SOURCE, TARGET). An existing path, file or folder, and any operand with an extension or a separator win over a word; `o1`, `off` and the like are not names.
- **`--team NAME`:** on every command that accepts the four names, declared once as `team_option(head)` in `src/athc/cli/__init__.py`, the shared decorator adding the fixed tail; profile's head "Team whose profiles off1, def1, off2 and def2 name", so the help reads "Team whose profiles off1, def1, off2 and def2 name (default: team in league.toml)." (`gameplan`: "Team whose game plans ..."). With no name among the operands it is `Error: Cannot use --team with a path.`, exit 2.
- **`--league NAME`:** never a contradiction; a named league must exist; the league's files are read only when needed.
- **`SOURCE TARGET...`:** one source, one or more targets, for a copy command.
- **Hints:** `No team for the league. Set team in this file, or pass --team or a .prf file.`; `No path for the league. Set path in this file, or pass a .prf file.`; `Set ppp_path in <league.toml>, or pass the file.` on a team file missing at the league location when the team is the one `team` names; `Run from another folder to use your team's profile.` after `Access is denied.` on a one-file operand.
- **Shared code and fixtures:** `src/athc/cli/_team.py` (`TEAM_FILE_NAMES`, `load_league_files`, `resolve_team`, `team_files`, `locate` / `Located`); `tests/integration/conftest.py` (`build_league`, `lg2_league`, `pnfl_league`, `team()`).

## Sources

- Windows `fc`: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/fc>
- Windows `copy`: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/copy>
- git diff, `--no-index` and the bare form: <https://git-scm.com/docs/git-diff>
- clig.dev: <https://clig.dev/>
- `tee --help` and `diff --help` (GNU coreutils and diffutils, Git for Windows): local help output
- Click `Choice(case_sensitive)`, `Argument.__init__` (`required = nargs > 0`), `Argument.make_metavar` and `get_error_hint`, `Parameter.process_value` and `value_is_missing`, `MissingParameter.format_message`, the extra-argument text, `Group.__init__`'s `no_args_is_help` default: `click/types.py`, `click/core.py`, `click/exceptions.py` in the venv (Click 8.4.1)
- athc: `src/athc/cli/profile/check.py`, `copy.py`, `diff.py`, `_common.py`, `src/athc/cli/_files.py`, `src/athc/cli/__init__.py`, `src/athc/cli/check_ppp.py`, `src/athc/cli/gameplan/replace_play.py` (`_is_path`), `src/athc/cli/playpool/check.py`, `src/athc/config.py` (`league_dir`), `src/athc/profile/writer.py`, `errors.py`, `config.py`, `src/athc/fbpro98_lg2/model.py`, `reader.py`, `src/athc/fbpro98_lge/model.py`, `src/athc/fbpro98_profile/model.py`, `docs/fbpro98_lg2/specs/lg2.md`, `docs/fbpro98_profile/README.md`, `docs/fbpro98_profile/specs/prf.md`, `docs/profile/README.md`, `docs/profile/ARCHITECTURE.md`, `docs/design/architecture.md`, `docs/design/TODO/check-ppp-cli.md`, `docs/design/TODO/cli-help.md`, `docs/design/TODO/gameplan-cli.md` (section 11), `docs/design/TODO/convert-pdb-cli.md` (decision 22), `config/release/docs/COMMANDS.txt`, `config/release/leagues/PNFL/league.toml`, `STATUS.md`, `TODO.md`, `tests/integration/conftest.py`, `tests/integration/README.md`, `tests/integration/test_profile_check.py`, `test_profile_copy.py`, `test_profile_diff.py`, `test_cli_root.py`, `test_check_ppp.py`, `tests/unit/profile/test_writer.py`; today's help output of `athc profile`, `profile check`, `profile copy` and `profile diff`
- The real `PNFL.lg2` and `PNFL.lge` in the folder the dev `league.toml` names (`E:\SIERRA\FbPro98`), and the team folders under it, read on 2026-10-13
