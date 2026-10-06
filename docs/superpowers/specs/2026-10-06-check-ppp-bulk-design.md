# check-ppp: both files required, plus directory and tree checks — design

Date: 2026-10-06. Status: written while the user was away; every open choice
took the recommended option (listed under Decisions).

## Goal

`check-ppp` checks profiles and gameplans together, never one alone. It takes
one profile and one gameplan, or a directory (a tree with `-r`) where the
league's `.lg2` says which files go together.

## Current state (main b2016c3)

- `check-ppp file [file]` takes a profile, a gameplan, or both.
- `fbpro98_lg2` reads a league's `.lg2`: each team's eight file locations,
  as `FilePair(profile, gameplan)` per half and side.
- `league.ini` has `play_path` (and athc-admin's `db_path`); no league file
  setting.

## User requirements

- The path to the league files in each league's `league.ini`; both leagues'
  files are in `E:\SIERRA\FbPro98`. PCFL's files don't exist yet; set it
  anyway. The `.lg2` is named after the league, and the lg2 library builds its
  path from the folder and the league name.
- Both a profile and a gameplan are required for a single check.
- Directory mode: check every pair named in the `.lg2` found in the
  directory, matched by file name; team identity doesn't matter. 1st-half
  offense profile goes with 1st-half offense gameplan, and so on.
- Tree mode: the same over a whole tree.
- Console output and logging like `gameplan check` and `profile check`.
- Removing `profile check --gameplan` is out of scope.
- Test plans copied from `E:\SIERRA\FbPro98\PNFL\2049\Plans\<team>` and
  renamed to the league file's names; nothing under `E:\SIERRA` changes.

## Decisions (made while away; each is the recommended option)

1. Setting: `path` under `[league]` (the user's call), the folder that holds
   the league's files; leagues can live anywhere, not only in the game's
   install folder. Relative paths resolve against the league folder.
2. Set in both `dev\` and `release\` copies of PNFL and PCFL as
   `E:\SIERRA\FbPro98`, except release PNFL, which uses `C:\SIERRA\FBPRO98`
   like its `play_path` (the user's call).
3. Command shape: `athc check-ppp [-h] [-r] [--league name] path [path]` —
   two files (one `.prf`, one `.pln`, either order) or one directory.
4. Only one directory per run.
5. Argument errors (one file alone, missing path, wrong type, two of a kind,
   a directory next to a file) are all logged and nothing is checked, since a
   pair is required.
6. `-r` with two files is ignored, as in `profile check`.
7. Pairs match by file name only, ignoring case and the `.lg2` folder.
8. A pair's two files must be in the same directory; in a tree each
   directory is matched on its own (seasons and weeks reuse names).
9. Files no pair names are ignored silently.
10. Order: directories top first, then subfolders by name; inside a
    directory, the `.lg2` order (team, then 1st-half offense, 1st-half
    defense, 2nd-half offense, 2nd-half defense). The same pair named twice
    is checked once.
11. Output per pair: the profile report (with its cross-check), then the
    gameplan report. A gameplan shared by two pairs (one plan for both
    halves) is reported once; each profile still gets its own cross-check.
12. In directory mode a side mismatch is that pair's error line; the other
    pairs are still checked; the summary prints; exit 2. Two-file mode keeps
    stopping everything on a mismatch.
13. No pair found: a stdout line `<dir>: no profile and gameplan pairs from
    the league file in directory` (`tree` with `-r`), exit 0, since no file has
    to be there (the user's call). Folders that can't be read are skipped
    silently, like `os.walk` (the user's call).
14. The `.lg2` is a setup file like the rules: read only in directory mode,
    its errors logged with the others; it is needed to find the pairs.
15. Test data: Denver's 2049 week 6 files as-is (`2049\Plans\Denver (Brian)`)
    plus a renamed copy as Las Vegas (`LVOFF1.prf` …, shared `RAIDEROFF.pln`
    / `RAIDERDEF.pln`), with the repo's copy of `PNFL.lg2`.

## Behavior

- Two-file mode: unchanged reports, cross-check, setup and mismatch rules.
- Directory mode:
  1. Validate the argument (exists, is a directory).
  2. Load every setup piece (profile rules, gameplan rules and pool, `.lg2`);
     log each problem once.
  3. Without the `.lg2`, stop (exit 2).
  4. Find the pairs; none → a stdout line, exit 0 (2 after a setup error).
  5. Setup failed → print only unreadable-file and mismatch lines, exit 2.
  6. Else check each pair, print the summary; exit 0 / 1 / 2 as today.
- `path` errors: missing key → `no path for the league; set path in
  <league.ini>`; a missing, unreadable, invalid or stock `.lg2` → the
  library's message.

## Code

All in `src/athc/cli/check_ppp.py` (it owns its reading and reports):
`league_pairs(lg2)` (file-name pairs), `find_pairs(directory, pairs,
recursive)` (path pairs per directory), `load_lg2(league, logged)`, and a
directory-mode loop beside the two-file path.

## Tests

`tests/integration/test_check_ppp.py`:

- One-file and third-argument cases become errors; boundaries 0 / 1 / 2 / 3
  arguments.
- Directory mode on tmp folders with the TST files renamed to built `.lg2`
  names: output equals the existing goldens in `.lg2` order; case-insensitive
  names; half pairs skipped; shared gameplan once; duplicate pairs once;
  unlisted files ignored; top level only without `-r`; per-directory
  matching with `-r`; no pairs; mismatch continues; unreadable file;
  setup errors; `path` missing; `.lg2` missing / invalid / stock.
- Real data: the Denver and Las Vegas tree with `PNFL.lg2`.
- `test_cli_root.py`: new metavars; `--league` reaches check-ppp with a pair.
- `test_config.py`: every shipped league sets `path`.

## Docs

`docs/check_ppp/README.md`, `docs/design/config.md`, `release/docs/COMMANDS.txt`,
`release/docs/README.txt`, shipped `league.ini` comments,
`tests/integration/README.md`, `CHANGELOG.md`, `STATUS.md`.

## Out of scope

- Removing `profile check --gameplan`.
- Checking that two files given by hand are a pair in the `.lg2`.
- Globs and several directories.
