# profile

Check, compare and copy FbPro98 coaching profiles (`.prf`). Built on
[fbpro98_profile](../fbpro98_profile/).

## Results and exit codes

Every command prints through the shared console ([architecture](../design/architecture.md#console-run-log-and-errors)): results, `OK` and `SKIP` lines on stdout; `WARN` and `FAIL` lines, progress and usage errors on stderr; every status line also in the run log. The same codes everywhere: `0` done (warnings included), `1` findings, `2` error (usage, config, a bad or missing file, a file that failed inside a batch, a bug). A batch processes every file and exits with the worst outcome. A named file that does not exist is `FAIL <file>: The system cannot find the file specified.`

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
- The setup lines (team or `path` not set, the league files, no team matching) are [check-ppp](../check_ppp/README.md)'s, ending `or pass a .prf file.`

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
profile together with its game plan, use [check-ppp](../check_ppp/README.md).

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
[`config/release/leagues/PNFL/profile.toml`](../../config/release/leagues/PNFL/profile.toml),
and its comments explain every key.
