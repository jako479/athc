# athc TODO

One line per task. Current state and reasoning: [STATUS.md](STATUS.md).

## TODO

- check: one `athc check` taking any mix of .pln and .prf, replacing `gameplan check` and `profile check`; open questions in [STATUS.md](STATUS.md)
- check: make PyInstaller EXE or subcommand
- scheduler: switch to PyInstaller exe??
- autocontinue: switch to PyInstaller exe?
- scheduler: review and simplify the ruleset — 50 `[phase2]` keys, some redundant; consider simple vs. full ruleset switch. Reasoning and plan in [STATUS.md](STATUS.md)
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: revisit edit\copy options
- autocontinue: add halftime
- tests: add ruff's `PT` rule group (pytest style); 117 findings today, 111 auto-fixable under `--unsafe-fixes`
- cli: wire logging in the `cli()` group callback — global `-v/--verbose`, `RichHandler` on stderr, `click.style` on stdout; drop the 13 per-command `basicConfig` calls. Design: [docs/design/logging.md](docs/design/logging.md)
- [DONE] profile: new substitution % rules — non-QB, non-K groups capped at 95 out / 96-100 in
- [DONE] profile: gameplan compatibility is checked both ways, fails the check, and is gated by the rules file
- [DONE] gameplan: new 2-DL rules — 50% Pass Short/Medium, 75% Pass Long, 100% Pass Dazzle
- [DONE] gameplan: attribute caps take a count, ratio or percent form
- [DONE] scheduler: league.ini - dropped [Divisions]; [DivisionStandings] now defines division membership + finish order
- [DONE] scheduler: soft objective so seasons vary like real NFL years; NFL-typical bands per [docs/design/research/cpsat-rule-patterns.md](docs/design/research/cpsat-rule-patterns.md)
- [DONE] scheduler: count-caps to prevent rule pileups; implemented per [docs/design/research/cpsat-rule-patterns.md](docs/design/research/cpsat-rule-patterns.md)
- [DONE] scheduler: convert league config into a single file [league.ini only; history file removed]
- [DONE] scheduler: Schedulers C and D (fixed-place + CP-SAT); A and B removed
- [DONE] schedule research: SOS analysis of real PNFL schedules
- [DONE] playpool: rename PlayRecord to Play; Same with OffensivePlayRecord, etc.
- [DONE] gameplan: rename Play to PlayRef; Same with CustomPlay and StockPlay
- [DONE] scheduler rules: range for shape (`p`); [0.75 to 1 (flat) seems ideal]
- [DONE] athc general: Handle exit codes consistently [Design and tools fixed]
- [DONE] scheduler: what is current backup strategy? Documented in design and release docs? Tests? [N/A]
- [DONE] gameplan: what is current backup strategy? Documented in design and release docs? Tests? [Yes]
- [DONE] profile: what is current backup strategy? Documented in design and release docs? Tests? [Yes]
- [DONE] playpool: user category now golden; folder categories for play attributes

## PLANNED

- scheduler: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/design/quirk-budget.md](docs/design/quirk-budget.md). Do the ruleset simplification first

## DECIDED FOR

- Use `Click` for CLI, including `CliRunner` for CLI tests
- athc-admin using full installer (can always revisit)
- `uv` over pip and other tools

## DECIDED AGAINST

- Pydantic for config library - sticking with `configparser`
- Fully league agnostic playpool
- Fully league agnostic gameplan
- Fully league agnostic profile
