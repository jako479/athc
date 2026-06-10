# Assistant to the Head Coach: athc

Game plan (.pln) editor, profile (.prf) editor, and other tools for Front Page Sports Football Pro '98 coaches and league managers.

## Install

End-user (from a local wheel; not yet on PyPI):

```
uv tool install ./dist/athc-0.1.0-py3-none-any.whl
```

## Commands

`athc --help` lists top-level commands
`athc <group> --help` lists subcommands
`athc <group> <subcommand> --help` for flags

`hello` is a built-in subcommand; `helloworld` is a standalone script (separate `[project.scripts]` entry, not under the `athc` umbrella).

## Configuration

`athc` reads `%LOCALAPPDATA%\athc\athc.ini`. Each tool has its own `[section]`; missing file or section falls back to defaults.

```ini
[hello]
greeting = hello, head coach
```

## Extending

Third-party packages add subcommands by registering entries under the `athc.commands` group in their own `pyproject.toml`:

```toml
[project.entry-points."athc.commands"]
mytool = "mypkg.cli:mytool"
```

The umbrella discovers them at runtime — no changes to `athc` needed.

See [docs/design/overview.md](docs/design/overview.md) for the full architecture.

## Development

Perform an editable install (run both):

```
uv venv
uv pip install -e ".[dev]"
```

For local paths different from production (e.g., game files on `E:\`), put a local `athc.ini` in `dev/` at the repo root (gitignored) and set `ATHC_CONFIG_DIR = "$PWD\dev"`. See [docs/design/cli.md](docs/design/cli.md) for the dev-config pattern.

## Tests

```
pytest
```

## License

[MIT](LICENSE).
