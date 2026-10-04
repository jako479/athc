# Multi-league config — design

One folder per league under the config dir. Every league-aware tool reads its
rules, standings and settings from the selected league's folder. The selected
league is a key in `athc.ini`, edited by hand or with
`athc config set league NAME`, so `--league` is not needed on every run.
`athc.ini` keeps only app-wide settings.

## Layout

Identical in `dev\`, `release\` and the installed config dir
(`%LOCALAPPDATA%\athc`):

```
athc.ini                      app-wide settings + selected league
leagues\
  PNFL\
    league.ini                per-league settings
    rules\
      gameplan.toml
      profile.toml
      playpool.toml
      scheduler.toml
    standings\
      2045.league.ini … 2049.league.ini
  PCFL\
    (same fixed names)
```

Fixed, well-known file names inside a league folder; nothing lists them in
config. A league is any folder under `leagues\`; its name is the folder name.

### `athc.ini`

```ini
[athc]
; the league the tools use when --league / ATHC_LEAGUE is not given
league = PNFL

[autocontinue]
mouse_move_duration = 0.0
delay_before_continue = 1.0
hot_corner = true
```

`league` replaces `default_league`. The shipped `athc.ini` presets it to
`PNFL`, as today.

Removed: `default_league`, `[gameplan]`, `[profile]`, `[convert-pdb]`,
`[league.*]`. If any are still present, log one warning naming them and
pointing at the new layout, then ignore them.

### `leagues\<NAME>\league.ini`

One `[league]` section holding per-league values that are not files. athc
reads `play_path` and the optional rule-file lists; athc-admin reads
`db_path`, `log_dir`, `play_path`. Any key is allowed and passed through.
Relative paths resolve against the league folder.

```ini
[league]
play_path = E:\SIERRA\FbPro98\PNFL
db_path = E:\PNFL\Game Log Database\49W4\pnfl_athc.db
```

Rule-file layering is kept. By default a tool reads its one fixed file under
`rules\`. Optional multi-line keys replace that default with an ordered list,
later files overriding earlier ones, exactly as `rule_files` works today:

```ini
[league]
play_path = E:\SIERRA\FbPro98\PNFL
gameplan_rules =
    rules\gameplan.toml
    rules\house-rules.toml
profile_rules =
    rules\profile.toml
```

## League selection

Highest wins:

1. `--league NAME` (per run, never persisted).
2. `ATHC_LEAGUE` env var.
3. `[athc] league` in `athc.ini`.
4. Error: `no league selected; run 'athc config set league NAME' or pass
   --league. Available: PNFL, PCFL` (names are the folders under `leagues\`).

A name with no `leagues\<NAME>\` folder is an error listing the available
folders.

## Commands

New: `athc config set KEY VALUE` in the existing `athc config` group. Writes
`[athc] KEY = VALUE` in `athc.ini`, creating the file, section or key if
missing, and keeps every comment and the file's layout (ConfigUpdater).
Prints `Set league = PNFL`. Only known keys are accepted; today that is
`league`, whose value must be a folder under `leagues\` (error listing the
available folders otherwise).

`--league` (existing shared decorator, unchanged) on every league-aware
command:

- `gameplan check`, `replace-play`, `set-normals`, `set-specials` (already).
- `profile check` (new).
- `convert-pdb` (new).
- `generate-schedule` (new).

All other commands are unchanged.

## Per-tool behaviour

Existing CLI overrides (`--rules`, `--play-path`, `--playpool-rules`) keep
winning over the league folder and stay CWD-relative. A league is resolved
only when a value is still needed after the overrides, as gameplan does
today, so `convert-pdb --play-path X --playpool-rules Y` needs no league.

- **gameplan**: `play_path` from `league.ini`; rules from `gameplan_rules`
  or `rules\gameplan.toml`; playpool rules from `rules\playpool.toml`. A
  missing rules file means no rules (in-code defaults), as today for an
  empty `rule_files`.
- **profile**: rules from `profile_rules` or `rules\profile.toml`; same
  missing-file rule.
- **convert-pdb**: `play_path` from `league.ini` unless `--play-path`;
  playpool rules from `rules\playpool.toml` unless `--playpool-rules`.
- **generate-schedule**: `standings\<season>.league.ini` (missing → error,
  as today); tunables from `rules\scheduler.toml` (missing → defaults, as
  today). `--season` is unchanged.

## Code shape

`athc.config` keeps its public surface for athc-admin:

- `load_league(league: str | None = None) -> dict[str, str]` — resolves the
  league (priority above) and returns the `[league]` section of its
  `league.ini`. Same name, signature and return shape as today.
- `LeagueError`, `config_dir()`, `config_file()`, `resolve_path()`,
  `load_config()` — unchanged.

New in `athc.config`:

- `league_dir(name) -> Path`, `available_leagues() -> list[str]`,
  `set_config_value(key, value) -> None` (the ConfigUpdater write).

`athc.cli.league_option` is unchanged. Each tool's `config.py` stops reading
its own `athc.ini` section and reads the league folder instead.
`athc.scheduler.config` takes the league into account when locating the
standings and rules files.

New dependency: `configupdater` (core, `uv add configupdater`).

## Install and release

- `release-build.ps1` stages `leagues\` recursively (replaces staging
  `rules\` and `*.league.ini`).
- `install.bat`: `leagues\*\rules\*.toml` are shipped reference → always
  overwritten; `league.ini` and `standings\*` are user-owned → copied only if
  absent; `athc.ini` guarded as today.
- Fresh install works out of the box on PNFL, as today.

## Docs to update

`docs/design/config.md` (layout, section taxonomy, selection, `config set`;
drop the "no current-league pointer" rule), `docs/design/cli.md`,
`docs/design/reference-projects.md`, `docs/gameplan/ARCHITECTURE.md`,
`README.md`, `release/docs/README.txt`, `release/docs/COMMANDS.txt`,
`release/docs/SCHEDULER-COMMANDS.txt`, `tests/integration/README.md`,
STATUS, CHANGELOG, TODO.

## Testing

- Unit: selection priority (flag, env, key, none), unknown league,
  `set_config_value` preserving comments and creating file/section/key,
  each tool's config loader reading a league folder with and without the
  optional files and rule lists, layering order, relative-path resolution in
  `league.ini`, the obsolete-keys warning.
- Integration (CliRunner, `ATHC_CONFIG_DIR` → a temp layout):
  `athc config set league` (valid, unknown league, unknown key), one
  league-aware command per tool picking up the configured league,
  `--league` overriding it.
- Existing tests that assert the old `athc.ini` keys change because the
  behaviour changes by design.

## Out of scope

- athc-admin changes: it keeps working through the preserved `load_league`
  API; its tests that write `[league.PNFL]` into `athc.ini` will need
  updating when it picks up this athc version.
- A migration tool for existing installs.
- Creating a new league folder from the CLI (users copy `leagues\PNFL\`).
