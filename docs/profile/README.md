# profile

Validate and compare FbPro98 coaching profiles (`.prf`). Built on
[fbpro98_profile](../fbpro98_profile/).

## Results and exit codes

| Exit | Meaning |
|---|---|
| `0` | **Clean** — no violations or issues (`check`), identical (`diff`), done (`copy`). |
| `1` | **Findings** — rule violations (`check`), differences (`diff`), or a per-file failure (`copy`). |
| `2` | **Error** — couldn't run: I/O, parse, side mismatch, or usage. |

An **error** means the check couldn't run; a **finding** is a real problem to
fix. Every check runs to the end — one bad file or violation does not stop the
rest.

## check

```bash
athc profile check OFF.prf
athc profile check
athc profile check profiles\ -r
athc profile check *.prf
```

Each PATH is a `.prf` file, a directory (top level, or the whole tree with `-r`),
or a glob; with no PATH, the current directory. Each profile prints `OK` or its
violations. Needs rules (below).
To check a profile together with its gameplan, use
[check-ppp](../check_ppp/README.md).

## diff

```bash
athc profile diff A.prf B.prf
athc profile diff A.prf B.prf -o changes.csv
```

Shows what changed from `file1` to `file2` (same side only) — situations, PAT, substitutions,
field-goal range, audibles. `-o file` writes a `.txt` or `.csv` report instead of
stdout. Exit 0 (identical), 1 (differs), or 2 (I/O error or side mismatch). No
rules needed.

## copy

```bash
athc profile copy SRC.prf DST.prf --stop-clock --goal-line
athc profile copy SRC.prf profiles\ --sub-percent -r
```

Copies selected fields from `source` into one or more targets (a `.prf` file, a
directory, or the tree with `-r`). Pick at least one: `--stop-clock`,
`--sub-percent`, `--field-goal-range`, `--fourth-down`, `--goal-line`, `--pat-logic`. Wrong-side
targets are skipped; no backup is made. Exit 0 (ok), 1 (a target failed), or 2 (usage or unreadable source). No rules needed —
validate afterward with `check`.

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
[`config/release/leagues/PNFL/profile.toml`](../../config/release/leagues/PNFL/profile.toml),
and its comments explain every key.
