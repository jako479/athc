# config

Locate, edit, or reveal the athc settings file (`athc.ini`) so users don't have to hunt for the hidden `%LOCALAPPDATA%\athc` folder.

## Usage

```bash
athc config path     # print the full path to athc.ini
athc config edit     # open athc.ini in an editor (created if missing)
athc config reveal   # reveal athc.ini in File Explorer
```

`edit` uses `$VISUAL`/`$EDITOR` if set, else the file's associated app (Notepad by default). `reveal` opens the file manager with `athc.ini` selected, or the folder if it doesn't exist yet.

## Config

Operates on `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)) — there is no `--config` flag and no `[config]` section; the group reads no settings.

## Tests

`pytest tests/integration/test_config.py` covers the three commands (editor/Explorer launches mocked), alongside the shared `load_league` resolver.
