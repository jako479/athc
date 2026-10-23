# Worklog

History of what changed and why: one entry per session or piece of work, at a
high level — what was worked on and the reasoning, not the resulting state.
Where things stand now: [STATUS.md](STATUS.md).

- 2026-10-22 — **fbpro98_profile situations**: a situation stored its number
  and five game-state buckets, all fixed by its place in the profile, and its
  constructor cross-checked them. It now holds only its rules, as a game
  plan's slots do; the profile decodes the place into the game state and walks
  the situations with both, and profile check, diff and copy read them from
  that walk. Files, checks and command output are unchanged.
- 2026-10-22 — **fbpro98_play follow-ups**: the review's open points, settled.
  A record offset below 25 (inside the header or category bytes) parsed as
  garbage, so the reader rejects it and ply.md lists the rule. The game's
  source (`PLAY.CPP`) names the Dazzle categories "Razzle Dazzle Run/Pass" on
  both sides, so the defensive enum, the profile category table and the docs
  drop "Run Dazzle / Pass Dazzle"; the league labels are untouched. The
  fixture-naming convention now says a real game file keeps its real name.
- 2026-10-22 — **fbpro98_play tests**: the first of the per-subpackage test
  reviews. It found the rollout margin only ever tested at 100, one real
  fixture pinned by nothing, `parse_play` keeping an unknown category
  untested, no case for a lineman without a snap spot or an unrecognized
  defense, and size limits probed far from the edge; all filled. The
  unknown-category and bad-header messages are now pinned in full, the front
  tests are one parametrized test per rule, category resolution is tested at
  `resolve_category`, and the tests that restated the enums, repeated what
  the parser already enforces or pinned incidental behavior (offset 0) went.
  The zero-byte `PS7Xmids.ply` is named as such. The matrix was rewritten.
- 2026-10-22 — **fbpro98_gameplan tests**: a review of the library's tests
  found the reader's truncated-record and S98-overrun errors untested, size
  limits tested far past the boundary, a stock play never written into a
  normal slot, tests that skipped when a committed fixture did not fit, and
  goldens that only sorted another golden. The tests now cut and shift the
  fixture bytes at each limit, write a stock play and a custom special play
  through the writer, pad both sides, and fail instead of skipping; the
  name-sorted goldens went and the special-play names moved inline.
  `docs/formats/pln.md` said only defense files carry the parity pad, yet
  the game-saved offense plans carry it too; it now says either file, when
  the size needs it.
- 2026-10-22 — **fbpro98_lge, fbpro98_lg2 tests**: a review of the two
  league-file test suites found the fixtures and goldens sound (every file
  real and used, every tie recomputed from the games) but a few gaps: the
  strength-of-schedule test could not tell each-opponent-once from
  every-game counting, a tree with more divisions or teams than its counts
  say was untested, as were an empty week, the playoff rounds' week
  numbering, the `<buffer>` path, the `.lg2` error offsets and its
  size-before-fields order. Each got a test; the `.lg2` team order is now
  checked against the `.lge`; a dataclass-access test, a redundant `ranked`
  test and a duplicate team walk went.
- 2026-10-22 — **fbpro98_profile tests**: a review of the profile library's
  tests found the situation layout pinned only at situations 1 and 2520 (a
  consistent swap of two buckets would have passed), the PAT weight rule and
  three I95 checks untested, the field goal range tested past one limit only,
  and a third of the writer cases and a quarter of the reader cases restating
  what the byte-identical round trip or the model already proved. The gaps got
  tests from the spec's layout and offsets; the redundant cases went; the
  pinned values became one table per fixture; missing fixtures now fail
  instead of skipping; two stock profiles no test opened went. A situation's
  range message had the wrong closing bracket.
- 2026-10-21 — **gameplan**: set-normals checked a list for special plays
  first and stopped there, so a missing or wrong-side play on another line
  showed only after the special one was fixed. It now reports every bad line
  in one run, the special ones still pointing to set-specials. A check in the
  play-list reader that could never be false went.
