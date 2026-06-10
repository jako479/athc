# athc config

Where settings live, how they're structured, and how tools read them at runtime.
Deploy mechanics (install/upgrade overwrite rules) live in [installer.md](installer.md).

## Format and location

- **Format**: INI via stdlib `configparser`. Chosen over TOML for non-dev-user familiarity (`.ini` files have been a Windows convention for decades; users are comfortable editing them in Notepad).
- **Path**: `%LOCALAPPDATA%\athc\athc.ini` (resolved via `platformdirs.user_config_path("athc", appauthor=False)`).

### Why stdlib over a third-party config library

`configparser` is the only mainstream Python option that gives non-dev users a Notepad-editable INI file with native `[DEFAULT]` cascade and `%(key)s` interpolation out of the box. The popular alternatives in 2026 don't fit:

- **pydantic-settings** (370M downloads/month, FastAPI's standard) targets env vars, `.env`, secrets — no native INI reading.
- **dynaconf** reads INI but its layering model is dev/staging/prod, not `[PNFL]`/`[PCFL]`; loses `%(key)s` (uses Jinja, Notepad-unfriendly).
- **confuse** is YAML-only.

If load-site validation becomes a real pain (user typos `Defualt_League`), the proportionate upgrade is `pydantic` (the core lib, **not** `pydantic-settings`) — swap `@dataclasses.dataclass` for `@pydantic.dataclasses.dataclass` on each `Config` class. One-line change per Config; keep `configparser` as the loader.

## Section taxonomy

Three kinds of sections, distinguished by naming convention:

| Section | Convention | Example | Purpose |
|---|---|---|---|
| **Umbrella / tool** | lowercase | `[athc]`, `[hello]`, `[gameplan]` | Settings owned by the umbrella or a specific tool. One section per command name. |
| **League** | UPPERCASE | `[PNFL]`, `[PCFL]` | Per-league overrides for tools that operate on league-specific data. |
| **Cross-cutting defaults** | `[DEFAULT]` | `[DEFAULT]` | Native to `configparser`. Keys here cascade into every other section unless overridden. |

The uppercase-vs-lowercase split lets code (and humans) tell at a glance whether a section is a tool or a league. Don't name a league after a tool — the convention is the safeguard.

## Example

```ini
[DEFAULT]
RosterPath = %(LeagueRoot)s\rosters
LogLevel = INFO

[athc]
default_league = PNFL

[hello]
greeting = hello, head coach

[PNFL]
LeagueRoot = D:\Leagues\PNFL
PlayPath = D:\Leagues\PNFL\plays
Season = 2026

[PCFL]
LeagueRoot = E:\Leagues\PCFL
PlayPath = E:\Leagues\PCFL\plays_v2
LogLevel = DEBUG
```

`RosterPath` cascades from `[DEFAULT]` into every league section. `configparser`'s `%(key)s` interpolation resolves `%(LeagueRoot)s` against the section being read, so each league gets its own roster path automatically. `LogLevel` cascades into `[PNFL]` (uses default `INFO`) and is overridden in `[PCFL]` (`DEBUG`).

## Multi-league selection

Tools that operate on league-specific data take a `--league NAME` option on whichever node (group or leaf) actually needs it. **Not** a global `athc --league` flag — keeping it scoped means non-league tools (generate-schedule, autocontinue) don't see an irrelevant option.

A shared decorator keeps the flag consistent:

```python
# athc/cli.py
def league_option(f):
    return click.option(
        "--league",
        envvar="ATHC_LEAGUE",
        default=None,
        help="League name (matches a section like [PNFL] in athc.ini).",
    )(f)
```

Used per command or group that needs it:

```python
@click.command()
@league_option
def gameplan_check(league):
    cfg = config.load_league(league)
    play_path = Path(cfg["PlayPath"])
    ...
```

**Selection priority** (highest wins):

1. `--league NAME` flag (explicit).
2. `ATHC_LEAGUE` environment variable.
3. `[athc] default_league` key.
4. Error with a helpful listing of configured leagues (`athc leagues list`).

No stateful "current league" pointer — explicit beats hidden state for non-dev users.

## Per-tool config code

Each tool owns its `config.py`:

```python
# athc/gameplan/config.py
from dataclasses import dataclass
from pathlib import Path

from athc.config import load_config, load_league

@dataclass(frozen=True)
class Config:
    play_path: Path
    rule_files: tuple[Path, ...] = ()

def load(league: str | None = None) -> Config:
    raw = load_config().get("gameplan", {})
    league_raw = load_league(league)  # raises if no league resolvable
    return Config(
        play_path=Path(league_raw["PlayPath"]),
        rule_files=tuple(Path(p) for p in raw.get("rule_files", "").split(";") if p),
    )
```

- `Config` is a frozen dataclass with typed defaults.
- `load()` reads the tool's own section plus any league-specific section.
- Missing keys → dataclass defaults; missing section → defaults across the board.
- Type conversion (string → Path, semicolon-list → tuple) is the tool's responsibility — `configparser` returns everything as strings.

## In-code defaults are authoritative

The whole config is optional from the runtime's perspective:

- Missing file → use defaults for every section.
- Missing section → use defaults for that section.
- Missing key inside an existing section → use the dataclass default.

A tool only errors when a value it genuinely needs at runtime can't be resolved (e.g., `PlayPath` doesn't exist on disk for the selected league). This matches the standard Python plugin pattern — pytest, mkdocs, Sphinx, Flask all behave this way.

When a new tool ships with a `[new-tool]` section, the user sees nothing on upgrade. The tool runs on defaults. The new section appears in the always-overwritten `athc.ini.example` (see [installer.md](installer.md)) for users who want to customize.

## Deprecation

When a tool reads a deprecated key, log a one-line stderr warning at startup:

```
WARNING: [gameplan] rules_path is deprecated; use rule_files. Reading rules_path for now.
```

Keep reading it for 2–3 releases, then drop. Pattern follows VS Code's `deprecationMessage`.
