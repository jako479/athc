# Worklog

History of what changed and why: one entry per session or piece of work, at a
high level — what was worked on and the reasoning, not the resulting state.
Where things stand now: [STATUS.md](STATUS.md).

- 2026-10-07 — **file specs, library READMEs**: the Reader and Writer
  Contract, Validation & Test Vectors and Status lines left every file spec,
  as the `.lg2` spec had done the day before; a spec now holds only the
  layout, the validity rules and real open questions, and the `.lg2` spec got
  back the three it had lost. Each library README gained an API section after
  Usage, the way an API reference sits apart from a quickstart in Sphinx-built
  docs; the decoded-sample checks moved to the research notes; playpool got
  the README it was missing; the overview indexes the five README pages.
- 2026-10-07 — **gameplan, profile**: `gameplan check`, `profile check` and
  `find-play` default to the current directory when no path is given, as
  `grep -r`, `find` and other tools that search every file in a folder do,
  so a BAT file run from a team folder needs no path. `find-play` keeps its
  trailing positional path, so only the one-argument form defaults; with two
  or more arguments the last is always the path.
- 2026-10-07 — **file specs**: every file-format spec under docs\ now names
  fields in prose (Play category, Stock flag) and keeps code font for bytes
  stored in the file, the way the NumPy .npy, safetensors and Zarr specs do;
  ALL_CAPS enumeration labels became the game's own names. The reader and
  writer contract sections are untouched, pending their move to an API doc.
- 2026-10-07 — **play and gameplan specs**: a byte scan of the PNFL pool
  (5,155 plays, 28 plans, 28 profiles) showed bits 7–6 of the two category
  bytes are one per-file pair, identical in both bytes and of unknown
  meaning, and that a plan's category bytes are a verbatim copy of the play
  file's. The `.ply` spec now gives the bit layout, the observed pairs and
  sample plays; the `.pln` spec defers category values to the `.ply` spec
  instead of defining its own, the way PNG defers deflate to RFC 1951.
