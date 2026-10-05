# athc config

Where settings live, how they're structured, and how tools read them at runtime.
Deploy mechanics (install/upgrade overwrite rules) live in [installer.md](installer.md).

## Format and location

- **Format**: INI via stdlib `configparser`. Chosen over TOML for non-dev-user familiarity (`.ini` files have been a Windows convention for decades; users are comfortable editing them in Notepad).
- **Path**: `%LOCALAPPDATA%\athc\athc.ini` (resolved via `platformdirs.user_config_path("athc", appauthor=False)`).

### Why stdlib over a third-party config library

`configparser` is the only mainstream Python option that gives non-dev users a Notepad-editable INI file with native `[DEFAULT]` cascade and `%(key)s` interpolation out of the box. The popular alternatives in 2026 don't fit:

- **pydantic-settings** (370M downloads/month, FastAPI's standard) targets env vars, `.env`, secrets — no native INI reading.
- **dynaconf** reads INI but its layering model is dev/staging/prod, not one folder per league; loses `%(key)s` (uses Jinja, Notepad-unfriendly).
- **confuse** is YAML-only.

If load-site validation becomes a real pain (user typos `Defualt_League`), the proportionate upgrade is `pydantic` (the core lib, **not** `pydantic-settings`) — swap `@dataclasses.dataclass` for `@pydantic.dataclasses.dataclass` on each `Config` class. One-line change per Config; keep `configparser` as the loader.

## Editing the config

The `athc config` group locates and opens the settings file so users don't hunt for the hidden `%LOCALAPPDATA%` path:

- `athc config path` — print the full path to `athc.ini`.
- `athc config edit` — open `athc.ini` in its default app (created if missing).
- `athc config reveal` — reveal `athc.ini` in the file manager (Explorer), or its folder if absent.

Thin wrappers over `click.edit` / `click.launch`; no `[config]` section (the group operates on the file, it reads no settings).

## Dev config (running from source)

Source runs read a per-machine **dev config** instead of the installed one:

- **Override**: `ATHC_CONFIG_DIR`, if set, replaces the whole config dir; else the default `%LOCALAPPDATA%\athc` wins. Resolution: [`athc.config.config_dir()`](../../src/athc/config.py).
- **Location**: a full `athc.ini` in `dev/` at the repo root (mirrors `release/`).
- **Shared dir**: athc and athc-admin read the same dir, so one `dev/` serves both.
- **Production**: end users never set the var.

VS Code terminal/F5 steps: [cli.md](cli.md#running-from-source-dev-config).

## Layout

One folder per league under the config dir; `athc.ini` holds only app-wide settings.

```
athc.ini                      app-wide settings + the selected league
leagues\
  PNFL\
    league.ini                per-league settings ([league] play_path, …)
    rules\                    gameplan.toml, profile.toml, playpool.toml, scheduler.toml
    standings\                <season>.league.ini
  PCFL\                       same fixed names
```

Fixed, well-known file names inside a league folder; nothing lists them in config. A league is any folder under `leagues\`; its name is the folder name. Per-league values that are not files (`play_path`; athc-admin's `db_path`, `log_dir`) go in `league.ini` under `[league]`; relative paths there resolve against the league folder.

Precedent: OBS Studio (`basic/profiles/<Name>/basic.ini`), Kodi (`profiles/<name>/`), Hugo (`config/_default/` + `config/<env>/`).

## `athc.ini`

```ini
[athc]
league = PNFL

[autocontinue]
mouse_move_duration = 0.0
delay_before_continue = 1.0
hot_corner = true

[convert-pdb]
calculate_percentages = true
include_category_worksheets = false
exclude_sacks_from_pass_attempts = true
```

`[athc] league` is edited by hand or with `athc config set league NAME`, which validates the folder and rewrites the file through ConfigUpdater so comments survive (`configparser` drops them on write).

An unreadable `athc.ini` or `league.ini` raises `ConfigFileError`; a missing or unknown league raises `LeagueError`.

Log level is not a setting ([logging.md](logging.md#handler-setup)).

## Rule files

Each tool reads its one fixed file under the league's `rules\`. An optional multi-line list in `league.ini` (`gameplan_rules`, `profile_rules`) replaces it with an ordered set, later files overriding earlier ones. No command-line option overrides the league's rules or play pool. Rule files are league data only; there is no shared default outside the league folders.

## Multi-league selection

`--league name` is an option on each league-aware command (`gameplan check` / `replace-play` / `set-normals` / `set-specials`, `profile check`, `check-ppp`, `check-playpool`, `convert-pdb`, `generate-schedule`), placed after the command name: `athc profile check OFF1.prf --league PCFL`. Other commands don't have it. The shared option is in [cli.md](cli.md#cross-cutting-options---league).

**Selection priority** (highest wins):

1. `--league NAME` (one run, never persisted).
2. `[athc] league`.
3. Error naming `athc config set league` and listing the folders under `leagues\`.

## Per-tool config code

Each tool owns its `config.py`:

```python
# athc/gameplan/config.py
from dataclasses import dataclass
from pathlib import Path

from athc.config import load_league_config

@dataclass(frozen=True)
class Config:
    play_path: Path
    rule_files: tuple[Path, ...] = ()

def load(league: str | None = None) -> Config:
    cfg = load_league_config(league)  # LeagueError if no league resolvable
    return Config(
        play_path=cfg.path("play_path"),
        rule_files=cfg.rule_files("gameplan_rules", "gameplan.toml"),
    )
```

- `Config` is a frozen dataclass with typed defaults.
- `load()` asks the resolved `LeagueConfig` for what the tool needs: `path(key)` for a value in `league.ini`, `rules_file(name)` / `rule_files(key, default)` for files under `rules\`.
- Missing file or key → dataclass defaults. Type conversion is the tool's responsibility — `configparser` returns everything as strings.

## In-code defaults are authoritative

The whole config is optional from the runtime's perspective:

- Missing file → use defaults for every section.
- Missing section → use defaults for that section.
- Missing key inside an existing section → use the dataclass default.

A tool only errors when a value it genuinely needs at runtime can't be resolved (e.g., `play_path` doesn't exist on disk for the selected league). This matches how peer end-user CLIs behave — pgcli, mycli, and yt-dlp all run on defaults when the config is absent or partial.

When a new tool ships with a `[new-tool]` section, the user sees nothing on upgrade. The tool runs on defaults. To customize, the user looks at the freshly-extracted `athc.ini` in the new zip — a single self-documenting file that lists every current setting (the pgcli/mycli model; see [installer.md](installer.md)) — and copies the new section into their own `athc.ini`.

## Deprecation

When a tool reads a deprecated key, log a one-line stderr warning at startup:

```
WARNING: [autocontinue] hot_corner_delay is deprecated; use delay_before_continue. Reading hot_corner_delay for now.
```

Keep reading it for 2–3 releases, then drop. Pattern follows VS Code's `deprecationMessage`.
