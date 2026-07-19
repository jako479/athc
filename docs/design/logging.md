# athc — Logging & Output

How athc writes to the terminal. Applies to **every CLI command and library** —
a cross-cutting concern, not CLI-wiring-specific (CLI structure: [cli.md](cli.md)).

## The rule

- **stdout** (`click.echo`) — **everything the user reads**: results *and*
  status. Reports (check/diff violations, list output), and success/progress
  notes ("Updated …", "Wrote N plays"). No level prefixes, so it pipes cleanly.
- **stderr** (`logging`) — **errors and warnings only**.

A command that edits files in place has no other stdout output, so its status
line still goes to stdout (the `cp -v` / `rsync -v` convention). Errors go to
stderr, so `cmd > out.txt` keeps the result and `2> err.log` keeps the failures —
that split is the whole point of using stderr.

## Why two streams

- **stdout = the result.** Gets piped/saved (`cmd > out.txt`) and belongs to the
  app. Any junk written here pollutes the output.
- **stderr = side notes.** Errors/warnings/progress. Still shown on screen, but a
  separate stream — `> out.txt` doesn't capture it; save it with `2> err.log`.

A library doesn't know who calls it, so it must never touch stdout. It logs to
stderr instead, where the app can still silence or redirect it.

## Who writes what

| Component | What | Channel | How |
|---|---|---|---|
| CLI command | Results + status/success (reports, lists, "Updated …") | stdout | `click.echo` |
| CLI command | Failures (fatal or per-item) | stderr | `logger.error` |
| Library | Recoverable "skipped X" notices | stderr | `logger.warning` |
| Library | Progress | stderr | `logger.info` |
| Library | Results | — | never (libraries don't print results) |

- Use `click.echo` for stdout, **never `print()`** — `click.echo` handles
  encoding/redirection. (Audited: no `print()` in the codebase.)
- CLI commands never call `logger.info`/`logger.warning`; status is echoed to
  stdout. Libraries never call `logger.error` or `basicConfig` — the app owns
  handler setup and decides what's fatal.

## CLI commands

Every command sets up logging identically:

```python
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
```

- Results and status/success → `click.echo` (stdout).
- `logger.error` — a failure. **Not** "abort": it may stop the command or be one of
  several per-item failures with the run continuing. The exit code
  ([cli.md](cli.md#exit-codes)) is set by control flow, not the log level.
- A `-q/--quiet` flag (where offered) skips the success `click.echo`; errors
  still log.
- CLI commands don't call `logger.info`/`logger.warning` — status is echoed.

## Libraries

Libraries (`<pkg>/<tool>/`, `playpool`, …) never print results and never call
`basicConfig` — the app owns handler setup. They use `logger.warning` for
recoverable "skipped X" notices and `logger.info` for progress. So
library-emitted progress (e.g. `convert-pdb`'s "Conversion complete", from
`pdbtoexcel`) lands on **stderr** — that's the library boundary, not a CLI
status line.

## Exit codes

Computed once after the work loop, so a non-zero exit never aborts a multi-file
run mid-loop — every file is processed and reported first.

## Unexpected errors

The umbrella `main()` ([cli/__init__.py](../../src/athc/cli/__init__.py)) wraps the
CLI: any *unexpected* exception (a bug, not an anticipated `ConfigError`/usage error)
is logged as a one-line message and exits 2 — no traceback. Set `ATHC_DEBUG=1` to
re-raise it for debugging.
