# athc — Integration & System Testing Design

How athc's **system/integration** tests are structured — a command invoked end-to-end, through the libraries, down to a real **output file**. Unit tests (components in isolation): [testing-unit.md](testing-unit.md). Conventions from Black, sqlfluff, pip-tools, sqlite-utils — see [reference-projects.md](reference-projects.md#testing-exemplars).

> First implemented: `athc profile check` — writes to **stdout**, not a file; same conventions apply, golden report under `expected/`.

## Tiers

- **Integration / system** — run a command via `CliRunner` through the libraries to a real output file, then assert on the produced file. (functional / e2e / system are used interchangeably; we say *integration*.)
- **Packaging check** — `CliRunner` tests the command object, not the installed script. A couple of tests `subprocess.run` the real `athc` entry point to confirm it wires up and propagates exit codes. Keep it minimal.

## Framework

`pytest` + Click `click.testing.CliRunner` for in-process runs (`runner.invoke(main, [...], catch_exceptions=False)`, output to `isolated_filesystem()` / `tmp_path`). Mock external shell-outs at the call boundary.

## Config

Tests use an **isolated, empty config dir**, never the real `athc.ini`: the autouse `config_dir` fixture (root `tests/conftest.py`) monkeypatches `ATHC_CONFIG_DIR` to a `tmp_path`. Tests needing config write their `athc.ini` there with the shared `write_config` helper (also in root `tests/conftest.py`) or pass `--rules`. Subprocess packaging checks set `ATHC_CONFIG_DIR` in the child `env` explicitly.

## Layout

`tests/integration/`, organized by command (not mirrored to modules):

```
tests/
  integration/
    conftest.py
    data/                  # real input files (.ply/.pln/.prf), named by scenario
    expected/              # committed expected-output files
    test_<command>.py      # one file per command
    README.md              # this tier's test matrix
```

Packaging checks live inline in the command's test file — no separate file, no marker.

## Input & expected data

Keep the two apart so source vs. target is obvious: **`data/` = source inputs, `expected/` = expected results.** Any real file used as an *expected* result goes in `expected/`, never mixed in with `data/`.

- **Input** — real files in `tests/integration/data/`, named by scenario, located via `Path(__file__).parent`. Reserve `tmp_path` for the command's *output* (scratch), never for committed inputs.
- **Expected** — committed files in `expected/`. For deterministic binary writers, compare the output **byte-for-byte**; where incidental bytes vary, compare **semantically** — reopen it with athc's reader and check the model. For **stdout**, compare to a golden `.txt`, normalizing the file path printed on each line so the comparison is machine-independent. Regenerate expected files with a script; never hand-edit one to pass.

## Test shape

Per command: build args → `CliRunner().invoke(main, [...])` in an isolated dir → assert `exit_code == 0` and the output exists → compare it to its expected file (byte or semantic). Parametrize over the `data/` ↔ `expected/` pairs.

## Documentation

Same as unit: a per-tier matrix at `tests/integration/README.md` — each command/scenario, its test, status.
