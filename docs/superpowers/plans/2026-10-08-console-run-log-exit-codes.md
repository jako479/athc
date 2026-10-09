# Console, run log, errors and exit codes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every athc command prints through one Rich console, writes one rotating run log, raises one error family, and exits 0 / 1 findings / 2 error / 130 Ctrl-C, the way `pdf-converter` does.

**Architecture:** `athc/errors.py` holds `AthcError` and the shared config, league and rules errors; every library error subclasses it. `athc/console.py` is the one printer (stdout for results, stderr for the rest, prefix-only color, each status line also logged). `athc/log.py` owns the `athc` logger and the rotating `athc.log`. The Click entry classes in `athc/cli/__init__.py` run Click in non-standalone mode and are the one place that turns a usage error, `AthcError`, `OSError`, Ctrl-C or a bug into a line, a log entry and an exit code. Commands print, propagate startup errors, catch per item inside a batch, and exit with the worst outcome. Libraries return warnings and take a `progress` callback.

**Tech Stack:** Python 3.12 syntax (the 3.13 floor is being raised in the main checkout; pyright here is still pinned to 3.12), Click 8.4 (`standalone_mode=False`, `CliRunner` with separate `stdout` / `stderr`), Rich (new dependency, `uv add rich`), stdlib `logging.handlers.RotatingFileHandler`, `platformdirs.user_log_path`, pytest.

**Spec:** `docs/design/TODO/logging.md` (framework, situations table) and `docs/design/TODO/logging-by-command.md` (sample code, per command, per library). Both files are deleted by the last task; `docs/design/architecture.md` then describes the code.

## Global Constraints

- Subtask order is the TODO's: errors, console, run log, main(), exit codes, library warnings and progress, tests, docs. The Python 3.13 subtask is already ticked in the main checkout and is not touched here.
- Each task ends green on all four: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`; coverage stays at or above 92%.
- Every text file is UTF-8 with CRLF line endings and a final newline. After creating or editing a file with a tool that writes LF, run `sed -i 's/\r*$/\r/' <file>` and confirm with `file <file>`.
- No 3.13-only syntax. Full type hints, `pathlib`, dataclasses with `slots=True`, 88 columns, double quotes.
- Labels are exactly `OK`, `SKIP`, `WARN`, `FAIL`, padded to five characters (`"OK   "`, `"SKIP "`, `"WARN "`, `"FAIL "`), only the word colored (green, cyan, yellow, red). No `athc <command>:` prefix, no timestamps on the console.
- Streams: results on stdout (`print`, `ok`, `skip`, `result`); `progress`, `warn`, `fail`, `unexpected` on stderr. Nothing in `src/athc` calls `click.echo`, `print()` or `logging.basicConfig` when the task is done; libraries and tool packages never import the console, never log.
- Exit codes: 0 done (warnings only included), 1 findings (checker and finder commands only), 2 any error (usage, config, league, input, a failed batch item, a missing dependency, a bug), 130 Ctrl-C (`autocontinue`: 0). A batch processes every item; error beats findings beats clean.
- Rich consoles are built with `soft_wrap=True, highlight=False, markup=False, emoji=False`: `markup=False` is required, since detail lines like `  [Run Left] message` would otherwise be eaten as markup tags.
- The run log is `athc.log` under `platformdirs.user_log_path("athc", appauthor=False)` (`%LOCALAPPDATA%\athc\Logs`), 1 MB x 5, UTF-8, `time LEVEL message`; `ATHC_LOG_DIR` overrides the folder the way `ATHC_CONFIG_DIR` overrides the config dir, so tests and dev runs never touch the real log. No CLI option, no config key.
- The `athc` logger never propagates and carries a `NullHandler` from import, so nothing from `logging` reaches the console and `logging.lastResort` never prints a duplicate under `CliRunner`.
- Commit per task, one line, prefixed with the tool: `athc: <what>`; tick the TODO subtask in the same commit. Never mention Claude or AI tooling.
- Reader messages keep their trailing `in <path>` text (out of scope); the plan does not reword library error messages except where a task says so.
- `set-normals -q` stays as it is (a separate TODO item).

## Review Focus

1. A result or detail line containing square brackets or `::` (`  [Run Left] message`, `:: header`) must print verbatim; the console test in Task 2 prints such a line and asserts it byte for byte.
2. A command invoked through `CliRunner` directly (no `athc` process) must not print a status line twice via `logging.lastResort`; Task 2's console test asserts a single stderr line for `warn`.
3. `NO_COLOR` set to an empty string must leave color on, while any non-empty value turns it off; Task 2 tests both values.
4. Ctrl-C during a batch must print `FAIL interrupted`, log it, write the `exit 130` end line and exit 130; Task 4 tests it by stubbing a command to raise `KeyboardInterrupt`.
5. A bug in one file of a directory must not stop the batch and must still exit 2; Task 5 tests `gameplan check` with the reader stubbed to raise `RuntimeError` on one of two files.

---

### Task 1: `athc/errors.py`, one error family

**Files:**
- Create: `src/athc/errors.py`
- Modify: `src/athc/config.py` (classes move out, re-exported; `load_config` wraps `configparser.Error`; `_category_labels` re-wraps)
- Modify: `src/athc/gameplan/rules.py:150-157`, `src/athc/profile/rules.py:300-306`, `src/athc/playpool/rules.py:34-41` (the three `RulesFileError` copies become imports)
- Modify: `src/athc/gameplan/writer.py:18`, `src/athc/pdbtoexcel/pdb.py:138`, `src/athc/scheduler/schedulers/errors.py:4`, `src/athc/fbpro98_gameplan/reader.py:43`, `src/athc/fbpro98_profile/reader.py:41-45`, `src/athc/fbpro98_play/reader.py:27`, `src/athc/fbpro98_lg2/reader.py:22-26` (base class)
- Modify: `src/athc/scheduler/config.py:44` and `src/athc/autocontinue/config.py:25` (`ConfigError` goes; `ConfigFileError` from `athc.errors`), every `ConfigError` import and `except` in `src/athc` and `tests/`
- Create: `src/athc/profile/errors.py` (`ProfileTypeMismatchError` moves here from `profile/writer.py:25`; `profile/diff.py:67` raises it)
- Modify: `src/athc/fbpro98_play/labels.py:57-80` (`_validate` raises `ConfigFileError`)
- Modify: `src/athc/fbpro98_gameplan/reader.py` (`read_gameplan` wraps the `GamePlan(...)` construction's `ValueError`)
- Test: `tests/unit/test_errors.py` (new), existing unit tests that name `ConfigError`

**Interfaces:**
- Produces:
  ```python
  class AthcError(Exception): ...
  class ConfigFileError(AthcError): ...
  class LeagueError(AthcError): ...
  class RulesFileError(AthcError):
      errors: list[str]
      def __init__(self, errors: str | Iterable[str]) -> None: ...
  ```
  `athc.config` keeps exporting `ConfigFileError` and `LeagueError` (athc-admin imports them from there). `athc.gameplan`, `athc.profile`, `athc.playpool` keep exporting `RulesFileError`, now the one class. `athc.profile` exports `ProfileTypeMismatchError(source_type, target_type, message=None)` with `.source_type` / `.target_type`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_errors.py
"""Every expected error is an AthcError; the shared ones live in athc.errors."""

from __future__ import annotations

import pytest

from athc.autocontinue import config as autocontinue_config
from athc.errors import AthcError, ConfigFileError, LeagueError, RulesFileError
from athc.fbpro98_gameplan import InvalidGamePlanError
from athc.fbpro98_lg2 import InvalidLg2Error, UnsupportedLg2Error
from athc.fbpro98_play import CategoryLabels, InvalidPlayFileError
from athc.fbpro98_profile import InvalidProfileError, UnsupportedProfileError
from athc.gameplan import RulesFileError as GameplanRulesFileError
from athc.gameplan.writer import InvalidPlayInputError
from athc.pdbtoexcel import InvalidPDBError
from athc.playpool import RulesFileError as PoolRulesFileError
from athc.profile import ProfileTypeMismatchError
from athc.profile import RulesFileError as ProfileRulesFileError
from athc.scheduler import config as scheduler_config
from athc.scheduler.schedulers.errors import SchedulerError


@pytest.mark.parametrize(
    "error",
    [
        ConfigFileError,
        LeagueError,
        RulesFileError,
        InvalidGamePlanError,
        InvalidLg2Error,
        UnsupportedLg2Error,
        InvalidPlayFileError,
        InvalidProfileError,
        UnsupportedProfileError,
        InvalidPlayInputError,
        InvalidPDBError,
        ProfileTypeMismatchError,
        SchedulerError,
    ],
)
def test_every_library_error_is_an_athc_error(error: type) -> None:
    assert issubclass(error, AthcError)


def test_rules_file_error_is_shared() -> None:
    assert GameplanRulesFileError is ProfileRulesFileError is PoolRulesFileError


def test_rules_file_error_carries_every_message() -> None:
    error = RulesFileError(["a", "b"])
    assert error.errors == ["a", "b"] and str(error) == "a\nb"
    assert RulesFileError("one").errors == ["one"]


def test_the_two_config_errors_are_gone() -> None:
    assert not hasattr(scheduler_config, "ConfigError")
    assert not hasattr(autocontinue_config, "ConfigError")


def test_category_labels_raise_config_file_error() -> None:
    with pytest.raises(ConfigFileError, match="not a game category name"):
        CategoryLabels.from_tables({"Nope": "x"}, {})
```