- 2026-10-07 — **config**: a league's rule files moved up beside its
  `league.ini`. The `rules\` subfolder held only four fixed-name files, so the
  extra level bought nothing for a user editing them in Notepad; `standings\`
  stays a folder because it grows by one file a season. Code, installer,
  shipped files, docs and tests follow the new path.
- 2026-10-06 — **gameplan**: every play category is now supported, so only a
  league's rules decide what a plan may hold. The two clock categories (Run
  Clock, Stop Clock) joined the play-category enum, and the `.pln` model keeps
  one typed custom/stock slot per special category 1-12 instead of an
  interleaved 20-tuple plus separate clock plays, so no consumer does index
  arithmetic. Rules sections name the five categories without a league
  abbreviation by their game name, and a `.pln` with an unrecognized play
  category is rejected as corrupt.
- 2026-10-06 — **convert-pdb**: compared against the last pnfl version and
  brought over what never made the port: the `.pdb` spec
  (`docs/pdbtoexcel/specs/`) and the master VBA workbooks (`excel-template/`,
  verified to extract to the shipped `.bin` files). The config loaders for
  gameplan, profile and convert-pdb lost the override arguments only the
  removed `--play-path`, `--playpool-rules` and `--rules` options ever fed,
  with their tests. A golden workbook test now pins the real `.pdb` converted
  against the curated pool, since pnfl's real-file cell checks were replaced
  by constructed-data tests at the port and nothing checked real numbers end
  to end.
- 2026-10-06 — **convert-pdb**: removed the `skip_totals` parameter and test
  case left behind when `--skip-totals` was dropped.
- 2026-10-06 — **check-ppp**: `require_all_gameplan_categories_in_profile`
  moved from the profile rules' `[gameplan_compatibility]` to a new
  `[profile_compatibility]` section in the gameplan rules, so each side's
  rules hold its own cross-check setting; check-ppp reads the flag from the
  gameplan rules, and the profile rules reject the old key. `profile check`
  and `gameplan check` are untouched.
- 2026-10-06 — **check-ppp**: now always takes a profile with its gameplan,
  and checks a whole folder or tree too. A team-to-file list in config was
  dropped for the league's own `.lg2`, which already names each team's eight
  files; a new `path` league setting names the folder that holds
  it (`<league>.lg2`). Pairs match by file
  name within one folder, since weeks and seasons reuse names. `profile check`
  and `gameplan check` stay for checking many files of one kind; check-ppp
  takes over `profile check --gameplan`.
- 2026-10-06 — **athc**: `dev\` and `release\` moved under `config\` so the two
  config trees sit together. Tests, VS Code settings and docs follow; the
  release scripts were left alone.
- 2026-10-06 — **league files**: reverse engineered the PNFL's other game
  files to learn what sets the `.lg2` team order (the `.lge` tree order) and
  what each file holds. Team and roster chunks use a running XOR key and the
  player file a per-file byte table, so both got specs (`.lge`, `.pyr`), the
  lg2 spec its team order, and a design doc lists every file type with its
  masks and layout variants. Notes live in `docs/design/research/`, a
  read-only decoder in `research/`.
- 2026-10-06 — **check-ppp**: now follows the profile rules'
  `[gameplan_compatibility]` settings instead of ignoring them, so a league
  decides what fails. A profile category the gameplan lacks is the profile's
  error, so both settings stay in the profile rules; they were renamed to read
  as yes/no (`require_all_...`). PNFL and PCFL require every profile category
  in the gameplan and leave unused gameplan categories as info, which
  `profile check` now follows too.
- 2026-10-05 — **athc**: hooked the PCFL up to gameplan, playpool and profile
  by copying the PNFL's rules into its league folder. `set-normals`,
  `set-specials` and `replace-play` wrote every play path as `PNFL\...`; they
  now use the play pool's folder name. Tests no longer name a league: test
  leagues get neutral names, rules come from the tests' own files, shipped-file
  tests run once per league folder, and an empty list of shipped files fails
  the run instead of skipping.
- 2026-10-05 — **check-playpool**: new command that checks the play pool on
  its own, with the same checks and messages pool loading already gives
  convert-pdb and the gameplan tools. The pool now also keeps those warnings
  in a list, so the command can print and count them as findings like the
  other check commands do with their results.
- 2026-10-05 — **check-ppp**: a missing or bad rules file on one side no
  longer lets the other file be checked. Like `gameplan check` and
  `profile check`, any setup error now stops every rule check; errors that
  need no rules (bad files, a side mismatch) are still reported in the same
  run. check-ppp also stopped reusing code from `gameplan check` and
  `profile check`, which it will replace; their split for sharing was undone.
  A side mismatch now stops the checks like a setup error, instead of
  checking each file on its own.
- 2026-10-04 — **check-ppp**: new command that checks one profile and/or one
  gameplan in a single run, ahead of replacing `gameplan check` and
  `profile check`. Files are positional and told apart by extension (the gcc
  pattern), since either one may be left out. Each check's file reading and
  report code was split out, so check-ppp prints exactly what the two commands
  print and reads each file once. The cross-check follows the corrected
  league rule: a profile category the gameplan lacks fails, while a gameplan
  category the profile never uses is only info, both regardless of the
  `[gameplan_compatibility]` flags (`profile check` keeps them and still fails
  on unused categories). Every input, config and file error is reported in one run, and the
  error hints name no options check-ppp lacks. Directories wait until
  pairing files by team (names differ, 1st and 2nd halves) is worked out.
- 2026-10-04 — **scheduler**: phase 1 now solves the way phase 2 does —
  multithreaded across `solver_workers`, stopping on deterministic time
  (`phase1_time_limit`, now 120) — through one shared solver setup in
  `schedulers/utils.py`. Phase 1 ran three times in fresh processes for every
  test league, spread and seed, and both golden leagues ran end to end twice:
  identical every time. The goldens and model checksums did not change. The
  flat-line phase-1 test dropped from about 30 s to about 3 s, so it is no
  longer `slow`.
- 2026-10-04 — **config**: rebased the multi-league layout onto the
  league-agnostic scheduler. The scheduler keeps its new code but reads its
  files from the league folder (`standings\<season>.league.ini`,
  `rules\scheduler.toml`). The PCFL standings, rules and settings moved into
  `leagues\PCFL\`, laid out like the PNFL's. The gameplan fix that keeps the
  league's playpool rules under `--play-path` carried over.
- 2026-09-27 — **config**: a second league (PCFL) needs its own rules,
  standings and play pool, but everything was PNFL-shaped: one `rules\` folder,
  season files at the config root, and `[league.PNFL]` plus per-tool
  `rule_files` keys in `athc.ini`, with `profile check` and `generate-schedule`
  unable to pick a league at all. Surveyed how end-user apps do it (OBS, Kodi,
  Calibre, Firefox, Hugo; pip/gcloud for `config set`) and went with one
  folder per league under `leagues\` with fixed file names, the league in use
  as `[athc] league` written by a new `athc config set` command (ConfigUpdater,
  so comments survive), and `--league` as a single root option. convert-pdb
  keeps its workbook options in `athc.ini` and gets default playpool rules
  next to it, overridable per league. The installer ships the new tree and
  preserves each league's `league.ini` and standings. Compatibility code for
  the old layout was written and then dropped: nothing has been released.
- 2026-10-04 — **scheduler**: the scheduler still named the PNFL everywhere:
  a fixed same-place table, PNFL division constants, `PNFL.scheduler.toml`,
  `<season>.league.ini`, PNFL titles, and two test folders with league-specific
  names. Now `--league` picks the league, its files are `<league>.<season>.ini`
  and `rules\<league>.scheduler.toml`, conferences and divisions come from the
  standings keys, the same-place rule is computed from the divisions, the writers
  take the league name, a solver failure exits 1, and one validator and one test
  suite run every league. The PCFL files moved from `dev/leagues/` to `dev/` and
  `release/`. The PNFL models and schedule are unchanged (checksums and the
  `.txt` golden); only the report's Scheduler line and the HTML titles changed.
- 2026-10-04 — **scheduler**: reviewed phase-2 multithreading against the
  OR-Tools 9.15 source and maintainer guidance. Interleave search is CP-SAT's
  documented deterministic parallel mode: The threads take turns in lockstep
  instead of racing, so the same seed always gives the same schedule; the
  solve ends as soon as it finds a schedule that breaks no rule. The worker
  pin is needed because the strategy mix depends on the count. Caveats:
  results can differ across OS/CPU families (floats), and `randomize_search`
  does nothing without a decision strategy.
- 2026-09-27 — **scheduler**: the scheduler was hard-wired to the PNFL (four
  divisions, 16 weeks). A second league, the PCFL, has two conferences of nine,
  no divisions and 12 weeks with rivalry week last. The league file now takes
  `[ConferenceStandings]` instead of `[DivisionStandings]`, the rules file gains
  `[league] weeks`, three toggles for the NFL-pattern home/away rules, two PCFL
  rules and `[rivalries]`; every divisional rule applies only with divisions. A
  fingerprint test pins the PNFL CP-SAT models so the golden schedule is unchanged.
- 2026-09-23 — **fbpro98_play**: `read_play` logged an error for an unrecognized
  play category and returned the play anyway, so the play pool loaded it as
  neither a run nor a pass. A library raises instead of logging errors, so it now
  raises `InvalidPlayFileError`; the pool skips that file with a warning and keeps
  reading the rest.
- 2026-09-21 — **config**: league sections used mixed-case keys (`PlayPath`,
  `PlayPoolRules`) while every other key in `athc.ini` was lowercase, and a
  parser subclass existed only to keep that case. The keys are `play_path` and
  `playpool_rules` now, matching `[convert-pdb]`, and the subclass is gone.
- 2026-09-21 — **gameplan**: attribute caps were one fixed form per attribute
  (a count for QB draws and rollouts, a fraction for timed and 2-DL), so a
  league could not say what its own rule said. Each attribute now takes one of
  `max_<attr>_count`, `max_<attr>_ratio` or `max_<attr>_percent`, and naming two
  forms for one attribute is a rules-file error. Ratio and percent compare the
  exact play ratio, so nothing rounds. The PNFL 2-DL caps moved to the new
  percent form at their current league values: 50% Pass Short and Medium, 75%
  Pass Long, 100% Pass Dazzle.
- 2026-09-21 — **profile**: the league rule that a gameplan's play categories
  must all appear in the profile was only an informational warning, so a profile
  breaking it still passed. It is a violation now, like every other rule, and
  `CompatWarning` is gone — both directions are `CompatIssue`. The two
  compatibility checks also moved out of the code and into the rules file, under
  `[gameplan_compatibility]`, so a league enables each one itself. Substitution
  rules gained the league's non-QB bounds: every group but QB and K is capped at
  95 out and 96-100 in.
- 2026-09-21 — **docs**: `RULES_PNFL.md` was deleted for both gameplan and
  profile. Each restated every league value in prose tables, so it went stale
  the moment a number changed; the rules TOML and its comments are the reference
  now. Both rules files lost their `schema_version` and their explanatory
  preamble. Exit codes and the error-vs-finding distinction moved from
  ARCHITECTURE into each tool's README, where a coach will actually look.
- 2026-09-20 — **profile**: substitution thresholds only matched an exact
  percentage, so a league rule stated as a range could not be written down.
  Each side now takes `min_`/`max_` bounds as well as an exact value, a side
  with no key is unchecked, and each unmet side is reported on its own line.
  The rule that an exact out percentage cannot exceed the exact in percentage
  stayed — the game engine requires it, so it is not a league choice.
- 2026-09-18 — the shipped `release/athc.ini` is checked by one test per
  section loader in `test_config.py`, with `ATHC_CONFIG_DIR` pointed at
  `release/` so the bundled rule files must exist. The old autocontinue-only
  check is gone; it proved only that its own section parsed.
- 2026-09-18 — **AGENTS.md** gained two rules: new STATUS, WORKLOG, CHANGELOG
  and TODO entries go at the top of their section, and a finished branch is
  handed off as separate code blocks — the squash-merge first, the worktree and
  branch removal second — so a failed merge is never followed by the cleanup.
- 2026-09-18 — **config**: `dev/athc.ini` pointed at the integration test play
  pool, which nothing required; the tests build their own config. It points at
  the real play pool and game log database now.
- 2026-09-18 — **specs**: the `.ply` and `.pln` format docs each gained a
  whole-file map, and the `.ply` categories were split into sections. The
  `.pln` slot layout became its own section: 86 offsets in both offensive and
  defensive plans, with 0–63 always the normal slots `1-1` through `16-4` and
  64–85 always the special slots. Defensive plans have no clock plays, so their
  last two offsets are always zero. "Special teams" became "special"
  throughout, since the categories include run clock and stop clock.
- 2026-09-17 — **docs**: added CHANGELOG, grouped by component and alphabetized
  rather than ordered by date, with umbrella topics like `config:` and `cli:`
  under athc. Added the logging design — one `basicConfig` in the `cli()` group
  callback with a global `-v/--verbose`, replacing the 13 per-command calls —
  and a per-tool audit checklist for reviewing each tool once it is wired.
- 2026-09-17 — project tooling reworked to match how a modern Python project is
  normally set up. No tool behaves differently; 1153 tests pass at 93.5%
  coverage, ruff and pyright are clean.
  - **Setup is `uv sync`, commands run through `uv run`.** Dev tools moved out
    of `[project.optional-dependencies]` into a `dev` dependency group, which
    is the current standard — extras ship to anyone who installs athc, groups
    stay local. `uv.lock` is committed now, so every machine installs the exact
    same versions.
  - **Coverage runs with every test run and fails below 92%.** It was measured
    nowhere before. The floor sits two points under the real number so a genuine
    drop fails and normal churn does not. There is no CI, so the check has to
    live in the test command.
  - **Ruff gained the pathlib, simplify, comprehension and pycodestyle-warning
    rule groups.** It flagged eight things. Two were real and fixed — a file
    opened without pathlib in `pdbtoexcel` and in a test helper. Three were a
    false "Yoda condition" reading of `assert CONSTANT == frozenset(...)`, now
    ignored in tests. Two are the glob calls behind `--glob` arguments, kept
    with a comment: the user types a whole pattern like `plays\**\*.ply`, and
    only `glob.glob` accepts one — `Path.glob` matches within a folder you
    already have.
  - **Pytest turns warnings into errors**, so a deprecation notice cannot sit
    in the output unread.
  - **Agent instructions live in [AGENTS.md](AGENTS.md)** at the repo root, the
    format ~60k projects use, with `.claude/CLAUDE.md` reduced to a pointer at
    it. The old file named a skill that does not exist and carried another
    project's test commands.
  - **`.vscode/` is no longer tracked.** Of 15 major Python projects checked,
    14 ignore it outright: the project pins the tool in pyproject.toml, and
    each developer wires up their own editor.
  - **Binary game files are marked binary in `.gitattributes`.** `.ply`, `.pln`,
    `.prf`, `.pdb` and `.bin` were left to git's guesswork, which risks line-ending
    damage to a file it misreads as text.
  - **The `.pdb` test data is in the repo.** The stock Python `.gitignore` line
    for MSVC debug symbols was silently excluding both convert-pdb fixtures, so
    a fresh clone had no test data.
