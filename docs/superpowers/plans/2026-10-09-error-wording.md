# Error Wording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every `FAIL` and `WARN` line reads the way Windows command-line tools word errors, names its file once, and fits on one line.

**Architecture:** One set of wording helpers in `athc/errors.py` (Windows phrases, `reason_of`, `missing_reason`, `error_line`, `sentence`, `ini_reason`, `toml_reason`); the console prints one labeled line per message line; every message in the sweep is reworded at its source.

**Tech Stack:** Python 3.13, Click, Rich, pytest, ruff, pyright.

**Spec:** `docs/superpowers/specs/2026-10-09-error-wording-design.md`

## Global Constraints

- File-system phrases, exact text: `The system cannot find the file specified.`, `The system cannot find the path specified.`, `Access is denied.`, `The directory name is invalid.`, `Cannot create a file when that file already exists.`
- Shape: `<path>: <Sentence.>`, `<path>: line N: <Sentence.>`; capital after the last location prefix; exactly one trailing period.
- TOML: `Not valid TOML: <parser text>.` INI: `Not valid INI: <reason> (at line N).`
- Click usage errors: athc's part starts lowercase, ends with a period.
- Out of scope: findings and result lines, `OK` / `SKIP` lines, tallies, labels, exit codes, run-log-only lines.
- Tests change first: a pinned string changes only to the spec's wording, before the code, and is seen to fail. Never change a test to match what the code happens to print.
- Commands run one per call from the worktree root: `uv run pytest <path>`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`.
- Every text file is UTF-8 with CRLF endings and a final newline; check new files with `git ls-files --eol <file>` (`w/crlf`).
- Commit messages: one line, prefixed with the owning tool (`athc:`, `gameplan:`, `profile:`, `convert-pdb:`, `scheduler:`, `autocontinue:`); no tool or AI mentions, no trailers.

## Review Focus

1. An `OSError` with no file name (winreg in `scheduler/cpu.py`, a screen grab): the phrase alone, never `None: …`. Test in Task 1.
2. An `OSError` whose `filename` is bytes or an int: the phrase alone, no `b'…'` prefix. Test in Task 1.
3. Embedded text that already ends with a period (a configparser message, a model `ValueError`, Windows' own `strerror`): one period, never `..`. Test in Task 1 (`sentence`).
4. A message with blank lines or a trailing newline: no empty `FAIL ` lines. Test in Task 2.
5. A play list typed at the console with blank and `::` lines first, CRLF endings: the line number is still the real one. Test in Task 5.

---

### Task 1: Wording helpers

**Files:**
- Modify: `src/athc/errors.py`
- Test: `tests/unit/test_errors.py`

**Interfaces:**
- Produces (in `athc.errors`): constants `FILE_NOT_FOUND`, `PATH_NOT_FOUND`, `ACCESS_DENIED`, `DIRECTORY_INVALID`, `ALREADY_EXISTS` (str); `sentence(text: str) -> str`; `reason_of(error: OSError) -> str`; `missing_reason(path: StrPath) -> str`; `error_line(error: AthcError | OSError) -> str`; `ini_reason(error: configparser.Error) -> str` (whole reason, `Not valid INI: … (at line N).`); `toml_reason(error: tomllib.TOMLDecodeError) -> str` (`Not valid TOML: <text>.`).

- [ ] **Step 1: Write the failing tests.** In `tests/unit/test_errors.py` replace `test_reason_of_keeps_only_the_system_wording`, `test_reason_of_falls_back_to_the_whole_text` and the `ini_reason` parametrize with:

```python
import errno
import tomllib

from athc.errors import (
    ACCESS_DENIED,
    ALREADY_EXISTS,
    DIRECTORY_INVALID,
    FILE_NOT_FOUND,
    PATH_NOT_FOUND,
    error_line,
    missing_reason,
    sentence,
    toml_reason,
)


def _win(code: int, text: str, filename: str | None = None) -> OSError:
    error = OSError(errno.EINVAL, text, filename)
    error.winerror = code  # type: ignore[attr-defined]  # set by Windows calls
    return error


@pytest.mark.parametrize(
    ("code", "phrase"),
    [
        (2, FILE_NOT_FOUND),
        (3, PATH_NOT_FOUND),
        (5, ACCESS_DENIED),
        (267, DIRECTORY_INVALID),
        (183, ALREADY_EXISTS),
    ],
)
def test_reason_of_a_windows_code_is_windows_phrase(code: int, phrase: str) -> None:
    assert reason_of(_win(code, "whatever")) == phrase


def test_reason_of_missing_file_in_an_existing_folder(tmp_path: Path) -> None:
    error = FileNotFoundError(errno.ENOENT, "No such file or directory", str(tmp_path / "x.pln"))
    assert reason_of(error) == FILE_NOT_FOUND


def test_reason_of_missing_folder_on_the_way(tmp_path: Path) -> None:
    error = FileNotFoundError(
        errno.ENOENT, "No such file or directory", str(tmp_path / "gone" / "x.pln")
    )
    assert reason_of(error) == PATH_NOT_FOUND


@pytest.mark.parametrize(
    ("number", "phrase"),
    [
        (errno.EACCES, ACCESS_DENIED),
        (errno.EISDIR, ACCESS_DENIED),
        (errno.ENOTDIR, DIRECTORY_INVALID),
        (errno.EEXIST, ALREADY_EXISTS),
    ],
)
def test_reason_of_an_errno_is_windows_phrase(number: int, phrase: str) -> None:
    assert reason_of(OSError(number, "whatever", "x")) == phrase


def test_reason_of_an_unknown_error_keeps_windows_text_as_a_sentence() -> None:
    error = _win(32, "The process cannot access the file because it is being used by another process")
    assert reason_of(error) == (
        "The process cannot access the file because it is being used by another process."
    )


def test_reason_of_without_strerror_uses_the_whole_text() -> None:
    assert reason_of(OSError("disk on fire")) == "Disk on fire."


def test_missing_reason(tmp_path: Path) -> None:
    assert missing_reason(tmp_path / "x.pln") == FILE_NOT_FOUND
    assert missing_reason(tmp_path / "gone" / "x.pln") == PATH_NOT_FOUND
    assert missing_reason("x.pln") == FILE_NOT_FOUND  # the current folder exists


def test_error_line_names_the_file(tmp_path: Path) -> None:
    error = PermissionError(errno.EACCES, "Permission denied", "x.pln")
    assert error_line(error) == f"x.pln: {ACCESS_DENIED}"


