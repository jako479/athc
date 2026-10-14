# Docs layout plan

**Goal:** fewer folders under `docs/`: one folder per kind of doc, flat inside, the file name says the subject; and one rule for what happens to a design and its plan when the work is done.

**Status:** proposal, 2026-10-13, counts updated 2026-10-14; nothing moved yet. Every choice is decided below; the reasons sit next to each one.

## 1. Today

- 120 files in 36 folders; outside `superpowers/`, 93 files in 33 folders.
- One folder per module mirrors `src/athc/`, so most folders hold two or three files, and `fbpro98_cities`, `fbpro98_pyr` and `fbpro98_stats` exist for modules that do not (a spec only).
- 13 files are named `README.md` and 12 `ARCHITECTURE.md`; a search hit or an editor tab cannot tell them apart.
- A module's README and ARCHITECTURE overlap: gameplan's share the intro and the whole Config section.
- Links between specs climb two levels (`../../fbpro98_lge/specs/lge.md`).
- `2048 Schedule.txt` is an example, not a spec, and has a space in its name (`generate-schedule` writes `schedule_<season>_<timestamp>.txt`).
- `superpowers/` holds 12 specs and 15 plans, every one for a feature already merged, and nothing marks them done.

## 2. What other projects do

- Decision records, RFCs and proposals: one flat folder, the file name carries the subject. MADR `docs/decisions/NNNN-title-with-dashes.md` (subfolders "for large projects" only); Rust `text/NNNN-feature.md`; Go `design/NNNN-shortname.md`, flat but for a few numbered subfolders; Swift keeps a `proposals/` folder.
- athc's peer Click projects keep their docs flat: Click's `docs/` is dozens of pages in one folder; sqlite-utils and llm have one page per topic, llm with two topic subfolders. git's `Documentation/` has the command pages flat at the top with `technical/` and `howto/` beside them.
- One page per module: Python's library reference.
- Binary-format definitions: the two format catalogs, corkami and Kaitai, both name the folder `formats`; ImHex's `patterns/` is flat (`png.hexpat`, `zip.hexpat`) with subfolders only for families of formats. athc has ten formats.
- Diátaxis: a few sections, each flat; add a layer inside a section only when it gets crowded. Structuring docs around product features "is rarely successful".
- One ARCHITECTURE doc per project, "a map of a country, not an atlas of maps of its states"; module detail goes in its own doc or in the code (matklad).
- Google's doc guide: a README orients readers to its folder; delete dead docs; "duplication is evil".
- Proposal records: a PEP keeps a status line (Draft, Accepted, Final, Rejected, ...) and, once resolved, "is considered a historical document rather than a living specification".

## 3. Strategy

1. One folder per kind of doc; the docs root holds the design and module docs.
2. Flat inside each folder; the file name is the subject (module name, file extension).
3. A subfolder only when a kind outgrows one listing; none does today.
4. Pending work lives in one folder, `proposals/`; finished work has no doc of its own beyond the design docs and `CHANGELOG.md`.

## 4. Layout

```
docs/
  README.md                        index, one line per doc
  architecture.md                  the cross-cutting docs, as today
  fbpro98-game-behavior.md
  installer.md
  reference-projects.md
  release.md
  testing-integration.md
  testing-unit.md
  autocontinue.md                  one doc per module, from README + ARCHITECTURE
  check_ppp.md
  config.md
  fbpro98_gameplan.md
  fbpro98_lg2.md
  fbpro98_lge.md
  fbpro98_play.md
  fbpro98_profile.md
  gameplan.md
  pdbtoexcel.md
  playpool.md
  profile.md
  scheduler.md
  scheduler-phase-1-matchups.md
  scheduler-phase-2-schedule.md
  formats/                         every file-format spec with its patterns
    README.md                      from fbpro98-files.md: what each game file holds
    cities.md    cities.hexpat
    lg2.md       lg2.hexpat
    lge.md       lge.hexpat
    pdb.md       pdb.hexpat       pdb.hsl
    pln.md       pln.hexpat       pln.hsl
    ply.md       ply.hexpat
    prf.md       prf.hexpat       prf.hsl
    pyr.md       pyr.hexpat
    stats.md     stats.hexpat
    schedule-import.md  schedule-import-example.txt
  research/                        unchanged
  proposals/                       from design/TODO: pending work only
    cli-help.md  logging-updates.md  quirk-budget.md  docs-layout.md
```

33 folders become 4.

Decisions:

