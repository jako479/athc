# check-ppp

Check one coaching profile (`.prf`) and/or one gameplan (`.pln`) against the
league rules, and check that the two fit together. Meant to replace
`profile check` and `gameplan check`.

## Usage

```bash
athc check-ppp OFF.prf OFF.pln
athc check-ppp OFF.prf
athc check-ppp OFF.pln --league PCFL
```

Pass one profile, one gameplan, or both, in either order; the extension tells
them apart. The only option is `--league name`: the rules come from that
league, or from `[athc] league` in `athc.ini`.

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

The output is the same report lines those commands print: the profile, then
the gameplan, then one summary line. Every error is reported in one run: a bad
file does not hide the rest.

A side mismatch, a missing or bad rules file, or any other setup error stops
the rule checks and the summary for both files, as a setup error does in
`gameplan check` and `profile check`; bad files and the mismatch are still
reported.

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

`src/athc/cli/check_ppp.py` is a leaf command. It takes nothing from
`gameplan check` or `profile check`, since it replaces them: reading, rules
loading and reports live in it. It uses the `profile` / `gameplan` libraries
and the gameplan group's `build_pool`. Tests:
`tests/integration/test_check_ppp.py`.
