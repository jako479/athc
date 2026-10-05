# config

Locate, edit, reveal, or set a value in the athc settings file (`athc.ini`) so users don't have to hunt for the hidden `%LOCALAPPDATA%\athc` folder.

## Usage

```bash
athc config path               # print the full path to athc.ini
athc config edit               # open athc.ini in its default app (created if missing)
athc config reveal             # reveal athc.ini in File Explorer
athc config set league NAME    # set the league used when --league is not given
```

`reveal` opens the file manager with `athc.ini` selected, or the folder if it doesn't exist yet.

## Config

Operates on `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)) — there is no `--config` flag and no `[config]` section; the group reads no settings.

## Tests

`pytest tests/integration/test_config.py` covers `path`, `edit` and `reveal` (app/Explorer launches mocked), alongside the shared `load_league` resolver; `set` is in `tests/integration/test_config_set.py`.
