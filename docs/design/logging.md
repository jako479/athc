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
stderr, so `cmd > out.txt` keeps the result and `2> err.log` keeps the failures.

## CLI commands

Every command sets up logging identically:

```python
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
```

- Results and status/success → `click.echo` (stdout).
- `logger.error` — a failure. **Not** "abort": may be fatal (exit 2) or per-item
  with the run continuing (exit 1). Control flow decides stopping, not the level.
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