Add to `tests/integration/test_config.py` (next to `test_malformed_athc_ini_errors`):

```python
def test_load_config_wraps_configparser_errors(write_config) -> None:
    write_config("[athc\nleague = x\n")
    with pytest.raises(ConfigFileError, match="athc.ini"):
        load_config()
```

Add to `tests/unit/fbpro98_gameplan/` (the reader test module): a `.pln` whose J95 counts are valid but whose plays break a `GamePlan` invariant is hard to build by hand, so stub instead:

```python
def test_read_gameplan_wraps_model_value_error(monkeypatch, tmp_path) -> None:
    def _boom(*args, **kwargs):
        raise ValueError("bad plan")

    monkeypatch.setattr(reader, "GamePlan", _boom)
    with pytest.raises(InvalidGamePlanError, match="bad plan"):
        read_gameplan(GOOD_PLN)  # any valid fixture the module already uses
```

Add to `tests/unit/profile/test_diff.py`:

```python
def test_diff_profiles_cross_side_raises_type_mismatch(offense, defense) -> None:
    with pytest.raises(ProfileTypeMismatchError, match="cannot diff OFFENSE against DEFENSE"):
        diff_profiles(offense, defense)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/test_errors.py -q`
Expected: ImportError on `athc.errors`.

- [ ] **Step 3: Write `src/athc/errors.py`**

```python
"""The one error family: every expected failure athc reports is an AthcError.

The message is the whole human text; `main()` prints it after `FAIL` and
exits 2. A command adds the file path where the library did not. The shared
errors live here so the config, league and rules readers raise one class
each, whichever tool is asking.
"""

from __future__ import annotations

from collections.abc import Iterable


class AthcError(Exception):
    """Base of every expected athc error."""


class ConfigFileError(AthcError):
    """athc.ini, a league.toml, a tool's TOML file or a league setting cannot
    be read or is invalid: malformed file, wrong value type, bad label, a
    required setting missing."""


class LeagueError(AthcError):
    """No league can be resolved, or the named league has no folder."""


class RulesFileError(AthcError):
    """A rules TOML file cannot be parsed or validated. Carries one or more
    messages (`errors`); every detected problem is reported together."""

    def __init__(self, errors: str | Iterable[str]) -> None:
        self.errors: list[str] = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))
```

- [ ] **Step 4: Move the shared classes and rebase the library errors**

- `src/athc/config.py`: delete the `LeagueError` / `ConfigFileError` class bodies; add `from athc.errors import ConfigFileError, LeagueError` and `__all__`-style re-export (keep the names importable from `athc.config`). `load_config()` becomes:
  ```python
  def load_config() -> dict[str, dict[str, str]]:
      """`athc.ini` as `{section: {key: value}}`; `{}` when absent.
      ConfigFileError when it cannot be parsed."""
      path = config_dir() / CONFIG_FILE
      cp = configparser.ConfigParser(interpolation=None)
      if path.is_file():
          try:
              cp.read(path, encoding="utf-8")
          except configparser.Error as e:
              raise ConfigFileError(f"{path}: {e}") from e
      return {section: dict(cp[section]) for section in cp.sections()}
  ```
  `configured_league()` drops its own `try`. `_category_labels` catches `ConfigFileError` (not `ValueError`) and re-raises `ConfigFileError(f"{path}: {e}")`.
- `src/athc/fbpro98_play/labels.py`: `from athc.errors import ConfigFileError`; the four `raise ValueError(...)` in `_validate` become `raise ConfigFileError(...)`; the docstring says ConfigFileError.
- The three `RulesFileError` definitions: replace each class with `from athc.errors import RulesFileError`; each package `__init__` keeps the name in its exports.
- `class InvalidGamePlanError(AthcError)`, `InvalidProfileError`, `UnsupportedProfileError`, `InvalidPlayFileError`, `InvalidLg2Error`, `UnsupportedLg2Error`, `InvalidPlayInputError`, `InvalidPDBError`, `SchedulerError`: change the base to `AthcError` (import from `athc.errors`).
- `src/athc/scheduler/config.py`: delete `class ConfigError`, `from athc.errors import ConfigFileError`, rename every use. Same in `src/athc/autocontinue/config.py` and `src/athc/autocontinue/main.py`. Update `src/athc/cli/generate_schedule.py` and `src/athc/cli/autocontinue.py` imports (their handling is rewritten in Task 2 anyway) and every test under `tests/unit/scheduler/` and `tests/integration/test_autocontinue.py` that imports `ConfigError`.
- `src/athc/profile/errors.py`:
  ```python
  """Errors the profile tool raises."""

  from __future__ import annotations

  from athc.errors import AthcError
  from athc.fbpro98_profile import ProfileType


  class ProfileTypeMismatchError(AthcError):
      """The two profiles are not the same side (offense vs defense)."""

      def __init__(
          self, source_type: ProfileType, target_type: ProfileType, message: str | None = None
      ) -> None:
          self.source_type = source_type
          self.target_type = target_type
          super().__init__(
              message
              or f"profile type mismatch: {source_type.name} vs {target_type.name}"
          )
  ```
  `profile/writer.py` imports it and raises `ProfileTypeMismatchError(source.profile_type, target.profile_type, "Profile type mismatch: source is X, target is Y. copy only copies offense -> offense or defense -> defense.")` with today's exact text; `profile/diff.py` raises `ProfileTypeMismatchError(a.profile_type, b.profile_type, f"cannot diff {a.profile_type.name} against {b.profile_type.name}")`; `athc/profile/__init__.py` exports it from `athc.profile.errors`.
