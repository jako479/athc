# Logging audit

Review checklist, not a design. Run it on each tool after that tool has
been wired to the logging design in [docs/design/logging.md](docs/design/logging.md).
Prompted by pnfl-admin's logparser, where all four of these were broken.

## Check per tool

1. Who configures logging — umbrella only, or subcommands too? Should be one place.
2. Is there a verbosity flag, and does it reach the handler?
3. Any unreachable log lines (DEBUG with no way to enable it)?
4. Do errors name the file/path/arg that failed?
5. Soft fallback paths — does the code log when it takes a default, or just take it?

## What logparser looked like

- `main()` called `logging.basicConfig(level=INFO)` itself, no `--verbose`/`--debug`
  flag — the one `logger.debug(...)` line could never emit.
- `basicConfig` is a no-op if the caller already configured the root logger, so a
  subcommand's level/format silently depended on who invoked it. (Unverified —
  needs the pnfl umbrella CLI.)
- That debug line logged `sys.argv`, not the `argv` passed to `main()`.
- A typo'd log directory produced only "No log files found.", no path.

Carry over when logparser migrates: `import_logs.py` lines 26-27 and 563 are
existing TODOs asking for exactly this. Visibility gaps only — parse errors are
raised and recorded, not swallowed.
