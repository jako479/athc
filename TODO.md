# athc TODO

## TODO

- gameplan check: add profile option? to make sure profile is valid?
  for remaining matchups??
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: revisit edit\copy options
- autocontinue: add halftime
- scheduler: convert league config into a single file
- [IN PROGRESS] scheduler: add schedule-C: Fixed-matchups for 2 or 3 matches (configurable?) + CP-SAT
- [DONE] schedule research: SOS analysis of real PNFL schedules
- [DONE] playpool: rename PlayRecord to Play; Same with OffensivePlayRecord, etc.
- [DONE] gameplan: rename Play to PlayRef; Same with CustomPlay and StockPlay
- [DONE] scheduler rules: range for shape (`p`); [0.75 to 1 (flat) seems ideal]
- [DONE] athc general: Handle exit codes consistently [Design and tools fixed]
- [DONE] scheduler: what is current backup strategy? Documented in design and release docs? Tests? [N/A]
- [DONE] scheduler: Find out how schedule-A resolves final matchups [H2H + fixed-rank]
- [DONE] gameplan: what is current backup strategy? Documented in design and release docs? Tests? [Yes]
- [DONE] profile: what is current backup strategy? Documented in design and release docs? Tests? [Yes]
- [DONE] playpool: user category now golden; folder categories for play attributes

## PLANNED

## DECIDED FOR

- Use `Click` for CLI, including `CliRunner` for CLI tests
- athc-admin using full installer (can always revisit)
- `uv` over pip and other tools

## DECIDED AGAINST

- Pydantic for config library - sticking with `configparser`
- Fully league agnostic playpool
- Fully league agnostic gameplan
- Fully league agnostic profile
