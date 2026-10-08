# profile — Architecture

Tool (CLI + logic) that validates FbPro98 `.prf` coaching profiles against league
rules. Built on `fbpro98_profile`. League-agnostic: rules live in an external
TOML file, never in code.

## Layout

```
src/athc/profile/          # tool logic (no Click)
├── __init__.py    # public API
├── config.py      # profile.toml (or profile_rules list) from the league folder
├── model.py       # RuleName, Violation
├── rules.py       # ProfileRules, SituationRule, SubstitutionRule/PercentBound, load_rules, RulesFileError
├── validators.py  # validate_profile
├── compat.py      # check_gameplan_compatibility + gameplan_extra_categories -> CompatIssue (profile vs .pln; used by check-ppp)
├── diff.py        # diff_profiles, ProfileDiff + change types
├── display.py     # category / bucket labels for diff output
└── writer.py      # ProfileWriter, ProfileTypeMismatchError (field copy)

src/athc/cli/profile/      # Click wiring
├── __init__.py    # `profile` group
├── _common.py     # collect_files, resolve_rules
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
matches. Substitution rules are one `SubstitutionRule` per position group, a
`PercentBound` per side (out/in): an exact value or an optional min/max range;
a side with no key is unchecked, and each unmet side is its own violation. The
shipped [config/release/leagues/PNFL/profile.toml](../../config/release/leagues/PNFL/profile.toml)
is the reference; its comments cover the matrix, category counts, disallowed
categories and substitutions.

The min-categories exemption is built into `validators.py`, not the rules file: a
situation using only kick/punt (plus run-clock on offense; never fakes) is never
flagged for too few categories.

Loading reports every problem at once (`RulesFileError.errors`); any error aborts
`check` with each logged (exit 2).

## Config

`leagues\<NAME>\profile.toml`, or a `profile_rules` list in the league's
`league.ini` (one path per line); the league comes from `--league` /
`[athc] league` (config found via `ATHC_CONFIG_DIR` / the default
config dir; no `--config` flag). `check` has no rules override. No rules
configured ⇒ `check` logs an error and exits 2 (nothing to validate). See [../design/config.md](../design/config.md).

## Check

`athc profile check [PATH]... [-r]` — each PATH a `.prf` file, directory, or glob
(`-r` recurses a directory; no PATH means the current directory). Reads each via `fbpro98_profile.read_profile`, runs
`validate_profile`, prints a head line plus one line per violation. Exit 0 clean
/ 1 violations / 2 I/O or no rules. Continues past per-file parse errors.

`check` does not look at gameplans. `compat.py` is the profile-vs-gameplan
logic that `athc check-ppp` runs ([../check_ppp/README.md](../check_ppp/README.md)):
`check_gameplan_compatibility` maps each used profile category code to the
gameplan's custom plays — normal codes (0x00–0x0F) to the 64 normal slots
(resolved by `category_name`, defense collapsing pass directions), special codes
(FG/PAT, punt, fakes) to the 10 custom special slots; clock/random codes are
skipped, and rules are not consulted here. A category with no custom play is a
`CompatIssue`. The reverse, `gameplan_extra_categories`, reports gameplan
custom-play categories the profile never weights, per gameplan category (defense
pass directions stay collapsed, so those carry no `category_code`).

## Diff

`athc profile diff file1 file2 [-o file]` — reads both (no rules), refuses a
cross-side compare (exit 2), then `diff_profiles` builds a `ProfileDiff` by
aligning the fixed records (2520 situations, 60 PAT, 8 subs, FG, audibles) and
keeping only changes. The model (`diff.py`) is separate from rendering (`cli`):
stdout prints `[profile]`/`[situations]`/`[pat]` sections, one dense line per
change; `--output file` writes `.txt` (same text) or `.csv` (one row per change),
format from the extension (unknown → exit 2). Exit 0 identical / 1 differs / 2 I/O.

## Copy

`athc profile copy source target <flags> [-r]` — copies selected
fields from `source` into one or many targets (`ProfileWriter.apply` → updated
`Profile`, written via `write_profile`). `target` resolves to a file, directory, or
tree (`-r`); files of the wrong side are skipped by file-size parity (offense
even, defense odd), and `source` is never overwritten. No backup is made. Flags (≥1 required, combinable):
`--stop-clock`, `--sub-percent`, `--field-goal-range`, `--fourth-down`,
`--goal-line`; the last two copy whole situations (stop-clock + weights).
Copy does not validate (use `check`). Exit 0 ok / 1 a target failed / 2 couldn't run.

## Exit codes

See [README.md](README.md#results-and-exit-codes).

## CLI integration

Registered under the `athc` umbrella via the `athc.commands` entry point
(`profile = "athc.cli.profile:profile"`); `AthcGroup` lazy-loads it. Follows the
Click group/leaf pattern in [../design/cli.md](../design/cli.md).

## Scope

Implemented: `check`, `diff`, `copy` — the full tool. Out of scope: `.prf` byte
I/O (`fbpro98_profile`).

## Tests

- `tests/integration/test_profile_{check,diff,copy}.py` — CLI end-to-end on real `.prf` files.
- `tests/unit/profile/` — rules loader, validators, compat, diff model, display labels, writer.
- Matrices: `tests/integration/README.md`, `tests/unit/profile/README.md`.
