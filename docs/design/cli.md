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
autocontinue = "athc.cli.autocontinue:autocontinue"

# any extension package's pyproject.toml
[project.entry-points."athc.commands"]
mytool = "mypkg.cli.mytool:mytool"
```

Extension packages can mirror athc's `<pkg>/cli/` layout (CLI wiring under `<pkg>/cli/`, tool logic under `<pkg>/<tool>/`) — the umbrella doesn't care. It just loads whatever the entry-point points at.

## Per-tool layout

All CLI wiring lives under `<pkg>/cli/`. Each leaf command is its own `.py`; each large command group is its own folder. Tool logic lives separately under `<pkg>/<tool>/` and stays free of Click. Mirrors pnfl's prior structure.

- **Leaf command** (single action, e.g. `athc autocontinue`): `<pkg>/cli/<name>.py`, one `@click.command(...)`.
- **Large command group** (multiple subcommands, e.g. `athc gameplan list-plays check ...`): `<pkg>/cli/<name>/` folder with `__init__.py` (defines the group) and one `.py` per leaf.

```python
# athc/cli/autocontinue.py — leaf command
from athc.autocontinue.core import run_autocontinue

@click.command(help="Advance the sim to the next coaching decision.")
def autocontinue() -> None:
    run_autocontinue()
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

Dev runs read a per-machine `dev/athc.ini` instead of the installed config, selected by `ATHC_CONFIG_DIR` (design: [config.md](config.md#dev-config-running-from-source)). Both methods below use `${workspaceFolder}/dev`, so they work on any clone.

### Run in VS Code (terminal)

In `.vscode/settings.json`:

```json
"terminal.integrated.env.windows": {
  "ATHC_CONFIG_DIR": "${workspaceFolder}/dev"
}
```

In a multi-root workspace, folder settings are ignored for this key — put the block in the `.code-workspace` `settings` with `${workspaceFolder:athc}/dev` instead. Open a new terminal to pick it up.

### Debug in VS Code (F5)

Per command in `.vscode/launch.json`; `env` sets the var on the debug process:

```json
{
  "name": "athc profile check",
  "type": "debugpy",
  "request": "launch",
  "module": "athc",
  "args": ["profile", "check"],
  "console": "integratedTerminal",
  "env": { "ATHC_CONFIG_DIR": "${workspaceFolder}/dev" }
}
```

Edit `args` per command. Terminal and launch `env` are independent — set both if you run both ways.

### One-off

```powershell
$env:ATHC_CONFIG_DIR = "$PWD\dev"   # this session only
```

Production users never set the var; the default `%LOCALAPPDATA%\athc` wins.

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
        help="League name (matches a section like [league.PNFL] in athc.ini).",
    )(f)
```

Selection priority (highest first): `--league` flag → `ATHC_LEAGUE` env → `[athc] default_league` in config → error. Full rules in [config.md](config.md).

For a command group, putting the decorator on the group means every leaf inherits it once. For a single leaf, decorate the leaf directly.

## Help text conventions

- Every `@click.command` / `@click.group` gets a one-line `help="..."` describing what it does.
- Help text refers to the user's perspective ("Advance the sim to the next decision") rather than implementation ("Read the [autocontinue] section").
- Default values shown via `show_default=True` on `@click.option` where useful.

## Output and logging

Two channels: stdout (`click.echo`) for everything the user reads (results and
status), stderr (`logging`) for errors and warnings only. Full convention — log
levels, library behavior, exit-code timing: [logging.md](logging.md).

**Libraries** (`<pkg>/<tool>/`, `playpool`, …) call `getLogger(__name__)` but **never** `basicConfig` (the app owns handler setup). They use `logger.warning` for recoverable "skipped X" notices (duplicate play, missing file) and `logger.info` for progress — they don't print results.

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
