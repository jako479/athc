# fbpro98_lg2 Stock Leagues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `fbpro98_lg2` reads custom, modern stock and old stock `.lg2` files and says which one it read.

**Architecture:** Drop the stock rejection; the same entry parser already handles every layout. A `LeagueType` enum on `Lg2File`, judged by the first entry's folder field, replaces `UnsupportedLg2Error`.

**Tech Stack:** Python 3.13, pytest, ruff, pyright.

**Spec:** [docs/superpowers/specs/2026-10-09-lg2-stock-leagues-design.md](../specs/2026-10-09-lg2-stock-leagues-design.md)

## Global Constraints

- Text files UTF-8, CRLF, final newline.
- Commit messages one line, prefixed `fbpro98_lg2:` (or `check-ppp:`), no AI mention.
- Never change an existing assertion to make a test pass; tests that pin the old rejection are replaced because the request reverses it.

## Review Focus

- Custom league whose first entry has an empty folder: labeled `OLD_STOCK` (first-entry rule); locations still read correctly — pinned by the built-bytes rule test.
- Stock signature on a later entry or team: still `CUSTOM` — existing tests gain a `league_type` assertion.
- `STOCK` folder with other leftover text, or one character past the signature: `CUSTOM`.
- Truncated or field-corrupt stock file: `InvalidLg2Error`, same as custom.
- `check-ppp` pointed at a stock league: pairs are checked, exit 1 with findings.

---

### Task 1: Library reads stock leagues

**Files:**
- Modify: `src/athc/fbpro98_lg2/model.py`, `reader.py`, `__init__.py`
- Test: `tests/unit/fbpro98_lg2/test_reader.py`, `test_model.py`, `tests/unit/test_errors.py`

**Interfaces:**
- Produces: `LeagueType(Enum)` with `CUSTOM`, `MODERN_STOCK`, `OLD_STOCK`; `Lg2File(league_type: LeagueType, teams: tuple[TeamFiles, ...])`.

- [ ] **Step 1: Tests.** In `test_reader.py`: `_team` takes an empty folder (bare filename); replace `test_stock_league_rejected` with `test_custom_league_type`, `test_modern_stock_league` (30 teams, `MODERN_STOCK`, teams 0/1/29 = BILLS/COLTS/RAMS files under `STOCK`), `test_old_stock_league` (8 identical teams, `OLD_STOCK`, `OFF1.PRF`, `OFF.PLN`, `DEF1.PRF`, `DEF.PLN`, `OFF2.PRF`, `OFF.PLN`, `DEF2.PRF`, `DEF.PLN`); add `league_type is CUSTOM` to the later-entry, second-team and partial-signature tests, plus a `STOCK\0A\FBPRO97\STOCKX` case; add `test_first_entry_decides_league_type` (full signature → `MODERN_STOCK`, empty → `OLD_STOCK`, only entry 0 changed); rename the check-order tests to `test_stock_league_size_checked` (body unchanged) and `test_stock_league_fields_checked` (empty filename → `InvalidLg2Error` "Empty filename"). `test_model.py`: build with `league_type=LeagueType.CUSTOM`, assert it. `test_errors.py`: drop `UnsupportedLg2Error`.

```python
@pytest.mark.parametrize(
    ("folder", "league_type", "profile"),
    [
        (b"STOCK\x00A\\FBPRO97\\STOCK", LeagueType.MODERN_STOCK, "STOCK\\O1.prf"),
        (b"", LeagueType.OLD_STOCK, "O1.prf"),
    ],
)
def test_first_entry_decides_league_type(
    make_entry, make_team, make_entries, folder, league_type, profile
):
    lg2 = parse_lg2(make_team(make_entries(0, make_entry(folder=folder))))
    assert lg2.league_type is league_type
    assert lg2.teams[0].first_half.offense.profile == profile
    assert lg2.teams[0].first_half.offense.gameplan == "Plans\\Team\\O1.pln"
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/fbpro98_lg2 tests/unit/test_errors.py` — expect import failure on `LeagueType`.

- [ ] **Step 3: Implement.** `model.py`:

```python
class LeagueType(Enum):
    """Which of the three .lg2 layouts a file has; see specs/lg2.md."""

    CUSTOM = "custom"
    MODERN_STOCK = "modern stock"
    OLD_STOCK = "old stock"
```

`Lg2File` gains `league_type: LeagueType` as its first field. `reader.py`: delete `UnsupportedLg2Error` and `_check_stock`; add

```python
def _league_type(buffer: bytes) -> LeagueType:
    # Only the first entry decides; a later stock-looking entry is read as is.
    if buffer.startswith(MODERN_STOCK_FOLDER):
        return LeagueType.MODERN_STOCK
    if buffer.startswith(OLD_STOCK_FOLDER):
        return LeagueType.OLD_STOCK
    return LeagueType.CUSTOM
```

and build `Lg2File(league_type=_league_type(buffer), teams=...)`. Docstrings drop the stock `Raises`. `__init__.py` exports `LeagueType`, not `UnsupportedLg2Error`.

- [ ] **Step 4: Run** the same tests — PASS.

- [ ] **Step 5: Commit** `fbpro98_lg2: read stock leagues, modern and old; Lg2File.league_type says which`.

### Task 2: check-ppp with a stock league file

**Files:**
- Test: `tests/integration/test_check_ppp.py`, `tests/integration/README.md`

- [ ] **Step 1:** `test_dir_bad_league_file` keeps only the invalid-bytes case (plain test); add

```python
@pytest.mark.parametrize(
    "folder", ["STOCK\x00A\\FBPRO97\\STOCK", ""], ids=["modern", "old"]
)
def test_dir_stock_league_file(runner, lg2_league, tmp_path: Path, folder: str) -> None:
    """A stock league's .lg2 pairs files like any other."""
    lg2_league(team(off1=OFF, folder=folder))
    folder_path = put(tmp_path / "plans", OFF1, GP_OFFENSE)
    result = run(runner, folder_path)
    assert result.exit_code == 1
    assert "2 file(s) checked, 2 with violations, 0 failed" in result.stdout
```

- [ ] **Step 2: Run** `uv run pytest tests/integration/test_check_ppp.py` — PASS (no CLI code changes).
- [ ] **Step 3:** README rows: bad league file = invalid bytes; new stock row.
- [ ] **Step 4: Commit** `check-ppp: a stock league's .lg2 pairs files like any other`.

### Task 3: Docs and meta

**Files:** `docs/fbpro98_lg2/README.md`, `ARCHITECTURE.md`, `tests/unit/fbpro98_lg2/README.md`, `STATUS.md`, `CHANGELOG.md`, `WORKLOG.md`.

- [ ] **Step 1:** Library README: features, usage (`lg2.league_type`), API (`LeagueType`, first-entry rule, checks size then fields; no `UnsupportedLg2Error`). ARCHITECTURE: module layout, does / does not. Test README: new rows and count.
- [ ] **Step 2:** STATUS fbpro98_lg2 line; CHANGELOG top lines for the library and check-ppp; WORKLOG entry at the top.
- [ ] **Step 3: Commit** `fbpro98_lg2: docs for stock leagues`.

### Final

- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` — all green.
- [ ] One whole-branch review; fix findings; hand off.
