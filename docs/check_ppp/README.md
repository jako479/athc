# check-ppp

Check coaching profiles (`.prf`) against their game plans (`.pln`), as the
league file pairs them: each file against the league rules, and each pair for
how it fits. Replaced `profile check --gameplan`.

## Usage

```bash
athc check-ppp
athc check-ppp .
athc check-ppp --all-teams handed-in -r
athc check-ppp --team "Las Vegas" handed-in
athc check-ppp DEN-OFF1.prf DEN-OGP1.pln
```

| PATH | Team | Files come from | A missing file |
|---|---|---|---|
| none, `ppp_path` set | your team (`team`, or `--team` naming it) | `ppp_path`, each file by its `.lg2` name; with `-r`, each folder of its tree on its own | a partner: `WARN`, counted as missing; a whole pair: nothing; all the team's files: one `WARN` |
| none | `team`, `--team` or `--all-teams` | the league locations: `path` joined with each file's `.lg2` folder | a file: `FAIL`, counted as failed; all the team's files: one `FAIL` per folder |
| a folder | `team`, `--team` or `--all-teams` | that folder (`.` is the current one); with `-r`, each folder of its tree on its own | as the first row |
| one `.prf` and one `.pln` | none | the two files, in either order | `FAIL` |

- The team is `team` in `league.toml`, `--team NAME` for one run, or
  `-a, --all-teams` for every team. A name is the `.lge` team name, the
  nickname or both (`Denver`, `Broncos`, `Denver Broncos`), matched without
  case; exactly one team must match.
- `ppp_path` is for your team only: the team `team` names, by default or
  named with `--team`. Another team and `--all-teams` use the league
  locations.
- One file alone is an error that names the command that checks it alone
  (`profile check`, `gameplan check`).
- `--team` or `--all-teams` with two files, or both flags together, is a
  usage error. `-r` with two files, or at the league locations, is ignored.

The rules come from `--league NAME`, or from `[athc] league` in `athc.ini`.
`athc check-ppp --help` gives the short form; the rules are below.

## Finding the files

The league's `.lg2` and `.lge` in `path` are named after the league. The
`.lg2` lists each team's four pairs: 1st-half offense profile and game plan,
1st-half defense, 2nd-half offense, 2nd-half defense. The `.lge` names the
teams, in the same order.

- In a folder, each file is found by its `.lg2` name, without case. The
  folder modes always use the current league file's names, so an archived
  season of a renamed team shows as "no files".
- At the league locations, `path` may point at a copy of the league's files;
  the `.lg2` folders resolve under it.
- A stock league's `.lg2` is an error; so are two league files that list
  different team counts.
- Order: top folder first, then subfolders by name; inside a folder, teams in
  `.lge` order, each team's pairs in `.lg2` order. A missing file's line sits
  where its report would. The "no files" lines of a folder come last.
- A game plan two pairs share (one plan for both halves) is reported once,
  its missing line included; each profile still gets its own cross-check.
  A pair two teams share is checked once.
- A found file shows its name as it is on disk; a missing one as the league
  file spells it.

## What it checks

- The profile, exactly as `profile check` does.
- The game plan, exactly as `gameplan check` does.
- The pair must be the same side (offense or defense). Each side's rules then
  decide what fails:
  - `require_all_profile_categories_in_gameplan`, in the profile rules'
    `[gameplan_compatibility]` — every play category the profile uses must
    have a custom play in the game plan; each one missing is a `gameplan:`
    line that fails the check. Off, it isn't checked.
  - `require_all_gameplan_categories_in_profile`, in the game plan rules'
    `[profile_compatibility]` — every category the game plan has a custom
    play for must be used by the profile; each one unused is a `gameplan:`
    line that fails the check. Off, they are only `gameplan info:` lines that
    don't fail.
- A file whose partner is missing is checked alone, without the cross-check.

Setup comes first and stops the run at its first problem: the league, then
`team`, the league files and the team, then `ppp_path`, then the rules and
the play pool. With two files, a side mismatch stops the checks too; in a
folder, it is that pair's error line and the other pairs are still checked.

## Results and exit codes

Every command prints through the shared console ([architecture](../design/architecture.md#console-run-log-and-errors)): results, `OK` and `SKIP` lines on stdout; `WARN` and `FAIL` lines and usage errors on stderr; every status line also in the run log.

- Per pair, the `profile check` and `gameplan check` lines (`OK   <file>: ...`, or a `<file>: <n> violation(s) (...)` headline with its detail lines); a blank line; the tally.
- Tally: `<n> file(s) checked, <n> with violations, <n> failed`; a folder adds `, <n> missing`; `--all-teams` adds `, <n> team(s) with no files`.
- `missing` counts a pair's other file only, the one noted with a `WARN`; a whole pair absent prints nothing and counts nowhere.
- A team with no file in the folder (or the tree with `-r`): `WARN <folder>: No Denver files. The league file names DEN-OFF1.prf, DEN-OGP1.pln, ...` (each name once); with `--all-teams`, one `WARN <folder>: No files for 15 team(s): Buffalo, Miami, ...`.
- At the league locations, a team with none of its files: `FAIL <folder>: No Denver files.`, or Windows' path phrase when the folder is absent; checking your team alone adds `Run 'athc config set ppp_path FOLDER' or pass the folder.` Each such line counts as one failed item.
- At the league locations, a single missing file: `FAIL <folder>\DEN-OGP2.pln: The system cannot find the file specified.`
- No team: `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team or --all-teams.`
- No `path`: `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass the folder.`
- A team name that matches no team, or two, lists the league's teams or the two by both names: a `FAIL` naming `league.toml` for `team`, a usage error for `--team`.
- `ppp_path` missing or a file: `FAIL <ppp_path>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER'.` (or `The directory name is invalid.`).
- A missing, unreadable or wrong-type file given by hand, or a second file of a kind, is a `FAIL` line each; nothing is checked, 2.

| Exit | Meaning |
|---|---|
| `0` | Done: no violations or issues (warnings included). |
| `1` | Findings: rule violations, or game plan issues the league requires. |
| `2` | Error: a bad argument, a missing, unreadable or wrong-type file, a side mismatch, a config, rules or league file problem, a team with no files at the league locations, a failed pair, a bug. |

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

- The team modes read `<league>.lg2` and `<league>.lge` from `path`; the pair
  mode needs neither `path` nor `team`.
- [convert-pdb](../pdbtoexcel/README.md) reads the same `team`, `path` and
  `ppp_path` for its Slot columns.
- The rules are the two check commands': `profile.toml`, `gameplan.toml` and
  `play_path`. See [profile](../profile/README.md) and
  [gameplan](../gameplan/README.md).

## Code

`src/athc/cli/check_ppp.py` is a leaf command. It takes nothing from
`gameplan check` or `profile check`: reading, rules loading, pairing and
reports live in it. Which team, and where its files are, comes from the
shared team layer `src/athc/cli/_team.py` (the league files, the team
resolver, each team's files and where each one is, and the team checks and
lines the commands share). It uses the `profile`,
`gameplan`, `fbpro98_lg2` and `fbpro98_lge` libraries and the gameplan
group's `build_pool`. Tests: `tests/integration/test_check_ppp.py`.