- `docs/design/` dissolves: `docs/` holds only docs for repo readers (the end-user docs live in `config/release/docs/`), so the extra level says nothing; the peer projects and git keep that level flat.
- One doc per module: Python's library reference is one page per module; the pairs duplicate their intro and Config; the 25 same-named files go.
- `formats`, not `specs`: the word both format catalogs use, and it says what is inside; `specs` would sit next to the skill's `specs` folder (section 8).
- `stats`: the spec's own title is "Statistics File Format", and `.dat` is generic (`CITIES.DAT`, `injury.dat`, `PNFL.dat`), so the content names it, like `cities`; the library is `fbpro98_stats`, like `fbpro98_play` for `.ply`.
- `schedule-import`: the file is the input of the schedule-import tool, not a game file, and the `.lge` already holds a schedule, so the bare word would be ambiguous.
- `proposals`, not `TODO`: the mainstream word for pending design work (Swift `proposals/`, Go `proposal`, PEPs, RFCs), lowercase like every other folder; `TODO.md` keeps indexing it.
- `formats/README.md` from `fbpro98-files.md`: it is the index of the formats; GitHub shows a README when the folder is opened; Google's "README orients its folder".
- `docs/README.md`: one line per doc; `architecture.md` drops its "Library docs" list and keeps the rule.

Naming rules:

- A module doc takes the module's name (`fbpro98_lge.md`, `check_ppp.md`); a module's extra docs take it as a prefix (`scheduler-phase-1-matchups.md`).
- A format takes its extension where one format owns it (`lge`), the file's content where it does not (`cities`, `stats`), and its purpose where it is not a game file (`schedule-import`); a pattern shares its spec's stem.
- Everything else is kebab-case.

## 5. Moves

| From | To |
|---|---|
| `design/*.md` (8) | `docs/*.md`, except `fbpro98-files.md`, which becomes `formats/README.md` |
| `<module>/README.md` + `<module>/ARCHITECTURE.md` (12 pairs; `check_ppp` has a README only) | `<module>.md`: the README's sections, then the ARCHITECTURE's under one `## How it works`; the duplicated intro and Config go |
| `scheduler/phase-1-matchups.md`, `scheduler/phase-2-schedule.md` | `scheduler-phase-1-matchups.md`, `scheduler-phase-2-schedule.md` |
| `<module>/specs/*.md`, `*.hexpat`, `*.hsl` (23 files) | `formats/`, same names except the three below |
| `fbpro98_stats/specs/stats_dat.md`, `stats_dat.hexpat` | `formats/stats.md`, `formats/stats.hexpat` |
| `scheduler/specs/schedule_format.md` | `formats/schedule-import.md` |
| `scheduler/specs/2048 Schedule.txt` | `formats/schedule-import-example.txt` |
| `design/TODO/*` | `proposals/*` |
| `design/research/*` | `research/*` |
| `superpowers/specs/*`, `superpowers/plans/*` (27 files) | deleted (section 8) |
| new | `docs/README.md` |

Order: formats first (a pure move), then the module docs (a move plus a merge), then research, proposals and the superpowers deletions, then the links and meta below. Every move is a `git mv`; every edit keeps CRLF; one branch, one squash-merge.

## 6. Links and rules to update

- `docs/architecture.md`: the project-layout tree, the "Library docs" rule (reworded for one doc per module, list dropped) and the sentence "Each tool's own behavior is in its `docs/<tool>/` README and ARCHITECTURE".
- `formats/README.md` and `research/pnfl-formats.md`: spec links.
- `README.md`, `STATUS.md` (about 30 links, and the sentence "The design docs are one `docs/design/architecture.md`"), `TODO.md`, `LOGGING_AUDIT.md`, `AGENTS.md` (section 8).
- `tests/integration/README.md`, the nine `tests/unit/<module>/README.md` and the three `tests/unit/scheduler/test-matrix-*.md`: links to the testing docs and the scheduler phase docs.
- Comments in `src/athc/scheduler/config.py`, `schedulers/scheduler.py`, `schedule_builder.py`, `types.py`, `writers/txt_writer.py` and `research/pnfl_decode.py`.
- The moved docs' own links: sibling links become plain file names.
- athc-admin: its three links into `docs/design/` (`installer.md`, `reference-projects.md`, `release.md`) get the new paths; its other four already point at files that no longer exist.
- `CHANGELOG.md` gets one line; `WORKLOG.md` keeps its history as is.

## 7. Superpowers specs and plans: what happens today

Checked against the skill texts (superpowers 6.4.1):

- brainstorming writes the design to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commits it on the current branch; writing-plans writes `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`; the worktree comes later, "at execution time". Both skills say a project preference for the location overrides the default.
- After the plan is executed no skill needs either file, and none deletes them: finishing-a-development-branch cleans up the worktree only, and "delete this plan's workspace" in executing-plans means the git-ignored ledger folder, not the plan.
- Superpowers' own repository keeps every spec and plan in main; the plugin ships its own under `docs/superpowers/`. That is the record model of PEPs and ADRs: keep the document forever, with a status line.
- Here, each of the 27 files in main arrived with the squash-merge of its own feature, so all of them are done:

