# config

Show, open, read or change the athc settings files, so users don't have to hunt for the hidden `%LOCALAPPDATA%\athc` folder:

- `athc.toml` holds the league in use (`[athc] league`) and each tool's app-wide settings.
- A league's `leagues\<NAME>\league.toml` holds its `path`, `play_path`, `team` and `ppp_path`.

Usage, what each verb does, lines and exit codes: [usage/config.txt](../usage/config.txt).

## Tests

`pytest tests/integration/test_config.py` covers `path`, `edit`, `reveal` and `get` (app and Explorer launches mocked), alongside the shared league resolver; `set` is in `tests/integration/test_config_set.py`.

## How it works

- KEY (`league`, `path`, `play_path`, `team`, `ppp_path`) and FILE (`athc.toml`, `league.toml`) are matched without case by Click callbacks; a bad word gets Click's `Choice` wording.
- `settings_file(file, league)` picks the file for `path`, `edit` and `reveal`: `config_file()` or `league_file(league)`; a named league is checked even for `athc.toml`.
- `path` → `console.print` of the path.
- `edit` → create a missing `athc.toml`, fail on a missing `league.toml`, then `os.startfile(path)`; its `OSError` reaches `main` as a `FAIL` line.
- `reveal` → `click.launch(<file>, locate=True)`, or `click.launch(<folder>)` when the file is missing.
- `get` → `league` through `resolve_league()`; the other keys through `load_league_config()` and `LeagueConfig.path()` or `string()`.
- `set` → `league` through `set_config_value()` (tomlkit; a missing `[athc]` table leads the file, or ends it when a key sits above the first table), after the folder check; the other keys through `set_league_value()` (tomlkit too; a new key goes on the line after its commented example, else after `[league]`'s last key); both write through `atomic_write`, so a failed write leaves the old file whole; then the `OK` line.

### Layout

```
src/athc/cli/config/
├── __init__.py     # the `config` group; KEY and FILE matching; settings_file()
├── path.py         # print the file's path
├── edit.py         # open the file in its default app
├── reveal.py       # show the file in File Explorer
├── get.py          # print one setting
└── set.py          # write one setting, keeping comments

src/athc/config.py  # config_file(), league_file(), resolve_league(), the readers and writers (shared base module)
```

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — path or value printed, file opened or revealed, value written; an unset `ppp_path` is a `WARN` only. |
| `2` | **Usage** — unknown subcommand, KEY or FILE, or bad arguments. |
| `2` | **FAIL** — no league set or no folder for it; a malformed `athc.toml` or `league.toml`; `get` of an unset `path`, `play_path` or `team`; a missing `league.toml` (`edit`, `set`); a file Windows cannot open (`edit`). |

### Boundaries

- Five thin commands and no domain logic.
- `get` and `set` are the only verbs that read `league.toml`; `path`, `edit` and `reveal` only locate it.
- `set` writes `[athc] league` in `athc.toml` and the four keys under `[league]` in `league.toml`; comments and other lines stay.
- Creates the settings folder and an empty `athc.toml` when missing; never creates a `league.toml` or a league folder.
- App and Explorer launches are mocked in tests ([../tests/integration/test_config.py](../../tests/integration/test_config.py)).
