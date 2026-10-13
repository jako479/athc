# gameplan CLI plan

**Goal:** `athc gameplan` works on your team's game plans with nothing after the subcommand: `find-play`, `replace-play` and `set-specials` run over the four `.pln` files the league file names for your team, and every subcommand that takes a game plan, `check` included, takes one of the four by its name (`off1`, `def1`, `off2`, `def2`) in place of a path. A path still points any of them at a file, a folder or a wildcard. `gameplan check` keeps the current folder as its default, as check-ppp-cli.md decided, and every help text follows cli-help.md.

**Status:** proposal, 2026-10-13; nothing changed yet. Every choice is decided below, with its reason next to it. Reviewed in two rounds (coach workflows, codebase fit); the findings and the shared rules now in cli-help.md (rules 16 to 28) are folded in. Depends on cli-help.md landing first: every usage line, placeholder, hint and help block below is in its form.

## 1. Today

Source: `src/athc/cli/gameplan/` (`check.py`, `find_play.py`, `list_normals.py`, `list_specials.py`, `replace_play.py`, `set_normals.py`, `set_specials.py`, `_common.py`); the tool logic in `src/athc/gameplan/` (`config.py`, `writer.py`, `rules.py`, `validators.py`); the file library in `src/athc/fbpro98_gameplan/`.

