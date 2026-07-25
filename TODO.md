# athc TODO

## TODO

- scheduler: Re-order report columns
- scheduler: league.ini - rename Standings to OverallStandings; add comments to make ordering clear for divs and confs
- gameplan check: add profile option? to make sure profile is valid?
  for remaining matchups??
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: revisit edit\copy options
- autocontinue: add halftime
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

- scheduler: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/design/quirk-budget.md](docs/design/quirk-budget.md)

## DECIDED FOR

- Use `Click` for CLI, including `CliRunner` for CLI tests
- athc-admin using full installer (can always revisit)
- `uv` over pip and other tools

## DECIDED AGAINST

- Pydantic for config library - sticking with `configparser`
- Fully league agnostic playpool
- Fully league agnostic gameplan
- Fully league agnostic profile
