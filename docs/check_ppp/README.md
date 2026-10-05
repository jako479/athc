# check-ppp

Check one coaching profile (`.prf`) and/or one gameplan (`.pln`) against the
league rules, and check that the two fit together. Meant to replace
`profile check` and `gameplan check`.

## Usage

```bash
athc check-ppp OFF.prf OFF.pln
athc check-ppp OFF.prf
athc check-ppp OFF.pln
```

Pass one profile, one gameplan, or both, in either order; the extension tells
them apart. There are no options: the rules come from the current league
(`[athc] league` in `athc.ini`, `ATHC_LEAGUE`, or `athc --league NAME`).

## What it checks

- The profile, exactly as `profile check` does.
- The gameplan, exactly as `gameplan check` does.
- With both, the two must be the same side (offense or defense), and every
  play category the profile uses must have a custom play in the gameplan (a
  `gameplan:` line that fails the check).
- Gameplan categories the profile never uses are only `gameplan info:` lines;
  they don't fail the check. Unlike `profile check`, which fails on them.
- Both always run. The `[gameplan_compatibility]` flags are for
  `profile check` only.

The output is the same report lines those commands print, profile first, then
any side-mismatch error, then one summary line. Every error is reported in one
run: a bad file, a side mismatch or a missing rules file on one side does not
hide the rest, and the other file is still checked.

## Results and exit codes

| Exit | Meaning |
|---|---|
| `0` | **Clean** — no violations or issues. |
| `1` | **Findings** — rule violations, or profile categories the gameplan lacks. |
| `2` | **Error** — couldn't run: a missing, unreadable or wrong-type file, two files of one kind, a side mismatch, or a config or rules problem. |

## Rules

The same league files the two check commands read: `rules\profile.toml`,
`rules\gameplan.toml`, `rules\playpool.toml` and `play_path` in `league.ini`.
Only what the given files need is loaded. See [profile](../profile/README.md)
and [gameplan](../gameplan/README.md).

## Code

`src/athc/cli/check_ppp.py` is a leaf command with no logic of its own. It
reads, validates and prints through `read_file` / `report` in
`cli/profile/check.py` and `cli/gameplan/check.py` (plus `side_mismatch`), and
loads rules through their `_common.py`. Tests:
`tests/integration/test_check_ppp.py`.
