# check-ppp

Check coaching profiles (`.prf`) with their gameplans (`.pln`) against the
league rules, and check that each pair fits together. Replaced
`profile check --gameplan`.

## Usage

```bash
athc check-ppp OFF.prf OFF.pln
athc check-ppp "plans\Denver (Brian)"
athc check-ppp plans -r --league PCFL
```

- Two files: one profile and one gameplan, in either order; the extension
  tells them apart. Both are required.
- A directory: every pair the league file names whose two files are both
  there. With `-r`, every folder in the tree, each on its own.

The rules come from `--league name`, or from `[athc] league` in `athc.ini`.

## Pairs from the league file

`path` in `league.ini` names the folder that holds the league's
files; the league's `.lg2` there is named after the league. For each
team it lists four pairs: 1st-half offense profile and gameplan, 1st-half
defense, 2nd-half offense, 2nd-half defense.

- Matched by file name only, ignoring case; the `.lg2` folders don't matter.
- Both files of a pair must be in the same folder.
- Pairs with a file missing, files no pair names, and folders that can't be
  read are skipped. With no pairs at all, it says so and exits 0.
- Order: top folder first, then subfolders by name; inside a folder, the
  `.lg2` order.
- A gameplan used by two pairs (one plan for both halves) is reported once;
  each profile still gets its own cross-check.

## What it checks

- The profile, exactly as `profile check` does.
- The gameplan, exactly as `gameplan check` does.
- The pair must be the same side (offense or defense). Each side's rules then
  decide what fails:
  - `require_all_profile_categories_in_gameplan`, in the profile rules'
    `[gameplan_compatibility]` — every play category the profile uses must
    have a custom play in the gameplan; each one missing is a `gameplan:`
    line that fails the check. Off, it isn't checked.
  - `require_all_gameplan_categories_in_profile`, in the gameplan rules'
    `[profile_compatibility]` — every category the gameplan has a custom play
    for must be used by the profile; each one unused is a `gameplan:` line
    that fails the check. Off, they are only `gameplan info:` lines that
    don't fail.

The output is the same report lines those commands print: per pair, the
profile, then the gameplan; then one summary line. Every error is reported in
one run: a bad file does not hide the rest.

A missing or bad rules file, league file or other setup error stops the rule
checks and the summary; bad files and side mismatches are still reported. With
two files, a side mismatch stops the checks too; in a directory, it is that
pair's error line and the other pairs are still checked.

## Results and exit codes

| Exit | Meaning |
|---|---|
| `0` | **Clean** — no violations or issues. |
| `1` | **Findings** — rule violations, or gameplan issues the league requires. |
| `2` | **Error** — couldn't run: a bad argument, a missing, unreadable or wrong-type file, a side mismatch, or a config, rules or league file problem. |

## Settings

The same league files the two check commands read: `profile.toml`,
`gameplan.toml`, `playpool.toml` and `play_path` in
`league.ini`, plus `path` for a directory. See
[profile](../profile/README.md) and [gameplan](../gameplan/README.md).

## Code

`src/athc/cli/check_ppp.py` is a leaf command. It takes nothing from
`gameplan check` or `profile check`: reading, rules loading, pairing and
reports live in it. It uses the `profile`, `gameplan` and `fbpro98_lg2`
libraries and the gameplan group's `build_pool`. Tests:
`tests/integration/test_check_ppp.py`.