def test_error_line_without_a_file_name_is_the_phrase_alone() -> None:
    assert error_line(_win(2, "gone")) == FILE_NOT_FOUND


@pytest.mark.parametrize("filename", [b"x.pln", 3])
def test_error_line_ignores_a_bytes_or_number_file_name(filename: object) -> None:
    error = PermissionError(errno.EACCES, "Permission denied")
    error.filename = filename
    assert error_line(error) == ACCESS_DENIED


def test_error_line_of_an_athc_error_is_its_text() -> None:
    assert error_line(AthcError("Bad.", "x.pln")) == "x.pln: Bad."


@pytest.mark.parametrize(
    ("text", "result"),
    [
        ("bad thing", "Bad thing."),
        ("Bad thing.", "Bad thing."),
        ("bad thing...", "Bad thing."),
        ("'x' is bad", "'x' is bad."),
        ("  padded  ", "Padded."),
        ("", ""),
    ],
)
def test_sentence(text: str, result: str) -> None:
    assert sentence(text) == result


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("garbage\n", "Not valid INI: No [section] header above it (at line 1)."),
        ("[a]\nbroken\n", "Not valid INI: Not a 'key = value' line (at line 2)."),
        ("[a]\nbroken\nworse\n", "Not valid INI: Not a 'key = value' line (at lines 2, 3)."),
        ("[a]\n[a]\n", "Not valid INI: Section [a] repeats (at line 2)."),
        ("[a]\nx = 1\nx = 2\n", "Not valid INI: Option 'x' in [a] repeats (at line 3)."),
    ],
)
def test_ini_reason_is_one_line_without_the_path(text: str, reason: str) -> None:
    assert ini_reason(_ini_error(text)) == reason


def test_toml_reason() -> None:
    with pytest.raises(tomllib.TOMLDecodeError) as exc:
        tomllib.loads("x = \n")
    assert toml_reason(exc.value) == f"Not valid TOML: {exc.value}."
```

- [ ] **Step 2: Run them, expect failures** (`ImportError` on the new names).

Run: `uv run pytest tests/unit/test_errors.py`

- [ ] **Step 3: Implement in `src/athc/errors.py`.** Add `import errno`, `import tomllib`, `from pathlib import Path`; replace `reason_of` and `ini_reason`; add:

```python
FILE_NOT_FOUND = "The system cannot find the file specified."
PATH_NOT_FOUND = "The system cannot find the path specified."
ACCESS_DENIED = "Access is denied."
DIRECTORY_INVALID = "The directory name is invalid."
ALREADY_EXISTS = "Cannot create a file when that file already exists."

# Windows' own words for the problems a user meets, whichever call hit them:
# Python gives one problem two texts (open: "No such file or directory",
# os.stat: "The system cannot find the file specified").
_BY_WINERROR = {
    2: FILE_NOT_FOUND,
    3: PATH_NOT_FOUND,
    5: ACCESS_DENIED,
    183: ALREADY_EXISTS,
    267: DIRECTORY_INVALID,
}
_BY_ERRNO = {
    errno.EACCES: ACCESS_DENIED,
    errno.EISDIR: ACCESS_DENIED,  # Windows refuses to open a folder this way
    errno.ENOTDIR: DIRECTORY_INVALID,
    errno.EEXIST: ALREADY_EXISTS,
}


def sentence(text: str) -> str:
    """`text` as a sentence: capital first letter, exactly one trailing period."""
    text = text.strip().rstrip(".")
    return f"{text[:1].upper()}{text[1:]}." if text else ""


def _file_name(error: OSError) -> StrPath | None:
    name = error.filename
    return name if isinstance(name, str | PathLike) else None


def missing_reason(path: StrPath) -> str:
    """What Windows says for a missing `path`: the path phrase when the folder
    it should be in is missing too, else the file phrase."""
    return FILE_NOT_FOUND if Path(path).parent.is_dir() else PATH_NOT_FOUND


def reason_of(error: OSError) -> str:
    """An OSError's reason alone, in Windows' words, for a line that names the
    path itself."""
    winerror = getattr(error, "winerror", None)
    if winerror in _BY_WINERROR:
        return _BY_WINERROR[winerror]
    if winerror is None and error.errno == errno.ENOENT:
        name = _file_name(error)
        return FILE_NOT_FOUND if name is None else missing_reason(name)
    if winerror is None and error.errno in _BY_ERRNO:
        return _BY_ERRNO[error.errno]
    return sentence(error.strerror or str(error))


def error_line(error: AthcError | OSError) -> str:
    """The line a `FAIL` shows: an AthcError's own text, or an OSError as
    `<file>: <reason>` (the reason alone when it names no file)."""
    if isinstance(error, AthcError):
        return str(error)
    return _line(reason_of(error), _file_name(error))


def ini_reason(error: configparser.Error) -> str:
    """A configparser error as one line without the path, for an AthcError
    that carries the path itself."""
    match error:
        case configparser.MissingSectionHeaderError():
            reason = f"No [section] header above it (at line {error.lineno})"
        case configparser.ParsingError():
            numbers = [str(lineno) for lineno, _ in error.errors]
            noun = "line" if len(numbers) == 1 else "lines"
            reason = f"Not a 'key = value' line (at {noun} {', '.join(numbers)})"
        case configparser.DuplicateSectionError():
            reason = f"Section [{error.section}] repeats (at line {error.lineno})"
        case configparser.DuplicateOptionError():
            reason = (
                f"Option '{error.option}' in [{error.section}] repeats "
                f"(at line {error.lineno})"
            )
        case _:
            reason = " ".join(error.message.split())
    return sentence(f"Not valid INI: {reason}")


def toml_reason(error: tomllib.TOMLDecodeError) -> str:
    """A TOML parse error as one sentence; tomllib's text already names the
    line and column."""
    return sentence(f"Not valid TOML: {error}")