- 2026-10-20 — **stats files**: compared the 2047 season's weekly `.dat` and
  `.idx` pairs to see how the game maintains them (updated in place,
  last-game records deleted and re-added, deleted slots reused, playoffs
  touching only last-game records) and matched the header to FairCom's
  c-tree Plus V6 file header. The weekly behavior went into
  `docs/fbpro98-game-behavior.md`; the header mapping, the delete-stack and
  reuse rules, the index's free-node stack and the node capacities went into
  `docs/formats/stats.md` and its pattern.
- 2026-10-20 — **athc tests**: an audit of the file libraries' tests found
  that every `test_schema.py` only restated its module's constants and that
  the frozen-dataclass tests only checked Python. Those went, with the `.lg2`
  model tests, whose model has no logic; `docs/testing-unit.md` now says so.
  The audit's other findings are not acted on yet.
- 2026-10-20 — **fbpro98_stats**: the standings' net-touchdowns tie-breaker
  needs touchdowns the `.lge` does not have, and stat corrections will need a
  writer, so the `.dat` got a read-only library in the shape of the other
  readers. Tests run on four of the 2047 PNFL season's files; season points
  rebuilt from the stats match the `.lge` at week 1 (from week 3 the `.dat`
  gives Pittsburgh a touchdown the `.lge` score lacks). The real files also
  showed that game details keep the team's own opponent and score in its
  opponents' blocks too, and the latest regular-season game in season
  blocks; and that a Hall of Fame points record can hold a zero count,
  conference and points. The stats
  spec and the stat-corrections proposal were updated to match.
- 2026-10-18 — **gameplan**: a review of the tests found rule limits tested
  on one side only, validator messages checked only through the two golden
  reports, the duplicate-play rule with no test of its own, untested rules-file
  keys (`custom_special_play_required`, the shapes of
  `required_special_categories`, a bad fraction), and tests that only checked
  the exit code. Each limit is now tested at the limit and one past it on both
  sides, every violation message is pinned, the clean `check` runs on real
  rules instead of a mock, and duplicate usage-error tests went. New command
  tests cover a wrong `--league`, a bug in one file of a batch and a play list
  that does not fit; the test matrices follow.
- 2026-10-17 — **athc**: the setup.exe now reads the installed version and
  refuses to install over a newer one; the same version or an older one is
  replaced as before. The sandbox test fakes a newer install to prove it.
- 2026-10-17 — **convert-pdb**: the Options sheet's Highlight Selected Row
  option went; an `.xlsm` now always outlines the selected row, and the
  category lists moved to the left of the sheet. The golden workbook test ran
  three seasons of stats against the small test pool, so it warned about
  every missing play and checked only the ones the pool had; it now uses a
  real week's PDB with its own pool holding every play in it, so it runs with
  no warnings. A first try copied those plays into the shared test pool and
  broke the release sandbox check that pins that pool at 128 plays, so they
  moved to a folder of their own. AGENTS.md's project meta list now names
  WORKLOG.md.
- 2026-10-17 — **athc**: PNFL and PCFL are clones, so each league carried the
  same convert-pdb settings twice in its own `pdbtoexcel.toml`, while the rest
  of convert-pdb's settings sat in `athc.ini`. Settings now have one home and
  one format: `athc.toml` replaces `athc.ini` (TOML like every other settings
  file, tomlkit for `config set`), and a league overrides a tool's table key by
  key in its `league.toml`, through one shared merge that remembers which file
  set each key so every message names it. convert-pdb is the first tool on it;
  `pdbtoexcel.toml` went. The branch review found `config set league` could
  pull a key written above the first table into a new `[athc]`, and a
  non-UTF-8 `league.toml` crashed; both fixed with tests.

