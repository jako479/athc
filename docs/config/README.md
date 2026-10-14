# config

Show, open, read or change the athc settings files, so users don't have to hunt for the hidden `%LOCALAPPDATA%\athc` folder:

- `athc.ini` holds the league in use (`[athc] league`) and each tool's app-wide settings.
- A league's `leagues\<NAME>\league.toml` holds its `path`, `play_path`, `team` and `ppp_path`.

## Usage

```bash
athc config path [FILE]          # print the path of athc.ini or league.toml
athc config edit [FILE]          # open it in its default app
athc config reveal [FILE]        # show it in File Explorer
athc config get KEY              # print a setting
athc config set KEY VALUE        # change a setting, keeping the file's comments
```

- FILE is `athc.ini` (the default) or `league.toml`, in any case; with `--league NAME` and no FILE it is `league.toml`.
- KEY is `league`, `path`, `play_path`, `team` or `ppp_path`, in any case.
- `--league NAME` on every verb picks the league; without it, the league in use. A named league must have a folder under `leagues\`.
- Set `path`, `play_path`, `team` and `ppp_path` with `athc config set` (or by hand with `athc config edit league.toml`); read them with `athc config get`.

## What each verb does

- `path` prints the path; the file need not exist.
- `edit` opens the file with Windows' app for it; a missing `athc.ini` is created empty first; a missing `league.toml` is a failure, and nothing is created.
- `reveal` selects the file in File Explorer, or opens its folder when the file is missing.
- `get league` prints the league in use, checked against the league folders; the other keys print from the league's `league.toml`, a relative path resolved against the league folder.
- `set league` writes `athc.ini` after checking the folder; the other keys write the league's `league.toml`, as supplied. `--league` is not valid with `set league`.

## Lines and codes

| When | Line | Code |
|---|---|---|
| `path`, `get` done | the path or value (stdout) | 0 |
| `edit`, `reveal` done | nothing | 0 |
| `set` done | `OK   <file>: <key> = <value>` | 0 |
| `get ppp_path`, not set | `WARN <league.toml>: Game plan and profile folder is not set; using the folders the league file names.` | 0 |
| `get path`, `play_path` or `team`, not set | `FAIL <league.toml>: ... is not set. Run 'athc config set <key> ...'.` | 2 |
| no league set, or no folder for it | `FAIL League is not set. ...` or `FAIL League 'X' not found. ...` | 2 |
| `league.toml` missing or without `[league]` (`set`, `edit`) | `FAIL <league.toml>: The system cannot find the file specified.` | 2 |
| a malformed `athc.ini` or `league.toml` | `FAIL <file>: Not valid INI: ...` or `Not valid TOML: ...` | 2 |
| `edit`, a file Windows cannot open | `FAIL <file>: <Windows' text>` | 2 |
| unknown KEY or FILE, a `set league` name with no folder, any other usage error | Click's `Error:` line | 2 |

Shared console and codes: [architecture](../design/architecture.md#console-run-log-and-errors).

## Config

The files are found through `ATHC_CONFIG_DIR` or the default settings folder (see [../design/architecture.md](../design/architecture.md#config)); there is no `--config` flag and no `[config]` section.

## Tests

`pytest tests/integration/test_config.py` covers `path`, `edit`, `reveal` and `get` (app and Explorer launches mocked), alongside the shared league resolver; `set` is in `tests/integration/test_config_set.py`.