- `athc gameplan`: a group; bare, it prints its help on standard error and exits 2. Summary "Validate and edit Front Page Sports Football Pro '98 gameplans (.pln)."
- `check [path]...`: `.pln` files, folders (`-r` for the tree) and wildcards; no path means the current folder. Reads the league's rules (`gameplan.toml` or the `gameplan_rules` list) and `play_path`; each play's attributes come from its play file (ddae7a1 dropped `playpool.toml`). `OK` per clean file, a headline and detail lines per file with violations, `FAIL` per file that cannot be read, a blank line and the tally `<n> file(s) checked, <n> with violations, <n> failed`. Exit 0 clean, 1 violations, 2 error. `--league`.
- `find-play play... [path]`: one argument is a play searched in the current folder; with two or more, the last is always the path (a file or a folder, `-r` for the tree, never a wildcard: a wildcard is a usage error). No league, pool or rules. Per file and play `<file>: 'play' found in slot 1-3` / `slots 1-3, 16-2` / `found in special slot 1 (Field Goal/PAT)` or `<file>: 'play' not found`; a folder ends with a blank line and one tally per play, `'play': found <n> instance(s) in <m> gameplan(s)`; a single file gets no tally. Exit 0 when any play is found anywhere, 1 none, 2 a failed file (`failed` wins). No `--league`.
- `list-normals gameplan [output_file]`: one `.pln`, checked to exist first (`named_file`); writes the 64 normal plays under a `:: <source>` header to `output_file`, or to `<name>.normals.txt` beside the game plan; `-` prints them. `--sort slot|name|category` (default `slot`); `category` groups under `:: <label>` headers with the league's names, so the command reads the league. `OK   <file>: <n> normal play(s)` when a file is written; exit 0 or 2. `--league`.
- `list-specials gameplan [output_file]`: the ten custom special-teams plays in game plan order, same output rules, `<name>.specials.txt`. Reads no league or config at all. No `--league`.
- `replace-play play replacement... [path]`: the last argument is the path when it is an existing file or folder, has a `\` or `/`, ends in `.pln` or is a wildcard (`_is_path`, `split_args`); otherwise the path is the current folder and every name after the first is a replacement, repeats dropped. Every replacement must be in the pool (one `FAIL`, nothing touched); the play need not. Per game plan the first replacement not already in it with which the plan passes `check` is written; `SKIP` lines say why one was passed over; `OK   <file>: 'OLD' (RL) replaced with 'NEW' (RM) [1-1]` per updated file; `<file>: 'OLD' not replaced, no valid replacement`; a single file without the play prints `<file>: 'OLD' not found`, a folder stays silent; a folder or wildcard ends with the tally `'OLD' -> 'NEW1', 'NEW2': replaced <n> instance(s) in <m> gameplan(s), <f> failed, <k> not replaced`. Exit 2 any failed file, 1 nothing replaced or a plan with no valid replacement, else 0. `--league`.
- `set-normals gameplan play_list`: one `.pln`, checked to exist first, and a play list (`-` reads the console); `::` lines and ` ::` trailers are ignored; more than 64 plays is `FAIL <list>: Too many plays (65). The most is 64.`; a special-teams play, or a play the pool lacks, is one `FAIL <list>: line N: ...` per bad line and nothing is written. `OK   <gameplan>: <n> normal play(s)`; `-q/--quiet` hides that line (the only quiet option in athc). Exit 0 or 2. `--league`. A list that is not UTF-8 text (a `.pln` given as the list) raises Python's `UnicodeDecodeError`, which `main` does not catch, so it prints `FAIL Unexpected error. See <log> for details.`
- `set-specials path play_list`: a `.pln`, a folder (`-r`) or a wildcard, and a play list (`-` for the console); more than 10 plays fails the list before the league is read; a duplicate, a non-special play or two plays for one special category fail it after the pool is built, before any game plan is read. The list's side comes from its first resolvable play; files of the other side are `SKIP <file>: defense gameplan`; categories not in the list keep their plays. `OK   <file>: updated (<n> special play(s))`, `FAIL <file>: <reason> (<list> line N).` for a play the plan cannot take, a blank line and the tally `<n> file(s) processed, <n> updated, <n> skipped, <n> failed`, for one file too. Exit 2 any failed file, else 0. `--league`. The same `UnicodeDecodeError` hole as `set-normals`.
- Nothing in the group knows which team is yours or where the game reads your game plans. The `.lg2` lists each team's eight files, each a folder relative to the game folder plus a name; the `.lge` beside it holds the team names (`src/athc/fbpro98_lg2/`, `src/athc/fbpro98_lge/`; both read from `path`). check-ppp-cli.md adds `team` and `ppp_path` under `[league]`, a team resolver over the `.lge` names and the three file sources; this plan reuses all of it through the shared `_team.py` decided in section 9.
- The real league (`E:\SIERRA\FbPro98\PNFL.lg2` and `PNFL.lge`, read 2026-10-13): 18 teams, one folder each (`PNFL\2048\Plans\<Team (Coach)>`), game plan names of every shape (`JAGS-O1.pln`, `BUFoff1.pln`, `DEN-OGP1.pln`, `Chargers OFFX.pln`, `49-48-O1.pln`), all distinct across teams; four teams use one game plan for both halves (`RAIDEROFF.pln` and `RAIDERDEF.pln` for Las Vegas; Los Angeles, Pittsburgh and Minnesota likewise); no team name or nickname repeats. The game's own stock leagues name the four profiles `OFF1.PRF`, `DEF1.PRF`, `OFF2.PRF`, `DEF2.PRF` (`08_TEAMS.LG2`) or `BILLSO1.PRF`, `BILLSD1.PRF`, `BILLSO2.PRF`, `BILLSD2.PRF` (`NFLPI97.LG2`), and share one game plan per side across halves (`OFF.PLN` / `DEF.PLN`, `BILLS0.PLN` / `BILLSD.PLN`).

## 2. Who runs it, for what

| # | Who | Wants to | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach | know which of this week's game plans hold a play, and where | `athc gameplan find-play OR45RL01` | a line per game plan of the four, then the tally |
| 2 | Coach | look for several plays in one game plan | `athc gameplan find-play OR45RL01 BCFGPAT --path off1` | one line per play, no tally |
| 3 | Coach | search a folder of drafts, or every archived week | `athc gameplan find-play OR45RL01 --path .` / `--path plans -r` | that folder, or each folder of the tree |
| 4 | Coach | swap a play the league removed from the pool, in every game plan | `athc gameplan replace-play OLDRUN NEWRUN` (`NEWRUN BACKUP` for a backup) | the four game plans, each updated or explained, then the tally |
| 5 | Coach | the same swap in one game plan, or in a draft | `athc gameplan replace-play OLDRUN NEWRUN --path def2` / `--path try3.pln` | that file, no tally |
| 6 | Coach | the swap through every archived week | `athc gameplan replace-play OLDRUN NEWRUN --path plans -r` | each folder of the tree |
| 7 | Coach | set the special-teams plays in every game plan from one list | `athc gameplan set-specials spec.txt` | the two game plans of the list's side updated, the other two `SKIP`ped, then the tally |
| 8 | Coach | set them in a draft | `athc gameplan set-specials spec.txt --path try3.pln` | that file, then the tally |
| 9 | Coach | edit the 1st-half offense plays in Notepad | `athc gameplan list-normals off1` (`--sort category` for groups, `-` for the console) | `<name>.normals.txt` beside the game plan |
| 10 | Coach | load the edited list back, then check it | `athc gameplan set-normals off1 plays.txt` (`-` reads the console), then `athc gameplan check off1` | the 64 normal slots replaced, one `OK` line; then that game plan's report |
| 11 | Coach | see the special-teams plays of the 1st-half defense | `athc gameplan list-specials def1 -` | the ten names on the console |
| 12 | Coach | list both halves' offense plays | `athc gameplan list-normals off1`, then `off2` | two files; for a team with one offense game plan, the same `<name>.normals.txt` written twice, the `OK` line naming the same path |
| 13 | Coach | the same with a game plan by path | any of 9 to 12 with `DEN-OGP1.pln` instead of the name | that file |
| 14 | Coach | check ten candidate game plans | `athc gameplan check *.pln` | each file (unchanged) |
| 15 | Coach | check this week's game plans with their profiles | `athc check-ppp` | the four pairs (check-ppp-cli.md) |
| 16 | Coach | keep the files in a working folder, not where the game reads them | `ppp_path` set once; the same commands | the four found there by name |
| 17 | Coach | run before setting `team`, or for a second team | `--team Broncos` on a run with no path, or with one of the four names (rows 1, 2, 4, 5 by name, 7, 9 to 12) | that team's files for one run |
| 18 | Coach | another league | any of these with `--league PCFL` | |
| 19 | Coach | from a script | the exit code; `> nul` hides the `OK` lines, `2> errors.txt` keeps the problems | |

## 3. What other tools do

- **Config names the default scope, a flag picks one other.** check-ppp-cli.md decisions 3 and 4, with their sources: kubectl's context namespace and `-n`, cargo's package and `-p`, pytest's `testpaths` ("Directories to search for tests when no files or directories are given on the command line"), ruff's `[default: .]`.
- **One of several must be named; a configured default or a flag picks it.** kubectl logs: "If the pod has only one container, the container name is optional." kubectl exec `-c, --container`: "Container name. If omitted, use the kubectl.kubernetes.io/default-container annotation for selecting the container to be attached or the first container in the pod will be chosen". cargo run: "If there are multiple binary targets, you must pass a target flag to choose one. Or, the default-run field may be specified in the [package] section of Cargo.toml to choose the name of the binary to run by default." and "--bin name Run the specified binary."
- **The game's own names for the four files.** The stock leagues' `.lg2` files name a team's profiles `OFF1.PRF`, `DEF1.PRF`, `OFF2.PRF`, `DEF2.PRF` (old stock) and `BILLSO1.PRF`, `BILLSD1.PRF`, `BILLSO2.PRF`, `BILLSD2.PRF` (modern stock); PNFL coaches name theirs `BUFoff1.pln`, `CINOFF1.pln`, `SKINDEF2.pln`, `DEN-OFF1.prf`, `LVOFF1.prf`. The `.lg2` spec words the slots "1st half offensive game plan" and so on.
- **Literal keywords are lowercase; capitals are placeholders.** cli-help.md rule 2 puts placeholders in UPPERCASE; kubectl's `-o` takes "json, yaml, kyaml, name, go-template, ..."; Click prints `Choice` values as they are declared.
- **A location option when the positionals vary in number.** grep keeps its files positional by fixing the pattern count: "grep [OPTION]... PATTERNS [FILE]..." with one PATTERNS, and several through "-e PATTERNS ... If this option is used multiple times or is combined with the -f (--file) option, search for all patterns given."; "If no FILE is given, recursive searches examine the working directory". git's `-C <path>`: "Run as if git was started in <path> instead of the current working directory." is the location-option form. cli-help.md already makes find-play's location `--path PATH`; check-ppp-cli.md decision 16 keeps check-ppp's PATH positional and names `-C` as "the flag form athc does not take".
- **Output on success, and quiet flags.** clig.dev: "Display output on success, but keep it brief." then "It's rare that printing nothing at all is the best default behavior, but it's usually best to err on the side of less." and "For instances where you do want no output (for example, when used in shell scripts), to avoid clumsy redirection of stderr to /dev/null, you can provide a -q option to suppress all non-essential output."; its standard-flag list has "-q, --quiet: Quiet. Display less output. This is particularly useful when displaying output for humans that you might want to hide when running in a script." under "Use standard names for flags, if there is a standard." Tools with one: git commit `-q` "Suppress commit summary message."; pip `-q` "Give less output. Option is additive, and can be used up to 3 times"; uv `-q` "Use quiet output." and "Repeating this option, e.g., -qq, will enable a silent mode in which uv will write no output to stdout."; xcopy `/q` "Suppresses the display of xcopy messages."; robocopy has no quiet switch but `/np`, `/nfl`, `/ndl`, `/njh`, `/njs`, `/ns`, `/nc`, each turning off one kind of line. Tools without one: Windows' `copy` (its switches are `/d /v /n /y /-y /z /a /b`; it ends with `<n> File(s) copied`); kubectl apply (25 options, no `-q`); pdf-converter, the project's model for the console.
- **Redirection on Windows.** Microsoft: "When you redirect console output using the > symbol, you are only redirecting STDOUT. In order to redirect STDERR, you have to specify 2>"; with `dir file.xxx > nul` "you will still see the error message". athc's design puts results, `OK` and `SKIP` on standard output and `WARN` and `FAIL` on standard error (architecture.md, Console), so `> nul` is one redirect that hides the success lines and keeps the problems.
- **An existing name is a path.** athc's own rule: replace-play today, "an existing file or folder (first, so a folder named like a play is the folder)", and cli-help.md rule 15, "A name that exists is a name, never a wildcard, so a folder like `Season [2029]` works."
- **A list from a file, later.** git: "--pathspec-from-file=<file> Pathspec is passed in <file> instead of commandline args. If <file> is exactly - then standard input is used."
- **Hints and defaults.** clig.dev: "Suggest commands the user should run." and "Make the default the right thing for most users."
- **A named file that is missing is an error; a discovered one is not.** athc's own rule (architecture.md): a named file that does not exist is `FAIL <path>: The system cannot find the file specified.`, a folder with nothing matching is a `WARN`; check-ppp-cli.md decision 6 applies it to the league locations (every file is named for the game: `FAIL`) and to a folder (nothing has to be there: `WARN`).

## 4. Decisions

1. **One scope rule for the group: no path means the command's default scope, `.` means the current folder, an explicit path overrides both** (check-ppp-cli.md decision 3). The default scope is your team's game plans for `find-play`, `replace-play` and `set-specials`, and the current folder for `check`. The three work on the game plans a coach means by "my game plans": the four files the game reads (rows 1, 4, 7). A coach's current folder can be anywhere, and a folder of drafts is the one place those three must not touch by accident; a working folder is `ppp_path`'s job (row 16), and a folder on the command line is `--path`'s. `check` keeps the current folder because check-ppp-cli.md decided it (decision 1, section 8): check-ppp is the team-scope checker, `gameplan check` checks `.pln` files by any name, many at once, like `ruff check`'s `[default: .]`.
2. **The scope of the three batch commands is an option, `--path PATH`.** `find-play` and `replace-play` take a variable number of play names, so a trailing positional path cannot be optional: Click's `_unpack_args` does give a trailing fixed positional the last word, but with the specs `[-1, 1]` and one argument it hands that word to PATH and leaves PLAY empty, which is today's single-argument ambiguity (`_is_path`'s guesswork, and the reason for cli-help.md's find-play fix); no path has to mean the default scope, so the path is an option. `set-specials` alone could keep `INPUT_FILE [PATH]`, the shape `list-normals` has; it takes `--path` so the three read alike (clig.dev: be consistent across subcommands), and for no other reason. This is a deviation from check-ppp-cli.md decision 16, which keeps PATH positional on check-ppp and calls git's `-C` "the flag form athc does not take": the reason is the variadic play arguments, which check-ppp does not have; `gameplan check` keeps PATH positional (cli-help.md rule 20).
3. **`--path` takes a `.pln` file, a folder, a wildcard, or one of the four names (decision 4), the same on all three.** A wildcard counts as a folder (a tally, misses silent), as `replace-play` does today. cli-help.md's "find-play --path refuses them" is dropped on consistency alone: one meaning of PATH across the group is what the request asks for, and today's code states the refusal without its reason. With Click's own Windows expansion off (cli-help.md G12) a wildcard in `--path` reaches the command whole, like `check`'s. Across plans `--path` means "where the game plans are" (cli-help.md rule 20): the three batch commands act on every game plan they find there, because they edit or search whatever is there; convert-pdb's `--path` takes a folder only and picks the team's four plans by their `.lg2` names, because its workbook has four slots.
4. **Your team's four game plans have names: `off1`, `def1`, `off2`, `def2`,** the 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense game plan the `.lg2` names for your team (its entries 2, 4, 6 and 8), in that order, matched without case. Lowercase because cli-help.md rule 2 reserves UPPERCASE for placeholders, so `OFF1` in a help line would read as one; Click prints `Choice` values as declared, and mainstream keywords are lowercase (kubectl `-o json`); the words themselves are the game's own stock names (`OFF1.PRF`, `DEF1.PRF`, `OFF2.PRF`, `DEF2.PRF`) and the shape most PNFL coaches use. In prose they are "the four names". An existing path always wins (cli-help.md rule 15, replace-play's `_is_path`): a file or folder named `off1` in the current folder is that file or folder. Two names that resolve to one file (a game plan shared across halves) are the same file. The profile commands use the same four words for the four `.prf` (Shared vocabulary).
5. **The four names are accepted wherever a game plan operand is: `GAME_PLAN` on `list-normals`, `list-specials` and `set-normals`, `--path` on the batch three, and `PATH` on `check`** (cli-help.md rule 17). `set-normals off1 plays.txt` is followed by `check off1`, as `profile check off2` is in profile-cli.md; adding a name to `check`'s PATH does not reopen check-ppp-cli.md decision 1 (its default and its job are unchanged). No `GAME_PLAN` stays Click's `Missing argument 'GAME_PLAN'.` (exit 2): with four candidates there is no right default (kubectl logs needs `-c` for a pod with several containers; cargo run needs `--bin` for several binaries), and listing all four is not what a list or a set of normals is (each game plan's 64 plays are its own). The help line names the four words, so `-h` teaches them. The arguments carry no explicit metavar (cli-help.md rule 22): the parameters are named `game_plan`, `input_file`, `output_file`, `play`, `replacement` and, on `check`, `path`, so Click derives `GAME_PLAN`, `INPUT_FILE`, `[OUTPUT_FILE]`, `PLAY...`, `REPLACEMENT...` and `[PATH]...` for the usage line and the same words in its `Missing argument` hints (a parameter named `plays` would read `PLAYS...`).
6. **`--team NAME` on every gameplan subcommand** (check-ppp-cli.md decisions 4 and 5): `team` in `league.toml` by default, `--team` for one run, the `.lge`'s names (team, nickname or both) matched without case, exactly one match, check-ppp's lines. `--team` with no name among the operands is a contradiction, so it is a usage error, `Error: Cannot use --team with a path.` (check-ppp decision 10's rule; cli-help.md rule 18): a `--path`, `GAME_PLAN` or `PATH` that is a real path, and `check --team X` with no PATH, which checks the current folder and names no team. `--league NAME` is never a contradiction: it is the shared option on every league command. A named league must exist, as `playpool check` with an explicit folder enforces today (`src/athc/cli/playpool/check.py`), so every subcommand resolves `--league` when it is given (the existing `League '<name>' not found` line, exit 2) and reads the league's files only when the run needs them: `find-play` and `list-specials` with a path need nothing from it, `check` reads its rules on every run, the other three the pool (cli-help.md rule 19). `--league` always takes a value (cli-help.md rule 19), with rule 10's text. `--team` only reads `team` to tell whether `ppp_path` applies. No `--all-teams`: no coach workflow needs it.
7. **Three sources for the files, in a fixed order** (check-ppp decision 3): the path on the command line; else `ppp_path` under `[league]` (your team's files found there by their `.lg2` names, without case; with `-r`, each folder of its tree on its own); else the league locations (`path` joined with each file's `.lg2` folder and name, exact). `ppp_path` applies only to the team `team` in `league.toml` resolves to: `--team` naming that same team goes through it; `--team` naming another team, or `--team` with `team` unset or unresolvable, uses the league locations (check-ppp decision 4; cli-help.md rule 18). `-r` is ignored for a file, a name and the league locations (check-ppp decision 9).
8. **Missing files follow check-ppp decision 6.** At the league locations every file is named for the game: a missing game plan is a `FAIL` counted as failed, and a team none of whose game plans exists gets one `FAIL` per `.lg2` folder, counted as one failed item. The `Set ppp_path ...` hint is added only when the run's team is the one `team` resolves to (defaulted, or `--team` naming it), as check-ppp decision 6 adds it only when the run checks your team; for another team `ppp_path` never applies (cli-help.md rule 18), so its lines carry no hint. In `ppp_path` nothing has to be there: a batch command `WARN`s per missing game plan and goes on, and when none of the four is in the scope (the folder, or the tree with `-r`) prints one `WARN` for the scope naming the team and the four names; the code stays what the files found give. A one-file command, or `check` with a name, names one file, so a missing one is the run's error (`FAIL`, exit 2) in either source. Whether a file is there is decided before anything reads it; a file that is there but cannot be read is handled as today.
9. **A game plan the `.lg2` names twice is processed once,** in `.lg2` order (off1, def1, off2, def2), `team_files` returns both pairs (section 9) and the command drops the repeat by resolved path, as `collect_files` already does and as check-ppp reports a shared game plan once.
10. **Tallies stay each command's.** `find-play` and `replace-play` print one for a set (the four game plans, a folder, a tree, a wildcard) and none for one file (a `.pln` path or a name), as today; `set-specials` prints its tally for one file too, as today and as `profile copy` does. Tally fields do not change; a `WARN`ed missing file counts nowhere.
11. **The league is read only when needed.** `find-play` and `list-specials` with an explicit path read no league files, pool or rules, as today; `--league` on such a run is resolved (the league must exist) and nothing is read from it; with the default scope, a name or `--team` they read `league.toml`, the `.lg2` and the `.lge`. Both gain `--league` (cli-help.md rule 10's shared option, on every command that reads league data).
12. **`-q/--quiet` goes, and no athc command has a quiet flag** (TODO.md's question, decided here for every command and recorded as cli-help.md rule 24). The evidence cuts both ways: clig.dev offers `-q` "to avoid clumsy redirection of stderr to /dev/null", and git commit, pip, uv and xcopy have one; Windows' `copy`, kubectl and pdf-converter do not, and robocopy has a switch per kind of line instead. What decides it is athc's own console design: the lines a script would hide (`OK`, `SKIP`, tallies) are on standard output and the problems on standard error, so `> nul` is one plain redirect that keeps every `FAIL`, which is exactly the clumsy case clig.dev's `-q` exists to avoid; `set-normals` prints one `OK` line (clig.dev: "keep it brief"); and athc has one output level per command (architecture.md's message kinds), not the graded verbosity pip's and uv's `-q` are the low end of. A `-q` on `set-normals` alone is the inconsistency TODO.md flagged; one on every command would need a definition of what it hides in a batch (`OK`, `SKIP`, the tally, which shares `console.result` with findings headlines) and a change to the console, for a need `> nul` already meets. `-q` becomes Click's unknown-option error, as on every other command; the README and COMMANDS.txt say `> nul`.
13. **`replace-play` takes `PLAY` then `REPLACEMENT...`, nothing else positional.** `split_args` and `_is_path` go; a replacement listed again, in any case, is still tried once. One name alone is Click's `Missing argument 'REPLACEMENT...'.`. The 1.0.0 TODO item for a list of play/replacement pairs will arrive as an option that reads a file (git's `--pathspec-from-file` shape, `-` for the console); since Click cannot make `PLAY` optional only when that option is given, that change makes both positionals optional and checks by hand that either the two positionals or the option is present. The file's format belongs to that change.
14. **`check` keeps its behaviour and gains the four names and `--team`** (decisions 5 and 6; cli-help.md's help fixes). Its default stays the current folder and its job the any-name checker; check-ppp is the command that checks your team's files with their profiles, and its one-file hints already point at `gameplan check`. Its docs gain the sentence that check-ppp checks pairs (check-ppp-cli.md section 8).
15. **A written list still lands beside its game plan by default** (architecture.md, Output files): with `ppp_path` that is the coach's own folder; at the league locations the `OK` line names the full path, and `OUTPUT_FILE` puts it anywhere. Two names for one shared game plan write the same file twice (row 12).
16. **Setup order:** Click's argument parsing; then `--league`, when given, resolved to an existing league folder (`resolve_league`, no file read; cli-help.md rule 19), before any operand, so a wrong name fails first on every subcommand; then the operands left to right as the usage line shows them: a game plan operand (a path is checked to exist, as `set-normals` does today; a name reads `team` from `league.toml`, a missing one failing here, then loads the `.lg2` and `.lge`, matches the team against the `.lge` names and locates the file, which is checked to exist), a play list operand (read, parsed and counted); then, for a batch command with the default scope, `league.toml`, the team, the `.lg2` and `.lge`, the four located; then the pool and rules; then the files are read. The `team` key is read from `league.toml` alone before the league files are loaded (cli-help.md rule 21), so a missing `team` shows before a missing `path`, and both show before the pool's `WARN` lines (check-ppp decision 12). A stock league is `Stock league not supported.` as in check-ppp. The order is today's for every run that names paths, except that a wrong `--league` now fails before the operands (today `set-normals` checks the game plan first, `set_normals.py` line 49); only a name adds the league reads in front of the file check.
17. **Lines are check-ppp-cli.md's where they say the same thing** (team resolution, `path` and `ppp_path` problems, the league files, a missing file, a team with no files), with "game plans" where check-ppp says "files". The "No team" and "No path" lines keep check-ppp's shape and end with the command's own way out (cli-help.md rule 21): `or pass --team or --path.` when the run used the default scope, `or pass --team or a .pln file.` when it used a name. The "No league selected" line is the shared one from `src/athc/config.py` and stays as it is; the help names `--path`.
18. **Keys: `team`, `ppp_path`, `path` under `[league]`, nothing new** (check-ppp decisions 14 and 15). Edited by hand in `league.toml`, like `play_path`.
19. **Help text is cli-help.md's** (its rule 25; that plan lands first): the blocks in section 5 (`[OPTIONS]`, UPPERCASE placeholders derived from the parameter names, a Positional arguments section, an Examples epilog, rule 10's `-r` and `--league` texts). The `--team` text is a per-command head and the shared tail: `Team whose game plans off1, def1, off2 and def2 name (default: team in league.toml).` (cli-help.md rule 18).
20. **A play list file that is not UTF-8 text is `FAIL <list>: Not a text file.`, exit 2.** Today a `.pln` given as the list raises `UnicodeDecodeError` (only bytes that are not valid UTF-8 raise it), a `ValueError` that `main` does not catch, so the coach sees the "Unexpected error" line and the log a traceback. The list reader turns it into `AthcError("Not a text file.", path)`, naming the list, for `set-normals` and `set-specials` alike (the same hole exists today in both). A list from the console (`-`) is text Python has already decoded (`sys.stdin.read()`) and is outside this change. The phrase is `collect_files`' `Not a .pln file.` shape.
21. **`check`'s attribute-cap violations name the counted plays** (handed over from playpool-cli.md section 8). After the count, in parentheses, the plays that were counted, in slot order, `A, B, C` style (architecture.md's list form): `Offensive category 'Pass Short Right' has 3 of 5 timed passes (A, B, C); allows at most 1/2.`, the game name as today (`src/athc/gameplan/rules.py` returns `member.long`), and the same for the `QB runs`, `rollouts` and defense `2-DL plays` lines (`_validate_offense` / `_validate_defense` in `src/athc/gameplan/validators.py`; `RuleName.CATEGORY_MAX_QB_RUNS`, `CATEGORY_MAX_ROLLOUTS`, `CATEGORY_MAX_TIMED`, `CATEGORY_MAX_TWO_DL`). The cap moment is when a coach needs the names, and `athc playpool show PLAY...` then says what each play is. The list is already in slot order: `_resolve_normal_plays` walks the slots in order and `_group_by_category` keeps it. `replace-play`'s `SKIP ... fails check:` line carries the same text through `format_violation`, and check-ppp's game plan reports too.

## 5. The command

### gameplan (group)

Summary "Check and edit game plans (.pln)." (cli-help.md). Bare `athc gameplan` prints its help on standard error and exits 2, as today.

### check

Default scope and job unchanged (decision 14); PATH takes the four names and the command takes `--team` (decisions 5 and 6).

```
Usage: athc gameplan check [OPTIONS] [PATH]...

  Check game plans against the league's rules.

  With no PATH, every .pln in the current folder is checked. To check your
  team's game plans with their profiles, run athc check-ppp.

