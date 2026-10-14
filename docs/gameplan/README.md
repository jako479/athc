# gameplan

Library + CLI for FbPro98 gameplans (`.pln`). Validates a gameplan against league rules supplied as **external TOML files** — no rules are baked in; the tool is league-agnostic. Wraps [fbpro98_gameplan](../fbpro98_gameplan/) (`.pln` I/O) and [playpool](../playpool/) (per-play attributes).

**Status:** six pnfl subcommands ported — `check`, `find-play`, `list-normals`, `list-specials`, `set-normals`, `set-specials` — plus `replace-play` (new).

## Results and exit codes

Every command prints through the shared console ([architecture](../design/architecture.md#console-run-log-and-errors)): results, `OK` and `SKIP` lines on stdout; `WARN` and `FAIL` lines, progress and usage errors on stderr; every status line also in the run log. The same codes everywhere: `0` done (warnings included), `1` findings, `2` error (usage, config, a bad or missing file, a file that failed inside a batch, a bug). A batch processes every file and exits with the worst outcome. A named file that does not exist is `FAIL <file>: The system cannot find the file specified.`; an error in a play list names the list and its line, `FAIL <list>: line <n>: <reason>.`

| Command | Lines | Exit 1 (findings) |
|---|---|---|
| `check` | `WARN` per play-pool issue (`athc playpool check` lists the same problems on their own, with an exit code), then per file `OK   <file>: <side>, <n> normal` or the headline `<file>: <n> violation(s) (<side>, <n> normal)` with its indented detail lines; a blank line; `<n> file(s) checked, <n> with violations, <n> failed` | violations |
| `find-play` | per file and play `<file>: 'play' found in slot(s) ...` or `<file>: 'play' not found`; in directory mode a tally per play, `'play': found <n> instance(s) in <m> gameplan(s)`; a single path, found or not, gets no tally | a play found nowhere (2 if any file failed) |
| `list-normals` / `list-specials` | the play names (with `-`), else `OK   <file>: <n> normal play(s)` / `... special play(s)` | never |
| `replace-play` | per skipped replacement `SKIP <file>: 'new' already in the gameplan` or `SKIP <file>: 'new' fails check: [cat] message`; `OK   <file>: 'old' (cat) replaced with 'new' (cat) [1-1][2-2]` per updated file; `<file>: 'old' not replaced, no valid replacement` when none fits; a single file without the play prints `<file>: 'play' not found`; in directory mode `'old' -> 'new1', 'new2': replaced <n> instance(s) in <m> gameplan(s), <f> failed, <k> not replaced` | nothing replaced anywhere, or a gameplan with no valid replacement; a replacement not in the pool is an error |
| `set-normals` | `OK   <gameplan>: <n> normal play(s)` (`> nul` hides it; `FAIL` lines still show); a play list that is not UTF-8 text is `FAIL <list>: Not a valid play list.`; a bad play list is one `FAIL <list>: line <n>: <reason>` per bad line (`FAIL line <n>: <reason>` when the list came from the console), the game plan untouched, exit 2 | never |
| `set-specials` | `OK   <file>: updated (<n> special play(s))`, `SKIP <file>: <other side> gameplan`, `FAIL <file>: <why>` for a file the list does not fit; a tally `<n> file(s) processed, <n> updated, <n> skipped, <n> failed` | never (a failed file is exit 2) |

## Setup

```bash
uv sync
```

## Library

```python
from athc.fbpro98_gameplan import read_gameplan
from athc.gameplan import load_rules, validate_gameplan
from athc.playpool import read_play_pool

pool = read_play_pool("C:/PNFL/plays")
rules = load_rules(["gameplan.toml"])           # validation-only; pass more to layer
gp = read_gameplan("OFF.pln")
violations = validate_gameplan(gp, rules, pool)  # tuple[RuleViolation, ...]
```

## CLI

```bash
athc gameplan check                           # every .pln in the current folder
athc gameplan check off1                      # your team's 1st-half offense game plan
athc gameplan check plans -r                  # a folder and its subfolders
athc gameplan check OFF.pln --league PCFL     # another league

athc gameplan list-normals off1                    # 64 normal plays beside the game plan
athc gameplan list-normals OFF.pln plays.txt --sort category
athc gameplan list-specials def1 -                 # special teams to the console
athc gameplan find-play OR45RL01                   # your team's game plans
athc gameplan find-play OR45RL01 BCFGPAT --path plans -r
athc gameplan set-normals off1 plays.txt           # replace 64 normal slots
athc gameplan set-normals OFF.pln - > nul          # list from the console, OK lines hidden
athc gameplan set-specials spec.txt                # your team's game plans of the list's side
athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r
```

**Scope.** No path means the command's default, `.` the current folder, an explicit path overrides both. `check` defaults to the current folder; `find-play`, `replace-play` and `set-specials` default to your team's four game plans, and `--path` points them at a `.pln` file, a folder, a wildcard or one game plan key. `-r` includes subfolders.

**Game plan keys.** `off1`, `def1`, `off2` and `def2` are your team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense game plan, matched without case, wherever a game plan operand is (`check`'s PATH, `--path`, `GAME_PLAN`). A file or folder that exists by that name wins. A game plan shared by both halves is processed once.

**Team and sources.** The team is `team` in `league.toml`, or `--team NAME` for one run (the `.lge`'s team name, nickname or both, without case). A key's file comes from `ppp_path` (your team only), else from where the league file puts it (`path` plus the `.lg2` folder). `--team` with a path and no key is a usage error: `check`, `list-*` and `set-normals` need a key among their operands, and `find-play`, `replace-play` and `set-specials` need `--path` to be a key or left out.

**Missing files.** Where the league file puts them, a missing game plan is a `FAIL` counted as failed, and a team with none is one `FAIL` per folder; your team's lines add `Run 'athc config set ppp_path FOLDER' or pass --path.` (or `... or pass a .pln file.` for a key). In `ppp_path` a batch command `WARN`s per missing game plan, and one `WARN` names the team when none of the four is there. A named file that is missing is the run's error, exit 2.

`list-specials` and `find-play` with a path just read a `.pln` — no pool, rules or config; with the default scope, a key or `--team` they read `league.toml` and the league files. `list-normals` also reads the league's category names. `list-*` write beside the game plan by default and create the output file's missing folders. `set-*` need the pool and edit in place with no backup. `replace-play PLAY REPLACEMENT...` swaps one play for the first replacement that is not already in the game plan and with which it passes `check`; every replacement must be in the pool, and a repeated one is tried once. No command has a quiet flag: `> nul` hides the `OK` lines and keeps every `FAIL`. `athc gameplan <command> --help` for flags.

To check your team's game plans together with their profiles, use
[check-ppp](../check_ppp/README.md).

## Config

The league folder `leagues\<NAME>\` (see [../design/architecture.md](../design/architecture.md#config)), picked by `--league` / `[athc] league`:

- `gameplan.toml` — the rules (or a `gameplan_rules` array in `league.toml`, later files layering over earlier).
- `league.toml` `play_path` (pool dir) and its `[categories.*]` labels.
- `league.toml` `path`, `team` and `ppp_path`, read only when a run uses your team's game plans (the default scope, a key or `--team`).

`check` and `replace-play` read all of these from the league folder only. No rules resolvable ⇒ `check` exits 2 (nothing to validate); `replace-play` checks no league rule.

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers, layout, violation format.
- `config/release/leagues/<NAME>/gameplan.toml` — each league's rule set.

## Tests

`pytest tests/integration/test_gameplan_check.py`
