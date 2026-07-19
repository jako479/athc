# profile — Architecture

Tool (CLI + logic) that validates FbPro98 `.prf` coaching profiles against league
rules. Built on `fbpro98_profile`. League-agnostic: rules live in an external
TOML file, never in code.

## Layout

```
src/athc/profile/          # tool logic (no Click)
├── __init__.py    # public API
├── config.py      # [profile] rule_files from athc.ini
├── model.py       # RuleName, Violation
├── rules.py       # ProfileRules, SituationRule, load_rules, RulesFileError
├── validators.py  # validate_profile
├── compat.py      # check_gameplan_compatibility/CompatIssue + gameplan_extra_categories/CompatWarning (profile vs .pln)
├── diff.py        # diff_profiles, ProfileDiff + change types
├── display.py     # category / bucket labels for diff output
└── writer.py      # ProfileWriter, ProfileTypeMismatchError (field copy)

src/athc/cli/profile/      # Click wiring
├── __init__.py    # `profile` group
├── _common.py     # collect_files, make_backup, resolve_rules
├── check.py       # `athc profile check`
├── diff.py        # `athc profile diff` (+ render / render_csv)
└── copy.py        # `athc profile copy`
```

## Rules

External TOML, loaded via `load_rules(paths)` — multiple files layer in order
(scalars overwrite; per-situation rules replace by section label). **No rules
ship in the package**; `validate_profile` requires a rule set and never falls
back to one. Situation rules are a list: each has optional game-state filters
(time/down/yards/fields — omitted = all) and constraints (`allowed`,
`disallowed`, `mandatory`, `min_categories`); a situation gets every rule it
matches. The shipped `release/rules/PNFL.profile.toml` is the documented
reference; rule meanings (matrix, category counts, exemptions, disallowed):
[RULES_PNFL.md](RULES_PNFL.md).

The min-categories exemption is built into `validators.py`, not the rules file: a
situation using only kick/punt (plus run-clock on offense; never fakes) is never
flagged for too few categories.

Loading reports every problem at once (`RulesFileError.errors`); any error aborts
`check` with each logged (exit 2).

## Config

`athc.ini [profile] rule_files` — one path per line (config found via
`ATHC_CONFIG_DIR` / the default config dir; no `--config` flag). `check` accepts
a repeatable `--rules` to override. No rules configured ⇒ `check` logs an
error and exits 2 (nothing to validate). See [../design/config.md](../design/config.md).

## Check

`athc profile check PATH... [-r]` — each PATH a `.prf` file, directory, or glob
(`-r` recurses a directory). Reads each via `fbpro98_profile.read_profile`, runs
`validate_profile`, prints a head line plus one line per violation. Exit 0 clean
/ 1 violations / 2 I/O or no rules. Continues past per-file parse errors.

`--gameplan FILE` (no short form) loads one `.pln` once
(`fbpro98_gameplan.read_gameplan`; bad path / extension / parse aborts, exit 2)
and runs `check_gameplan_compatibility(profile, gameplan)` per same-side file.
`compat.py` maps each used profile category code to the gameplan's custom plays —
normal codes (0x00–0x0F) to the 64 normal slots (resolved by `category_name`,
defense collapsing pass directions), special codes (FG/PAT, punt, fakes) to the
10 custom special slots; clock/random codes are skipped, and rules are not
consulted. A category with no custom play is a `CompatIssue` reported as a
`gameplan:` line and counted toward exit 1. The reverse,
`gameplan_extra_categories`, reports gameplan custom-play categories the profile
never weights as `CompatWarning`s (`gameplan warning:` lines): informational,
per gameplan category (defense pass directions stay collapsed), and not counted
toward the exit code. A profile whose side differs from the gameplan is a
per-file error (exit 2).

## Diff

`athc profile diff A.prf B.prf [-o FILE]` — reads both (no rules), refuses a
cross-side compare (exit 2), then `diff_profiles` builds a `ProfileDiff` by
aligning the fixed records (2520 situations, 60 PAT, 8 subs, FG, audibles) and
keeping only changes. The model (`diff.py`) is separate from rendering (`cli`):
stdout prints `[profile]`/`[situations]`/`[pat]` sections, one dense line per
change; `--output FILE` writes `.txt` (same text) or `.csv` (one row per change),
format from the extension (unknown → exit 2). Exit 0 identical / 1 differs / 2 I/O.

## Copy

`athc profile copy SRC.prf TARGET <flags> [-r] [--no-backup]` — copies selected
fields from SRC into one or many targets (`ProfileWriter.apply` → updated
`Profile`, written via `write_profile`). TARGET resolves to a file, directory, or
tree (`-r`); files of the wrong side are skipped by file-size parity (offense
even, defense odd), and SRC is never overwritten. A timestamped `.bak` is made
before each write unless `--no-backup`, named `<file>.<YYYY-MM-DD-HHMM>.bak`;
backups accumulate, but two edits of one file in the same minute reuse one name,
so the second silently overwrites the first. Flags (≥1 required, combinable):
`--stop-clock`, `--sub-percent`, `--field-goal-range`, `--fourth-down`,
`--goal-line`; the last two copy whole situations (stop-clock + weights).
Copy does not validate (use `check`). Exit 0 ok / 1 a target failed / 2 couldn't run.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Clean** — no violations or issues (`check`), identical (`diff`), done (`copy`). Informational warnings may still print. |
| `1` | **Findings** — rule violations + gameplan coverage issues (`check`), differences (`diff`), or a per-file failure (`copy`). |
| `2` | **Error** — couldn't run: I/O, parse, side mismatch, or usage. |

Three tiers, distinct: an **error** means the check couldn't run; a **finding** is a
real problem to fix; a **warning** is informational only. `check --gameplan`
warnings (gameplan categories the profile never uses) are warnings — they never
change the exit code.

## CLI integration

Registered under the `athc` umbrella via the `athc.commands` entry point
(`profile = "athc.cli.profile:profile"`); `AthcGroup` lazy-loads it. Follows the
Click group/leaf pattern in [../design/cli.md](../design/cli.md).

## Scope

Implemented: `check`, `diff`, `copy` — the full tool. Out of scope: `.prf` byte
I/O (`fbpro98_profile`).

## Tests

- `tests/integration/test_profile_{check,diff,copy}.py` — CLI end-to-end on real `.prf` files (`check` also covers `--gameplan` against real `.pln`).
- `tests/unit/profile/` — rules loader, validators, compat, diff model, display labels, writer.
- Matrices: `tests/integration/README.md`, `tests/unit/profile/README.md`.