Positional arguments:
  PATH  .pln files, folders or wildcards, or off1, def1, off2 or def2 for
        one of your team's game plans (default: current folder).

Options:
  -r, --recursive  Include subfolders.
  --team NAME      Team whose game plans off1, def1, off2 and def2 name
                   (default: team in league.toml).
  --league NAME    League to use (default: the one set with athc config
                   set league).
  -h, --help       Show this message and exit.

  Examples:

    athc gameplan check
    athc gameplan check off1
    athc gameplan check plans -r
```

- A name is one file in the batch, found as section 5's one-file modes say (a missing one is a `FAIL` counted as failed, with the hint when the team is yours); lines, order and codes are today's. A folder named `off1` in the current folder is searched like any folder, and a file named `off1` is `FAIL off1: Not a .pln file.`, as `collect_files` says today (cli-help.md rule 21).
- `--team` with paths only, or with no PATH at all (the current folder names no team), is `Error: Cannot use --team with a path.` (cli-help.md rule 18); `--league` is read for the rules as today.

### find-play

```
Usage: athc gameplan find-play [OPTIONS] PLAY...

  Find plays by name in game plans.

  Searches the normal and special-teams slots of your team's game plans, or
  of the game plans --path names, and lists each play's slots per game plan.

Positional arguments:
  PLAY  Plays to find (any case).

