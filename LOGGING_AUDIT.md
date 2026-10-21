# Logging audit

Review checklist, not a design. Run it on each tool after that tool has
been wired to the logging design in [docs/design/architecture.md](docs/design/architecture.md#output-streams).

## Check per tool

1. Who configures logging — umbrella only, or subcommands too? Should be one place.
2. Is there a verbosity flag, and does it reach the handler?
3. Any unreachable log lines (DEBUG with no way to enable it)?
4. Do errors name the file/path/arg that failed?
5. Soft fallback paths — does the code log when it takes a default, or just take it?
