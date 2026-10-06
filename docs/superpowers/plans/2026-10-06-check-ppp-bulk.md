# check-ppp Pairs, Directory and Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `check-ppp` requires a profile and a gameplan, and checks every
`.lg2` pair found in a directory or tree.

**Architecture:** All new code lives in `src/athc/cli/check_ppp.py`: the
two-file path becomes `check_pair`, a new `check_directory` reads the league's
`.lg2` (`lg2_path` in `league.ini`), turns it into file-name pairs, finds them
per folder and reuses the existing per-pair reading and reports.

**Tech Stack:** Python 3.12, Click, `athc.fbpro98_lg2`, pytest.

**Spec:** `docs/superpowers/specs/2026-10-06-check-ppp-bulk-design.md`

## Global Constraints

- Python 3.12 syntax only; ruff (88 columns) and pyright standard must pass.
- Every text file UTF-8, CRLF, final newline.
- Output like `gameplan check` / `profile check`: reports and summary on
  stdout, errors via `logger.error("%s: ...", PROG, ...)`.
- Exit 0 clean, 1 findings, 2 error.
- Never modify `tests/integration/expected/*` goldens.
- Nothing under `E:\SIERRA` changes; test data is copied.

## Review Focus

- Same profile in two pairs (two gameplans): reported twice, each with its
  own cross-check — test in Task 3.
- A mismatched pair whose gameplan another pair shares: the gameplan is
  still reported with the later pair — test in Task 3.
- Single path that is a file: clear error, nothing checked — Task 2.
- Relative `lg2_path`: resolves against the league folder — Task 3.
- Same file names in sibling folders (weeks, seasons): never paired across
  folders — Task 4.

---

### Task 1: `lg2_path` setting

**Files:**
- Modify: `dev/leagues/PNFL/league.ini`, `dev/leagues/PCFL/league.ini`,
  `release/leagues/PNFL/league.ini`, `release/leagues/PCFL/league.ini`
- Test: `tests/integration/test_config.py` (`test_release_league_loads`)

- [ ] **Step 1: failing test** — add to `test_release_league_loads`:

```python
    assert cfg.values["lg2_path"]
```

- [ ] **Step 2:** `uv run pytest tests/integration/test_config.py -k release_league_loads` → FAIL (KeyError).
- [ ] **Step 3:** add `lg2_path = E:\SIERRA\FbPro98\PNFL.lg2` (PCFL:
  `PCFL.lg2`) under `[league]` in all four files; in the release copies a
  comment line above it: `; Needed for check-ppp on a directory -- your
  FbPro98 league file (.lg2).`
- [ ] **Step 4:** rerun → PASS.
- [ ] **Step 5:** commit `check-ppp: lg2_path league setting`.

### Task 2: both files required

**Files:**
- Modify: `src/athc/cli/check_ppp.py`
- Test: `tests/integration/test_check_ppp.py`, `tests/integration/test_cli_root.py`

**Interfaces:**
- Produces: `check_pair(first: str, second: str, league: str | None) -> int`,
  `summarize(reports: list[tuple[int, str]]) -> int`,
  `check_files(profile_path: Path, profile_rules: ProfileRules | None,
  gameplan_path: Path, gameplan_setup: tuple[Rules, PlayPool] | None, *,
  report_gameplan: bool = True) -> tuple[list[tuple[int, str]], str | None]`.

- [ ] **Step 1: tests** — replace the one-file tests with:

```python
@pytest.mark.parametrize("path", [OFF1, GP_OFFENSE])
def test_cli_one_file_is_an_error(runner, full_league, caplog, path) -> None:
    with caplog.at_level(logging.ERROR):
        result = run(runner, path)
    assert result.exit_code == 2
    assert (
        f"{path}: not a directory; pass one profile and one gameplan, "
        "or a directory" in caplog.text
    )
    assert result.stdout == ""
```

  and change: second-of-a-kind, bad input, missing file, malformed file,
  other-kind file, play-path, playpool and `--league` tests to pass pairs;
  argument errors now check nothing (`result.stdout == ""`).
  `test_cli_root.py`: check-ppp gets `[OFF1, GP_OFFENSE]` in
  `_unknown_league_args`; help metavars `path [path]`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** split the command body into `check_pair` / `summarize`;
  one argument goes to a directory check stub that errors when the path is a
  file; `sort_inputs` message `pass one profile and one gameplan`;
  `check_files` takes required paths.