Options:
  --path PATH      Game plans to search: a .pln file, a folder, a wildcard,
                   or off1, def1, off2 or def2 (default: your team's game
                   plans).
  -r, --recursive  Include subfolders.
  --team NAME      Team whose game plans off1, def1, off2 and def2 name
                   (default: team in league.toml).
  --league NAME    League to use (default: the one set with athc config
                   set league).
  -h, --help       Show this message and exit.

  Examples:

    athc gameplan find-play OR45RL01
    athc gameplan find-play OR45RL01 BCFGPAT --path plans -r
```

- Every argument is a play (cli-help.md). Lines are today's; the four game plans are a set, so they end with the blank line and the per-play tallies; `--path off1` or `--path x.pln` is one file, no tally.
- Order: the four in `.lg2` order, a shared game plan once; in a folder or tree, `collect_files`' order as today.
- Exit codes as today: 0 a play found anywhere, 1 none, 2 any failed file.

### replace-play

```
Usage: athc gameplan replace-play [OPTIONS] PLAY REPLACEMENT...

  Replace one play with another in game plans.

  Each game plan gets the first REPLACEMENT not already in it with which it
  still passes athc gameplan check; the others are backups, tried in order.

Positional arguments:
  PLAY         Play to replace (any case).
  REPLACEMENT  Plays to put in its place, in order; each must be in the play
               pool.

Options:
  --path PATH      Game plans to edit: a .pln file, a folder, a wildcard, or
                   off1, def1, off2 or def2 (default: your team's game
                   plans).
  -r, --recursive  Include subfolders.
  --team NAME      Team whose game plans off1, def1, off2 and def2 name
                   (default: team in league.toml).
  --league NAME    League to use (default: the one set with athc config
                   set league).
  -h, --help       Show this message and exit.

  Examples:

    athc gameplan replace-play OLDRUN NEWRUN
    athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r
```

- Lines, order and codes as today; the four game plans are a set (tally, misses silent), a name or a `.pln` one file (`not found` line, no tally).
- A replacement listed again, in any case, is tried once (today's rule, kept in the command).

### set-specials

```
Usage: athc gameplan set-specials [OPTIONS] INPUT_FILE

  Set the special-teams plays from a play list.

  The list's side picks the game plans: files of the other side are skipped.
  Categories not in the list keep their plays.

Positional arguments:
  INPUT_FILE  Play list, one name per line (- reads the console).

Options:
  --path PATH      Game plans to edit: a .pln file, a folder, a wildcard, or
                   off1, def1, off2 or def2 (default: your team's game
                   plans).
  -r, --recursive  Include subfolders.
  --team NAME      Team whose game plans off1, def1, off2 and def2 name
                   (default: team in league.toml).
  --league NAME    League to use (default: the one set with athc config
                   set league).
  -h, --help       Show this message and exit.

  Examples:

    athc gameplan set-specials spec.txt
    athc gameplan set-specials spec.txt --path plans -r
```

- With the default scope an offense list updates off1 and off2 and prints `SKIP <path>: defense gameplan` for def1 and def2 (today's folder behaviour); the tally reads `4 file(s) processed, 2 updated, 2 skipped, 0 failed` (`2 ... 1 updated, 1 skipped` for a team with one game plan per side). One file (`--path try3.pln` or a name) gets its tally too, as today (decision 10).
- Lines and codes as today: 2 any failed file, else 0.

### Modes of the three batch commands

| `--path` | Team | Files come from | What is missing |
|---|---|---|---|
| none, `ppp_path` set | `team`, or `--team` naming it | that folder, each of the four by its `.lg2` name without case; with `-r`, each folder of its tree on its own | a game plan: `WARN`, not counted; all four, in the whole scope: one `WARN` naming the team and the names |
| none | `team`, or `--team` naming it, with `ppp_path` unset; `--team` naming another team, or with `team` unset, always | the league locations: `path` joined with each game plan's `.lg2` folder and name | a game plan: `FAIL`, counted as failed; all four: one `FAIL` per folder, absent or empty, counted as one failed item, with the `ppp_path` hint when the team is yours and none for another team (decision 8) |
| `off1`, `def1`, `off2` or `def2` | as the two rows above | that one file, from `ppp_path` when it applies, else its league location | `FAIL`, exit 2 (one file was named) |
| a `.pln`, a folder, a wildcard, `.` | none (`--team` is a usage error; `--league` must name an existing league and is otherwise not read) | as today | as today |

- A folder named `off1` in the current folder is a folder, so `--path off1` searches it like any folder, and a file named `off1` is `FAIL off1: Not a .pln file.`, as `collect_files` says today (decision 4, cli-help.md rule 21); the four names mean your team's file only when no such path exists.
- Argument errors: bare `find-play` is Click's `Missing argument 'PLAY...'.`, bare `replace-play` `Missing argument 'PLAY'.` and `replace-play OLD` `Missing argument 'REPLACEMENT...'.`, bare `set-specials` `Missing argument 'INPUT_FILE'.`, and `set-specials spec.txt extra` `Got unexpected extra argument (extra).` (Click's line with athc's period, added once in `src/athc/cli/__init__.py`, cli-help.md rule 23, the mechanism named in convert-pdb-cli.md); a `--team` that matches no team or two is Click's `Invalid value for '--team'` line (check-ppp's text); `--team` with a path is `Error: Cannot use --team with a path.`; `--league` naming a league with no folder is today's `FAIL League 'NOPE' not found. ...` line on every run, path or not (cli-help.md rule 19); a missing explicit path keeps today's lines.

### list-normals

```
Usage: athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT_FILE]

  List the 64 normal plays in a game plan.

  Writes them to OUTPUT_FILE, or to <name>.normals.txt beside the game plan;
  an existing file is replaced.

Positional arguments:
  GAME_PLAN    A .pln file, or off1, def1, off2 or def2 for one of your
               team's game plans.
  OUTPUT_FILE  Where to write the list (default: GAME_PLAN with
               .normals.txt, beside it; - prints it).

Options:
  --sort [slot|name|category]  slot keeps slot order (empty slots blank);
                               name sorts by name; category groups by
                               category under :: headers with the league's
                               names.  [default: slot]
  --team NAME                  Team whose game plans off1, def1, off2 and
                               def2 name (default: team in league.toml).
  --league NAME                League to use (default: the one set with
                               athc config set league).
  -h, --help                   Show this message and exit.

  Examples:

    athc gameplan list-normals off1
    athc gameplan list-normals DEN-OGP1.pln plays.txt --sort category
```

### list-specials

```
Usage: athc gameplan list-specials [OPTIONS] GAME_PLAN [OUTPUT_FILE]

  List the special-teams plays in a game plan.

  Writes them, in game plan order, to OUTPUT_FILE, or to <name>.specials.txt
  beside the game plan; an existing file is replaced.

Positional arguments:
  GAME_PLAN    A .pln file, or off1, def1, off2 or def2 for one of your
               team's game plans.
  OUTPUT_FILE  Where to write the list (default: GAME_PLAN with
               .specials.txt, beside it; - prints it).

Options:
  --team NAME    Team whose game plans off1, def1, off2 and def2 name
                 (default: team in league.toml).
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc gameplan list-specials def1 -
    athc gameplan list-specials DEN-DGP1.pln spec.txt
```

### set-normals

```
Usage: athc gameplan set-normals [OPTIONS] GAME_PLAN INPUT_FILE

  Set the 64 normal plays from a play list.

  Lines starting with ::, and text after " ::", are ignored. The league's
  play pool resolves names; run athc gameplan check afterward.

Positional arguments:
  GAME_PLAN   A .pln file, or off1, def1, off2 or def2 for one of your
              team's game plans.
  INPUT_FILE  Play list, one name per line (- reads the console).

Options:
  --team NAME    Team whose game plans off1, def1, off2 and def2 name
                 (default: team in league.toml).
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc gameplan set-normals off1 plays.txt
    athc gameplan set-normals DEN-OGP1.pln -
```

### Modes of the three one-file commands

| `GAME_PLAN` | Team | The file | What is missing |
|---|---|---|---|
| `off1`, `def1`, `off2` or `def2`, `ppp_path` set | `team`, or `--team` naming it | `<ppp_path>\<its .lg2 name>`, matched without case | `FAIL <ppp_path>\<name>: The system cannot find the file specified.`, 2 |
| one of the four names | `team`, or `--team` naming it, with `ppp_path` unset; `--team` naming another team, or with `team` unset, always | its league location | the same `FAIL`, with the `ppp_path` hint when the team is yours and none for another team (decision 8), 2 |
| a path | none (`--team` is a usage error; `--league` must name an existing league; `list-normals` reads it for its labels and `set-normals` for the pool, `list-specials` reads nothing from it) | that file, as today | as today |

- An existing path named `off1` is that path. A folder named `off1` in the current folder therefore gives `FAIL off1: Access is denied. Run from another folder to use your team's game plan.` (`named_file`'s folder line, with the imperative hint sentence added when the name is one of the four; cli-help.md rule 21, the shape every plan uses). A name the `.lg2` knows nothing of (`off3`) is a path like any other, so it is today's missing-file `FAIL`.
- No `GAME_PLAN` is Click's `Missing argument 'GAME_PLAN'.`; no `INPUT_FILE` on `set-normals` is `Missing argument 'INPUT_FILE'.`; `-q` is Click's unknown-option error; a `.pln`, or any file that is not UTF-8 text, given as `INPUT_FILE` is `FAIL <list>: Not a text file.` (decision 20); `set-normals off1 plays.txt extra` is `Got unexpected extra argument (extra).` (cli-help.md rule 23).
- `list-normals` and `list-specials` write beside the file they read (decision 15); `-` prints.

