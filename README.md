# Assistant to the Head Coach: athc

Game plan (.pln) editor, profile (.prf) editor, and other tools for Front Page Sports Football Pro '98 coaches and league managers.

Current state and what's next: [STATUS.md](STATUS.md) · task list: [TODO.md](TODO.md)

## Install

End-user (from a local wheel; not yet on PyPI):

```
uv tool install ./dist/athc-0.1.0-py3-none-any.whl
```

## Commands

`athc --help` lists top-level commands
`athc <group> --help` lists subcommands
`athc <group> <subcommand> --help` for flags

## Configuration

`athc` reads `%LOCALAPPDATA%\athc\athc.ini` for app-wide settings and `leagues\<NAME>\` next to it for each league (`league.toml`, rule TOMLs, `standings\`); missing file or section falls back to defaults. `athc config set league NAME` picks the league.

```ini
[toolname]
setting = value
```

## Extending

Third-party packages add subcommands by registering entries under the `athc.commands` group in their own `pyproject.toml`:

```toml
[project.entry-points."athc.commands"]
mytool = "mypkg.cli:mytool"
```

The umbrella discovers them at runtime — no changes to `athc` needed.

See [docs/design/architecture.md](docs/design/architecture.md) for the full architecture and the conventions every command follows.

## Development

Install the project and its dev tools:

```
uv sync
```

Source runs read the dev config in `config/dev/` (a full `athc.ini` plus league folders, shared with athc-admin) instead of the installed one: point `ATHC_CONFIG_DIR` at that folder. For the VS Code terminal, in `.vscode/settings.json` (in a multi-root workspace, in the `.code-workspace` `settings` with `${workspaceFolder:athc}`; open a new terminal to pick it up):

```json
"terminal.integrated.env.windows": {
  "ATHC_CONFIG_DIR": "${workspaceFolder}/config/dev"
}
```

For F5, each `.vscode/launch.json` entry sets it on the debug process (terminal and launch `env` are independent; set both if you run both ways):

```json
{
  "name": "athc profile check",
  "type": "debugpy",
  "request": "launch",
  "module": "athc",
  "args": ["profile", "check"],
  "console": "integratedTerminal",
  "env": { "ATHC_CONFIG_DIR": "${workspaceFolder}/config/dev" }
}
```

For one shell session:

```powershell
$env:ATHC_CONFIG_DIR = "$PWD\config\dev"
```

## Tests

```
uv run pytest
```

Coverage runs with every test run and fails below 92%.

## License

[MIT](LICENSE).
