# config — Architecture

The `athc config` command group: three thin commands that locate and open the settings file. No domain logic — it operates on `athc.ini` itself.

## Layout

```
src/athc/cli/config/
├── __init__.py     # defines the `config` group
├── path.py         # print config_file()
├── edit.py         # open athc.ini in an editor
└── reveal.py       # reveal athc.ini in the file manager

src/athc/config.py  # config_dir() + config_file() helpers (shared base module)
```

## How it works

- `path` → `click.echo(config_file())`.
- `edit` → create `athc.ini` if missing, then `click.edit(filename=…)` when `$VISUAL`/`$EDITOR` is set, else `click.launch(path)` (the file's associated app — Notepad by default on Windows).
- `reveal` → `click.launch(<athc.ini>, locate=True)` (selects the file), or `click.launch(config_dir())` if it's absent — opens Explorer on Windows.

## Boundaries

- Reads no settings (no `[config]` section); only locates/opens the file and its folder.
- Creates the config dir / file when missing; never edits their contents.
- Editor/Explorer launches are mocked in tests ([../../tests/integration/test_config.py](../../tests/integration/test_config.py)).