- `src/athc/fbpro98_gameplan/reader.py`: find where `read_gameplan` builds the `GamePlan(...)` (after `_parse_j95` / `_parse_s98`, around line 251's `except ValueError`); wrap the construction:
  ```python
  try:
      return GamePlan(...)
  except ValueError as e:
      raise InvalidGamePlanError(f"{e} in {path}") from e
  ```
  (keep the existing `except ValueError` that already wraps a reader-level check; the point is that no `ValueError` escapes `read_gameplan`).

- [ ] **Step 5: Run the suite, lint, format, pyright**

Run the four commands. Expected: all green (the CLI commands still catch the old names only where they still exist; `ValueError` catches in commands still work because nothing they catch changed base yet except the classes above, which they also name explicitly).

- [ ] **Step 6: Tick and commit**

Tick `- [x] errors: ...` in `TODO.md`.

```bash
git add -A
git commit -m "athc: one error family in athc/errors.py; shared config, league and rules errors"
```

---

### Task 2: console on Rich, and every command prints through it

**Files:**
- Modify: `pyproject.toml` via `uv add rich` (then `uv lock` is implicit; `uv sync`)
- Create: `src/athc/log.py` (the logger only; `setup_logging` comes in Task 3)
- Create: `src/athc/console.py`
- Modify: every module under `src/athc/cli/` that calls `click.echo` or `logger.*` (list in Step 4)
- Test: `tests/unit/test_console.py` (new); the CLI tests that break (listed in Step 5)

**Interfaces:**
- Produces `athc.log.logger` (`logging.getLogger("athc")`, `propagate=False`, `NullHandler`, level INFO) and `athc.log.log_path() -> Path`.
- Produces `athc.console.console: AthcConsole` with `print(text="")`, `ok(msg)`, `skip(msg)`, `result(msg)`, `progress(msg)`, `warn(msg)`, `fail(msg)`, `unexpected(what=None)`; `AthcConsole(force_terminal=None, no_color=None)` for tests.

- [ ] **Step 1: Add Rich**

Run: `uv add rich` then `uv sync`. Confirm `rich>=` appears in `[project] dependencies` with the `>=` pin uv writes. Read `.venv/Lib/site-packages/rich/console.py` for `no_color`, `force_terminal`, `FORCE_COLOR` and the `file` property before writing the tests, so the assertions match the installed version.

- [ ] **Step 2: Write the failing console tests**

```python
# tests/unit/test_console.py
"""The one console: streams, labels, prefix-only color, NO_COLOR / FORCE_COLOR,
verbatim text, and the log line each status line writes."""

from __future__ import annotations

import logging

import pytest

from athc.console import AthcConsole
from athc.log import logger


@pytest.fixture
def plain(monkeypatch: pytest.MonkeyPatch) -> AthcConsole:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    return AthcConsole()


def test_results_go_to_stdout_unlogged(plain: AthcConsole, capsys, caplog) -> None:
    handler = logging.handlers.MemoryHandler(100)
    logger.addHandler(handler)
    try:
        plain.print("x.pln: 2 violation(s)")
        plain.print()
    finally:
        logger.removeHandler(handler)
    out, err = capsys.readouterr()
    assert out == "x.pln: 2 violation(s)\n\n" and err == ""
    assert handler.buffer == []


@pytest.mark.parametrize(
    ("call", "stream", "line", "level"),
    [
        ("ok", "out", "OK   x.pln: updated", logging.INFO),
        ("skip", "out", "SKIP x.pln: defense", logging.INFO),
        ("result", "out", "3 file(s) checked", logging.INFO),
        ("progress", "err", "Phase 1: selecting matchups", logging.INFO),
        ("warn", "err", "WARN plays: no .pln files", logging.WARNING),
        ("fail", "err", "FAIL x.pln: not found", logging.ERROR),
    ],
)
def test_status_lines_stream_label_and_log(
    plain: AthcConsole, capsys, call: str, stream: str, line: str, level: int
) -> None:
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    logger.addHandler(handler)
    try:
        getattr(plain, call)(line.split(" ", 1)[1] if line[:4].strip() in ("OK", "SKIP", "WARN", "FAIL") else line)
    finally:
        logger.removeHandler(handler)
    out, err = capsys.readouterr()
    assert (out if stream == "out" else err) == line + "\n"
    assert (err if stream == "out" else out) == ""
    assert [(r.levelno, r.getMessage()) for r in records] == [(level, line)]


def test_text_prints_verbatim(plain: AthcConsole, capsys) -> None:
    plain.print("  [Run Left] :: 'OR45RL01' [1-3] :smile:")
    assert capsys.readouterr().out == "  [Run Left] :: 'OR45RL01' [1-3] :smile:\n"


def test_warn_prints_once_without_a_handler(plain: AthcConsole, capsys) -> None:
    plain.warn("only once")
    assert capsys.readouterr().err == "WARN only once\n"


def test_color_only_on_the_label(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    AthcConsole(force_terminal=True).ok("x.pln: updated")
    out = capsys.readouterr().out
    assert out.startswith("\x1b[") and out.endswith("   x.pln: updated\n")
    assert "\x1b[" not in out.split("OK", 1)[1].split("m", 1)[1]


@pytest.mark.parametrize(("value", "colored"), [("1", False), ("", True)])
def test_no_color(monkeypatch: pytest.MonkeyPatch, capsys, value: str, colored: bool) -> None:
    monkeypatch.setenv("NO_COLOR", value)
    AthcConsole(force_terminal=True).fail("x")
    assert ("\x1b[" in capsys.readouterr().err) is colored


def test_force_color(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    AthcConsole().ok("x")
    assert "\x1b[" in capsys.readouterr().out


def test_piped_output_has_no_color(plain: AthcConsole, capsys) -> None:
    plain.ok("x")
    assert capsys.readouterr().out == "OK   x\n"


def test_unexpected_names_the_log_and_logs_the_traceback(
    plain: AthcConsole, capsys, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    logger.addHandler(handler)
    try:
        try:
            raise RuntimeError("kaboom")
        except RuntimeError:
            plain.unexpected("x.pln")
    finally:
        logger.removeHandler(handler)
    err = capsys.readouterr().err
    assert err == f"FAIL x.pln: unexpected error (see log: {tmp_path / 'athc.log'})\n"
    assert records[0].levelno == logging.ERROR and records[0].exc_info is not None
```

Add `test_unexpected_without_a_subject` asserting `FAIL unexpected error (see log: ...)`. Adjust the `logging.handlers` import (`import logging.handlers`).

- [ ] **Step 3: Write `src/athc/log.py` (logger only) and `src/athc/console.py`**

```python
# src/athc/log.py
"""The run log: the `athc` logger and, from Task 3, the rotating file."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from platformdirs import user_log_path

LOGGER_NAME = "athc"
LOG_FILE = "athc.log"

logger = logging.getLogger(LOGGER_NAME)
# File only: nothing from `logging` reaches the console, and a run without
# `setup_logging()` (a command under CliRunner) never falls back to
# `logging.lastResort`.
logger.propagate = False
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)


def log_dir() -> Path:
    """`%LOCALAPPDATA%\\athc\\Logs`, or `ATHC_LOG_DIR` when set (tests, dev)."""
    if override := os.environ.get("ATHC_LOG_DIR"):
        return Path(override)
    return user_log_path("athc", appauthor=False)


def log_path() -> Path:
    return log_dir() / LOG_FILE
```

```python
# src/athc/console.py
"""The one console. Every line a command shows goes through here: results on
stdout, status and progress where logging.md says, the label word colored and
nothing else, and every status line also written to the run log.
"""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.text import Text

from athc.log import log_path, logger

# Never wrap a line, never restyle numbers or paths, never read `[x]` or
# `:x:` in a message as markup or an emoji.
_OPTIONS: dict[str, Any] = {
    "soft_wrap": True,
    "highlight": False,
    "markup": False,
    "emoji": False,
}
_WIDTH = 5  # label padded to this: "OK   ", "SKIP ", "WARN ", "FAIL "


class AthcConsole:
    """One Console for stdout, one for stderr. Rich turns color on for a
    terminal and off when piped; `NO_COLOR` forces it off, `FORCE_COLOR` on."""

    def __init__(
        self, *, force_terminal: bool | None = None, no_color: bool | None = None
    ) -> None:
        self.out = Console(force_terminal=force_terminal, no_color=no_color, **_OPTIONS)
        self.err = Console(
            stderr=True, force_terminal=force_terminal, no_color=no_color, **_OPTIONS
        )

    def print(self, text: str = "") -> None:
        """A result line: the command's product. stdout, never logged."""
        self.out.print(text)

    def ok(self, message: str) -> None:
        self._status(self.out, "OK", "green", message, logging.INFO)

    def skip(self, message: str) -> None:
        self._status(self.out, "SKIP", "cyan", message, logging.INFO)

    def result(self, message: str) -> None:
        """A tally, or a headline for an item with findings. stdout, logged."""
        self.out.print(message)
        logger.info("%s", message)

    def progress(self, message: str) -> None:
        self.err.print(message)
        logger.info("%s", message)

    def warn(self, message: str) -> None:
        self._status(self.err, "WARN", "yellow", message, logging.WARNING)

    def fail(self, message: str) -> None:
        self._status(self.err, "FAIL", "red", message, logging.ERROR)

    def unexpected(self, what: str | None = None) -> None:
        """A bug. Call it inside the `except` so the traceback reaches the log."""
        subject = f"{what}: " if what else ""
        message = f"{subject}unexpected error (see log: {log_path()})"
        self._status(self.err, "FAIL", "red", message, logging.ERROR, exc_info=True)

    def _status(
        self,
        target: Console,
        label: str,
        color: str,
        message: str,
        level: int,
        *,
        exc_info: bool = False,
    ) -> None:
        target.print(Text.assemble((label, color), label.ljust(_WIDTH)[len(label):], message))
        logger.log(level, "%s%s", label.ljust(_WIDTH), message, exc_info=exc_info)


console = AthcConsole()
```

Run `uv run pytest tests/unit/test_console.py -q`; fix against the installed Rich until green.

- [ ] **Step 4: Route every command's lines through the console**

Every `logging.basicConfig(...)` line, every `logger = logging.getLogger(__name__)`, every `import logging` that no longer has a use, and every `click.echo` go. The error *flow* (what is caught, `ctx.exit` codes) stays as today in this task; only the printing changes. Mapping, per module:

| Module | Today | Now |
|---|---|---|
| `cli/gameplan/_common.py` | `resolve_rules` / `build_pool` / `emit_play_list` take `prog`, `logger`; `logger.error(prog: ...)`; `click.echo` | drop `prog` / `logger` parameters; `console.fail(line)` (no prefix); `emit_play_list` prints with `console.print` and ends with `console.ok(f"{out_path}: {count} {noun} play(s)")` |
| `cli/profile/_common.py` | same for `resolve_rules` | same |
| `cli/gameplan/check.py`, `cli/profile/check.py` | `click.echo(line)` per file (one multi-line string); blank + tally | per file: clean → `console.ok(f"{path}: {summary}")`; with violations → `console.result(f"{path}: {n} violation(s) ({summary})")` then `console.print(f"  {detail}")` per violation; unreadable → `console.fail(f"{path}: {error}")`; tally → `console.print()` then `console.result(f"{total} file(s) checked, {files_with_violations} with violations, {io_errors} failed")`. `check_file` returns `(count, lines: list[str])` so the golden tests still compare the report text; the command prints the first line through `result` and the rest through `print`. |
| `cli/check_ppp.py` | `click.echo` of report lines; `logger.error(PROG: ...)`; `_log_once` | the same per-line scheme as the checkers (`ok` / `result` + `print` / `fail`); every `logger.error("%s: %s", PROG, x)` → `console.fail(x)`; side mismatch → `console.fail(f"{path}: profile is X but gameplan is Y")` (no `ERROR:`); "no pairs" → `console.warn(f"{raw}: no profile and gameplan pairs from the league file in {scope}")` |
| `cli/gameplan/find_play.py` | `click.echo` hits / misses / summary; `ERROR:` line | hits and misses → `console.result(...)`; unreadable → `console.fail(f"{file}: {error}")`; blank + per-play summary → `console.result(f"'{play}': found {n} instance(s) in {m} gameplan(s)")` |
| `cli/gameplan/list_normals.py`, `list_specials.py` | `logger.error` → exit 1 | `console.fail(str(error))`, same exit for now |
| `cli/gameplan/replace_play.py` | `click.echo` lines; `failed (...)` line | updated → `console.ok(line)` per formatted line (`'OLD' (RL) replaced with 'NEW' (RM) [1-1]` text unchanged); failed → `console.fail(f"{path}: {error}")`; single-file miss → `console.result(f"{file}: '{play}' not found")`; tally → `console.result(f"'{play}' -> '{replacement}': replaced {n} instance(s) in {m} gameplan(s), {failed} failed")` |
| `cli/gameplan/set_normals.py` | `logger.error`; `click.echo("Updated ...")` | errors → `console.fail`; success → `console.ok(f"{gameplan_path}: {count} normal play(s)")` unless `-q` |
| `cli/gameplan/set_specials.py` | `click.echo(f"{path}: {status} ({message})")`; silent skip | updated → `console.ok(f"{path}: updated ({message})")`; failed → `console.fail(f"{path}: {message}")`; wrong side → `console.skip(f"{path}: {other side} gameplan")`; tally → `console.result(f"{len(files)} file(s) processed, {updated} updated, {skipped} skipped, {failed} failed")` |
| `cli/profile/copy.py` | as set-specials; source itself silently skipped | `ok` / `fail` / `skip(f"{path}: {side} profile")` and `skip(f"{path}: the source")`; same tally shape |
| `cli/profile/diff.py` | `click.echo(render(...))`; `logger.error` | report → `console.print(render(...))`; `-o` → `console.ok(f"{output}: written")`; errors → `console.fail` |
| `cli/playpool/check.py` | `click.echo` issues + tally; pool logger silencing | issues → `console.print(message)`; blank; tally → `console.result(f"{plays} play(s) checked in '{play_dir}', {n} issue(s)")`; the `pool_logger` block goes (the library stops logging in Task 6; until then its warnings go to the NullHandler) |
| `cli/convert_pdb.py` | `logger.error` | `console.fail`; after a successful run `console.ok(f"{outputfile}: written")` (the play count comes in Task 6) |
| `cli/generate_schedule.py` | `logger.error` | `console.fail`; `missing ortools -- reinstall athc` text |
| `cli/autocontinue.py` | `logger.error`; animated `click.echo` goodbye with `time.sleep` | `console.fail`; Ctrl-C → `console.result("Shutting down AutoContinue")`, no animation, no `time` import |
| `cli/config/path.py` | `click.echo(path)` | `console.print(str(config_file()))` |
| `cli/config/set.py` | `click.echo(f"Set ...")` | `console.result(f"Set {key} = {value}")` |
| `cli/__init__.py` `main()` | `basicConfig` + `logger.error` | `console.unexpected()` inside the `except` (keep `ATHC_DEBUG` until Task 4) |

`build_pool` also prints `console.warn(issue)` for every `pool.issues` entry and, when rules were given, for every `rule_warnings(pool, rules)` line, in that order, before returning the pool (the design: "WARN per play-pool issue and rules-file notice, before the files"); `playpool check` does not use `build_pool` any more: it calls `read_play_pool(play_dir, labels=labels)` itself after checking `play_dir.is_dir()` (`console.fail(f"{play_dir}: not a directory")`, exit 2).

- [ ] **Step 5: Repair the tests the printing change breaks**

Run `uv run pytest -q`. Expected failures: tests asserting `caplog` (the logger no longer propagates) and tests asserting the old line text (`: OK (`, `ERROR:`, `Updated `, `Wrote `, `updated (`, `failed (`, `across`, `Shutting down` timing). For each: assert `result.stderr` for `FAIL` / `WARN` lines and `result.stdout` for the rest, with the new text; do not change exit-code assertions in this task. The golden files under `tests/integration/expected/*.report.txt` keep their text because the violation headline and detail lines are unchanged; if a golden differs, the code is wrong, not the golden.

Files touched: `test_autocontinue.py`, `test_check_ppp.py`, `test_cli_root.py`, `test_config.py`, `test_config_set.py`, `test_convert_pdb.py`, `test_gameplan_check.py`, `test_gameplan_find_play.py`, `test_gameplan_list.py`, `test_gameplan_replace_play.py`, `test_gameplan_set_normals.py`, `test_gameplan_set_specials.py`, `test_playpool_check.py`, `test_profile_check.py`, `test_profile_copy.py`, `test_profile_diff.py`, `tests/unit/scheduler/test_cli.py`, `tests/unit/test_cli_main.py`.

- [ ] **Step 6: Run the four commands; tick; commit**

Tick `- [x] console: ...` in `TODO.md`.

```bash
git add -A
git commit -m "athc: one Rich console prints every command line; click.echo and basicConfig gone"
```

---

### Task 3: the run log

**Files:**
- Modify: `src/athc/log.py` (`setup_logging`)
- Modify: `src/athc/cli/__init__.py` (`main()` sets it up and writes the start and end lines; the rest of `main()` is Task 4)
- Modify: `tests/conftest.py` (autouse `log_dir` fixture setting `ATHC_LOG_DIR`)
- Test: `tests/unit/test_log.py` (new)

**Interfaces:**
- Produces `athc.log.setup_logging() -> Path`: creates the folder, installs one `RotatingFileHandler` (replacing and closing a previous one, so repeated calls in tests never stack handlers), returns the log path.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_log.py
"""The run log: where it goes, what a line looks like, rotation, and that
`setup_logging` is safe to call again."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from athc import log as log_module
from athc.log import log_path, logger, setup_logging


def test_log_dir_defaults_to_the_user_log_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATHC_LOG_DIR", raising=False)
    path = log_path()
    assert path.name == "athc.log" and path.parent.name == "Logs" and path.parent.parent.name == "athc"


def test_athc_log_dir_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path / "logs"))
    assert log_path() == tmp_path / "logs" / "athc.log"


def test_setup_creates_the_folder_and_writes_time_level_message(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path / "a" / "b"))
    path = setup_logging()
    logger.info("hello %s", "there")
    line = path.read_text(encoding="utf-8").splitlines()[-1]
    date, time, level, *message = line.split()
    assert level == "INFO" and " ".join(message) == "hello there"
    assert len(date) == 10 and len(time) == 8


def test_setup_twice_keeps_one_file_handler(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    setup_logging()
    setup_logging()
    assert sum(isinstance(h, RotatingFileHandler) for h in logger.handlers) == 1


def test_rotation_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    setup_logging()
    handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
    assert handler.maxBytes == 1_000_000 and handler.backupCount == 5
    assert handler.encoding == "utf-8"


def test_nothing_reaches_the_root_logger(tmp_path: Path, monkeypatch, caplog) -> None:
    monkeypatch.setenv("ATHC_LOG_DIR", str(tmp_path))
    setup_logging()
    with caplog.at_level(logging.INFO):
        logger.warning("quiet")
    assert caplog.records == []
```

- [ ] **Step 2: Implement `setup_logging`**

```python
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5
_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> Path:
    """Open the rotating run log; called once per run by `main()`. A previous
    file handler is closed and replaced, so a test may call it again."""
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    logger.addHandler(handler)
    return path
```

`tests/conftest.py` gets, next to `config_dir`:

```python
@pytest.fixture(autouse=True)
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep every run log in the test's temp dir, never the machine's."""
    d = tmp_path / "athc-logs"
    monkeypatch.setenv("ATHC_LOG_DIR", str(d))
    return d
```

The subprocess packaging tests pass `ATHC_LOG_DIR` in the child `env` the way they pass `ATHC_CONFIG_DIR`.

- [ ] **Step 3: Wire `main()` (interim)**

In `src/athc/cli/__init__.py`, `main()` calls `setup_logging()` first, logs `athc <version> <argv[1:]>`, runs `cli()` as today, and logs `exit <code>` (catch `SystemExit`, re-raise after logging). Task 4 replaces this body.

- [ ] **Step 4: Run the four commands; tick; commit**

Tick `- [x] run log: ...`.

```bash
git add -A
git commit -m "athc: rotating run log under the per-user log folder, set up once in main()"
```

---

### Task 4: `main()`, the one place

**Files:**
- Modify: `src/athc/cli/__init__.py` (a `_run` mixin on `AthcCommand` and `AthcGroup`; `main()`; `ATHC_DEBUG` gone)
- Modify: `src/athc/__main__.py` (calls `main()`)
- Test: `tests/unit/test_cli_main.py` (rewrite)

**Interfaces:**
- Produces: `athc.cli.main() -> None` (the console script); every `AthcCommand` / `AthcGroup` `.main(...)` runs Click with `standalone_mode=False` and handles what comes out, so `CliRunner.invoke(cli, ...)` and `CliRunner.invoke(<leaf command>, ...)` get the same lines and codes as the real `athc` process. That is the design's `main()` body, placed where both the entry point and the tests reach it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_cli_main.py
"""The one place errors become a line, a log entry and an exit code."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from athc.cli import CONTEXT_SETTINGS, AthcCommand, cli
from athc.errors import AthcError


def _command(raiser):
    @click.command(cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
    def cmd() -> None:
        raiser()

    return cmd


def _log(log_dir: Path) -> str:
    return (log_dir / "athc.log").read_text(encoding="utf-8")


def test_athc_error_is_a_fail_line_exit_2(log_dir: Path) -> None:
    def _raise():
        raise AthcError("league 'NOPE' not found")

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 2
    assert result.stderr == "FAIL league 'NOPE' not found\n" and result.stdout == ""
    assert "ERROR FAIL league 'NOPE' not found" in _log(log_dir)
    assert _log(log_dir).rstrip().endswith("INFO exit 2")


def test_os_error_is_a_fail_line_exit_2() -> None:
    def _raise():
        raise FileNotFoundError(2, "No such file or directory", "x.pln")

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 2 and result.stderr.startswith("FAIL [Errno 2]")


def test_bug_is_unexpected_with_traceback_in_the_log(log_dir: Path) -> None:
    def _raise():
        raise RuntimeError("kaboom")

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL unexpected error (see log: {log_dir / 'athc.log'})\n"
    assert "RuntimeError: kaboom" in _log(log_dir)


def test_ctrl_c_is_interrupted_130(log_dir: Path) -> None:
    def _raise():
        raise KeyboardInterrupt

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 130
    assert result.stderr.endswith("FAIL interrupted\n")
    assert "INFO exit 130" in _log(log_dir)


def test_usage_error_keeps_clicks_text(log_dir: Path) -> None:
    result = CliRunner().invoke(cli, ["gameplan", "check", "--nope"])
    assert result.exit_code == 2
    assert "Usage:" in result.stderr and "No such option" in result.stderr
    assert "ERROR No such option" in _log(log_dir)


def test_findings_code_passes_through(log_dir: Path) -> None:
    @click.command(cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
    @click.pass_context
    def cmd(ctx: click.Context) -> None:
        ctx.exit(1)

    assert CliRunner().invoke(cmd, []).exit_code == 1
    assert "INFO exit 1" in _log(log_dir)


def test_start_line_names_the_version_and_args(log_dir: Path) -> None:
    CliRunner().invoke(cli, ["--version"])
    first = _log(log_dir).splitlines()[0]
    assert " INFO athc " in first and first.endswith("--version")


def test_athc_debug_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHC_DEBUG", "1")

    def _raise():
        raise RuntimeError("kaboom")

    assert CliRunner().invoke(_command(_raise), []).exit_code == 2


def test_python_m_athc_goes_through_main(log_dir: Path) -> None:
    import runpy

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("athc", run_name="__main__", alter_sys=True)
    assert exc.value.code == 2  # bare `athc`: Click's no-args help is a usage error
```

- [ ] **Step 2: Implement**

```python
# in src/athc/cli/__init__.py
from importlib.metadata import entry_points, version

from athc.console import console
from athc.errors import AthcError
from athc.log import logger, setup_logging


class _OnePlace:
    """Runs Click in non-standalone mode and turns whatever comes out into a
    line, a log entry and an exit code: the design's `main()`, on the command
    classes so `CliRunner` runs exercise it too."""

    def main(  # type: ignore[override]
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        **extra: Any,
    ) -> NoReturn:
        setup_logging()
        argv = list(args) if args is not None else sys.argv[1:]
        logger.info("athc %s %s", version("athc"), " ".join(argv))
        try:
            returned = super().main(  # type: ignore[misc]
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                **extra,
            )
            code = returned if isinstance(returned, int) else 0
        except click.ClickException as error:  # usage: Click's own text, 2
            error.show()
            logger.error("%s", error.format_message())
            code = error.exit_code
        except click.Abort:  # Ctrl-C
            console.fail("interrupted")
            code = 130
        except (AthcError, OSError) as error:  # an expected failure
            console.fail(str(error))
            code = 2
        except Exception:  # a bug
            console.unexpected()
            code = 2
        logger.info("exit %d", code)
        sys.exit(code)


class AthcCommand(_OnePlace, click.Command): ...
class CommandGroup(_OnePlace, click.Group): ...   # AthcGroup inherits it


def main() -> None:
    """The `athc` console script."""
    cli()
```

`src/athc/__main__.py`: `from athc.cli import main` / `main()`. Remove `os`, `logging` imports and the `ATHC_DEBUG` docstring. Note `KeyboardInterrupt` reaches us as `click.Abort` (Click converts it and echoes a blank line to stderr first).

- [ ] **Step 3: Run the four commands; tick; commit**

Tick `- [x] main(): ...`.

```bash
git add -A
git commit -m "athc: main() runs Click non-standalone and is the one place errors become lines and exit codes"
```

---

### Task 5: exit codes and the batch loop in every command

**Files:**
- Modify: every module under `src/athc/cli/` (error flow), `src/athc/cli/gameplan/_common.py` and `src/athc/cli/profile/_common.py` (`collect_files`)
- Test: the integration test file of each command (exit-code and line assertions), plus the Review Focus tests

**Interfaces:**
- `collect_files(paths, *, suffix, recursive) -> Collected` with
  ```python
  @dataclass(frozen=True, slots=True)
  class Collected:
      files: list[Path]
      errors: list[str]    # "<raw>: not found", "<raw>: not a .pln file"
      warnings: list[str]  # "<raw>: no .pln files", "<raw>: no .pln files match"
  ```
  A command prints each error with `console.fail` and counts it as a failed item; each warning with `console.warn`.

- [ ] **Step 1: Write the failing tests (per command, in its test file)**

For every command, one test per row that changed. The assertions use `result.stdout`, `result.stderr` and `result.exit_code`. The rows:

| Command | Case | stdout / stderr | exit |
|---|---|---|---|
| gameplan check, profile check, check-ppp | empty directory | stderr `WARN <dir>: no .pln files`; stdout tally `0 file(s) checked, 0 with violations, 0 failed` | 0 |
| gameplan check | missing path | stderr `FAIL <path>: not found`; tally `... 1 failed` | 2 |
| gameplan check | one of two files unreadable | `FAIL <bad>: ...`, the good file's line, tally | 2 |
| gameplan check | one of two files makes the reader raise `RuntimeError` (monkeypatch `athc.cli.gameplan.check.read_gameplan`) | `FAIL <bad>: unexpected error (see log: ...)`, the other file checked, tally | 2 |
| gameplan check | no league | stderr `FAIL no league selected...`; stdout empty | 2 |
| gameplan check | no rules | stderr `FAIL no rules configured - nothing to check. Add gameplan.toml to the league folder.` | 2 |
| find-play | empty directory | `WARN`; tally | 1 |
| find-play | missing path | `FAIL <path>: not found` | 2 |
| list-normals, list-specials | missing gameplan | stderr starts `FAIL [Errno 2]`; stdout empty | 2 |
| list-normals | no league | `FAIL no league selected` | 2 |
| replace-play | replacement not in pool | `FAIL replacement play 'X' not found in the play pool` | 2 |
| replace-play | malformed file in a directory | `FAIL <file>: ...`, tally `... 1 failed` | 2 |
| replace-play | directory, no hits | tally `replaced 0 instance(s) in 0 gameplan(s), 0 failed` | 1 |
| replace-play | single file, wrong-side replacement | `FAIL <file>: <model message>` | 2 |
| set-normals | too many plays | `FAIL input has 65 play(s), max is 64` | 2 |
| set-normals | special-teams play | `FAIL <input> line 1: 'X' is a special teams play; use set-specials`, file untouched | 2 |
| set-normals | missing play | `FAIL <input> line 1: ...`, file untouched | 2 |
| set-normals | missing .pln / missing play_path | `FAIL ...` | 2 |
| set-specials | normal play, duplicate, > 10 | `FAIL ...` | 2 |
| set-specials | one of two files fails | `OK` + `FAIL` + tally | 2 |
| set-specials | wrong side | `SKIP <file>: defense gameplan`; tally `... 1 skipped` | 0 |
| profile copy | failed target in a directory | `OK` + `FAIL` + tally | 2 |
| profile copy | wrong-side single target | `SKIP <file>: defense profile`; tally | 0 |
| profile copy | missing source | `FAIL [Errno 2] ...` | 2 |
| profile diff | cross side | `FAIL cannot diff OFFENSE against DEFENSE` | 2 |
| profile diff | `-o report.json` | Click's usage error on stderr | 2 |
| profile diff | write failure | `FAIL [Errno ...]` | 2 |
| playpool check | not a directory | `FAIL <dir>: not a directory` | 2 |
| check-ppp | side mismatch, pair mode | `FAIL <profile>: profile is offense but gameplan is defense`; no summary | 2 |
| check-ppp | side mismatch in a directory | that pair's `FAIL`, the other pair's lines, tally | 2 |
| check-ppp | no league | `FAIL no league selected` once; nothing on stdout | 2 |
| check-ppp | one file / wrong extension / third path | `FAIL <path>: not a directory; pass one profile and one gameplan, or a directory` etc. | 2 |
| convert-pdb | missing pdb | `FAIL <path>: not found` | 2 |
| convert-pdb | play path not a directory, missing pdbtoexcel.toml, invalid content, output folder is a file | `FAIL ...` | 2 |
| generate-schedule | config error, scheduler error, missing ortools | `FAIL ...` / `FAIL missing ortools -- reinstall athc` | 2 |
| autocontinue | no config, missing pyautogui | `FAIL ...` / `FAIL missing pyautogui -- reinstall athc` | 2 |
| autocontinue | Ctrl-C from the loop | stdout `Shutting down AutoContinue` | 0 |
| config set | malformed athc.ini | `FAIL <athc.ini>: ...` (no `Usage:`) | 2 |

- [ ] **Step 2: Implement, command by command**

The shape of a batch command (from the spec):

```python
cfg = load_config(league)                       # propagates
rules = load_rules_or_raise(cfg)                # ConfigFileError("no rules configured ...")
pool = build_pool(cfg.play_path, cfg.playpool_rules, cfg.categories)   # warns issues; ConfigFileError when not a dir
collected = collect_files(paths, suffix=".pln", recursive=recursive)
for line in collected.errors:
    console.fail(line)
for line in collected.warnings:
    console.warn(line)
findings = failed = len(collected.errors)  # errors count as failed items
for file in collected.files:
    try:
        plan = read_gameplan(file)
    except (AthcError, OSError) as error:
        console.fail(f"{file}: {error}")
        failed += 1
        continue
    except Exception:
        console.unexpected(str(file))
        failed += 1
        continue
    ...
console.print()
console.result(f"{len(collected.files)} file(s) checked, {findings} with violations, {failed} failed")
ctx.exit(2 if failed else 1 if findings else 0)
```

Per command (what changes beyond the shape):
- `_common.resolve_rules` → `load_rules_or_raise(rule_files, labels)`: no files → `raise ConfigFileError("no rules configured - nothing to check. Add gameplan.toml to the league folder.")`; otherwise return `load_rules(...)` (RulesFileError / OSError propagate). Profile: same with `profile.toml`.
- `_common.build_pool(play_path, playpool_rules, labels) -> PlayPool`: not a directory → `raise ConfigFileError(f"play path '{play_path}' is not a directory")`; warns as in Task 2.
- `collect_files`: the `Collected` dataclass; messages `f"{raw}: not found"`, `f"{raw}: not a {suffix} file"`, `f"{raw}: no {suffix} files"` (directory or tree), `f"{raw}: no {suffix} files match"` (glob).
- `gameplan check` / `profile check`: the shape; `check_file` loses its `try` (the loop catches).
- `find-play`: no league; the shape; `ctx.exit(2 if failed else 0 if any hit else 1)`; empty directory → warn, tally, exit 1.
- `list-normals` / `list-specials`: nothing caught; `emit_play_list` returns None.
- `replace-play`: `record is None` → `raise AthcError(f"replacement play '{replacement}' not found in the play pool")`; `replace_in_gameplan` wraps the model's `ValueError` into `AthcError(str(error))`; `_replace_one` goes, the loop does the per-item catch around read + replace + write; exit `2 if failed else 1 if replaced_total == 0 else 0`.
- `set-normals`: input read (`OSError` propagates); `len(lines) > 64` → `raise AthcError(f"input has {n} play(s), max is {NORMAL_COUNT}")`; special-teams pre-check → `console.fail(f"{input_path} line {i}: '{name}' is a special teams play; use set-specials")` per line then `ctx.exit(2)`; `InvalidPlayInputError` → `console.fail(f"{input_path} {violation}")` per violation (the writer's violation strings become `line {n}: {why}`: `line 3: 'X' not found in the play pool (slot 1-3)`, `line 3: 'X' is a special teams play, cannot add to normal slots`, `line 3: 'X' is a defensive play but gameplan is offensive`, and the special-list ones `line 3: duplicate special play 'X', already used for special category N`, `line 3: 'X' not found in the play pool`, `line 3: 'X' is not a special teams play`, `line 3: 'X' is a defensive special play but gameplan is offensive`, `line 3: 'X' is in special category N, which has no custom slot`, `line 3: 'X' targets special category N, already filled by another play`) then `ctx.exit(2)`; the gameplan is read before the input is applied and written only after; `OK` line unless `-q`. Update `tests/unit/gameplan/test_writer.py` only where it pins the old wording.
- `set-specials`: input validation errors → `console.fail(f"{input_path} {err}")` per line, `ctx.exit(2)`; the shape with `skip` for the wrong side; exit `2 if failed else 0`.
- `profile copy`: `UsageError` stays; source read propagates; the shape with two `skip` reasons; exit `2 if failed else 0`.
- `profile diff`: `_infer_format` None → `raise click.BadParameter("format from the extension: use .txt or .csv", param_hint="--output")`; reads propagate; `diff_profiles` raises `ProfileTypeMismatchError` (propagates); the write propagates; exit `1 if differences else 0`.
- `playpool check`: `LeagueError` when `play_dir` given and no `--league` is still swallowed (a given folder needs no league); everything else propagates; `play_dir.is_dir()` else `raise AthcError(f"{play_dir}: not a directory")`; exit `1 if pool.issues else 0`.
- `check-ppp`: `load_setup` raises (the first setup problem stops the run; `_log_once` and `logged` go); `sort_inputs` errors → `console.fail` each, `ctx.exit(2)`; pair mode side mismatch → `console.fail(...)`, `ctx.exit(2)`; directory: `load_lg2` raises; no pairs → `console.warn`, tally, exit 0; per pair the per-item catch; `summarize` returns the code from `failed` / `findings`.
- `convert-pdb`: a named input that is not a file → `raise AthcError(f"{path}: not found")`; nothing else caught (`XlsxWriterException` is a bug: unexpected).
- `generate-schedule`: `ImportError` → `raise AthcError(f"missing {error.name or 'ortools'} -- reinstall athc") from error`; nothing else caught.
- `autocontinue`: `ImportError` → `AthcError(f"missing {name or 'pyautogui'} -- reinstall athc")`; `KeyboardInterrupt` → `console.result("Shutting down AutoContinue")`; nothing else caught.
- `config set`: the `ConfigFileError` → `UsageError` rewrap goes.

- [ ] **Step 3: Run the four commands; tick; commit**

Tick `- [x] exit codes: ...`.

```bash
git add -A
git commit -m "athc: 0 / 1 findings / 2 error in every command; a batch catches per item and the worst outcome wins"
```

---

### Task 6: library warnings and progress as values and callbacks

**Files:**
- Modify: `src/athc/playpool/reader.py` (no `logging`; `_warn` only appends)
- Modify: `src/athc/pdbtoexcel/pdb.py` (`PDB.warnings: list[str]`), `src/athc/pdbtoexcel/workbook_creator.py` (`warnings`, `progress`), `src/athc/pdbtoexcel/main.py` (`ConversionResult`, `progress`)
- Modify: `src/athc/scheduler/main.py` (`GeneratedSchedule`, `progress`), `src/athc/scheduler/schedulers/scheduler.py` (`progress`)
- Modify: `src/athc/autocontinue/main.py` (`progress`, `warn`)
- Modify: `src/athc/cli/convert_pdb.py`, `src/athc/cli/generate_schedule.py`, `src/athc/cli/autocontinue.py`
- Test: `tests/unit/playpool/test_reader.py`, `tests/unit/pdbtoexcel/test_workbook_creation.py`, `tests/unit/scheduler/test_cli.py`, `tests/integration/test_convert_pdb.py`, `tests/integration/test_autocontinue.py`

**Interfaces:**
- `convert_pdb(..., progress: Callable[[str], None] | None = None) -> ConversionResult` with `ConversionResult(plays: int, warnings: tuple[str, ...])` (frozen, slots); `PdbWorkbookCreator.warnings: list[str]`; `create_workbook(filename, perform_calculations, calculate_totals, *, progress=None) -> int` (play rows written).
- `athc.scheduler.main.generate_schedule(..., progress: Callable[[str], None] | None = None) -> GeneratedSchedule` with `GeneratedSchedule(result: SchedulerResult, seed: int, files: tuple[Path, ...])`; `athc.scheduler.schedulers.scheduler.generate_schedule(..., progress=None)`.
- `auto_continue(hot_corner=None, *, progress: Callable[[str], None] | None = None, warn: Callable[[str], None] | None = None) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/playpool/test_reader.py (add)
def test_reader_never_logs(tmp_pool, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        read_play_pool(tmp_pool)
    assert caplog.records == []

# tests/unit/pdbtoexcel/test_workbook_creation.py (add)
def test_warnings_are_returned_not_logged(creator_with_missing_play, tmp_path, caplog) -> None:
    said: list[str] = []
    with caplog.at_level(logging.DEBUG):
        rows = creator.create_workbook(tmp_path / "w.xlsx", True, True, progress=said.append)
    assert caplog.records == []
    assert said == [f"Creating '{tmp_path / 'w.xlsx'}'"]
    assert any("Play file not found for play" in w for w in creator.warnings)
    assert rows >= 0

# tests/integration/test_convert_pdb.py (add)
def test_progress_on_stderr_warnings_and_ok_line(runner, league, tmp_path) -> None:
    out = tmp_path / "w.xlsx"
    result = runner.invoke(convert_pdb, [str(PDB_FILE), str(out)])
    assert result.exit_code == 0
    assert result.stderr.splitlines()[0] == f"Creating '{out}'"
    assert all(l.startswith("WARN ") for l in result.stderr.splitlines()[1:])
    assert result.stdout == f"OK   {out}: {N} play(s)\n"   # N from the golden
    assert "WARN" not in result.stdout

# tests/unit/scheduler/test_cli.py (add, run_generate stubbed to return a GeneratedSchedule)
def test_prints_files_and_result_line(runner, ...) -> None:
    ...
    assert result.stdout == "OK   schedule_2048_x.txt\nOK   schedule_2048_x.html\nOK   schedule_2048_x_report.html\nGenerated 128 games (seed 7)\n"

# tests/integration/test_autocontinue.py (add)
def test_loop_status_goes_to_stderr_through_the_callbacks(runner, valid, monkeypatch) -> None:
    def fake(hot_corner=None, *, progress, warn):
        progress("AutoContinue is RUNNING. Press CTRL-C to exit.")
        warn("Config reload failed; keeping previous settings. x")
        raise KeyboardInterrupt
    monkeypatch.setattr("athc.autocontinue.main.auto_continue", fake)
    result = runner.invoke(autocontinue, [])
    assert result.exit_code == 0
    assert result.stderr == "AutoContinue is RUNNING. Press CTRL-C to exit.\nWARN Config reload failed; keeping previous settings. x\n"
    assert result.stdout == "Shutting down AutoContinue\n"
```

- [ ] **Step 2: Implement**

- `playpool/reader.py`: delete `import logging`, `logger`, the `logger.info("Processing ...")` line; `_warn` keeps only `pool.issues.append(message)`.
- `pdbtoexcel/pdb.py`: `self.warnings: list[str] = []` in `PDB.__init__` before reading; the two `logger.warning` become `self.warnings.append(f"Skipping invalid play data at {offset:#x}")` / tendency; `logging` import and `logger` go.
- `pdbtoexcel/workbook_creator.py`: `self.warnings: list[str] = []` in `__init__`; `from_config` builds the creator then `creator.warnings.extend(f"{config.playpool_rules.name}: {m}" for m in rule_warnings(...))` and `creator.warnings.extend(play_pool.issues)` and `creator.warnings.extend(pdb.warnings)`; `create_workbook(..., *, progress=None) -> int`: `say = progress or (lambda _: None)`; `say(f"Creating '{filename}'")`; stale deleted play → `self.warnings.append(f"'{name}' is listed in [deleted_plays] but is in the play pool; its stats are skipped")`; "Skipping deleted play" line goes (deleted plays skip quietly); play not found → `self.warnings.append(f"Play file not found for play '{play_name}'")`; "Conversion complete" goes; return `len(resolved_plays)`.
- `pdbtoexcel/main.py`:
  ```python
  @dataclass(frozen=True, slots=True)
  class ConversionResult:
      plays: int
      warnings: tuple[str, ...]

  def convert_pdb(..., progress: Callable[[str], None] | None = None) -> ConversionResult:
      ...
      plays = creator.create_workbook(output_path, not skip_calcs, calculate_totals=True, progress=progress)
      return ConversionResult(plays, tuple(creator.warnings))
  ```
  The `play path is not a directory` check raises `ConfigFileError` instead of `OSError`.
- `cli/convert_pdb.py`: `result = run_conversion(..., progress=console.progress)`; `for w in result.warnings: console.warn(w)`; `console.ok(f"{outputfile}: {result.plays} play(s)")`.
- `scheduler/schedulers/scheduler.py`: `generate_schedule(league, seed=0, scheduler_config=None, *, season, progress=None)`; `say = progress or (lambda _: None)`; the two `logger.info` → `say("Phase 1: selecting matchups")`, `say("Phase 2: placing games into weeks. This usually takes several minutes and can take 30 minutes or more.")`; `logging` goes.
- `scheduler/main.py`: `GeneratedSchedule` dataclass; `generate_schedule(..., progress=None) -> GeneratedSchedule`; `say(f"Generating the {season} schedule")` replaces the first `logger.info`; the final `logger.info` goes; return `GeneratedSchedule(result, seed, (txt_path, html_path, report_path))`; pass `progress` to the solver.
- `cli/generate_schedule.py`: `generated = run_generate(..., progress=console.progress)`; `for path in generated.files: console.ok(str(path))`; `console.result(f"Generated {len(generated.result.schedule.games)} games (seed {generated.seed})")`.
- `autocontinue/main.py`: `auto_continue(hot_corner=None, *, progress=None, warn=None)`; `say` / `complain` defaults; the five `logger.info` → `say(...)`, the two `logger.warning` → `complain(...)`; `_apply_hot_corner` and `_log_config_changes` take `say`; `logging` goes.
- `cli/autocontinue.py`: `auto_continue(hot_corner=hot_corner, progress=console.progress, warn=console.warn)`.

After this task `grep -rn "logging" src/athc` finds only `athc/log.py` and `athc/console.py`.

- [ ] **Step 3: Run the four commands; tick; commit**

Tick `- [x] library warnings and progress: ...`.

```bash
git add -A
git commit -m "athc: libraries return warnings and take a progress callback; no library logs"
```

---

### Task 7: tests assert stdout and stderr apart

**Files:**
- Modify: every file under `tests/integration/` and `tests/unit/scheduler/test_cli.py`
- Modify: `tests/integration/README.md` (the exit column and the lines in each matrix)

- [ ] **Step 1: Replace every `result.output` and every `caplog` use**

`grep -rn "result.output\|caplog" tests` lists them. Each becomes an assertion on `result.stdout` or `result.stderr` by the stream the line belongs to, with the exact line where the test pins text (`== "...\n"` for a single-line stream, `in` for a line among many). A test that checked "nothing logged" now asserts `result.stderr == ""`. `caplog` disappears from the CLI tests entirely.

- [ ] **Step 2: Subprocess packaging tests**

Each `test_entry_point_subprocess` passes `ATHC_LOG_DIR` in `env`, asserts `stdout` / `stderr` apart, and one of them (`check-ppp`'s `test_entry_point_errors_go_to_stderr`) also asserts the log file holds the `FAIL` line and the `exit 2` end line.

- [ ] **Step 3: The README matrices**

`tests/integration/README.md`: each row's Expected column names the stream and the exact line; the preamble's exit legend becomes `0 done / 1 findings / 2 error / 130 Ctrl-C`.

- [ ] **Step 4: Run the four commands; tick; commit**

Tick `- [x] tests: ...`.

```bash
git add -A
git commit -m "athc: CLI tests assert stdout and stderr apart; console, NO_COLOR and run-log tests"
```

---

### Task 8: docs

**Files:**
- Modify: `docs/design/architecture.md` (`Cross-cutting conventions`: CLI bullet on `ImportError`, `Exit codes`, `Output streams` rewritten as `Console, run log and errors`; `Running from source` gains `ATHC_LOG_DIR`; `Project layout` lists `errors.py`, `console.py`, `log.py`)
- Modify: `docs/gameplan/README.md`, `docs/profile/README.md`, `docs/playpool/README.md`, `docs/check_ppp/README.md`, `docs/pdbtoexcel/README.md`, `docs/scheduler/README.md`, `docs/autocontinue/README.md`, `docs/config/README.md` (each tool's lines and codes, from `logging-by-command.md`)
- Delete: `docs/design/TODO/logging.md`, `docs/design/TODO/logging-by-command.md`
- Modify: `TODO.md` (tick the three older lines `CLI: confirm mainstream CLI strategy`, `Logging: switch to the mainstream logging strategy w/ color`, `Error handling and exit codes`; retarget the release-docs sub-item's link from `logging-by-command.md` to the per-tool READMEs; tick `docs`)
- Modify: `C:\Users\Brian\Projects\PNFL\athc-admin\TODO.md` (one line at the top of its first section: move its three commands onto `athc.console` and the run log, dropping `basicConfig`)
- Modify: `CHANGELOG.md`, `STATUS.md`, `WORKLOG.md` (top of section); `README.md` and `config/release/docs/README.txt` / `COMMANDS.txt` where they state exit codes or messages

- [ ] **Step 1: architecture.md describes the code as it is**

Replace `### Exit codes` and `### Output streams` with one section, `### Console, run log and errors`, holding (from logging.md, present tense, as implemented): the pieces table, the message kinds table, the color rules (plus `markup=False` / `emoji=False` and why), the run log (folder, `ATHC_LOG_DIR`, rotation, start and end lines), the exit-code table and rules, the library rules (errors subclass `AthcError`, warnings as values, `progress` callback), and that the one place is the `main` of `AthcCommand` / `AthcGroup` so `CliRunner` runs exercise it. Drop the "Not yet as designed" paragraph and `ATHC_DEBUG`.

- [ ] **Step 2: per-tool READMEs**

Each `Results and exit codes` (or equivalent) section: the command's lines (`OK`, `SKIP`, `WARN`, `FAIL`, result lines, tally), what counts as a finding, and `0 / 1 / 2` in the shared meaning, written from `logging-by-command.md`'s block for that command.

- [ ] **Step 3: retire the design files and the older TODO lines; meta files**

Delete the two TODO design files. In `TODO.md` tick the subtask and the three older lines, fix the link. CHANGELOG one line per user-visible change (console lines with `OK` / `SKIP` / `WARN` / `FAIL`, color, the run log, one exit scheme, library warnings). STATUS: the console/log/error layout under its own heading. WORKLOG: one dated entry on why. Release docs: exit codes and messages where they are stated.

- [ ] **Step 4: Run nothing (docs only); tick; commit**

```bash
git add -A
git commit -m "athc: docs describe the console, run log, errors and exit codes as built; TODO design retired"
```

---

## Hand-off

Leave the worktree (ExitWorktree, keep) and give the two blocks:

```
git merge --squash worktree-console-exit-codes
git commit -m "athc: console, run log, errors and exit codes the pdf-converter way"
```

```
git worktree remove .claude/worktrees/console-exit-codes
git branch -D worktree-console-exit-codes
```