```

`_line` must come before these (it already does). `error_line` references `AthcError`, defined below it: move `error_line` under the class definitions.

- [ ] **Step 4: Run the unit tests, expect pass.** Run: `uv run pytest tests/unit/test_errors.py`

- [ ] **Step 5: Move every TOML and INI parse error onto the helpers.** First the tests: in `tests/conftest.py` make `toml_error(text)` return `toml_reason(exc.value)`; then grep `tests/` for `toml_error(`, `TOML parse error`, `not valid TOML`, `not valid INI`, `no [section]`, `key = value`, `repeats` and change every expected line to the spec form (`<path>: Not valid TOML: <text>.`, `<path>: Not valid INI: <reason> (at line N).`). Run `uv run pytest tests/unit tests/integration` and see those fail. Then the code:

| File:line | Now | New |
|---|---|---|
| `src/athc/config.py:53-57` | `ConfigFileError(ini_reason(e), path)` | unchanged call (the helper now gives the whole reason) |
| `src/athc/config.py:183` | `ConfigFileError(str(e), path)` | `ConfigFileError(toml_reason(e), path)` |
| `src/athc/config.py:249` | `ini_reason(e)` | unchanged call |
| `src/athc/gameplan/rules.py:196` | `f"TOML parse error: {e}"` | `toml_reason(e)` |
| `src/athc/profile/rules.py:349` | `f"TOML parse error: {e}"` | `toml_reason(e)` |
| `src/athc/playpool/rules.py:87` | `f"TOML parse error: {e}"` | `toml_reason(e)` |
| `src/athc/pdbtoexcel/config.py:131` | `str(e)` | `toml_reason(e)` |
| `src/athc/scheduler/config.py:183` | `f"not valid TOML: {error}"` | `toml_reason(error)` |
| `src/athc/scheduler/config.py:357` | `f"not valid INI: {ini_reason(error)}"` | `ini_reason(error)` |

- [ ] **Step 6: Run the suite, expect pass.** Run: `uv run pytest`. Any other failure is a test pinning `reason_of`'s old text (Python's `strerror`): it must be one the spec changes; change its expectation to the phrase, rerun.

- [ ] **Step 7: Commit.** `git add src/athc tests` then `git commit -m "athc: Windows phrases for file errors; one form for TOML and INI errors"`

### Task 2: Console and the one place

**Files:**
- Modify: `src/athc/console.py`, `src/athc/cli/__init__.py`, `src/athc/cli/autocontinue.py:32-34`, `src/athc/cli/generate_schedule.py:86-88`
- Test: `tests/unit/test_console.py`, `tests/unit/test_cli_main.py`, the CLI tests that pin `interrupted`, `unexpected error`, `reinstall athc` or an `OSError` line from the one place

**Interfaces:**
- Consumes: `error_line` (Task 1).
- Produces: `console.fail` / `console.warn` print one labeled line, and one log record, per non-blank line of the message.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_console.py` (use the file's existing console/caplog fixtures; the names below follow them):

```python
def test_fail_labels_every_line(capsys, caplog) -> None:
    console.fail("a.toml: One.\na.toml: Two.")
    assert capsys.readouterr().err == "FAIL a.toml: One.\nFAIL a.toml: Two.\n"
    assert [r.getMessage() for r in caplog.records] == [
        "FAIL a.toml: One.",
        "FAIL a.toml: Two.",
    ]


def test_warn_labels_every_line(capsys) -> None:
    console.warn("One.\nTwo.")
    assert capsys.readouterr().err == "WARN One.\nWARN Two.\n"


def test_blank_lines_print_no_empty_labels(capsys) -> None:
    console.fail("One.\n\n  \nTwo.\n")
    assert capsys.readouterr().err == "FAIL One.\nFAIL Two.\n"


def test_unexpected_line(capsys) -> None:
    try:
        raise RuntimeError
    except RuntimeError:
        console.unexpected("x.pln")
    assert capsys.readouterr().err == (
        f"FAIL x.pln: Unexpected error. See {log_path()} for details.\n"
    )
```

Then grep `tests/` for `interrupted`, `unexpected error (see log`, `reinstall athc`, `[Errno`, `[WinError` and change each expected line: `FAIL Interrupted.`, `<what>: Unexpected error. See <log> for details.`, `FAIL Missing <module>. Reinstall athc.`, and the one place's OSError pin in `tests/unit/test_cli_main.py:49` to `"FAIL x.pln: The system cannot find the file specified.\n"`; the log-folder test (`test_cli_main.py:52-63`) to `f"FAIL {blocker}: {ALREADY_EXISTS}\n"` (drop its `os_error` capture).

- [ ] **Step 2: Run, expect failures.** Run: `uv run pytest tests/unit/test_console.py tests/unit/test_cli_main.py`

- [ ] **Step 3: Implement.** `src/athc/console.py`:

```python
    def warn(self, message: str) -> None:
        """Noted, nothing failed. One labeled line per line of `message`."""
        for line in _lines(message):
            self._status(self.err, "WARN", "yellow", line, logging.WARNING)

    def fail(self, message: str) -> None:
        """One item, or the run, failed. One labeled line per line of `message`."""
        for line in _lines(message):
            self._status(self.err, "FAIL", "red", line, logging.ERROR)

    def unexpected(self, what: str | None = None) -> None:
        """A bug. Call it inside the `except`, so the traceback reaches the log."""
        subject = f"{what}: " if what else ""
        message = f"{subject}Unexpected error. See {log_path()} for details."
        self._status(self.err, "FAIL", "red", message, logging.ERROR, exc_info=True)
```

and a module function:

```python
def _lines(message: str) -> list[str]:
    """A message's non-blank lines; a message never prints an unlabeled line."""
    return [line for line in message.splitlines() if line.strip()] or [message]
```

`src/athc/cli/__init__.py`: import `error_line` instead of `reason_of`; line 93 → `console.fail(error_line(error))`; line 116 → `console.fail("Interrupted.")`; line 119 → `console.fail(error_line(error))`. `cli/autocontinue.py` and `cli/generate_schedule.py`: `f"Missing {error.name or '<module>'}. Reinstall athc."`.

- [ ] **Step 4: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 5: Commit.** `git commit -am "athc: one labeled line per message line; Windows phrases at the one place"`

### Task 3: Path checks

**Files:**
- Modify: `src/athc/cli/_files.py`, `src/athc/cli/check_ppp.py`, `src/athc/cli/playpool/check.py`, `src/athc/config.py`, `src/athc/gameplan/config.py`, `src/athc/pdbtoexcel/config.py`, `src/athc/pdbtoexcel/main.py:41-45`, `src/athc/cli/gameplan/_common.py:126-143`, every `build_pool` caller (`cli/gameplan/check.py:45`, `replace_play.py:128`, `set_normals.py:56`, `set_specials.py:122`, `cli/check_ppp.py:171`)
- Test: `tests/unit/test_cli_files.py`, `tests/integration/test_check_ppp.py`, `test_playpool_check.py`, `test_convert_pdb.py`, `test_gameplan_*.py`, `test_profile_*.py`, `tests/unit/pdbtoexcel/test_config.py`

**Interfaces:**
- Consumes: `missing_reason`, `ACCESS_DENIED`, `PATH_NOT_FOUND`, `DIRECTORY_INVALID` (Task 1).
- Produces: `athc.config.play_dir(play_path: Path, league_file: Path) -> Path` (raises `ConfigFileError`); `league_file: Path` field on `athc.gameplan.config.Config` and `athc.pdbtoexcel.config.Config`; `build_pool(play_path, playpool_rules, categories, league_file)`.

- [ ] **Step 1: Tests first.** Add to `tests/unit/test_cli_files.py`:

```python
def test_named_file_missing(tmp_path: Path) -> None:
    with pytest.raises(AthcError) as exc:
        named_file(tmp_path / "x.pln")
    assert str(exc.value) == f"{tmp_path / 'x.pln'}: {FILE_NOT_FOUND}"


def test_named_file_in_a_missing_folder(tmp_path: Path) -> None:
    with pytest.raises(AthcError) as exc:
        named_file(tmp_path / "gone" / "x.pln")
    assert str(exc.value) == f"{tmp_path / 'gone' / 'x.pln'}: {PATH_NOT_FOUND}"


def test_named_file_given_a_folder(tmp_path: Path) -> None:
    with pytest.raises(AthcError) as exc:
        named_file(tmp_path)
    assert str(exc.value) == f"{tmp_path}: {ACCESS_DENIED}"
```

and to `tests/unit/test_config.py` (create if missing) for `play_dir`: a folder passes through; a missing one raises `f"{p}: {PATH_NOT_FOUND} Set play_path in {league_file}."`; a file raises `f"{p}: {DIRECTORY_INVALID} Set play_path in {league_file}."`. Then grep `tests/` for `: not found`, `not a file`, `not a directory`, `no play_path for the league`, `no path for the league`, `play path is not a directory`, `no .pln files`, `not a .pln file`, `second .p`, `not a .prf or .pln file`, `profile is ` and change each expected line per the table below. Run `uv run pytest tests/unit/test_cli_files.py tests/integration`, expect failures.

- [ ] **Step 2: Implement.**

| File:line | Now | New |
|---|---|---|
| `cli/_files.py:49` | `f"{raw}: no {suffix} files match"` | `f"{raw}: No {suffix} files match."` |
| `cli/_files.py:56` | `f"{raw}: not found"` | `f"{raw}: {missing_reason(raw)}"` |
| `cli/_files.py:60` | `f"{raw}: not a {suffix} file"` | `f"{raw}: Not a {suffix} file."` |
| `cli/_files.py:67` | `f"{raw}: no {suffix} files"` | `f"{raw}: No {suffix} files."` |
| `cli/_files.py:81` | `AthcError("not found", path)` | `AthcError(missing_reason(path), path)` |
| `cli/_files.py:83` | `AthcError("not a file", path)` | `AthcError(ACCESS_DENIED, path)` |
| `cli/check_ppp.py:116`, `:271` | `f"{raw}: not found"` | `f"{raw}: {missing_reason(raw)}"` |
| `cli/check_ppp.py:119-121` | `f"{raw}: not a directory; pass one profile and one gameplan, or a directory"` | `f"{raw}: {DIRECTORY_INVALID} Pass one profile and one gameplan, or a folder."` |
| `cli/check_ppp.py:129-131` | `f"{raw}: no profile and gameplan pairs from the league file in {scope}"` | `f"{raw}: No profile and gameplan pairs from the league file in {scope}."` |
| `cli/check_ppp.py:185-188` | `ConfigFileError(f"no path for the league; set path in {config.dir / LEAGUE_FILE}")` | `ConfigFileError("No path for the league. Set path in this file.", config.dir / LEAGUE_FILE)` |
| `cli/check_ppp.py:273` | `f"{raw}: not a file"` | `f"{raw}: {ACCESS_DENIED}"` |
| `cli/check_ppp.py:279-281` | `f"{raw}: second {suffix} file; pass one profile and one gameplan"` | `f"{raw}: Second {suffix} file. Pass one profile and one gameplan."` |
| `cli/check_ppp.py:283` | `f"{raw}: not a .prf or .pln file"` | `f"{raw}: Not a .prf or .pln file."` |
| `cli/check_ppp.py:343-346` | `f"{path}: profile is {a} but gameplan is {b}"` | `f"{path}: Profile is {a} but gameplan is {b}."` |
| `cli/playpool/check.py:46-49` | `f"no play_path for the league; set play_path in {cfg.dir / LEAGUE_FILE}"` | `ConfigFileError("No play_path for the league. Set play_path in this file.", cfg.dir / LEAGUE_FILE)` |
| `cli/playpool/check.py:52` | `AthcError("not found", play_dir)` | `AthcError(PATH_NOT_FOUND, play_dir)` |
| `cli/playpool/check.py:54` | `AthcError("not a directory", play_dir)` | `AthcError(DIRECTORY_INVALID, play_dir)` |
| `gameplan/config.py:36-39`, `pdbtoexcel/config.py:90-92` | `f"no play_path for the league; set play_path in {cfg.dir / LEAGUE_FILE}"` | `ConfigFileError("No play_path for the league. Set play_path in this file.", cfg.dir / LEAGUE_FILE)`; also set the new `league_file=cfg.dir / LEAGUE_FILE` field |
| `cli/gameplan/_common.py:136`, `pdbtoexcel/main.py:41-45` | `play path is not a directory …` | `play_dir(play_path, league_file)` |

`play_dir` in `src/athc/config.py`:

```python
def play_dir(play_path: Path, league_file: Path) -> Path:
    """`play_path` when it is a folder; else ConfigFileError in Windows' words,
    pointing at the league.toml that sets it."""
    if not play_path.is_dir():
        reason = DIRECTORY_INVALID if play_path.exists() else PATH_NOT_FOUND
        raise ConfigFileError(f"{reason} Set play_path in {league_file}.", play_path)
    return play_path
```

Update the `Collected` docstring examples in `cli/_files.py` and `named_file`'s docstring to the new wording.

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "athc: path checks in Windows' words; one play path wording"`

### Task 4: Batch loops and warnings that showed Python's text

**Files:**
- Modify: `cli/gameplan/find_play.py:93`, `replace_play.py:153`, `set_specials.py:155`, `cli/gameplan/check.py:59`, `cli/profile/check.py:57`, `cli/profile/copy.py:118`, `cli/check_ppp.py:145,328,336`, `src/athc/playpool/reader.py:198,201`, `src/athc/autocontinue/main.py:79,152-154`
- Test: the matching `tests/integration/test_*.py`, `tests/unit/playpool/test_reader.py`, `tests/integration/test_autocontinue.py`

**Interfaces:**
- Consumes: `error_line`, `reason_of` (Task 1).

- [ ] **Step 1: Tests first.** Grep `tests/` for `os_error(`, `strerror`, `Skipping invalid play file`, `Skipping unreadable play file`, `Config reload failed`, `Screen grab failed` and change each expected line: per-item OS errors `FAIL <file>: <phrase>`; play pool `WARN <path>: <reason> Skipped.`; autocontinue `WARN <error line> Keeping the previous settings.` and `WARN Screen grab failed: <phrase> Retrying in 60 seconds.` Add one integration test that makes a `.pln` unreadable inside a batch (open it with an exclusive lock or replace it with a folder named `x.pln`) and pins `FAIL <path>: Access is denied.`. Run, expect failures.

- [ ] **Step 2: Implement.** Every `console.fail(str(error))` in the listed loops → `console.fail(error_line(error))`; check-ppp's returned read lines (`:328`, `:336`) → `error_line(error)`; `playpool/reader.py:198` → `f"{exc} Skipped."` (an `InvalidPlayFileError` already reads `<path>: <Reason.>` after Task 8; until then it gets its period in Task 8); `:201` → `f"{error_line(exc)} Skipped."`; `autocontinue/main.py:79` → `f"{error_line(error)} Keeping the previous settings."`; `:152-154` → `f"Screen grab failed: {reason_of(error)} Retrying in {_LOCKED_SCREEN_BACKOFF:.0f} seconds."`.

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "athc: every loop and warning names the file in Windows' words"`

### Task 5: Play lists

**Files:**
- Modify: `src/athc/gameplan/writer.py`, `src/athc/cli/gameplan/_common.py:78-90`, `src/athc/cli/gameplan/set_normals.py`, `src/athc/cli/gameplan/set_specials.py`
- Test: `tests/unit/gameplan/test_writer.py` (or the existing writer test module), `tests/integration/test_gameplan_set_normals.py`, `tests/integration/test_gameplan_set_specials.py`, the `parse_play_list` tests

**Interfaces:**
- Produces (in `athc.gameplan.writer`):

```python
@dataclass(frozen=True, slots=True)
class PlayLine:
    """One play name and the line of the list it is on (1-based)."""
    line: int
    name: str


@dataclass(frozen=True, slots=True)
class Violation:
    """One play the list cannot place: its line and a sentence saying why."""
    line: int
    reason: str
```

- `parse_play_list(text: str) -> list[PlayLine]`; `apply_normal_plays(gp, plays: Sequence[PlayLine], pool)`; `apply_special_plays(gp, plays: Sequence[PlayLine], pool)`; `InvalidPlayInputError(violations: Sequence[Violation])`, text `f"{n} invalid input line(s)."`, `.violations: list[Violation]`.

- [ ] **Step 1: Tests first.**

```python
def test_parse_play_list_keeps_the_file_line_numbers() -> None:
    text = "\r\n:: comment\r\nPlay A\r\n\r\nPlay B :: note\r\n"
    assert parse_play_list(text) == [PlayLine(3, "Play A"), PlayLine(5, "Play B")]
```

Integration (set-normals, from a file and from `-`): a list `":: header\n\nNope\n"` with `Nope` missing from the pool → `FAIL <list>: line 3: 'Nope' not found in the play pool (slot 1-1).` and from the console `FAIL line 3: 'Nope' not found in the play pool (slot 1-1).`. set-specials per-gameplan problem → `FAIL <x.pln>: '<name>' is a defensive special play, but the gameplan is offensive (<list> line N).` and `(input line N)` from the console. Too many plays: `FAIL <list>: Too many plays (65). The most is 64.`; confirm a 64-play list is accepted and a 65-play list rejected (add whichever is missing), and the same at 10 / 11 for set-specials. Change every other pinned play-list line to the table below. Run, expect failures.

- [ ] **Step 2: Implement.** `parse_play_list`:

```python
def parse_play_list(text: str) -> list[PlayLine]:
    """Play names in order with their line numbers; drops blanks, `::` lines,
    and ` ::` trailers."""
    out: list[PlayLine] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_TOKEN):
            continue
        idx = line.find(f" {COMMENT_TOKEN}")
        if idx >= 0:
            line = line[:idx].rstrip()
        if line:
            out.append(PlayLine(number, line))
    return out
```

Writer reasons (each a `Violation(play.line, reason)`):

| Now (after `line {line_no}: `) | New `reason` |
|---|---|
| `'{name}' not found in the play pool (slot {grid})` | `'{name}' not found in the play pool (slot {grid}).` |
| `'{name}' is a special teams play, cannot add to normal slots` | `'{name}' is a special teams play and cannot go in a normal slot.` |
| `'{name}' is a defensive play but gameplan is offensive` | `'{name}' is a defensive play, but the gameplan is offensive.` |
| `'{name}' is an offensive play but gameplan is defensive` | `'{name}' is an offensive play, but the gameplan is defensive.` |
| `duplicate special play '{name}', already used for special category {c}` | `Duplicate special play '{name}', already used for special category {c}.` |
| `'{name}' not found in the play pool` | `'{name}' not found in the play pool.` |
| `'{name}' is not a special teams play` | `'{name}' is not a special teams play.` |
| `'{name}' is a defensive special play but gameplan is offensive` | `'{name}' is a defensive special play, but the gameplan is offensive.` |
| `'{name}' is an offensive special play but gameplan is defensive` | `'{name}' is an offensive special play, but the gameplan is defensive.` |
| `'{name}' is in special category {cat}, which has no custom slot` | `'{name}' is in special category {cat}, which has no custom slot.` |
| `'{name}' targets special category {cat}, already filled by another play` | `'{name}' targets special category {cat}, already filled by another play.` |

CLI checks (`Violation` too): set-normals `'{name}' is a special teams play. Use set-specials.`; set-specials `Duplicate play '{name}' (already on line {j}).` (`j` the real line), `'{name}' is not a special teams play. Use set-normals.`, `'{name}' targets special category {cat}, already filled by '{other}'.`

Printing, both commands: `prefix = "" if console input else f"{input_path}: "`; list problems `console.fail(f"{prefix}line {v.line}: {v.reason}")`. set-specials per-gameplan: `where = "input" if console input else str(input_path)`; `console.fail(f"{path}: {v.reason[:-1]} ({where} line {v.line}).")`. Too many: `raise AthcError(f"Too many plays ({len(plays)}). The most is {NORMAL_COUNT}.", None if console input else input_path)` (and `SPECIAL_COUNT`).

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "gameplan: play-list errors name the list and its real line"`

### Task 6: Config, league, athc.ini and usage errors

**Files:**
- Modify: `src/athc/config.py`, `src/athc/fbpro98_play/labels.py:75-85`, `src/athc/cli/profile/_common.py:20-23`, `src/athc/cli/gameplan/_common.py:119-122`, `src/athc/autocontinue/config.py`, `src/athc/pdbtoexcel/config.py:245-248`, `src/athc/cli/config/set.py:25-33`, `src/athc/cli/convert_pdb.py:24-26`, `src/athc/cli/profile/diff.py:51-53`, `src/athc/cli/profile/copy.py:88-92`, `src/athc/cli/gameplan/find_play.py:74-76`, `tests/conftest.py`
- Test: `tests/unit/test_config.py`, `tests/unit/test_labels.py` (or the labels test module), `tests/integration/test_config*.py`, `test_autocontinue.py`, `tests/unit/pdbtoexcel/test_config.py`, every test using the conftest league / rules helpers

**Interfaces:**
- Consumes: `sentence` (Task 1); `athc.config.config_file() -> Path` (existing; the athc.ini path).

- [ ] **Step 1: Tests first.** conftest: `no_league_selected` → `"FAIL No league selected. Run 'athc config set league NAME' or pass --league. {tail}\n"`; `league_not_found` → `f"FAIL League '{name}' not found. No folder {path}. {tail}\n"`; `no_rules_configured` → `f"FAIL No rules configured. Add {filename} to the league folder.\n"`. Then grep `tests/` for each "Now" text below and change it. Run, expect failures.

- [ ] **Step 2: Implement.**

| File:line | Now | New |
|---|---|---|
| `config.py:78-81` | `[league] {key}: expected a string, got an array` | `[league] {key}: Expected a string, got an array.` |
| `config.py:102-105` | `[league] {key}: expected an array of strings, got a string` | `[league] {key}: Expected an array of strings, got a string.` |
| `config.py:143` | `league '{name}' not found: no folder {path}.{_available()}` | `League '{name}' not found. No folder {path}.{_available()}` |
| `config.py:160-163` | `no league selected; run 'athc config set league NAME' or pass --league.{_available()}` | `No league selected. Run 'athc config set league NAME' or pass --league.{_available()}` |
| `config.py:198` | `[{name or key}] must be a table` | `[{name or key}]: Must be a table.` |
| `config.py:215-218` | `[league] {key}: expected a string or an array of strings` | `[league] {key}: Expected a string or an array of strings.` |
| `labels.py:75` | `{where}: not a game category name for {side}` | `{where}: Not a game category name for {side}.` |
| `labels.py:77` | `{where}: label must be a non-empty string` | `{where}: Label must be a non-empty string.` |
| `labels.py:79-81` | `{where}: label {value!r} is a game category name for {side}` | `{where}: Label {value!r} is a game category name for {side}.` |
| `labels.py:83-85` | `{where}: label {value!r} already used by {used[value]!r}` | `{where}: Label {value!r} already used by {used[value]!r}.` |
| `cli/profile/_common.py:20-23`, `cli/gameplan/_common.py:119-122` | `no rules configured - nothing to check. Add <file> to the league folder.` | `No rules configured. Add <file> to the league folder.` |
| `autocontinue/config.py:42-45` | `No [autocontinue] config found. Set ATHC_CONFIG_DIR or edit:\n  {path}` | `ConfigFileError("No [autocontinue] section. Add one, or set ATHC_CONFIG_DIR.", config_file())` |
| `autocontinue/config.py:77-79` | `Invalid '{key}' in [autocontinue]: {v!r} (expected true/false).` | `ConfigFileError(f"[autocontinue] {key}: Must be true or false, got {v!r}.", config_file())` |
| `autocontinue/config.py:85` | `Missing required setting '{key}' in [autocontinue].` | `ConfigFileError(f"Missing required setting '{key}' in [autocontinue].", config_file())` |
| `autocontinue/config.py:89-91` | `Invalid '{key}' in [autocontinue]: {v!r} (expected a number).` | `ConfigFileError(f"[autocontinue] {key}: Must be a number, got {v!r}.", config_file())` |
| `pdbtoexcel/config.py:245-248` | `[convert-pdb] {key}: expected true or false (yes/no, on/off, 1/0 also work), got {v!r}` | `ConfigFileError(f"[convert-pdb] {key}: Must be true or false (yes/no, on/off and 1/0 also work), got {v!r}.", config_file())` |
| `cli/config/set.py:25-28` | `unknown key '{key}'; known keys: {keys}` | `unknown key '{key}'. Known keys: {keys}.` |
| `cli/config/set.py:33` | `str(error)` | `msg = str(error); msg[:1].lower() + msg[1:]` (continues Click's sentence) |
| `cli/convert_pdb.py:24-26` | `must have a {exts} extension` | `must have a {exts} extension.` |
| `cli/profile/diff.py:51-53` | `format from the extension: use .txt or .csv` | `the format comes from the extension: use .txt or .csv.` |
| `cli/profile/copy.py:88-92` | `at least one copy option is required (…)` | same text plus a final `.` |
| `cli/gameplan/find_play.py:74-76` | `path must be a .pln file or a directory; wildcards are not supported` | same text plus a final `.` |

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "athc: config, league and usage errors as sentences; athc.ini errors name the file"`

### Task 7: Rules files and play-pool warnings

**Files:**
- Modify: `src/athc/gameplan/rules.py`, `src/athc/profile/rules.py`, `src/athc/playpool/rules.py`, `src/athc/playpool/reader.py:136-163,260-275`, `src/athc/cli/gameplan/_common.py:140-143`, `src/athc/pdbtoexcel/workbook_creator.py:79`
- Test: `tests/unit/gameplan/test_rules.py`, `tests/unit/profile/test_rules.py`, `tests/unit/playpool/test_rules.py`, `tests/unit/playpool/test_reader.py`, the CLI tests that pin rules or pool warnings

**Interfaces:**
- Consumes: `sentence` (Task 1).

- [ ] **Step 1: Tests first.** Grep `tests/` for each "Now" text below (`must be a table`, `unknown key`, `not an offense category label`, `Valid: [`, `(expected [`, `must be a boolean`, `must be an integer`, `must be >= 0`, `must be in [`, `must be a list`, `entries must be strings`, `unknown name`, `needs one of`, `mutually exclusive`, `empty rule`, `invalid fraction`, `invalid regex`, `play in the`, `play in a`, `Duplicate play name`, `exclude wins`, `is not in the play pool`, `it has no effect`) and change each expected line. Add one CLI test: a gameplan.toml with two problems prints two `FAIL <rules file>: …` lines and the log holds two `FAIL` records. Run, expect failures.

- [ ] **Step 2: Implement.** In the three rules modules every reason after its location prefix (`{where}:`, `(top):`, `[x]:`) becomes a sentence: capital first letter, one trailing period. Specific rewrites:

| Now | New |
|---|---|
| `{where} must be a table` | `{where}: Must be a table.` |
| `{where}: must be a table` | `{where}: Must be a table.` |
| `{where}: unknown key(s): {names}` | `{where}: Unknown key(s): {plain names}.` |
| `[{name}]: unknown key(s): {key}` (play pool) | `[{name}]: Unknown key(s): {key}.` |
| `unknown section [{key}] (expected {sorted(_SECTIONS)})` | `Unknown section [{key}]. Valid: {', '.join(sorted(_SECTIONS))}.` |
| `… label. Valid: {sorted(by_label)}` | `… label. Valid: {', '.join(sorted(by_label))}.` |
| `{where}: at most one of {names}` | `{where}: Set at most one of {plain names}.` |
| `{where}: empty rule; set at least one key` | `{where}: Empty rule. Set at least one key.` |
| ``{where}: needs one of `allowed`, `disallowed`, `mandatory`, `min_categories` `` | `{where}: Needs one of allowed, disallowed, mandatory, min_categories.` |
| any other text with Markdown backticks | the same words without backticks |
| `{where}: invalid fraction {value!r}: {e}` | `{where}: Invalid fraction {value!r}: {sentence-less e}.` |
| `{where}: invalid regex {pat!r}: {e}` | `{where}: Invalid regex {pat!r}: {e}.` |

"plain names" = names joined with `, ` without quotes (today `'max_x_count', 'max_x_ratio'`). Play-pool reader and its callers:

| File:line | Now | New |
|---|---|---|
| `playpool/reader.py:136` | `f"{Adj} play in the {side} tree: {path}"` | `f"{path}: {Adj} play in the {side} tree."` |
| `playpool/reader.py:140` | `f"{long} play in a {folder} folder: {path}"` | `f"{path}: {long} play in a {folder} folder."` |
| `playpool/reader.py:163` | `Duplicate play name '{n}'; last loaded wins` | `Duplicate play name '{n}'. The last one loaded wins.` |
| `playpool/reader.py:260-262` | `[{s}] '{n}' is in both include and exclude; exclude wins` | `[{s}] '{n}' is in both include and exclude. Exclude wins.` |
| `playpool/reader.py:267-269` | `[{s}] {key} '{n}' is not in the play pool` | same plus `.` |
| `playpool/reader.py:273-275` | `[{s}] {key} '{n}' is a {kind} play; it has no effect` | `[{s}] {key} '{n}' is a {kind} play. It has no effect.` |
| `cli/gameplan/_common.py:143`, `workbook_creator.py:79` | `f"{playpool_rules.name}: {notice}"` | `f"{playpool_rules}: {notice}"` (full path) |

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "athc: rules files and play-pool warnings as sentences, path first"`

### Task 8: Binary readers and models

**Files:**
- Modify: `src/athc/fbpro98_play/reader.py`, `src/athc/fbpro98_lg2/reader.py`, `src/athc/fbpro98_gameplan/reader.py`, `src/athc/fbpro98_gameplan/model.py`, `src/athc/fbpro98_profile/reader.py`, `src/athc/fbpro98_profile/model.py`, `src/athc/cli/gameplan/replace_play.py:93,131`
- Test: `tests/unit/fbpro98_*/test_reader.py`, `tests/unit/fbpro98_*/test_model.py`, `tests/integration/test_gameplan_replace_play.py`

- [ ] **Step 1: Tests first.** Grep the reader and model tests for every `match=` / pinned message and add the trailing period (and hex for bytes) per Step 2. Run, expect failures.

- [ ] **Step 2: Implement.** Every message these modules raise ends with one period. Embedded texts keep no period of their own: a model `ValueError` wrapped by a reader (`Invalid substitution pair for {group}: {exc}`, `Invalid {label} record at index {index}: {exc}`, `Invalid PAT situation record at index {index}: {exc}`, gameplan reader `:110` `str(e)`, `replace_play.py:93`) is composed as `sentence(f"…: {exc}")`, and the model's own messages lose any trailing period. Bytes values: `fbpro98_gameplan/reader.py:150-152` `Audible bytes {audible.hex(' ')} != expected {DEFAULT_AUDIBLE.hex(' ')}.`, `:280-282` `S98 data {data.hex(' ')} != expected {S98_EXPECTED_DATA.hex(' ')}.`. `replace_play.py:131`: `Replacement play '{replacement}' not found in the play pool.`

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "athc: binary readers' errors as sentences, bytes as hex"`

### Task 9: convert-pdb and profile copy/diff

**Files:**
- Modify: `src/athc/pdbtoexcel/config.py`, `src/athc/pdbtoexcel/pdb.py:176-211`, `src/athc/pdbtoexcel/workbook_creator.py:166-197`, `src/athc/pdbtoexcel/excel_workbook.py:109-118`, `src/athc/profile/writer.py:52-58`, `src/athc/profile/diff.py:69-73`, `src/athc/profile/errors.py:20-23`
- Test: `tests/unit/pdbtoexcel/test_*.py`, `tests/integration/test_convert_pdb.py`, `tests/unit/profile/test_*.py`, `tests/integration/test_profile_copy.py`, `test_profile_diff.py`

- [ ] **Step 1: Tests first.** Grep for each "Now" text below and change it. Run, expect failures.

- [ ] **Step 2: Implement.**

| File:line | Now | New |
|---|---|---|
| `pdbtoexcel/config.py:123-125` | `not found (convert-pdb needs the league's pdbtoexcel.toml)` | `f"{missing_reason(path)} convert-pdb needs this file in the league folder."` |
| `pdbtoexcel/config.py:134-136` | `unknown key {key!r} (expected {A}, {B})` | `Unknown key(s): {key}. Valid: {A}, {B}.` |
| `pdbtoexcel/config.py:138` | `[{ORDER_TABLE}] is missing` | `Missing the [{ORDER_TABLE}] table.` |
| `pdbtoexcel/config.py:147` | `[{key}] must be a table` | `[{key}]: Must be a table.` |
| `pdbtoexcel/config.py:156` | `[{s}] {k}: expected an array of strings` | `[{s}] {k}: Expected an array of strings.` |
| `pdbtoexcel/config.py:167-169` | `[{s}] {k}: unknown key (expected {e})` | `[{s}] {k}: Unknown key. Valid: {e}.` |
| `pdbtoexcel/config.py:188` | `[{ORDER_TABLE}] {key}: missing` | `[{ORDER_TABLE}] {key}: Missing.` |
| `pdbtoexcel/config.py:213-223` | `… category`, `… Valid: {sorted(valid)}`, `… is listed twice` | the same plus `.`; `Valid:` list plain |
| `pdbtoexcel/pdb.py:176-178` | `invalid data type {data!r} at {off:#x}` | `Invalid data type 0x{data.hex()} at {off:#x}.` |
| `pdbtoexcel/pdb.py:188`, `:211` | `Skipping invalid play data at {off:#x}` (tendency likewise) | `f"{pdb_path}: Invalid play data at {off:#x}. Skipped."` (tendency likewise) |
| `workbook_creator.py:166-169` | `'{name}' is listed in [deleted_plays] but is in the play pool; its stats are skipped` | `f"{pdbtoexcel_toml}: '{name}' is listed in [deleted_plays] but is in the play pool. Its stats are skipped."` |
| `workbook_creator.py:197` | `Play file not found for play '{p}'` | `Play '{p}' has no play file in the play pool.` |
| `excel_workbook.py:109-118` | `cause.strerror` / `str(error)` | `reason_of(cause)` / `sentence(str(error))` |
| `profile/writer.py:52-58` | `Profile type mismatch: source is X, target is Y. copy only copies …` | `AthcError`-path form: `f"Cannot copy from {source} ({s}) to a {t} profile."` with the target as the error's path (`s`, `t` lowercase side names) |
| `profile/diff.py:69-73` | `cannot diff X against Y` | `f"Cannot compare {a_path} ({a}) with {b_path} ({b})."` |
| `profile/errors.py:20-23` | default `profile type mismatch: X vs Y` | `Profile type mismatch: {x} vs {y}.` |

`pdb_path` / `pdbtoexcel_toml` / profile paths: pass them in where the message is built (the PDB reader, the workbook creator and the profile writer and diff already receive or can receive them; add a parameter where they don't, and update the callers).

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest`

- [ ] **Step 4: Commit.** `git commit -am "convert-pdb: errors and warnings as sentences naming their file; profile mismatches name both profiles"`

### Task 10: Scheduler

**Files:**
- Modify: `src/athc/scheduler/config.py`, `src/athc/scheduler/domain/league.py`, `src/athc/scheduler/schedulers/matchup_builder.py`, `src/athc/scheduler/schedulers/schedule_builder.py`
- Test: `tests/unit/scheduler/test_config.py`, `test_cli.py`, `test_matchups.py`, `test_schedule_builder.py`, `tests/integration/test_generate_schedule.py`

- [ ] **Step 1: Tests first.** Grep for each "Now" text and change it. Run, expect failures.

- [ ] **Step 2: Implement.**

| File:line | Now | New |
|---|---|---|
| `config.py:176`, `:216` | `"not found"` | `missing_reason(path)` |
| `config.py:221-225` | `must have exactly one of the [DivisionStandings] and [ConferenceStandings] sections.` | `Must have exactly one of …` |
| `config.py:233` | `f"invalid league data: {error}"` | `sentence(f"Invalid league data: {error}")` |
| `config.py:241-244` | `No standings file for {league} season {season}. Expected:\n  {path}\nRun 'athc config path' …` | `ConfigFileError(f"{FILE_NOT_FOUND} Add the {league} season {season} standings file.", path)` |
| `config.py:298` | `unknown [{name}] key(s): {list}.` | `[{name}]: Unknown key(s): {list}.` |
| `config.py:336-338` | `each [rivalries] pair is two team names; got {entry!r}.` | `Each [rivalries] pair is two team names; got {plain entry}.` |
| `config.py:363` | `missing the required [{section}] section.` | `Missing the required [{section}] section.` |
| `config.py:370` | `missing required setting '{key}' in [{section}].` | `Missing required setting '{key}' in [{section}].` |
| `config.py:373` | `empty '{key}' in [{section}].` | `Empty '{key}' in [{section}].` |
| `config.py:393-454` (cross-checks, no path today) | as now | same text, raised with the scheduler.toml path |
| `schedule_builder.py:55-58` | no path | raised with the scheduler.toml path |
| `domain/league.py` | `Valid: {sorted(...)}`, `{sorted(conferences)}`, `{duplicates}` | plain `, `-joined lists; no trailing period (embedded by `config.py:233`) |
| solver messages (`matchup_builder.py`, `schedule_builder.py`) | dict / dataclass reprs, no period | plain text, one trailing period |

"plain entry": a list entry joined with `, `, a string as is. The scheduler.toml path reaches the cross-checks through the loader that already has it (`config.py`); pass it to `schedule_builder` where needed.

- [ ] **Step 3: Run, expect pass.** Run: `uv run pytest` and `uv run pytest -m slow`

- [ ] **Step 4: Commit.** `git commit -am "scheduler: errors as sentences naming scheduler.toml or the standings file"`

### Task 11: Docs and the final check

**Files:**
- Modify: `docs/design/architecture.md` ("Console, run log and errors"), `docs/*/README.md` of each tool with changed lines, `tests/integration/README.md`, `tests/unit/*/README.md` that quote messages, `config/release/docs/*.txt` that quote messages, `CHANGELOG.md`, `STATUS.md`, `WORKLOG.md`

- [ ] **Step 1: architecture.md.** Read "Console, run log and errors" end to end. Add the wording rules (shape, sentence style, the phrase table, one line per problem, plain values, one form per parse error, Click's part) and the helpers (`reason_of`, `missing_reason`, `error_line`, `sentence`, `ini_reason`, `toml_reason`); replace the `named_file` bullet's `not found` / `not a file` and the one place's "`OSError` prints `FAIL <message>`" with the new wording.

- [ ] **Step 2: Tool READMEs, test READMEs, release docs.** Grep each for the old texts from Tasks 1-10 and change them to the new ones.

- [ ] **Step 3: Project notes.** CHANGELOG (top of the athc section, one line each): `athc: every FAIL and WARN line is a sentence in Windows' words, names its file once and fits on one line`; `gameplan: play-list errors name the list file and the real line`. STATUS and WORKLOG: one entry each at the top.

- [ ] **Step 4: Line endings.** For every new or rewritten text file: `git ls-files --eol <file>` shows `w/crlf`.

- [ ] **Step 5: Final check, one command per call.** `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`. All green.

- [ ] **Step 6: Commit.** `git commit -am "athc: docs describe the error wording"`
