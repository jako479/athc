# profile

Check, compare and copy FbPro98 coaching profiles (`.prf`). Built on
[fbpro98_profile](fbpro98_profile.md).

Usage, the profile keys, the rules files, lines and exit codes: [usage/profile.txt](../usage/profile.txt).

## How it works

### Layout

```
src/athc/profile/          # tool logic (no Click)
├── __init__.py    # public API
├── config.py      # profile.toml (or profile_rules list) and the category labels from the league folder
├── model.py       # RuleName, RuleViolation
├── errors.py      # ProfileTypeMismatchError
├── rules.py       # ProfileRules, SituationRule, SubstitutionRule/PercentBound, load_rules, RulesFileError
├── validators.py  # validate_profile
├── compat.py      # check_gameplan_compatibility + gameplan_extra_categories -> CompatIssue (profile vs .pln; used by check-ppp)
├── diff.py        # diff_profiles, ProfileDiff + change types
├── display.py     # category / bucket labels for diff output
└── writer.py      # ProfileWriter (field copy)

src/athc/cli/profile/      # Click wiring
├── __init__.py    # `profile` group
├── _common.py     # profile keys (team_profiles, expand_names, one_profile), help epilog, load_rules_or_raise
├── check.py       # `athc profile check`
├── diff.py        # `athc profile diff` (+ render / render_csv)
└── copy.py        # `athc profile copy`
```

### Rules

External TOML, loaded via `load_rules(paths, labels=...)` with the league's
category labels — multiple files layer in order (scalars and lists overwrite;
per-situation rules replace by section label). **No rules ship in the
package**; `validate_profile` requires a rule set and never falls back to one.

`allowed_offensive_categories` / `allowed_defensive_categories` list, by the
league's labels only, the categories a profile may use; an omitted or empty
list enforces nothing. They cover every category but the special ones (FG/PAT,
the fakes, punt, run clock), which they never limit; the randoms have no
label, so a non-empty list always bans them. A defense label stands for all of
its codes (`PassShort` for the three pass-short codes). An entry that is not
one of the side's labels (a game name, a User Specific label) is an error.

Situation rules are a list: each has optional game-state filters
(time/down/yards/fields — omitted = all) and constraints (`allowed`,
`disallowed`, `mandatory`, `min_categories`); a situation gets every rule it
matches. `allowed` limits a matching situation to the listed categories;
`disallowed` forbids exactly the listed ones and nothing else; a situation's
banned set is every in-scope category its side's allowed list leaves out plus
every matching rule's `disallowed`, reported as one violation. Substitution
rules are one `SubstitutionRule` per position group, a
`PercentBound` per side (out/in): an exact value or an optional min/max range;
a side with no key is unchecked, and each unmet side is its own violation. The
shipped [config/release/leagues/PNFL/profile.toml](../../config/release/leagues/PNFL/profile.toml)
is the reference; its comments cover the matrix, category counts, allowed
categories and substitutions.

The min-categories exemption is built into `validators.py`, not the rules file: a
situation using only kick/punt (plus run-clock on offense; never fakes) is never
flagged for too few categories.

Loading reports every problem at once (`RulesFileError.errors`); any error aborts
`check` with each logged (exit 2). The league comes from `--league` /
`[athc] league` (config found via `ATHC_CONFIG_DIR` / the default config dir;
no `--config` flag); `check` has no rules override.

### Profile keys

`off1`, `def1`, `off2`, `def2` name the team's four profiles (`.lg2` entries
1, 3, 5 and 7). `_common.py` resolves them through the team layer shared with
`check-ppp` and `gameplan` (`src/athc/cli/_team.py`: `load_league_files`,
`resolve_team`, `team_files`, `locate`, and the team checks and lines those
commands share):

- `is_key` (in `_team.py`): one of the four words, any case, with nothing of
  that name in the current folder; anything else is a path.
- `team_profiles(operands, team=, league=)`: the setup, once per run over all
  operands, in the order its errors show: `--team` with no key (usage error),
  `--league` resolved when given, then, only with a key, `team`, `path`, the
  league files and the team match, then `ppp_path` for the `team` team. Each
  key's file is located, and whether it exists decided, before anything reads
  it.