| Topic (spec and plan) | Merged as |
|---|---|
| multi-league-config | `28ccb5e` athc: config: multi-league |
| pcfl-scheduler | `47f083a` scheduler: second league format (PCFL) |
| league-agnostic-scheduler | `a183fc1` scheduler: league-agnostic code, config layout and one test suite |
| check-ppp-bulk | `fe6a786` check-ppp: profile and a gameplan required |
| fbpro98-lg2 | `b2016c3` fbpro98_lg2: new library |
| gameplan-special-slots | `304fdf3` gameplan: non-league categories supported; clock categories |
| league-toml-categories | `0998dd1` config: league category names move to league.toml |
| console-run-log-exit-codes (plan only) | `7b5bdab` athc: console, run log, errors and exit codes |
| installer-exe (plan only) | `95ab1f3` install: athc ships as a setup.exe |
| error-wording | `2f4b2a8` athc: messaging and error handling |
| fbpro98-lge | `be93529` fbpro98_lge: league names and standings library |
| lg2-stock-leagues | `76d12e5` fbpro98_lg2: read stock leagues |
| replace-play-backups | `c1de47c` gameplan: replace-play takes backup replacements |
| play-attributes-from-data (plan only) | `ddae7a1` playpool: play attributes from the play file; playpool.toml gone |
| scheduler-league-files | `dade898` generate-schedule: standings and structure from the league's .lge files |

- The one plan merged before its work (cli-help-style, 2026-10-11) was moved to `design/TODO/cli-help.md` by hand. The standings specs and plans (fbpro98-lge-standings, fbpro98-standings, standings-command) were folded into the standings docs and deleted on 2026-10-14.

## 8. Superpowers specs and plans: the rule

athc does not use the record model: the design docs describe the code as it is, `TODO.md` ticks finished items and `CHANGELOG.md` records each change, so a design or plan for merged work duplicates them (Google: "delete dead documentation"). The rule, for `AGENTS.md`:

1. A design and its plan are written to `docs/proposals/<topic>-design.md` and `docs/proposals/<topic>-plan.md`, on the feature branch; there is no `docs/superpowers/` folder. (The skills take the project's location; `AGENTS.md` states it.)
2. Enter the worktree before brainstorming writes the design, so nothing lands on main.
3. Before hand-off, the branch's last commit folds what lasts into the design docs, `CHANGELOG.md`, `STATUS.md` and `TODO.md`, then deletes the branch's design and plan, and any proposal in main that the branch completed. A squash-merge never adds a proposal to main.
4. A branch that stops keeps its design and plan on the branch. A dropped branch whose idea stays moves its design to main's `proposals/`, with a `TODO.md` line, as cli-help was.
5. So everything in `docs/proposals/` is pending, and nothing needs a status line.

Cleanup now: delete the 27 files in the table.

`AGENTS.md` changes: in "Working agreement", "a skill's own files (spec, plan) go where that skill says, no question" becomes rule 1 and 2; in "Commits and hand-off", rule 3 and 4 are added.

## Sources

- MADR layout and naming: <https://adr.github.io/madr/>
- Rust RFCs: <https://github.com/rust-lang/rfcs>; Go proposals: <https://github.com/golang/proposal>; Swift proposals: <https://github.com/swiftlang/swift-evolution>
- Click docs: <https://github.com/pallets/click/tree/main/docs>; sqlite-utils: <https://github.com/simonw/sqlite-utils/tree/main/docs>; llm: <https://github.com/simonw/llm/tree/main/docs>; git: <https://github.com/git/git/tree/master/Documentation>
- Python library reference, one page per module: <https://docs.python.org/3/library/index.html>
- corkami formats: <https://github.com/corkami/formats>; Kaitai formats: <https://github.com/kaitai-io/kaitai_struct_formats>; ImHex patterns: <https://github.com/WerWolv/ImHex-Patterns>
- Diátaxis: <https://diataxis.fr/map/>, <https://diataxis.fr/complex-hierarchies/>
- One ARCHITECTURE doc: <https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html>
- Google documentation best practices: <https://google.github.io/styleguide/docguide/best_practices.html>
- PEP statuses and records: <https://peps.python.org/pep-0001/>
- Superpowers skill texts: `~/.claude/plugins/cache/claude-plugins-official/superpowers/6.4.1/skills/` (brainstorming, writing-plans, executing-plans, finishing-a-development-branch); repository: <https://github.com/obra/superpowers>
