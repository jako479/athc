# profile

Check, compare and copy FbPro98 coaching profiles (`.prf`). Built on
[fbpro98_profile](fbpro98_profile.md).

## Results and exit codes

Every command prints through the shared console ([architecture](architecture.md#console-run-log-and-errors)): results, `OK` and `SKIP` lines on stdout; `WARN` and `FAIL` lines, progress and usage errors on stderr; every status line also in the run log. The same codes everywhere: `0` done (warnings included), `1` findings, `2` error (usage, config, a bad or missing file, a file that failed inside a batch, a bug). A batch processes every file and exits with the worst outcome. A named file that does not exist is `FAIL <file>: The system cannot find the file specified.`

| Command | Lines | Exit 1 (findings) |
|---|---|---|
| `check` | per file `OK   <file>: <side>, FG range ...` or the headline `<file>: <n> violation(s) (...)` with its indented detail lines; a blank line; `<n> file(s) checked, <n> with violations, <n> failed` | violations |
| `copy` | `OK   <file>: updated (stop-clock, substitutions, ...)`, `SKIP <file>: <other side> profile` and `SKIP <file>: the source profile`, `FAIL <file>: <why>`; a tally `<n> file(s) processed, <n> updated, <n> skipped, <n> failed`; no copy option is a usage error | never (a failed file is exit 2) |
| `diff` | the report; with `-o`, `OK   <file>: written`; different sides are `FAIL Cannot compare <a> (offense) with <b> (defense).`, 2; a bad `-o` extension is a usage error | any difference |

## Profile keys

`off1`, `def1`, `off2` and `def2` are your team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense profiles. Every profile operand takes them, in any case: `check`'s PATH, `diff`'s PROFILE1 and PROFILE2, `copy`'s SOURCE and TARGET.

- Your team is `team` in `league.toml`, or `--team NAME` (name, nickname or both).
- A key's file is its `.lg2` name in `ppp_path` (the `team` team only), else where the league file puts it (`path` joined with its `.lg2` folder).
- Something of that name in the current folder, or a word with an extension or a folder separator, is a path: `off1.prf`, `.\off1` and a folder named `off1` are never keys.
- `--team` needs a key among the operands.
- A key's file that is not there is a `FAIL`; for the `team` team at its league location the line adds `Run 'athc config set ppp_path FOLDER' or pass a .prf file.`
- The setup lines (team or `path` not set, the league files, no team matching) are [check-ppp](check_ppp.md)'s, ending `or pass a .prf file.`

`--league NAME` picks the league; a named league must exist. Its files are read only when the run needs them: `check` always (its rules), `diff` and `copy` only for a key.

## check

```bash
athc profile check
athc profile check off2
athc profile check drafts\*OFF*.prf
```

Each PATH is a `.prf` file, a folder (top level, or the whole tree with `-r`),
a wildcard or a profile key; with no PATH, the current folder. Each profile
prints `OK` or its violations, in PATH order. Needs rules (below). To check a
profile together with its game plan, use [check-ppp](check_ppp.md).

## diff

```bash
athc profile diff off1 off2
athc profile diff off1 try.prf -o changes.csv
```

Shows what changed from PROFILE1 to PROFILE2 (same side only): situations, PAT,
substitutions, field-goal range, audibles. Each is a `.prf` file or a profile
key; the report names the file a key stands for. `-o FILE` writes a `.txt` or
`.csv` report instead of the console, creating its missing folders. Exit 0
(identical), 1 (differs), or 2 (an error or a side mismatch). No rules needed;
use it to preview a copy.

## copy

```bash
athc profile copy off1 off2 --stop-clock --substitutions
athc profile copy new.prf off1 off2 --substitutions
```

Copies selected settings from SOURCE (a `.prf` file or a profile key) into each
TARGET (`.prf` files, folders, wildcards or profile keys; `-r` takes a folder's
whole tree), each file once, in TARGET order. Pick at least one:
`--stop-clock`, `--substitutions`, `--field-goal-range`, `--fourth-down`,
`--goal-line`, `--pat-logic`. Targets of the other side, and the source itself,
are skipped; no backup is made. A missing SOURCE stops the run before any
target is touched. Exit 0 (done, skips included) or 2 (an error, or a target
failed). No rules needed; check afterward with `check`.

## Rules

Rules are **not** built in — they are the league folder's `profile.toml`
(`leagues\<NAME>\` under the config dir, picked by `--league` /
`[athc] league`). To layer several files, list them in `league.toml`:

```toml
[league]
profile_rules = ['profile.toml', 'house-rules.toml']
```

Later files layer over earlier. With no rules configured,
`check` reports an error and exits 2. The shipped rule set is
[`config/release/leagues/PNFL/profile.toml`](../config/release/leagues/PNFL/profile.toml),
and its comments explain every key.

## How it works

### Layout

```
src/athc/profile/          # tool logic (no Click)
├── __init__.py    # public API
├── config.py      # profile.toml (or profile_rules list) from the league folder
├── model.py       # RuleName, RuleViolation
├── rules.py       # ProfileRules, SituationRule, SubstitutionRule/PercentBound, load_rules, RulesFileError
├── validators.py  # validate_profile
├── compat.py      # check_gameplan_compatibility + gameplan_extra_categories -> CompatIssue (profile vs .pln; used by check-ppp)
├── diff.py        # diff_profiles, ProfileDiff + change types
├── display.py     # category / bucket labels for diff output
└── writer.py      # ProfileWriter, ProfileTypeMismatchError (field copy)

src/athc/cli/profile/      # Click wiring
├── __init__.py    # `profile` group
├── _common.py     # profile keys (team_profiles, expand_names, one_profile), help epilog, load_rules_or_raise
├── check.py       # `athc profile check`
├── diff.py        # `athc profile diff` (+ render / render_csv)
└── copy.py        # `athc profile copy`
```

### Rules

External TOML, loaded via `load_rules(paths)` — multiple files layer in order
(scalars overwrite; per-situation rules replace by section label). **No rules
ship in the package**; `validate_profile` requires a rule set and never falls
back to one. Situation rules are a list: each has optional game-state filters
(time/down/yards/fields — omitted = all) and constraints (`allowed`,
`disallowed`, `mandatory`, `min_categories`); a situation gets every rule it
matches. `allowed` limits a matching situation to the listed categories;
`disallowed` forbids exactly the listed ones and nothing else; a situation's
disallowed set is the side's top-level `disallowed_offensive_categories` /
`disallowed_defensive_categories` list plus every matching rule's. Substitution
rules are one `SubstitutionRule` per position group, a
`PercentBound` per side (out/in): an exact value or an optional min/max range;
a side with no key is unchecked, and each unmet side is its own violation. The
shipped [config/release/leagues/PNFL/profile.toml](../config/release/leagues/PNFL/profile.toml)
is the reference; its comments cover the matrix, category counts, disallowed
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
SOURCE is never overwritten. No backup is made. Options (≥1 required,
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
