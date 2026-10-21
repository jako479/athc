# check-ppp

Check coaching profiles (`.prf`) against their game plans (`.pln`), as the
league file pairs them: each file against the league rules, and each pair for
how it fits. Replaced `profile check --gameplan`.

Usage, where the files come from, what it checks, lines and exit codes:
[usage/check-ppp.txt](../usage/check-ppp.txt).

## Code

`src/athc/cli/check_ppp.py` is a leaf command. It takes nothing from
`gameplan check` or `profile check`: reading, rules loading, pairing and
reports live in it. Which team, and where its files are, comes from the
shared team layer `src/athc/cli/_team.py` (the league files, the team
resolver, each team's files and where each one is, and the team checks and
lines the commands share). It uses the `profile`,
`gameplan`, `fbpro98_lg2` and `fbpro98_lge` libraries and the gameplan
group's `build_pool`. Tests: `tests/integration/test_check_ppp.py`.