## 6. Settings

In `league.toml`, under `[league]`, the keys check-ppp-cli.md adds; this plan adds none. The comment text for `path` and `team` is the one shipped text check-ppp-cli.md section 6 owns:

```toml
# Needed for check-ppp and generate-schedule, and for off1, def1, off2 and def2 in gameplan, profile and convert-pdb -- the folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# Your team, for the same commands: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

- `find-play`, `replace-play` and `set-specials` read `path`, `team` and `ppp_path` when `--path` is absent or one of the four names; `check`, `list-normals`, `list-specials` and `set-normals` when an operand is one of the four names; every command when `--team` is given. With paths only none of the three keys is read.
- `--league` is accepted on every subcommand and the named league must exist (today's `League '<name>' not found` line otherwise, as `playpool check` with a folder gives it); `find-play` and `list-specials` read the league's files only when the run needs them (the default scope, a name, `--team`); `check` reads its rules, and `replace-play`, `set-normals` and `set-specials` the pool, on every run (decision 11, cli-help.md rule 19).
- `replace-play`, `set-normals` and `set-specials` read `play_path` and (`replace-play`) the gameplan rules as today (`playpool.toml` is gone since ddae7a1; a play's attributes come from its play file); `list-normals` the category labels as today; `check` its rules and pool as today.
- The run log gets the same lines as the console, as everywhere.

## 7. Lines and exit codes

New or changed lines, in the project's wording (`src/athc/errors.py`, `src/athc/console.py`); everything else prints as today. Team labels are the `.lge` team name (`Denver`); a found file prints its on-disk name, a missing one the league file's spelling (check-ppp decisions 5 and 8).

| When | Line | Code |
|---|---|---|
| no league set, default scope or a name (`find-play`, `list-specials` included, which need none for a path) | `FAIL No league selected. Run 'athc config set league NAME' or pass --league. Available: PCFL, PNFL.` (the shared line from `src/athc/config.py`, unchanged) | 2 |
| `--league` names a league with no folder (any subcommand, path or not) | `FAIL League 'NOPE' not found. No folder <leagues>\NOPE. Available: PCFL, PNFL.` (the shared line, unchanged; `_available()` sorts the names) | 2 |
| an attribute cap is exceeded (`check`, and `replace-play`'s `SKIP ... fails check:` line) | `[Pass Short Right] Offensive category 'Pass Short Right' has 3 of 5 timed passes (A, B, C); allows at most 1/2.`, the counted plays' names in slot order; the same for `QB runs`, `rollouts` and defense `2-DL plays` | 1 (`check`), as today |
| no `team`, no `--team`, default scope (batch) | `FAIL <league.toml>: No team for the league. Set team in this file, or pass --team or --path.` | 2 |
| no `team`, no `--team`, a name given (`--path off1`, `GAME_PLAN`, `check`'s PATH) | `FAIL <league.toml>: No team for the league. Set team in this file, or pass --team or a .pln file.` | 2 |
| `team` matches no team | `FAIL <league.toml>: [league] team: No team named 'Denvr'. Teams: Jacksonville Jaguars, Buffalo Bills, ...` | 2 |
| `--team` matches no team | `Error: Invalid value for '--team': no team named 'Denvr'. Teams: Jacksonville Jaguars, Buffalo Bills, ...` | 2 |
| `team` matches two teams | `FAIL <league.toml>: [league] team: 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | 2 |
| `--team` matches two teams | `Error: Invalid value for '--team': 'New York' matches New York Giants and New York Jets. Use the nickname, or both names in quotes.` | 2 |
| `team` is an array | `FAIL <league.toml>: [league] team: Expected a string, got an array.` | 2 |
| `--team` with paths only, or `check --team X` with no PATH | `Error: Cannot use --team with a path.` | 2 |
| bare `find-play` / `replace-play` / `set-specials`; `replace-play OLD`; bare `list-normals`, `list-specials`, `set-normals`; `set-normals off1` | Click's `Error: Missing argument 'PLAY...'.` / `'PLAY'.` / `'INPUT_FILE'.`; `'REPLACEMENT...'.`; `'GAME_PLAN'.`; `'INPUT_FILE'.` | 2 |
| `set-normals -q` | Click's unknown-option error | 2 |
| an extra positional (`set-specials spec.txt extra`, `set-normals off1 plays.txt extra`, `list-normals off1 out.txt extra`) | `Error: Got unexpected extra argument (extra).` (Click's text, athc's period added once in `src/athc/cli/__init__.py`, cli-help.md rule 23) | 2 |
| a `.pln`, or any file that is not UTF-8 text, as `INPUT_FILE` | `FAIL <list>: Not a text file.` (today: the "Unexpected error" line) | 2 |
| no `path` in `league.toml`, default scope (batch) | `FAIL <league.toml>: No path for the league. Set path in this file, or pass --path.` | 2 |
| no `path` in `league.toml`, a name given | `FAIL <league.toml>: No path for the league. Set path in this file, or pass a .pln file.` | 2 |
| `ppp_path` missing on disk, or a file | `FAIL <ppp_path>: The system cannot find the path specified. Set ppp_path in <league.toml>.` / `... The directory name is invalid. ...` | 2 |
| `.lg2` or `.lge` missing or bad | the library's line (`FAIL <PNFL.lge>: ...`) | 2 |
| a stock league | `FAIL <PNFL.lg2>: Stock league not supported.` | 2 |
| the two league files disagree | `FAIL <PNFL.lg2>: Lists 17 team(s), but PNFL.lge has 18.` | 2 |
| league location, a game plan missing (batch) | `FAIL <folder>\DEN-OGP2.pln: The system cannot find the file specified.`, counted as failed | 2 |
| league location, none of the four, folder present (batch, your team) | `FAIL <folder>: No Denver game plans. Set ppp_path in <league.toml>, or pass --path.`, counted as one failed item | 2 |
| league location, none of the four, folder present (batch, `--team` naming another team) | `FAIL <folder>: No Las Vegas game plans.`, counted as one failed item; no hint, since `ppp_path` never applies to another team (cli-help.md rule 18) | 2 |
| league location, none of the four, folder absent (batch, your team) | `FAIL <folder>: The system cannot find the path specified. Set ppp_path in <league.toml>, or pass --path.`, counted as one failed item | 2 |
| league location, none of the four, folder absent (batch, another team) | `FAIL <folder>: The system cannot find the path specified.`, counted as one failed item, no hint | 2 |
| league location, the named game plan missing (one file, or `check` with a name; your team) | `FAIL <folder>\DEN-OGP1.pln: The system cannot find the file specified. Set ppp_path in <league.toml>, or pass the file.` (the path phrase when the folder is absent) | 2 |
| league location, the named game plan missing (another team) | `FAIL <folder>\RAIDEROFF.pln: The system cannot find the file specified.`, no hint | 2 |
| `ppp_path`, a game plan missing (batch) | `WARN <ppp_path>\DEN-OGP2.pln: The system cannot find the file specified.` | unchanged |
| `ppp_path`, none of the four in the scope (batch) | `WARN <ppp_path>: No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, DEN-OGP2.pln, DEN-DGP2.pln.` (each name once; one line for the scope, tree included) | `find-play` 1, `replace-play` 1, `set-specials` 0 |
| `ppp_path`, the named game plan missing (one file, or `check` with a name) | `FAIL <ppp_path>\DEN-OGP1.pln: The system cannot find the file specified.` | 2 |
| a folder named like one of the four is given where one file is needed | `FAIL off1: Access is denied. Run from another folder to use your team's game plan.` (cli-help.md rule 21) | 2 |
| a file named like one of the four is given on `check` PATH or `--path` | `FAIL off1: Not a .pln file.` (`collect_files`, as today) | 2 |
| the tallies | unchanged; the four count as the files found | |

A batch runs every file it found and exits with the worst outcome, as today: error beats findings beats clean; a `WARN` never changes the code.

## 8. Related commands

- **check-ppp** checks your team's four pairs with the same `team`, `ppp_path` and `path`, the same team resolver and the same lines; `gameplan check` stays the any-name checker and its help points at check-ppp.
- **profile** uses the four names for the four `.prf` (`athc profile diff off1 off2`, `athc profile check off2`) and the same `--team`; the Shared vocabulary section carries the texts both plans use.
- **playpool check** is the in-house precedent for "nothing means the configured place, a folder instead".
- **playpool show PLAY...** (playpool-cli.md) says what each play is, and **playpool list [CATEGORY]...** lists a category's plays with their attributes, so a coach can pick a replacement; `check`'s cap lines name the counted plays so a coach can go straight there (decision 21).

## 9. Code