- `expand_names(operands, profiles)`: keys replaced by their files for
  `collect_files` (`check` PATH, `copy` TARGET); a missing one becomes a
  `FAIL` line counted failed, never a path.
- `one_profile(raw, profiles)`: one file (`diff`, `copy` SOURCE): `named_file`
  for a path, the located file for a key, AthcError when it is missing.

### Check

`athc profile check [PATH]... [-r] [--team NAME]` — each PATH a `.prf` file,
folder, wildcard or profile key (`-r` takes a folder's tree; no PATH means the
current folder). Reads each via `fbpro98_profile.read_profile`, runs
`validate_profile`, prints a head line plus one line per violation. Exit 0 clean
/ 1 violations / 2 I/O or no rules. Continues past per-file parse errors.

`check` does not look at gameplans. `compat.py` is the profile-vs-gameplan
logic that `athc check-ppp` runs ([check_ppp.md](check_ppp.md)):
`check_gameplan_compatibility` maps each used profile category code to the
gameplan's custom plays — normal codes (0x00–0x0F) to the 64 normal slots
(resolved by `category_name`, defense collapsing pass directions), special codes
(FG/PAT, punt, fakes) to the 10 custom special slots; clock/random codes are
skipped, and rules are not consulted here. A category with no custom play is a
`CompatIssue`. The reverse, `gameplan_extra_categories`, reports gameplan
custom-play categories the profile never weights, per gameplan category (defense
pass directions stay collapsed, so those carry no `category_code`).

### Diff

`athc profile diff PROFILE1 PROFILE2 [-o FILE] [--team NAME]` — each a `.prf`
file or a profile key (`one_profile`); reads both (no rules), refuses a
cross-side compare (exit 2), then `diff_profiles` builds a `ProfileDiff` by
aligning the fixed records (2520 situations, 60 PAT, 8 subs, FG, audibles) and
keeping only changes. The model (`diff.py`) is separate from rendering (`cli`):
the console gets `[profile]`/`[situations]`/`[pat]` sections, one dense line
per change, under `<file> -> <file>` (a key shown as its file); `--output FILE`
writes `.txt` (same text) or `.csv` (one row per change), format from the
extension (another extension is a usage error from the option's callback, exit
2). Exit 0 identical / 1 differs / 2 error.

### Copy

`athc profile copy SOURCE TARGET... <options> [-r] [--team NAME]` — copies
selected fields from SOURCE (`one_profile`) into one or more targets
(`ProfileWriter.apply` → updated `Profile`, written via `write_profile`). The
TARGETs go through `expand_names` and `collect_files`: files, folders (`-r` for
the tree), wildcards and keys, each file once in TARGET order. Files of the
wrong side are skipped by file-size parity (offense even, defense odd), and
SOURCE is never overwritten: as the one file of a single TARGET it is an
AthcError before any profile is read, elsewhere it is skipped. No backup is made. Options (≥1 required,
combinable): `--stop-clock`, `--substitutions` (the writer's
`copy_sub_percent`), `--field-goal-range`, `--fourth-down`, `--goal-line`,
`--pat-logic`; `--fourth-down` and `--goal-line` copy whole situations
(stop-clock + weights); `--pat-logic` copies the 60-situation PAT table. Copy
does not validate (use `check`). Exit 0 done (skips included) / 2 error (a
target failed included).

### CLI integration

Registered under the `athc` umbrella via the `athc.commands` entry point
(`profile = "athc.cli.profile:profile"`); `AthcGroup` lazy-loads it. Follows the
Click group/leaf pattern in [architecture.md](architecture.md#cli).

### Scope

Implemented: `check`, `diff`, `copy` — the full tool. Out of scope: `.prf` byte
I/O (`fbpro98_profile`).

### Tests

- `tests/integration/test_profile_{check,diff,copy}.py` — CLI end-to-end on real `.prf` files, help screens pinned.
- `tests/integration/test_team.py` — the profile keys: which operand is a key, where its file is, the setup lines.
- `tests/unit/profile/` — rules loader, validators, compat, diff model, display labels, writer.
- Matrices: `tests/integration/README.md`, `tests/unit/profile/README.md`.
