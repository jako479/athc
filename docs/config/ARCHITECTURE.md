# config — Architecture

The `athc config` command group: five thin commands that locate, open, reveal, read or write the settings files, `athc.ini` and a league's `league.toml`. No domain logic.

## Layout

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

## How it works

- KEY (`league`, `path`, `play_path`, `team`, `ppp_path`) and FILE (`athc.ini`, `league.toml`) are matched without case by Click callbacks; a bad word gets Click's `Choice` wording.
- `settings_file(file, league)` picks the file for `path`, `edit` and `reveal`: `config_file()` or `league_file(league)`; a named league is checked even for `athc.ini`.
- `path` → `console.print` of the path.
- `edit` → create a missing `athc.ini`, fail on a missing `league.toml`, then `os.startfile(path)`; its `OSError` reaches `main` as a `FAIL` line.
- `reveal` → `click.launch(<file>, locate=True)`, or `click.launch(<folder>)` when the file is missing.
- `get` → `league` through `resolve_league()`; the other keys through `load_league_config()` and `LeagueConfig.path()` or `string()`.
- `set` → `league` through `set_config_value()` (ConfigUpdater), after the folder check; the other keys through `set_league_value()` (a TOML library that keeps comments; a new key goes on the line after its commented example, else after `[league]`'s last key); then the `OK` line.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — path or value printed, file opened or revealed, value written; an unset `ppp_path` is a `WARN` only. |
| `2` | **Usage** — unknown subcommand, KEY or FILE, or bad arguments. |
| `2` | **FAIL** — no league set or no folder for it; a malformed `athc.ini` or `league.toml`; `get` of an unset `path`, `play_path` or `team`; a missing `league.toml` (`edit`, `set`); a file Windows cannot open (`edit`). |

## Boundaries

- `get` and `set` are the only verbs that read `league.toml`; `path`, `edit` and `reveal` only locate it.
- `set` writes `[athc] league` in `athc.ini` and the four keys under `[league]` in `league.toml`; comments and other lines stay.
- Creates the settings folder and an empty `athc.ini` when missing; never creates a `league.toml` or a league folder.
- App and Explorer launches are mocked in tests ([../../tests/integration/test_config.py](../../tests/integration/test_config.py)).