- `src/athc/cli/_team.py` (new, beside `_files.py`; its contents are decided here, and profile-cli.md and convert-pdb-cli.md use the same): the team layer every plan shares, moved out of `check_ppp.py`. `TEAM_FILE_NAMES = ("off1", "def1", "off2", "def2")`; `load_league_files(league, league_dir)` (the `.lg2` with its stock check, then the `.lge`, then the team counts compared, check-ppp decision 12's order); `resolve_team(name, lge)` (team, nickname or both, without case, exactly one; check-ppp decision 5's two error lines); `team_files(team, kind)` (the four `(name, file)` pairs of one kind in `.lg2` order, a shared file repeated so a caller with fixed slots knows which slot each file fills; the batch commands and check-ppp drop repeats by resolved path, as `collect_files` does); `locate(file, ppp_path, league_path) -> Located(path, exists, source)` (check-ppp decision 3's three sources, existence decided before any read). Also the key constants `TEAM_KEY = "team"` and `PPP_PATH_KEY = "ppp_path"`, with `LEAGUE_PATH_KEY` imported from `src/athc/config.py`, where dade898 moved it from `check_ppp.py` (the third is re-exported, not defined twice), read through `LeagueConfig.string` and `LeagueConfig.path`. `team_option` goes in `src/athc/cli/__init__.py` beside `league_option` (architecture.md's "What goes where": shared decorators), with the per-command head passed in and the shared tail fixed.
- `src/athc/cli/gameplan/_common.py`: `scope(path, team, league, *, recursive) -> Collected`: a real path through `collect_files` as today; `None` or one of the four names through `_team`, the `WARN` / `FAIL` lines of decision 8 as `Collected.warnings` / `errors`, the `--team`-with-a-path `UsageError`. `one_game_plan(raw, team, league) -> Path`: `named_file` for a path (the folder hint added when `raw` is one of the four), the resolver for a name. `read_play_list(path) -> str`: `named_file(...).read_text(encoding="utf-8-sig")` with `UnicodeDecodeError` turned into `AthcError("Not a text file.", path)` (decision 20), used by `set-normals` and `set-specials`.
- `src/athc/cli/gameplan/check.py`: the argument `path` (`nargs=-1`, no metavar: `[PATH]...`); entries that are one of the four names resolved through `_team` before `collect_files`; `team_option`, a usage error with no name among the entries, no PATH at all included; help text.
- `src/athc/cli/gameplan/find_play.py`: the argument `play` (`nargs=-1, required=True`, no metavar, so Click prints `PLAY...`), `--path`, `team_option`, `league_option`; the single-argument split and the wildcard refusal go; `single_path` becomes "the scope is one file".
- `src/athc/cli/gameplan/replace_play.py`: the arguments `play` and `replacement` (`nargs=-1, required=True`), no metavars (Click prints `PLAY REPLACEMENT...` and hints `'REPLACEMENT...'`), `--path`, `team_option`; `split_args` and `_is_path` go; the repeat-dropping moves into the command.
- `src/athc/cli/gameplan/set_specials.py`: the one argument `input_file` (no metavar: `INPUT_FILE`), `--path`, `team_option`; the list through `read_play_list`.
- `src/athc/cli/gameplan/set_normals.py`: `-q/--quiet` removed; the arguments `game_plan` and `input_file` (no metavars); `game_plan` through `one_game_plan`; the list through `read_play_list`; `team_option`.
- `src/athc/cli/gameplan/list_normals.py`, `list_specials.py`: the arguments `game_plan` and `output_file` (no metavars: `GAME_PLAN [OUTPUT_FILE]`); `game_plan` through `one_game_plan`; `team_option`; `list_specials.py` gains `league_option`.
- `src/athc/cli/gameplan/__init__.py`: help text only.
- `src/athc/gameplan/validators.py`: `_validate_offense` and `_validate_defense` keep the matched plays of each cap (not just their count) and put their names, slot order, `, `-joined in parentheses after the count in the four cap messages; `RuleViolation` and `RuleName` are unchanged.
- `src/athc/config.py`: `LeagueConfig.string(key)` (check-ppp-cli.md section 9). `LgeFile.teams` already exists (`src/athc/fbpro98_lge/model.py`, dade898), so that item of check-ppp's section 9 is done.
- `src/athc/cli/check_ppp.py`: its resolver, league-file loader and sources import from `_team.py` (check-ppp-cli.md section 9 amended, below); no behaviour change here.
- `config/release/leagues/*/league.toml`, `config/dev/leagues/*/league.toml`: the comments above `path` name the gameplan commands too.

## 10. Tests

New, in the existing files (`tests/integration/test_gameplan_check.py`, `test_gameplan_find_play.py`, `test_gameplan_replace_play.py`, `test_gameplan_set_specials.py`, `test_gameplan_list.py`, `test_gameplan_set_normals.py`, `tests/unit/gameplan/test_validators.py`), on the fixtures check-ppp-cli.md builds, moved from `tests/integration/test_check_ppp.py` to `tests/integration/conftest.py` with the `.lg2`/`.lge` builders (decided here; profile-cli.md and convert-pdb-cli.md use the same names) under the shared clash-free names: `build_league` (a league folder with `path` and `team`; today's `league` fixture there, renamed because eight integration modules, `test_profile_check.py`, `test_gameplan_set_specials.py`, `test_gameplan_set_normals.py`, `test_gameplan_replace_play.py`, `test_gameplan_list.py`, `test_check_ppp.py`, `test_gameplan_check.py` and `test_convert_pdb.py`, and `tests/unit/pdbtoexcel/test_config.py` define a fixture named `league`), `lg2_league` (a built league with `.lg2` and `.lge` beside `league.toml`), `pnfl_league` (the real `tests/integration/data/PNFL.lg2` with a `PNFL.lge` beside it, over `data/ppp`: Denver's four files, Las Vegas's one game plan per side) and the `team()` builder (one team's eight names):

- Cap lines (decision 21), in `tests/unit/gameplan/test_validators.py`: each of the four cap messages names the counted plays in slot order, one play `(A)` and several `(A, B, C)`; a play outside the count is not named. Limits are the existing cap tests' (at the cap accepted, one past it fires).

