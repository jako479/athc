# profile

Validate and compare FbPro98 coaching profiles (`.prf`). Built on
[fbpro98_profile](../fbpro98_profile/).

## Results and exit codes

Every command prints through the shared console ([architecture](../design/architecture.md#console-run-log-and-errors)): results, `OK` and `SKIP` lines on stdout; `WARN` and `FAIL` lines, progress and usage errors on stderr; every status line also in the run log. The same codes everywhere: `0` done (warnings included), `1` findings, `2` error (usage, config, a bad or missing file, a file that failed inside a batch, a bug). A batch processes every file and exits with the worst outcome. A named file that does not exist is `FAIL <file>: not found`.

| Command | Lines | Exit 1 (findings) |
|---|---|---|
| `check` | per file `OK   <file>: <side>, FG range ...` or the headline `<file>: <n> violation(s) (...)` with its indented detail lines; a blank line; `<n> file(s) checked, <n> with violations, <n> failed` | violations |
| `copy` | `OK   <file>: updated (stop-clock, ...)`, `SKIP <file>: <other side> profile` and `SKIP <file>: the source profile`, `FAIL <file>: <why>`; a tally `<n> file(s) processed, <n> updated, <n> skipped, <n> failed`; no copy flag is a usage error | never (a failed file is exit 2) |
| `diff` | the report; with `-o`, `OK   <file>: written`; different sides are `FAIL cannot diff OFFENSE against DEFENSE`, 2; a bad `-o` extension is a usage error | any difference |

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
stdout, creating its missing folders. Exit 0 (identical), 1 (differs), or 2 (I/O
error or side mismatch). No rules needed.

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
