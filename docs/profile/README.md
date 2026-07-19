# profile

Validate and compare FbPro98 coaching profiles (`.prf`). Built on
[fbpro98_profile](../fbpro98_profile/).

## check

```bash
athc profile check OFF.prf
athc profile check profiles\ -r
athc profile check *.prf
athc profile check OFF.prf --gameplan OFF.pln
```

Each PATH is a `.prf` file, a directory (top level, or the whole tree with `-r`),
or a glob. Each profile prints `OK` or its violations; exit 0 (clean), 1
(violations), or 2 (I/O error or no rules configured). Needs rules (below).

`--gameplan FILE` (no short form) also checks play-category coverage: every
category the profile weights — normal run/pass and special teams (FG/PAT, punt,
the fakes) — must have a custom play in the `.pln`. It also warns (`gameplan
warning:` lines) about gameplan categories the profile never uses; warnings are
informational and don't affect the exit code. Profile and gameplan must be the
same side; a mismatch is an error (exit 2). Clock and "random" categories aren't
backed by custom plays and are skipped. Gameplan rules are not checked (use
`gameplan check`).

## diff

```bash
athc profile diff A.prf B.prf
athc profile diff A.prf B.prf -o changes.csv
```

Shows what changed from A to B (same side only) — situations, PAT, substitutions,
field-goal range, audibles. `-o FILE` writes a `.txt` or `.csv` report instead of
stdout. Exit 0 (identical), 1 (differs), or 2 (I/O error or side mismatch). No
rules needed.

## copy

```bash
athc profile copy SRC.prf DST.prf --stop-clock --goal-line
athc profile copy SRC.prf profiles\ --sub-percent -r --no-backup
```

Copies selected fields from SRC into one or more targets (a `.prf` file, a
directory, or the tree with `-r`). Pick at least one: `--stop-clock`,
`--sub-percent`, `--field-goal-range`, `--fourth-down`, `--goal-line`. Wrong-side
targets are skipped; a timestamped `.bak` is made before each write unless
`--no-backup`. Exit 0 (ok), 1 (a target failed), or 2 (usage or unreadable source). No rules needed —
validate afterward with `check`.

## Rules

Rules are **not** built in — point athc at a TOML rule file. In `athc.ini`:

```ini
[profile]
rule_files = C:\athc\rules\pnfl_profile.toml
```

One path per line (later files layer over earlier). Override with `--rules <path>`
(repeatable), or point `ATHC_CONFIG_DIR` at a different config folder. With no
rules configured, `check` reports an error and exits 2. The shipped, documented rule set is
[`release/rules/PNFL.profile.toml`](../../release/rules/PNFL.profile.toml);
rule meanings are in [RULES_PNFL.md](RULES_PNFL.md).