- The four names: each maps to its `.lg2` entry (off1 = 1st-half offense game plan, def1, off2, def2); any case; a shared game plan once for the batch commands and the same file for two names; an existing path named `off1` wins (a `.pln` file: used; a folder on a one-file command: the `Access is denied.` line with its imperative hint; a folder on `check` PATH or `--path`: searched; a file named `off1` on `check` PATH or `--path`: `Not a .pln file.`); `off3` is today's missing-file `FAIL`. On `check`: `check off1` checks that file, `check off1 x.pln` both. Limits: the four accepted, a fifth rejected.
- Sources: default scope with `ppp_path`; without it; `--path .`; `--path <folder>`; `--path <wildcard>` on all three (find-play's new one; the sixth wildcard CLI test of cli-help rule 15); a relative `ppp_path`; `ppp_path` missing on disk and a file; `-r` over a `ppp_path` tree (the no-game-plans `WARN` once for the tree); `-r` ignored at the league locations.
- Team: `team`; `--team` by name, nickname, both, mixed case; no match and two matches (a built `.lge`); blank; an array; `--team` beats `team`; `--team` naming your team goes through `ppp_path`, naming another team or with `team` unset uses the league locations (cli-help.md rule 18); neither set (the two "No team" hints); `--team` with paths only (usage error) on a batch command, a one-file command and `check`, and `check --team X` with no PATH (cli-help.md rule 18); `--league` with a path on `find-play` and `list-specials`: an existing league is resolved and nothing read from it, `--league NOPE` fails with the no-such-league line even with a path, and no `--league` with no `athc.ini` at all still works. Limits: one match accepted, zero and two rejected.
- Missing files: league locations, one game plan missing (`FAIL`, counted failed, exit 2, the others processed); none of the four, folder present and absent (one line, one failed item in the tally; the `ppp_path` hint for your team, none for `--team` naming another team, decision 8); `ppp_path`, one missing (`WARN`, code unchanged); none of the four (the names line; `find-play` 1, `replace-play` 1, `set-specials` 0); a one-file command's named file missing in each source; `check off1` with the file missing.
- League files: no `path` (the two hints); `.lg2` or `.lge` missing; a stock league; team counts equal accepted, off by one rejected; no league selected on `find-play` with the default scope and on `list-specials off1`.
- Setup order: a missing `team` shows before a missing `path`; a `--team` typo shows before the pool's `WARN` lines; a too-long list fails before any league read on `set-specials` and on `set-normals` with a path; `set-normals off1 <too long list>` reads the league first.
- `set-specials` over the four: the list's side updated, the other side `SKIP`ped, the tally; one file keeps its tally; `find-play` and `replace-play` over the four: `.lg2` order, a tally, a shared game plan once.
- `replace-play`: bare is `Missing argument 'PLAY'.`, `OLD` alone `Missing argument 'REPLACEMENT...'.` (`test_cli_one_name_is_usage_error` asserts `"Missing argument 'REPLACEMENT...'." in result.stderr`); a repeated replacement tried once (CLI, replacing the `split_args` unit tests). Bare `find-play` and bare `set-specials` give their `Missing argument` lines.
- `set-normals -q` rejected; a `.pln` as `INPUT_FILE` is `FAIL <list>: Not a text file.` on `set-normals` and `set-specials`, the game plan untouched.
- `tests/integration/test_cli_root.py`: `LEAGUE_COMMANDS` gains `find_play`, `list_normals` and `list_specials`; `_unknown_league_args` gives `find_play` `["Some Play", "--path", str(GP_OFFENSE)]` and `list_specials` `[str(GP_OFFENSE)]` (a named league must exist even with a path, cli-help.md rule 19), `list_normals` `[str(GP_OFFENSE)]`, `replace_play` `["Old Play", "New Play", "--path", str(GP_OFFENSE)]`, `set_specials` `[str(plays), "--path", str(GP_OFFENSE)]`; `--league NOPE` fails at `resolve_league` before any team or league file is needed, so the test's `make_league()` is fixture enough.
- Help: every block in section 5 under cli-help.md's style, in that plan's tests.

Existing tests that change:

- `tests/integration/test_gameplan_find_play.py`: `test_cli_single_arg_searches_current_directory` (one argument now searches your team's game plans: becomes the default-scope test; the current folder is `--path .`), `test_cli_single_arg_recursive` and `test_cli_single_arg_empty_directory_exit_1` (`--path .`), `test_cli_two_args_last_is_the_path` (two arguments are now two plays: becomes the "every argument is a play" test), `test_cli_wildcard_path_is_rejected` (a wildcard now works like a folder), and every test that passes the path as the last argument moves it to `--path`: `test_cli_single_file_hit`, `test_cli_single_file_miss_exit_1`, `test_cli_single_file_case_insensitive`, `test_cli_finds_custom_special`, `test_cli_multiple_plays_all_hit`, `test_cli_one_play_found_exit_0`, `test_cli_no_play_found_exit_1`, `test_cli_directory_reports_hit_and_miss_per_file`, `test_cli_directory_misses_are_reported`, `test_cli_verbose_option_is_rejected`, `test_cli_directory_summary_counts_multiple_hits`, `test_cli_directory_per_play_summary`, `test_cli_recursive_finds_in_subdir`, `test_cli_missing_path_exit_2`, `test_cli_malformed_pln_exit_2`. `test_cli_requires_args` keeps passing by design.
- `tests/integration/test_gameplan_replace_play.py`: the `split_args` tests go (`test_split_one_name_is_usage_error`, `test_split_play_and_replacement`, `test_split_play_and_folder_only_is_usage_error`, `test_split_last_existing_folder_is_path`, `test_split_last_existing_file_is_path`, `test_split_path_looking_name_is_path`, `test_split_plain_names_are_replacements`, `test_split_folder_named_like_play_is_the_folder`; `test_split_drops_repeated_replacements` becomes a CLI test); `test_cli_one_name_is_usage_error` (the message names `'REPLACEMENT...'`); `test_cli_path_left_out_uses_current_folder` (becomes the default-scope test); and every test that passes the path as the last argument moves it to `--path`: `test_cli_every_replacement_must_be_in_pool`, `test_cli_no_quiet_option`, `test_cli_replacement_not_in_pool_exit_2`, `test_cli_replacement_case_insensitive`, `test_cli_single_file_replaces_normal`, `test_cli_play_in_several_slots_not_replaced`, `test_cli_output_uses_game_names_without_league_labels`, `test_cli_single_file_replaces_special`, `test_cli_single_file_target_case_insensitive`, `test_cli_single_file_miss_exit_1`, `test_cli_backup_used_when_first_already_in_plan`, `test_cli_backup_used_when_first_breaks_rule`, `test_cli_rollout_cap_uses_the_play_file`, `test_cli_cross_category_swap_within_limits`, `test_cli_cross_category_swap_leaves_losing_category_short`, `test_cli_no_valid_replacement_single_file`, `test_cli_directory_counts_not_replaced`, `test_cli_refused_later_replacement_names_it`, `test_cli_wildcard_path_works_like_a_folder`, `test_cli_bad_rules_file_exit_2`, `test_writes_no_backup`, `test_no_backup_option_removed`, `test_cli_directory_updates_matching_files`, `test_cli_directory_leaves_other_side_untouched`, `test_cli_directory_no_hits_exit_1`, `test_cli_recursive_replaces_in_subdir`, `test_cli_replacement_special_for_normal_fails`, `test_cli_replacement_wrong_side_fails`, `test_cli_replacement_wrong_special_category_fails`, `test_cli_missing_path_exit_2`, `test_cli_malformed_pln_exit_2`, `test_cli_invalid_play_path_exit_2`, `test_cli_play_path_option_removed`, `test_cli_continues_past_failed_file`. `test_cli_requires_args` and the `pick_replacement`, `replace_in_gameplan` and `format_replacement_lines` tests keep passing by design.
- `tests/integration/test_gameplan_set_specials.py`: `test_requires_path` (becomes "requires INPUT_FILE"), `test_requires_play_list` (a `.pln` as the only argument is now the list: becomes the `Not a text file.` test, exit 2, the game plan untouched), and every test that passes the game plan first moves it to `--path`: `test_no_quiet_option`, `test_removed_options_rejected`, `test_writes_special_from_file`, `test_a_list_saved_with_a_bom_reads_its_first_play`, `test_merge_preserves_other_categories`, `test_writes_no_backup`, `test_skips_and_strips_comments`, `test_dash_reads_from_console`, `test_dash_input_errors_name_no_file`, `test_gameplan_problem_names_the_gameplan_and_the_list_line`, `test_gameplan_problem_from_the_console`, `test_rejects_normal_play`, `test_rejects_duplicate_play`, `test_as_many_plays_as_slots_pass_the_count`, `test_too_many_plays_rejected`, `test_missing_target`, `test_missing_play_list`, `test_invalid_play_path`, `test_directory_top_level_only`, `test_directory_recursive`, `test_offense_input_skips_defense_files`, `test_continues_past_failed_file`.
- `tests/integration/test_gameplan_set_normals.py`: `test_quiet_still_updates` becomes the "-q is rejected" test (exit 2, Click's unknown-option text); everything else keeps passing by design (`GAME_PLAN` stays positional, a path is still checked first).
- `tests/integration/test_gameplan_list.py`: `test_normals_help_uses_lowercase_names` and `test_specials_help_uses_lowercase_names` change with cli-help.md's style (that plan's change); the rest keeps passing by design.
- `tests/integration/test_gameplan_check.py`: `test_check_file_matches_golden[offense]` reads `tests/integration/expected/offense.report.txt`, whose two cap lines (lines 2 and 4, `timed passes`) gain the play names in parentheses (decision 21); the golden changes with the approved line, the test passes by design once it has. `test_cli_attribute_caps_apply` (ddae7a1's name; substring `timed passes`) and `test_check_file_pinned_counts` keep passing by design. The other goldens (`defense.report.txt`, `compat_offense.report.txt`, `compat_defense.report.txt`, `TST-OFF1.report.txt`, `TST-DEF1.report.txt`) hold no cap line and do not change. The file gains the name, `--team` and hint tests above.
- `tests/integration/test_gameplan_replace_play.py::test_cli_rollout_cap_uses_the_play_file`: pins `... has 1 of 1 rollouts; allows at most 0.` inline; becomes `... has 1 of 1 rollouts (AF1AwagR); allows at most 0.` (decision 21).
- `tests/integration/test_check_ppp.py`: its `golden()` helper (line 157) stitches the same `expected/*.report.txt` files, so `test_cli_both_matches_existing_reports`, `test_cli_bad_profile_still_checks_gameplan`, `test_dir_checks_each_pair_in_league_file_order`, `test_dir_teams_in_league_file_order`, `test_dir_unlisted_files_are_ignored`, `test_dir_shared_gameplan_is_reported_once` and `test_dir_unreadable_file` read the changed `offense.report.txt` and pass by design once it is updated.
- `tests/unit/gameplan/test_validators.py`: the cap tests (`test_offense_max_qb_runs_count_fires`, `test_offense_max_rollouts_count_fires`, `test_offense_max_timed_ratio_fires`, `test_offense_max_timed_percent_fires`, `test_two_dl_cap_fires` and their clean twins) check `RuleName` membership only, so they keep passing by design; the message tests above are new.
- `tests/integration/test_cli_root.py`: `LEAGUE_COMMANDS` and `_unknown_league_args` as above. cli-help.md lands first (its rule 25) and rewrites its rows in its style; this plan then changes the `test_help_uses_lowercase_names` rows whose shapes it changes: `gameplan find-play` shown `PLAY...`, `--path PATH`, `--team NAME`, `--league NAME`, hidden `PLAYS`, `[PATH]`; `gameplan replace-play` shown `PLAY REPLACEMENT...`, `--path PATH`, `--team NAME`, hidden `PATH]`; `gameplan set-specials` shown `INPUT_FILE`, `--path PATH`, `--team NAME`, hidden `PATH INPUT_FILE`; `gameplan check`, `set-normals` and `list-normals` add `--team NAME` to their shown lists. The `test_usage_lists_each_option` rows for `gameplan find-play` (`Usage: athc gameplan find-play [OPTIONS] PLAY...`) and `gameplan list-normals` (`Usage: athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT_FILE]`) keep cli-help.md's values, since `--path`, `--team` and `--league` sit under Options and not in the usage line; those two rows wait on cli-help.md alone.
- `tests/integration/test_check_ppp.py`: its `league`, `lg2_league`, `team` and `pnfl_league` fixtures and the `.lg2`/`.lge` builders move to `tests/integration/conftest.py`; `league` becomes `build_league` and the others keep their names (main's `tests/integration/league_files.py` module rules out a `league_files` fixture), and its tests take the new name; they keep passing by design.
- `tests/integration/README.md`: the rows of every test named above.

## 11. Docs and meta

- `docs/gameplan/README.md`: the CLI section rewritten around the scope rule, the four names, `--path`, `--team`, the sources and the lines above; the `check` row shows a cap line with its names and points at `playpool show`; the `set-normals` row loses `-q` and the section says `> nul` hides the `OK` lines; the sentence pointing at check-ppp for pairs (check-ppp-cli.md section 11).
- `docs/gameplan/ARCHITECTURE.md`: the check, find-play, set-normals / set-specials and replace-play sections (arguments, `--path`, the names, no `split_args`, `read_play_list`), the layout (`_team.py` shared), the exit-code paragraph unchanged.
- `docs/design/architecture.md`: CLI section: `--team NAME` as a shared decorator beside `--league`, on every command that resolves a team's files; the `--league` command list gains `find-play` and `list-specials`; Config: `team` and `ppp_path` are shared by check-ppp, gameplan and profile.
- `docs/design/TODO/check-ppp-cli.md`: this is the one list of its amendments (profile-cli.md and convert-pdb-cli.md point here). Section 9's team resolver, league-file loader and sources move to `src/athc/cli/_team.py`, with `team_files(team, kind)` returning the four `(name, file)` pairs, a shared file repeated (section 9; check-ppp drops repeats by resolved path), `locate(...) -> Located(path, exists, source)`, the key constants `TEAM_KEY` and `PPP_PATH_KEY`, and `LEAGUE_PATH_KEY` imported from `src/athc/config.py`, where dade898 moved it; its `--team` becomes the shared `team_option("Team to check")` in `src/athc/cli/__init__.py` (cli-help.md rule 18); its fixtures move to `tests/integration/conftest.py` as `build_league`, `lg2_league`, `pnfl_league` and `team()` (section 10); `LgeFile.teams` exists since dade898, so that item of its section 9 is done, and `LeagueConfig.string` stays to add; its own `Got unexpected extra argument` raise and section 7 row become unnecessary once `src/athc/cli/__init__.py` adds the period for every command (cli-help.md rule 23); its "No path" line becomes `FAIL <league.toml>: No path for the league. Set path in this file, or pass the folder.` (cli-help.md rule 21); `team` is read from `league.toml` before the league files (cli-help.md rule 21), so `test_dir_first_setup_error_stops_the_run` sees the "No team" error first instead of "No path"; its decision 17 and section 5 block become the cli-help.md form (`[OPTIONS] [PATH]...`, a PATH help line, `--team NAME`, rule 10's `-r` and `--league` texts; its rule 25); and its section 6 owns the shipped `league.toml` comment text for `path` and `team`, quoted in section 6 here.
- `docs/design/TODO/cli-help.md` changes: find-play's `--path` default becomes your team's game plans, takes a wildcard and the four names, and the command gains `--team` and `--league`; rule 15 lists `--path` in `find-play`, `replace-play` and `set-specials` instead of their PATH, drops "find-play --path refuses them", and its wildcard CLI tests become six; replace-play's usage is `[OPTIONS] PLAY REPLACEMENT...` and it gains `--team`; set-specials' usage is `[OPTIONS] INPUT_FILE` and it gains `--team`; check's PATH help gains the four names and the command `--team`; list-normals, list-specials and set-normals get the `GAME_PLAN` help line above, `--team`, and list-specials `--league`; set-normals loses `-q` (rules 11 and 24); rule 3's `GAME_PLAN` entry reads "one .pln file, or one of your team's four names (off1, def1, off2, def2)"; `--team NAME` is rule 18's.
- `config/release/docs/COMMANDS.txt`: sections 1 to 7 rewritten (examples above; the `-q` example gone, `> nul` in its place; section 1 gains the names, a cap line with its play names and the pointer to `playpool show`, and the check-ppp sentence); `config/release/docs/README.txt`: FIRST-TIME SETUP names `team` beside `path` for check-ppp and the gameplan commands; `config/release/athc.ini`'s header comment likewise.
- `CHANGELOG.md` (athc section, top): `gameplan: find-play, replace-play and set-specials work on your team's game plans by default; --path points them at a file, a folder, a wildcard or one game plan`; `gameplan: every subcommand takes off1, def1, off2 or def2 for one of your team's game plans`; `gameplan: set-normals dropped -q; redirect with > nul instead`; `gameplan: find-play's --path takes a wildcard`; `gameplan: a play list that is not a text file is one FAIL line, not an unexpected error`; `gameplan: check's attribute-cap lines name the plays counted, in slot order`.
- `STATUS.md`: the gameplan section gains the scope rule, the four names and `--team`; the Decisions list gains "No athc command has a quiet flag" and "The team's game plans are the default scope of the gameplan batch commands; check keeps the current folder", and its "Wildcards stay, expanded by athc" entry loses "`find-play` refuses one" (find-play's `--path` now takes one).
- `TODO.md`: the `set-normals -q` item is ticked when this lands; the check-ppp item's keys serve this plan too; the `replace-play` pairs item stays open, with the file-option shape and the both-positionals-optional note of decision 13.
- `tests/integration/README.md`: the rows named in section 10.

## Shared vocabulary

- **The four names: `off1`, `def1`, `off2`, `def2`** (cli-help.md rule 17). Your team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense file of the command's kind (`.pln` here, `.prf` under profile; `.lg2` entries 1 to 8 in that order), resolved from `ppp_path` by `.lg2` name, else the league location (`path` joined with the `.lg2` folder). Matched without case; an existing path wins (cli-help.md rule 15, replace-play's `_is_path`); two names may be one file. Accepted wherever a game plan or profile file operand is, the two check commands' PATH included (rule 17).
- **`GAME_PLAN`** (one-file gameplan commands): "A .pln file, or off1, def1, off2 or def2 for one of your team's game plans." (the shape `check` PATH and profile use); the profile twin is `PROFILE` with ".prf" and "profiles".
- **`--path PATH`** (batch gameplan commands only; a deviation from check-ppp-cli.md decision 16, cli-help.md rule 20): "Game plans to <verb>: a .pln file, a folder, a wildcard, or off1, def1, off2 or def2 (default: your team's game plans)." No `--path` means the default scope; `.` the current folder. Across plans `--path` means "where the game plans are" (rule 20): gameplan's batch commands act on every game plan found there; convert-pdb's takes a folder only and picks the team's four plans by their `.lg2` names, since its workbook has four slots.
- **`--team NAME`** (cli-help.md rule 18): declared once as `team_option` in `src/athc/cli/__init__.py`; the gameplan head is "Team whose game plans off1, def1, off2 and def2 name", the shared tail "(default: team in league.toml)." Check-ppp decisions 4 and 5's rules. With no name among the operands it is `Error: Cannot use --team with a path.`, `check --team X` with no PATH included (rule 18); `--league` is never a contradiction, but a named league must exist (today's no-such-league line, exit 2) and its files are read only when the run needs them, and it always takes a value (rule 19). `ppp_path` applies only to the team `team` resolves to (cli-help.md rule 18).
- **Lines** (cli-help.md rule 21): `FAIL <league.toml>: No team for the league. Set team in this file, or pass --team or <alternative>.` and `FAIL <league.toml>: No path for the league. Set path in this file, or pass <alternative>.`, the alternative being `--path` (batch default scope) or `a .pln file` (a name was given; `a .prf file` under profile); `No <Team> game plans.` (check-ppp: `No <Team> files.`; profile never processes the four as a set, so it has no such line); `FAIL <list>: Not a text file.` for a play list file that is not UTF-8 text; `FAIL off1: Access is denied. Run from another folder to use your team's <game plan|profile>.` on every one-file operand that takes a name (cli-help.md rule 21), while on a folder-taking operand a folder named `off1` is the folder and a file named `off1` is `Not a .pln file.` / `Not a .prf file.`; `Got unexpected extra argument (x).` with athc's period added once in `src/athc/cli/__init__.py` (cli-help.md rule 23).
- **Code** (decided here in sections 9 and 10; profile-cli.md and convert-pdb-cli.md use the same): `src/athc/cli/_team.py` with `TEAM_FILE_NAMES`, `load_league_files(league, league_dir)`, `resolve_team(name, lge)`, `team_files(team, kind)` (the four `(name, file)` pairs, a shared file repeated), `locate(file, ppp_path, league_path) -> Located(path, exists, source)`; the key constants `TEAM_KEY` and `PPP_PATH_KEY`, with `LEAGUE_PATH_KEY` re-exported from `src/athc/config.py` (dade898 moved it there); the fixtures `build_league`, `lg2_league`, `pnfl_league` and the `team()` builder in `tests/integration/conftest.py` (section 10: eight integration modules and `tests/unit/pdbtoexcel/test_config.py` already define a fixture named `league`).
- **Deviations.** From check-ppp-cli.md: decision 16, `--path` as an option on the three batch commands (decision 2 here). From cli-help.md: find-play's `--path` takes a wildcard and defaults to your team's game plans (decision 3), replace-play's usage drops the positional PATH for `--path` (decision 2), set-specials' PATH becomes `--path` (decision 2), `check`'s PATH takes the four names (decision 5). From the brief's shared rules (path sources, default team and its two keys, `--league` on league-reading commands, `-r`, the project's codes and lines, cli-help's help style, coach-only rows, the four-file team, Windows words): none.

## Sources

- check-ppp plan (the model; its decisions 3 to 13 and lines reused; decision 16 deviated from): `docs/design/TODO/check-ppp-cli.md`; help style and the shared rules 16 to 28: `docs/design/TODO/cli-help.md`
- clig.dev (output on success, `-q`, standard flags, suggesting commands, defaults): <https://clig.dev/>
- git commit `-q`: <https://git-scm.com/docs/git-commit>; pip `-q`: <https://pip.pypa.io/en/stable/cli/pip/>; uv `-q`: <https://docs.astral.sh/uv/reference/cli/>
- Windows `copy` (no quiet switch): <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/copy>; `xcopy /q`: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/xcopy>; robocopy's logging switches: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy>
- Microsoft, redirecting STDERR and STDOUT (`> nul`, `2>`): <https://learn.microsoft.com/en-us/troubleshoot/developer/visualstudio/cpp/language-compilers/redirecting-error-command-prompt>; the redirection operators and handles: <https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-xp/bb490982(v=technet.10)>
- kubectl logs (`-c`, "If the pod has only one container, the container name is optional."): <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/>; kubectl exec (`-c` with the default-container annotation): <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_exec/>; kubectl apply options and `-o json, yaml, ...`: <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/>
- cargo run (`--bin`, several binaries, `default-run`): <https://doc.rust-lang.org/cargo/commands/cargo-run.html>
- grep (synopsis, `-e`, no FILE with `-r`): <https://man7.org/linux/man-pages/man1/grep.1.html>
- git `-C`: <https://git-scm.com/docs/git>; git `--pathspec-from-file`: <https://git-scm.com/docs/git-add>
- Click 8.4.1 in the venv: `click/exceptions.py` (`MissingParameter`, `BadParameter`, `UsageError`), `click/core.py` (`Argument.make_metavar`, `get_error_hint`, `Got unexpected extra argument`), `click/parser.py` (`_unpack_args`), `click/types.py` (`Choice(case_sensitive)`, `Path(allow_dash)`)
- athc: `src/athc/cli/gameplan/*.py`, `src/athc/cli/_files.py`, `src/athc/cli/__init__.py`, `src/athc/cli/check_ppp.py`, `src/athc/cli/playpool/check.py`, `src/athc/cli/profile/copy.py`, `src/athc/config.py`, `src/athc/errors.py`, `src/athc/console.py`, `src/athc/gameplan/config.py`, `src/athc/gameplan/writer.py`, `src/athc/fbpro98_gameplan/model.py`, `src/athc/fbpro98_lg2/`, `src/athc/fbpro98_lge/`, `docs/gameplan/README.md`, `docs/gameplan/ARCHITECTURE.md`, `docs/fbpro98_lg2/specs/lg2.md`, `docs/fbpro98_lge/README.md`, `docs/design/architecture.md`, `config/release/leagues/PNFL/league.toml`, `config/release/leagues/PNFL/gameplan.toml`, `config/release/docs/COMMANDS.txt`, `config/release/docs/README.txt`, `STATUS.md`, `TODO.md`, `tests/conftest.py`, `tests/integration/test_gameplan_*.py`, `tests/integration/test_cli_root.py`, `tests/integration/conftest.py`, `tests/integration/README.md`
- The real `PNFL.lg2` and `PNFL.lge` in `E:\SIERRA\FbPro98` (the dev `league.toml`'s `path`), and the fixtures `tests/unit/fbpro98_lg2/data/NFLPI97.LG2` and `08_TEAMS.LG2`, read on 2026-10-13
