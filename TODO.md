# TODO

- athc: move league rules and league-specific configuration beneath a league folder
- athc: install through a PyInstaller-built installer (exe), replacing the `install.bat` + wheel zip and the uv prerequisite
- athc: cli: wire logging in the `cli()` group callback — global `-v/--verbose`, `RichHandler` on stderr, `click.style` on stdout; drop the 13 per-command `basicConfig` calls. Design: [docs/design/logging.md](docs/design/logging.md)
- athc: tests: add ruff's `PT` rule group (pytest style); 117 findings today, 111 auto-fixable under `--unsafe-fixes`
- autocontinue: work with Dean to determine usability requirements
- autocontinue: add halftime
- check-ppp: plan how to handle a directory of PPPs with a mix of .prf and .pln (config file with each team's filenames?)
- check-ppp: plan how to handle checking compatibility beteen a .prf and a .pln
- check-ppp: replace `gameplan check`
- check-ppp: replace `profile check`
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: revisit edit\copy options
- generate-schedule: generate schedules for PCFL
- generate-schedule: review and simplify the ruleset — 50 `[phase2]` keys, some redundant; consider simple vs. full ruleset switch. Reasoning and plan in [STATUS.md](STATUS.md)
- generate-schedule: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/design/quirk-budget.md](docs/design/quirk-budget.md). Do the ruleset simplification first