- 2026-10-14 — **scheduler**: phase 1's difficulty line aimed each team's
  average opponent conference rank, so a 4-team-division team had all five
  non-conference games tilted where a 5-team-division team had four. The
  target is now a sum, tilted over the league's smallest count with each
  extra game a neutral rank 5. The hard-coded top-half/bottom-half opponent
  rule went. The PCFL gets `random_nonconference`: seeded random pair weights
  in the same solve, so a seed repeats its games on any machine. The rules
  file now reads `[solver]` then `[phase1]` beside `[phase2]`, with the time
  limits named by phase and `--phase2-time-limit` to match.
  Unknown tables and `[solver]` keys are now errors, as in most mainstream
  tools, so a misspelled name no longer falls back to a default silently;
  like those tools, the error names only the unknown key, not every valid one.
- 2026-10-14 — **athc**: review of every console and run-log line. The
  2026-10-09 concerns were checked against the code and mainstream tools; the
  pool lines stay as the nag to fix the pool, find-play's misses go, plus
  wording and line-form drift from the 1.0.0 CLI work and a doubled level word
  in the run log. Fixed per the plan.
- 2026-10-14 — **docs**: `docs/` had 120 files in 36 folders: a folder per
  module with same-named READMEs and ARCHITECTUREs that overlapped, specs two
  levels down, and 27 superpowers specs and plans for merged work. Now one
  folder per kind of doc, flat inside: one doc per module at the top (README
  and ARCHITECTURE merged), `formats/` for every file spec with its patterns,
  `research/`, and `proposals/` for pending designs and plans. The
  superpowers files and the 1.0.0 CLI designs and plans went, and AGENTS.md
  holds the rule that a finished design and plan fold into the docs and go,
  so proposals is for pending work.
- 2026-10-14 — **docs**: the tie-breaking docs were scattered: the methods'
  steps lived only in a spec, three specs and three plans for merged work
  sat under `docs/superpowers/`, the tie-breakers research note was untracked,
  and the lge-standings spec described a point-differential order the code
  had dropped. The standings library's ARCHITECTURE is now the design doc
  (engine, steps, each method); the research note (the manual, the NFL,
  pnfl.biz and the scheduler side by side) is tracked under
  `docs/design/research/`; the six specs and plans went.
- 2026-10-13 — **standings**: a new `athc standings` command, the first user
  of the standings library. It shows the league's standings as played so far,
  as the game's standings screen or ESPN's League, Conference and Division
  tabs, so a commissioner can check them without opening the game. A fixed
  coin toss keeps the order the same on every run of the same file. The
  review caught PCT rounding a half down (13-3 read `.812`); it now rounds up
  as ESPN prints it.
