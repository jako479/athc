# athc CLI

How the command-line interface is structured. Config file structure and runtime
reading: [config.md](config.md).

## Terminology

Standard CLI terminology (matches Click/Typer):

athc gameplan list-plays — nesting is unlimited.

athc — root
gameplan — command group
list-plays — leaf command

In Click/Typer, groups are created with @app.group() / sub-Typer() instances and can nest arbitrarily. Args/options that come after the leaf are "arguments" (positional) and "options" (flags).

## Framework: Click

Click was picked over Typer and stdlib argparse because:

- It's the mainstream choice for plugin-extensible Python CLIs (Flask, Poetry, MkDocs, dbt, ruff, Black, pre-commit all use it).
- Its `Group` subclass hook lets us implement lazy plugin discovery in ~15 lines — what Flask's `FlaskGroup._load_plugin_commands` does.
- Typer's plugin story is weaker (vendored Click in 0.26 and removed click-plugins compatibility). For a public/private extension setup, Click is the safer bet.
- argparse is fine but every plugin would re-implement its own parser; Click gives a uniform shape across built-in and plugin commands.

## Umbrella architecture

The `athc` umbrella is one Click `Group` subclass that discovers all subcommands at runtime via setuptools entry points. The umbrella itself has zero knowledge of any specific tool — including its own built-ins.

```python
# athc/cli/__init__.py (abridged)
class AthcGroup(click.Group):
    _plugins_loaded = False

    def _load_plugins(self):
        if self._plugins_loaded:
            return
        for ep in entry_points(group="athc.commands"):
            self.add_command(ep.load(), name=ep.name)
        self._plugins_loaded = True

    def list_commands(self, ctx):
        self._load_plugins()
        return super().list_commands(ctx)

    def get_command(self, ctx, name):
        self._load_plugins()
        return super().get_command(ctx, name)
```

Loading is lazy — the first `--help` or first subcommand invocation triggers discovery once and caches it. Plugin import failures propagate (Flask's choice; broken plugin fails loudly rather than silently disappearing).

## Built-ins and plugins are symmetric

Every subcommand — built-in athc tool or third-party extension — is registered the same way: as an entry point under the `athc.commands` group in its package's `pyproject.toml`. The umbrella doesn't distinguish.

```toml
# athc/pyproject.toml
[project.entry-points."athc.commands"]
hello = "athc.cli.hello:hello"

# any extension package's pyproject.toml
[project.entry-points."athc.commands"]
mytool = "mypkg.cli.mytool:mytool"
```

Extension packages can mirror athc's `<pkg>/cli/` layout (CLI wiring under `<pkg>/cli/`, tool logic under `<pkg>/<tool>/`) — the umbrella doesn't care. It just loads whatever the entry-point points at.

## Per-tool layout

All CLI wiring lives under `<pkg>/cli/`. Each leaf command is its own `.py`; each large command group is its own folder. Tool logic lives separately under `<pkg>/<tool>/` and stays free of Click. Mirrors pnfl's prior structure.

- **Leaf command** (single action, e.g. `athc hello`): `<pkg>/cli/<name>.py`, one `@click.command(...)`.
- **Large command group** (multiple subcommands, e.g. `athc gameplan list-plays check ...`): `<pkg>/cli/<name>/` folder with `__init__.py` (defines the group) and one `.py` per leaf.

```python
# athc/cli/hello.py — leaf command
from athc.hello.core import greet

@click.command(help="Print the configured greeting.")
def hello() -> None:
    click.echo(greet())
```

```python
# athc/cli/gameplan/__init__.py — group
@click.group()
def gameplan():
    """Gameplan tools."""

from athc.cli.gameplan import check, list_plays  # noqa: registers leaves
```

```python
# athc/cli/gameplan/list_plays.py — leaf in a group
from athc.cli.gameplan import gameplan
from athc.gameplan.core import list_all_plays

@gameplan.command(name="list-plays")
@league_option
def list_plays(league):
    ...
```

## Running from source (dev config)

For local dev runs where your paths differ from production (e.g., game files on `E:\` instead of the default `C:\SIERRA\...`), point athc at a per-machine config without touching the production file.

Set `ATHC_CONFIG_DIR` to a directory containing `athc.ini`:

```
$env:ATHC_CONFIG_DIR = "$PWD\dev"
athc hello
```

Convention: keep dev config in `dev/` at the repo root, gitignored. Matches the layout of `release/` (end-user-facing). The dev folder isn't tracked, so each developer's machine-specific paths stay local.

```
athc/
  dev/                # gitignored — your local athc.ini
  release/            # ships to end users
```

Mechanism is config-side; resolution lives in `athc.config.config_dir()`:

```python
def config_dir() -> Path:
    if override := os.environ.get("ATHC_CONFIG_DIR"):
        return Path(override)
    return user_config_path("athc", appauthor=False, ensure_exists=False)
```

Production users never set the env var; the default path wins.

Matches the dominant pattern in small Python CLIs — `llm` (`LLM_USER_PATH`), `httpie` (`HTTPIE_CONFIG_DIR`), `tmuxp` (`TMUXP_CONFIGDIR`).

## Standard idioms

- `context_settings={"help_option_names": ["-h", "--help"]}` on the root group so both `-h` and `--help` work.
- `no_args_is_help=True` on the root group so bare `athc` prints help instead of hanging.
- `@click.version_option(package_name="athc")` reads the installed metadata — no hard-coded version strings.
- `python -m athc` works via `athc/__main__.py`.

## Cross-cutting options: `--league`

When a tool operates on league-specific data (gameplan, profile, playcatalog), it accepts `--league NAME`. This option lives on the command (or group) that needs it, **not** at the umbrella level. Non-league tools (generate-schedule, autocontinue) never see the flag.

A shared decorator keeps the option uniform:

```python
# athc/cli/__init__.py
def league_option(f):
    return click.option(
        "--league",
        envvar="ATHC_LEAGUE",
        default=None,
        help="League name (matches a section like [PNFL] in athc.ini).",
    )(f)
```

Selection priority (highest first): `--league` flag → `ATHC_LEAGUE` env → `[athc] default_league` in config → error. Full rules in [config.md](config.md).

For a command group, putting the decorator on the group means every leaf inherits it once. For a single leaf, decorate the leaf directly.

## Help text conventions

- Every `@click.command` / `@click.group` gets a one-line `help="..."` describing what it does.
- Help text refers to the user's perspective ("Print the greeting") rather than implementation ("Read [hello] section").
- Default values shown via `show_default=True` on `@click.option` where useful.

## What goes where

| Concern                                          | Location                                                        |
| ------------------------------------------------ | --------------------------------------------------------------- |
| Umbrella `AthcGroup` + plugin loader + `main()`  | `athc/cli/__init__.py`                                          |
| Shared option decorators (`league_option`, etc.) | `athc/cli/__init__.py`                                          |
| Leaf command (single action)                     | `<pkg>/cli/<name>.py`                                           |
| Command group + its leaves                       | `<pkg>/cli/<group>/__init__.py` + `<pkg>/cli/<group>/<leaf>.py` |
| Per-tool config reader + `Config` dataclass      | `<pkg>/<tool>/config.py`                                        |
| Per-tool logic (model, readers, writers)         | `<pkg>/<tool>/` (other modules)                                 |

CLI wiring is kept separate from tool logic — Click decorators live under `cli/`, tool code under `<tool>/`. The umbrella discovers and dispatches; it never imports from a specific tool.
