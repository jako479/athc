# League category labels in league.toml

## Goal

A league's short names for the game's play categories come from the league's
settings file, not from code. The settings file becomes `league.toml`.

## Decisions so far

- Only `league.ini` becomes TOML. `athc.ini` and `standings\<season>.league.ini`
  stay INI.
- Labels exist for offense and defense only. Special-teams categories always go
  by their game name.
- Gameplan rule files keep today's section names: the league label where the
  league defines one, else the game name in quotes.
- A folder name in the play pool is matched within the play's own side, so a
  label only has to be unique within its side.

## Section 1: league.toml

```toml
[league]
path = 'C:\SIERRA\FBPRO98'
play_path = 'C:\SIERRA\FBPRO98\PNFL'
# gameplan_rules = ['gameplan.toml']
# profile_rules = ['profile.toml']

[categories.offense]
"Run Right" = "RR"
"Pass Short Right" = "PSR"
"Run Left" = "RL"
"Pass Short Left" = "PSL"
"Run Middle" = "RM"
"Pass Short Middle" = "PSM"
# "Razzle Dazzle Run" = ""
"Razzle Dazzle Pass" = "PRD"
"Pass Medium Right" = "PMR"
"Pass Medium Left" = "PML"
"Pass Medium Middle" = "PMM"
"Pass Long Right" = "PLR"
# "Pass Long Left" = ""
# "Pass Long Middle" = ""
"Goal Line Run" = "GLR"
"Goal Line Pass" = "GLP"
# "User Specific" = ""

[categories.defense]
"Run Right" = "RunRight"
"Pass Short" = "PassShort"
"Run Left" = "RunLeft"
"Run Middle" = "RunMiddle"
"Run Dazzle" = "RunDazzle"
"Pass Dazzle" = "PassDazzle"
"Pass Medium" = "PassMedium"
"Pass Long" = "PassLong"
"Goal Line Run" = "GLrun"
"Goal Line Pass" = "GLpass"
# "User Specific" = ""
```

- Shipped files list every game category of each side in the game's order;
  categories without a league label are commented out.
- `[league]` lists `path` first, then `play_path`. Release files carry the
  explanatory comments and no `db_path`; dev files carry `path`, `play_path`
  and `db_path` with no comments. Existing values are kept as they are.
- Paths use single quotes so backslashes need no escaping.
- `[league]` values are strings. `gameplan_rules` and `profile_rules` are
  arrays of file names (today's multi-line lists).
- Loading fails with the existing config-file error, naming the file, when:
  the TOML is malformed; a `[league]` value has the wrong type; a key under
  `categories.offense` or `categories.defense` is not a game category name of
  that side; a label is empty, repeats within its side, or equals a game
  category name of its side.
- Missing file: no values, every category goes by its game name.
- Unknown keys outside the two category tables are ignored, as today.
- No `%(key)s` interpolation.

## Section 2: code

- `athc.config`: the league file is `league.toml`, read with the standard
  library's TOML parser. `LeagueConfig` keeps `values` (the string values of
  `[league]`), gains the two rule-file lists, and gains `categories`, the
  league's labels. `load_league()` still returns the `[league]` string values,
  so athc-admin is unaffected.
- `fbpro98_play`: the category enums lose `short`; `category_by_short` is
  removed. `long` keeps its name.
- `fbpro98_play` gains a `CategoryLabels` value built from the two tables:
  the label for a category (its league label, else its game name), and the
  offense or defense category a league label names. Validation lives here;
  `athc.config` turns its errors into the config-file error.
- `gameplan.rules`: `load_rules` takes the labels and builds the section-name
  map from them instead of from the enum.
- `gameplan.config`: the gameplan `Config` carries the labels and hands them
  to the rules loader.
- `playpool`: the play-pool reader and `folder_warnings` take the labels and
  resolve a folder name within the play's side. Every caller passes the
  league's labels.
- `gameplan replace-play`: output lines show the label for the category.

## Section 3: files, tests, docs

- Shipped config: `league.toml` for PNFL and PCFL in `config/dev` and
  `config/release`, with the labels above (both leagues' rule files already use
  them); the `league.ini` files are deleted. `install.bat` copies
  `league.toml`. Comments in `athc.ini` and the rule files that name
  `league.ini` are updated.
- Tests: the league fixture writes `league.toml`; every test that writes a
  league file is updated. New tests: label validation (each rule, accepted and
  rejected), league.toml loading (malformed, wrong type, unknown category key,
  empty, duplicate, game-name label, missing file), rule sections resolved
  through labels, folder names resolved per side, replace-play output labels,
  and the shipped files loading.
- Docs: `docs/design/config.md` (format section), `installer.md`,
  `overview.md`, the tool READMEs and ARCHITECTURE docs, the release docs,
  CHANGELOG, STATUS, README, TODO.

## Out of scope

- `athc.ini` and the standings files stay INI.
- A TOML writer; nothing writes `league.toml`.