- 2026-10-13 — **fbpro98_standings**: tie-breaking moved toward its own library,
  since it is a game rule and not part of the file format. One engine ranks
  for three methods (the game's, generate-schedule's, the NFL's), from one
  season or from last season's results for this season's divisions, with
  team moves for renamed teams and a seeded coin toss. Nothing uses it yet.
- 2026-10-13 — **playpool**: play attributes from the play's own bytes. The
  filename filters in `playpool.toml` guessed at what a play does and needed
  a per-league exception list, so `fbpro98_play` now reads each player's
  logic boxes and tells a timed pass, QB run, rollout and defensive front
  from them; only `Screens` still comes from a folder. The review follow-ups
  renamed `qb_draw` to `qb_run` (a QB sneak is a QB run, not a draw) and made
  every offense attribute read from the snap on.
- 2026-10-13 — **scheduler**: how a division whose members changed gets its
  finish order. The lge library's method that ranked an arbitrary team list
  was rejected as a kluge. The previous season stays as it stood, ranked by a
  plain library function the loader calls once per division; a loader sort
  was the simpler alternative but would have been a second standings rule.
  The moved-team cases are documented with the 2047 AFC East; the dead
  point-differential research files went.
- 2026-10-12 — **scheduler**: the standings come from the game's own league
  files instead of a hand-written INI per season. The lge library grew the
  played games, playoff results and the unplayed count; a new loader matches
  the previous season's teams to the upcoming season's by name (with a
  `[renames.<season>]` table, since a realignment moves team numbers around)
  and ranks them. Point differential, the library's own tiebreak, got two tie
  groups of the real 2048 order wrong; the league's strength-of-schedule rule
  reproduces it exactly, so the scheduler uses that for the overall order.
  Conferences and divisions now go by file position: the PNFL's conference
  names are empty. The divisional golden moved to the real 2047 -> 2048 files;
  the conference league gets a built pair so its goldens stayed.
- 2026-10-09 — **athc**: review of the error-wording branch. Choices made
  while building it were checked against mainstream tools: a file in use
  keeps Windows' own words, a game-file reader writes its own sentences
  instead of having them rewritten, a key never starts a sentence (style
  guides say to reword), and the screen-grab warning says the likely cause,
  as yt-dlp and urllib3 say what they were trying. A missing button image is
  a broken install, so it stops the run instead of retrying forever. The
  deferred items followed: config files that cannot be opened fail, play
  lists with a BOM read, unknown keys list the valid ones, and the scheduler
  names its table and key first.
- 2026-10-09 — **athc**: error wording, from the console review's open items.
  Research into Windows' own tools and end-user Python tools set the style:
  Windows' phrases for file problems, whatever call hit them, and every
  `FAIL` / `WARN` line a sentence that names its file once. A file error
  reads the same whether athc finds it first or Windows reports it, a rules
  file with several problems is several labeled lines, play-list errors point
  at the real line, and Python's lists and bytes no longer show through.
- 2026-10-09 — **gameplan**: `replace-play` takes a list of replacements and
  uses, per gameplan, the first one not already in it with which the
  gameplan passes `check`, so a swap never leaves a gameplan failing, say
  with a duplicate or one rollout too many. It loads the rules and the full
  play pool the way `check` does, since the attribute caps need the
  playpool rules. The path became optional, the last name counting as the
  path when it looks like one.
- 2026-10-09 — **fbpro98_lg2**: stock leagues are read, not rejected. All
  three layouts are fully specified and differ only in the folder field, so
  one parser serves them; the old stock check became `league_type`, so a
  caller can still tell them apart. `check-ppp` still fails on a stock
  league, now by checking `league_type` itself.
- 2026-10-08 — **athc**: the eight console follow-ups decided after the
  review landed, in order: an error carries its file's path as data and
  composes `<path>: <reason>` itself, the way `OSError` does, so the readers
  and loaders pass the path and no line names a file twice; a missing named
  file is `FAIL <path>: not found` through one shared helper, never
  Python's errno text; an unwritable log folder is one `FAIL` line, not a
  traceback; bare `athc` logs one line instead of its help; `playpool
  check` says `not found` for a missing folder; a play list from the
  console carries no `- ` prefix and `find-play` prints no tally for a
  failed single path; the check commands catch per item in the loop; and
  every single-line CLI stream is pinned whole, the shared lines coming from
  conftest helpers.
- 2026-10-08 — **athc**: the console, run log, errors and exit codes landed
  the pdf-converter way. One Rich console prints every line and writes the
  matching log line, one rotating run log holds every run, one error family
  replaces the per-tool copies, and `main` on the Click command classes is the
  one place errors become a line and a code, so `CliRunner` tests see exactly
  what the process does. Libraries stopped logging: warnings come back as
  values and progress through a callback. The two TODO designs retired into
  architecture.md and the per-tool READMEs.
- 2026-10-08 — **athc**: the logging rework got a design in place of a
  decision table. Research into what mainstream tools do (git, ruff, grep,
  pip, Black, clig.dev, Rich) confirmed pdf-converter's console, run log and
  error pattern as the mainstream one and settled the exit codes: one scheme
  in every command, 0 / 1 findings / 2 error, the worst outcome winning across
  a batch. That ends today's split, where the same league error exits 1 in
  some commands and 2 in others. Two TODO designs hold it, the framework and
  the per-command detail; LOGGING-IS-FUCKED.md and command-messages.md were
  folded into them.
- 2026-10-08 — **athc**: the output-files rule became code. `convert-pdb`,
  `list-normals`, `list-specials` and `profile diff -o` had each stopped with
  an error on a missing output folder; each now creates the whole folder chain
  before it writes, where the write happens, so the rule holds for every
  caller. The in-place editors are unchanged: a missing target is still an
  error and nothing is created. The TODO design note went with it.
- 2026-10-08 — **athc**: the CLI, config and logging design docs were half
  rules and half mechanics that duplicated the code, so the rules moved into
  `docs/design/architecture.md` (the renamed overview) as one Cross-cutting
  conventions section and the three files went. A new output-files rule came
  with it: another session had convert-pdb stop on a missing output folder,
  one level had been created before, and nothing wrote the rule down; the
  modern end-user tools checked (pandoc, 7-Zip, yt-dlp) create the whole
  chain, so that is the rule, with the code change still to do.
- 2026-10-08 — **convert-pdb**: the June port had dropped PdbToExcel's
  category order (the ini lists of RL / PSL / RunLeft codes that set the row
  order and the Options sheet) and its `DELETED_PLAYS` list, sorting by the
  game's own category list under the game's long names instead; neither drop
  was the user's decision. Both come back as league data in a new
  `pdbtoexcel.toml` beside the other league files, over the category names
  `league.toml` already holds; a category left out of the order stays out of
  the workbook. The playpool rules' include / exclude names are now checked
  against the pool the way PdbToExcel checked its overrides file (not in the
  pool, wrong side), plus a name under both lists. The release settings count
  sacks as pass attempts; the Total Stats filter stays out.
- 2026-10-08 — **gameplan**: the rules' disallowed-category lists became
  allowed-category lists (`allowed_offensive_categories` /
  `allowed_defensive_categories`), so a league says what a gameplan may
  contain by its own labels, the way the `[offense.X]` sections already
  do. The shipped PNFL and PCFL rules list the categories their old
  lists left out, so what they enforce is unchanged.
- 2026-10-08 — **gameplan**: `list-normals` gained `--sort category`, which
  groups the plays under `::` headers in the league's reading order so a coach
  can read a plan the way the game's grid presents it. The headers carry the
  league's category labels, so the command now resolves the league like every
  other league-reading command; a first cut had given Pass Long Left/Middle
  and Razzle Dazzle Run short labels in the category enum, dropped once the
  labels moved to `league.toml`. `find-play`, `replace-play` and `list-normals`
  now share one helper for a gameplan play's category. A review of the
  gameplan package then fixed the rules loader crashing on a non-table
  `offense` / `defense` value and folded its own `ConfigFileError` into the
  config package's; `check` now names a special category in its messages the
  way it names normal ones, the validator groups a plan's plays once, and the
  three integration test files that built gameplans by hand share one set of
  helpers in the integration conftest.
- 2026-10-08 — **playpool**: `check-playpool` became `playpool check`, so the
  play pool is a command group like `gameplan` and `profile`, the
  resource-then-verb shape of `git remote add` and `docker container ls`;
  `check-ppp` stays flat because it spans all three file types.
- 2026-10-07 — **config, fbpro98_play, gameplan, playpool**: the league's
  category labels were baked into the category enum, so every league got
  PNFL's names. They now come from the league's settings file, which became
  `league.toml` (TOML nests the two category tables and quotes keys with
  spaces); rule sections, play-pool folders and `replace-play` output resolve
  through `CategoryLabels`. `playpool check` on a given folder still reads a
  configured league for its category names. `athc.ini` and the standings
  files stay INI.
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