- [ ] **Step 4:** run → PASS. Commit `check-ppp: a profile and a gameplan
  are both required`.

### Task 3: directory mode

**Interfaces:**
- Produces: `LG2_PATH_KEY = "lg2_path"`,
  `load_lg2(league: str | None, logged: set[str]) -> Lg2File | None`,
  `league_pairs(lg2: Lg2File) -> list[tuple[str, str]]` (casefolded names),
  `find_pairs(directory: Path, pairs: Sequence[tuple[str, str]]) ->
  list[tuple[Path, Path]]`,
  `check_directory(raw: str, league: str | None) -> int`.

- [ ] **Step 1: tests** (tmp folders, TST files under their own names,
  `.lg2` built from names):

```python
def lg2_team(*names: str, folder: str = "PNFL\\2049\\Plans\\Team") -> bytes:
    """One team record from its eight file names, in file order: per half,
    offense profile, offense gameplan, defense profile, defense gameplan."""
    assert len(names) == 8
    entries = b"".join(
        folder.encode("ascii").ljust(FOLDER_SIZE, b"\x00")
        + name.encode("ascii").ljust(FILENAME_SIZE, b"\x00")
        for name in names
    )
    return entries + bytes(TEAM_TRAILER_SIZE)
```

  Cases: goldens in `.lg2` order (offense pair, then defense pair: 4 files,
  35 violations); case-insensitive names; half pair skipped; shared
  gameplan once; same profile twice; same pair twice; unlisted files
  ignored; subfolder not searched; no pairs; mismatch continues and the
  shared gameplan reports later; unreadable file; setup error prints only
  error lines; no league logged once; `lg2_path` missing / file missing /
  invalid / stock; relative `lg2_path`; pair mode needs no `lg2_path`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** implement:

```python
def league_pairs(lg2: Lg2File) -> list[tuple[str, str]]:
    pairs: dict[tuple[str, str], None] = {}
    for team in lg2.teams:
        for half in (team.first_half, team.second_half):
            for pair in (half.offense, half.defense):
                key = (_name(pair.profile), _name(pair.gameplan))
                pairs.setdefault(key, None)
    return list(pairs)


def _name(location: str) -> str:
    return PureWindowsPath(location).name.casefold()


def find_pairs(directory, pairs):
    files = {p.name.casefold(): p for p in directory.iterdir() if p.is_file()}
    return [
        (files[prof], files[plan])
        for prof, plan in pairs
        if prof in files and plan in files
    ]
```

  `check_directory`: path checks → load profile rules, gameplan setup,
  `.lg2` → no `.lg2` exit 2 → find pairs (none: error, exit 2) → each pair
  through `check_files(..., report_gameplan=gameplan not yet reported)`;
  a mismatch becomes `(-1, line)` → setup failed: print lines, exit 2 →
  else `summarize`.
- [ ] **Step 4:** run → PASS. Commit `check-ppp: check every league-file
  pair in a directory`.

### Task 4: tree mode

- [ ] **Step 1: tests:** `-r` finds pairs in subfolders; folder order (top,
  then by name); a pair split across folders is not found; no pairs → `in
  tree`; real data: committed `data/ppp/2049/Plans/Denver (Brian)` (week 6
  copy) and `Las Vegas (Neil)` (Denver renamed: `LVOFF1.prf`,
  `RAIDEROFF.pln` …) with `data/PNFL.lg2`, 14 files in `.lg2` order, Denver
  part equal to the two-file reports.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** add `-r/--recursive`; `find_pairs(..., recursive=)` walks
  with `Path.walk`, sorting subfolders by `str.casefold`, matching each
  folder on its own.
- [ ] **Step 4:** run → PASS. Commit `check-ppp: -r checks a whole tree`.

### Task 5: docs and finish

- [ ] `docs/check_ppp/README.md`, `docs/design/config.md`,
  `release/docs/COMMANDS.txt`, `release/docs/README.txt`,
  `tests/integration/README.md`, `CHANGELOG.md`, `STATUS.md`.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`,
  `uv run pyright` all green.
- [ ] One whole-branch review; fix findings; rerun the four commands.
- [ ] Commit `check-ppp: docs`.
