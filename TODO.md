# athc TODO

## TODO

- [ConferenceRanking] in tests and code, but not in config files? Claude you asshole
- profile check: add warning for game plan play categories not present in profile
- profile check: add proper punt\kick exemption (3-required, or all punt\kick\run clock)
- gameplan check: add profile option? to make sure profile is valid?
- profile rules: capitalize positions (QB, RB, etc.)
- rules files: need dev and release versions
- rules files: simpler comments; more readable
- playpool: simplification of directory processing (see Notepad++ `new 39`)
- scheduler rules: range for shape (`p`); 2 seems too flat
- scheduler: Find out how schedule-A resolves final matchups
- scheduler: `fixed-matchup`: one joint solve over the remaining 13 non-conference games,
  instead of the extra AFC-East-vs-NFC-East rank step + final H2H step.
- scheduler: add schedule-C: Fixed-matchups for 2 or 3 matches (configurable?) + CP-SAT
  for remaining matchups??
- autocontinue: add halftime; update for robustness
- gameplan: replace play (single and bulk) - list of plays as input??
- gameplan: remove play (single and bulk) - list of plays as input??

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
