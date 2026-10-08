# League category labels in league.toml — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A league's short names for the game's play categories come from `league.toml` instead of the category enum, and the league settings file becomes TOML.

**Architecture:** A new `CategoryLabels` value in `fbpro98_play` holds and validates a league's offense/defense labels. `athc.config` reads `league.toml` with `tomllib` and hands every tool a `LeagueConfig` carrying `categories`. The gameplan rules loader, the play-pool reader and `replace-play` take the labels instead of reading `short` off the enum; `short` and `category_by_short` are then deleted.

**Tech Stack:** Python 3.12, `tomllib` (stdlib), pytest, ruff, pyright.

**Spec:** [docs/superpowers/specs/2026-10-07-league-toml-categories-design.md](../specs/2026-10-07-league-toml-categories-design.md)

## Global Constraints

- Python 3.12 syntax only (pyright is pinned to 3.12); full type hints; ruff format at 88 columns, double quotes.
- Every text file is UTF-8, CRLF, final newline. New files written by a tool that emits LF are converted before the commit (command in Task 1, step 7).
- Commit messages: one line, prefixed with the owning tool (`fbpro98_play:`, `config:`, `gameplan:`, `playpool:`, `athc:`). Never mention Claude, Anthropic or any AI tool.
- Never change an expected test value to make a test pass; the behavior changes below are the spec's, and each one is named.
- All four checks green before a task is called done, run one per call from the worktree root:
  `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`
- Only `league.ini` becomes TOML. `athc.ini` and `standings\<season>.league.ini` stay INI; nothing in this plan touches the scheduler.
- Labels exist for offense and defense only; special-teams categories always go by game name.
- Rule-file section names stay: the league label where `league.toml` defines one, else the game name in quotes.
- No `%(key)s` interpolation in `league.toml`.

## Review Focus

Inputs the spec implies but no existing test exercised; each has a test in the task that owns the code.

1. A label used by both offense and defense (`"Run Right" = "RR"` on both sides) must resolve a play-pool folder to the play's own side, never warn. → Task 4.
2. A `league.toml` with no `[categories]` at all must load, and every category then goes by its game name (rules sections `[offense."Run Middle"]`, output `(Run Left)`). → Tasks 2, 3, 4.
3. A `[league]` value of the wrong type (`play_path = 1`, `gameplan_rules = ['a', 1]`) must be a config-file error naming the file, not a crash deeper in a tool. → Task 2.
4. A Windows path with `%` (`'%LOCALAPPDATA%\plays'`) must load literally now that there is no interpolation. → Task 2.
5. A rules section keyed by a category's game name when the league labels that category (`[offense."Run Middle"]` with `"Run Middle" = "RM"`) must be rejected with the message listing the valid labels. → Task 3.

---

### Task 1: `CategoryLabels` in `fbpro98_play`

**Files:**
- Create: `src/athc/fbpro98_play/labels.py`
- Modify: `src/athc/fbpro98_play/__init__.py`
- Create: `tests/unit/fbpro98_play/test_labels.py`
- Modify: `tests/unit/fbpro98_play/README.md`

**Interfaces:**
- Consumes: `OffensiveCategory`, `DefensiveCategory`, `PlayCategory` from `athc.fbpro98_play.model` (each member has `.long`, the game name).
- Produces: `CategoryLabels` (frozen dataclass): `offense: Mapping[OffensiveCategory, str]`, `defense: Mapping[DefensiveCategory, str]`; `CategoryLabels()` is "no labels"; `CategoryLabels.from_tables(offense: Mapping[str, object], defense: Mapping[str, object]) -> CategoryLabels` (raises `ValueError`); `label(category: PlayCategory) -> str`; `offense_by_label(label: str) -> OffensiveCategory | None`; `defense_by_label(label: str) -> DefensiveCategory | None`. Exported from `athc.fbpro98_play`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/fbpro98_play/test_labels.py`:

```python
"""Unit tests for CategoryLabels: a league's offense/defense category labels."""

from __future__ import annotations

import re

import pytest

from athc.fbpro98_play import (
    CategoryLabels,
    DefensiveCategory,
    OffensiveCategory,
    SpecialOffensiveCategory,
)

OFFENSE = {"Run Right": "RR", "Pass Short Right": "PSR"}
DEFENSE = {"Run Right": "RunRight", "Pass Short": "PassShort"}


def test_from_tables_maps_game_names_to_members() -> None:
    labels = CategoryLabels.from_tables(OFFENSE, DEFENSE)
    assert labels.offense == {
        OffensiveCategory.RUN_RIGHT: "RR",
        OffensiveCategory.PASS_SHORT_RIGHT: "PSR",
    }
    assert labels.defense == {
        DefensiveCategory.RUN_RIGHT: "RunRight",
        DefensiveCategory.PASS_SHORT: "PassShort",
    }


def test_label_is_league_label_else_game_name() -> None:
    labels = CategoryLabels.from_tables(OFFENSE, DEFENSE)
    assert labels.label(OffensiveCategory.RUN_RIGHT) == "RR"
    assert labels.label(OffensiveCategory.PASS_LONG_LEFT) == "Pass Long Left"
    assert labels.label(DefensiveCategory.RUN_RIGHT) == "RunRight"
    assert labels.label(DefensiveCategory.PASS_LONG) == "Pass Long"
    assert labels.label(SpecialOffensiveCategory.PUNT) == "Punt"


def test_no_labels_uses_game_names_everywhere() -> None:
    labels = CategoryLabels()
    assert labels.label(OffensiveCategory.RUN_RIGHT) == "Run Right"
    assert labels.offense_by_label("Run Right") is None
    assert labels.offense_by_label("RR") is None


def test_by_label_resolves_within_its_side() -> None:
    labels = CategoryLabels.from_tables(OFFENSE, DEFENSE)
    assert labels.offense_by_label("PSR") is OffensiveCategory.PASS_SHORT_RIGHT
    assert labels.defense_by_label("PassShort") is DefensiveCategory.PASS_SHORT
    assert labels.offense_by_label("PassShort") is None
    assert labels.defense_by_label("PSR") is None
    # A game name is not a label.
    assert labels.offense_by_label("Pass Short Right") is None


def test_same_label_on_both_sides_is_allowed() -> None:
    labels = CategoryLabels.from_tables({"Run Right": "RR"}, {"Run Right": "RR"})
    assert labels.offense_by_label("RR") is OffensiveCategory.RUN_RIGHT
    assert labels.defense_by_label("RR") is DefensiveCategory.RUN_RIGHT


def test_label_may_equal_the_other_sides_game_name() -> None:
    labels = CategoryLabels.from_tables({}, {"Run Right": "Pass Short Right"})
    assert labels.defense_by_label("Pass Short Right") is DefensiveCategory.RUN_RIGHT


@pytest.mark.parametrize(
    ("offense", "defense", "message"),
    [
        (
            {"Run Rite": "RR"},
            {},
            "[categories.offense] 'Run Rite': not a game category name for offense",
        ),
        (
            {},
            {"Pass Short Right": "PSR"},
            "[categories.defense] 'Pass Short Right': not a game category name "
            "for defense",
        ),
        ({"Run Right": 1}, {}, "'Run Right': label must be a non-empty string"),
        ({"Run Right": ""}, {}, "'Run Right': label must be a non-empty string"),
        ({"Run Right": " "}, {}, "'Run Right': label must be a non-empty string"),
        (
            {"Run Right": "Run Left"},
            {},
            "'Run Right': label 'Run Left' is a game category name for offense",
        ),
        (
            {},
            {"Run Right": "Pass Long"},
            "'Run Right': label 'Pass Long' is a game category name for defense",
        ),
        (
            {"Run Right": "X", "Run Left": "X"},
            {},
            "'Run Left': label 'X' already used by 'Run Right'",
        ),
    ],
)
def test_from_tables_rejects(
    offense: dict[str, object], defense: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        CategoryLabels.from_tables(offense, defense)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_play/test_labels.py -q`
Expected: ImportError, `CategoryLabels` not found.

- [ ] **Step 3: Write the module**

Create `src/athc/fbpro98_play/labels.py`:

```python
"""A league's labels for the offense and defense play categories.

Leagues abbreviate the game's category names (PNFL: `PSR` for Pass Short Right,
`RunLeft` for defense Run Left). The labels come from the league's settings
file; this module only holds and validates them. Special-teams categories have
no labels and always go by their game name.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from athc.fbpro98_play.model import DefensiveCategory, OffensiveCategory, PlayCategory


@dataclass(frozen=True, slots=True)
class CategoryLabels:
    """League label per offense / defense category. A category absent from its
    mapping has no label and goes by its game name. `CategoryLabels()` is a league
    with no labels."""

    offense: Mapping[OffensiveCategory, str] = field(default_factory=dict)
    defense: Mapping[DefensiveCategory, str] = field(default_factory=dict)

    @classmethod
    def from_tables(
        cls, offense: Mapping[str, object], defense: Mapping[str, object]
    ) -> CategoryLabels:
        """Build from two game-name -> label tables (the `[categories.offense]`
        and `[categories.defense]` tables of league.toml). ValueError names the
        first bad entry: a key that is not a category of that side, a label that
        is not a non-empty string, repeats within the side, or equals one of the
        side's category names."""
        return cls(
            _validate("offense", offense, list(OffensiveCategory)),
            _validate("defense", defense, list(DefensiveCategory)),
        )

    def label(self, category: PlayCategory) -> str:
        """The league label for `category`, else its game name."""
        if isinstance(category, OffensiveCategory):
            return self.offense.get(category, category.long)
        if isinstance(category, DefensiveCategory):
            return self.defense.get(category, category.long)
        return category.long

    def offense_by_label(self, label: str) -> OffensiveCategory | None:
        """The offense category the league calls `label`; None when none does."""
        return _by_label(self.offense, label)

    def defense_by_label(self, label: str) -> DefensiveCategory | None:
        """The defense category the league calls `label`; None when none does."""
        return _by_label(self.defense, label)


def _validate[C: PlayCategory](
    side: str, table: Mapping[str, object], members: Iterable[C]
) -> dict[C, str]:
    by_name = {m.long: m for m in members}
    result: dict[C, str] = {}
    used: dict[str, str] = {}  # label -> game name that claimed it
    for name, value in table.items():
        where = f"[categories.{side}] {name!r}"
        member = by_name.get(name)
        if member is None:
            raise ValueError(f"{where}: not a game category name for {side}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{where}: label must be a non-empty string")
        if value in by_name:
            raise ValueError(
                f"{where}: label {value!r} is a game category name for {side}"
            )
        if value in used:
            raise ValueError(f"{where}: label {value!r} already used by {used[value]!r}")
        used[value] = name
        result[member] = value
    return result


def _by_label[C: PlayCategory](labels: Mapping[C, str], label: str) -> C | None:
    for member, value in labels.items():
        if value == label:
            return member
    return None
```

- [ ] **Step 4: Export it**

In `src/athc/fbpro98_play/__init__.py` add, after the `model` import block:

```python
from athc.fbpro98_play.labels import CategoryLabels
```

and `"CategoryLabels",` to `__all__` (alphabetical: after `"CategoryLabels"` comes `"DefensiveCategory"`).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/fbpro98_play -q`
Expected: all pass.

- [ ] **Step 6: Test matrix**

In `tests/unit/fbpro98_play/README.md`, after the `## model.py — category enum & resolve_category` table, add:

```markdown
## labels.py — `CategoryLabels` (a league's offense/defense labels)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Tables → members | game name → label | `offense` / `defense` keyed by enum member | `test_from_tables_maps_game_names_to_members` | ☑ |
| `label()` | labeled / unlabeled / special | league label; game name; game name | `test_label_is_league_label_else_game_name` | ☑ |
| No labels | `CategoryLabels()` | game names; `*_by_label` → None | `test_no_labels_uses_game_names_everywhere` | ☑ |
| `*_by_label` per side | label, other side's label, game name | member; None; None | `test_by_label_resolves_within_its_side` | ☑ |
| Same label both sides | `RR` offense + defense | each side resolves its own | `test_same_label_on_both_sides_is_allowed` | ☑ |
| Label equals other side's game name | defense `"Pass Short Right"` | accepted | `test_label_may_equal_the_other_sides_game_name` | ☑ |
| Rejected tables | unknown key; non-string / empty / blank label; own-side game name; duplicate | `ValueError` naming the entry | `test_from_tables_rejects` `[P]` | ☑ |
```

- [ ] **Step 7: Line endings, then the four checks**

Convert the two new files to CRLF:

```bash
python -c "import pathlib; [p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')) for p in map(pathlib.Path, ['src/athc/fbpro98_play/labels.py', 'tests/unit/fbpro98_play/test_labels.py'])]"
```

Then run, one per call: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`. All green.

- [ ] **Step 8: Commit**

```bash
git add src/athc/fbpro98_play/labels.py src/athc/fbpro98_play/__init__.py tests/unit/fbpro98_play/test_labels.py tests/unit/fbpro98_play/README.md
git commit -m "fbpro98_play: CategoryLabels holds a league's category labels"
```

---

### Task 2: `league.toml` — loader, shipped files, installer, test fixtures

**Files:**
- Modify: `src/athc/config.py`
- Modify: `src/athc/gameplan/config.py:36-39`, `src/athc/cli/check_playpool.py:46-52`, `src/athc/pdbtoexcel/main.py:24-28`, `src/athc/cli/check_ppp.py:87`
- Create: `config/dev/leagues/PNFL/league.toml`, `config/dev/leagues/PCFL/league.toml`, `config/release/leagues/PNFL/league.toml`, `config/release/leagues/PCFL/league.toml`
- Delete: the four `league.ini` files in those folders
- Modify: `config/release/install.bat:32,46`, `config/release/release-build.ps1:54`, `config/release/athc.ini:4-9,28-29`, `config/dev/athc.ini:5`, every `config/*/leagues/*/gameplan.toml:2` and `config/*/leagues/*/profile.toml:2`
- Modify: `tests/conftest.py`, `tests/integration/test_config.py`, `tests/integration/test_check_playpool.py:42`, `tests/integration/test_check_ppp.py:62-64,757-762,781-784`, `tests/integration/test_convert_pdb.py:49,114,170,195`, `tests/integration/test_gameplan_check.py:39,294-296,315,345,358-361`, `tests/integration/test_gameplan_replace_play.py:38,459-461`, `tests/integration/test_gameplan_set_normals.py:26,194-196`, `tests/integration/test_gameplan_set_specials.py:26,189-191`, `tests/integration/test_profile_check.py:342,349-352,372`, `tests/unit/pdbtoexcel/test_config.py:46`, `tests/integration/README.md`, `tests/unit/pdbtoexcel/README.md`

**Interfaces:**
- Consumes: `CategoryLabels` (Task 1).
- Produces: `athc.config.LEAGUE_FILE == "league.toml"`; `LeagueConfig(name, dir, values: dict[str, str], lists: dict[str, tuple[str, ...]] = {}, categories: CategoryLabels = CategoryLabels())`; `LeagueConfig.rule_files(key, default)` reads the array under `key` from `lists`; `load_league()` still returns `dict[str, str]` (athc-admin depends on it). Test helpers in `tests/conftest.py`: `PNFL_OFFENSE`, `PNFL_DEFENSE` (dict[str, str]), `PNFL_LABELS` (CategoryLabels), `CATEGORIES_TOML` (str), `league_toml(play_path=None, *, labels=True) -> str`.

- [ ] **Step 1: Test fixtures**

In `tests/conftest.py`:

Add the import `from athc.fbpro98_play import CategoryLabels` next to the other imports, and after `OTHER_LEAGUE = "other_league"` add:

```python
# The PNFL labels. Real league names are fine in fixtures; they are data, not
# league-aware logic.
PNFL_OFFENSE: dict[str, str] = {
    "Run Right": "RR",
    "Pass Short Right": "PSR",
    "Run Left": "RL",
    "Pass Short Left": "PSL",
    "Run Middle": "RM",
    "Pass Short Middle": "PSM",
    "Razzle Dazzle Pass": "PRD",
    "Pass Medium Right": "PMR",
    "Pass Medium Left": "PML",
    "Pass Medium Middle": "PMM",
    "Pass Long Right": "PLR",
    "Goal Line Run": "GLR",
    "Goal Line Pass": "GLP",
}
PNFL_DEFENSE: dict[str, str] = {
    "Run Right": "RunRight",
    "Pass Short": "PassShort",
    "Run Left": "RunLeft",
    "Run Middle": "RunMiddle",
    "Run Dazzle": "RunDazzle",
    "Pass Dazzle": "PassDazzle",
    "Pass Medium": "PassMedium",
    "Pass Long": "PassLong",
    "Goal Line Run": "GLrun",
    "Goal Line Pass": "GLpass",
}
PNFL_LABELS = CategoryLabels.from_tables(PNFL_OFFENSE, PNFL_DEFENSE)


def _categories_table(side: str, labels: dict[str, str]) -> str:
    lines = "".join(f'"{name}" = "{label}"\n' for name, label in labels.items())
    return f"[categories.{side}]\n{lines}"


# The `[categories.*]` tables of a test league.toml: the PNFL labels.
CATEGORIES_TOML = _categories_table("offense", PNFL_OFFENSE) + _categories_table(
    "defense", PNFL_DEFENSE
)


def league_toml(play_path: Path | str | None = None, *, labels: bool = True) -> str:
    """A league.toml body: `play_path` when given and, by default, the PNFL
    category labels."""
    body = "[league]\n"
    if play_path is not None:
        body += f"play_path = '{play_path}'\n"
    return body + (CATEGORIES_TOML if labels else "")
```

In `make_league_dir`, change the docstring word `league.ini` to `league.toml` and the write call to `write_config_file(folder, body, "league.toml")`. In `write_config_file`'s docstring change "Write raw INI" to "Write a raw config file".

- [ ] **Step 2: Rewrite the league-file tests in `tests/integration/test_config.py`**

Module docstring: `leagues/<NAME>/league.ini` → `leagues/<NAME>/league.toml`.

Add to the imports: `from athc.fbpro98_play import CategoryLabels` and extend the `tests.conftest` import to `from tests.conftest import CATEGORIES_TOML, LEAGUE, OTHER_LEAGUE, PNFL_LABELS`.

Replace every body `"[league]\nplay_path = D:/p\n"` (lines 44, 51, 60, 88) with `"[league]\nplay_path = 'D:/p'\n"`.

Line 95: rename `test_missing_league_ini_gives_empty_values` → `test_missing_league_toml_gives_empty_values`.

Line 101: body → `"[league]\nplay_path = 'plays'\nabs = 'D:/x'\n"`.

Lines 134-138 body → `"[league]\ngameplan_rules = ['base.toml', 'D:\\house.toml']\n"` (the rest of the test is unchanged).

Replace `test_percent_in_league_ini_is_config_file_error` (lines 217-224) with:

```python
def test_percent_in_league_toml_is_literal(make_league: MakeLeague) -> None:
    # TOML has no %-interpolation, so a native Windows `%LOCALAPPDATA%` path
    # loads as written.
    make_league(LEAGUE, "[league]\nplay_path = '%LOCALAPPDATA%\\plays'\n")
    assert load_league(LEAGUE)["play_path"] == "%LOCALAPPDATA%\\plays"
```

Rename `test_malformed_league_ini_errors` → `test_malformed_league_toml_errors` and assert `str(folder / "league.toml") in str(exc.value)`.

Replace the `# ── %(key)s interpolation inside league.ini ──` section (lines 258-266) with:

```python
# ── [league] value types ──


def test_no_interpolation_in_league_toml(make_league: MakeLeague) -> None:
    body = "[league]\nleague_root = 'D:/x'\nplay_path = '%(league_root)s/plays'\n"
    make_league(LEAGUE, body)
    assert load_league(LEAGUE)["play_path"] == "%(league_root)s/plays"


def test_league_list_is_kept_apart_from_values(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\ngameplan_rules = ['a.toml']\n")
    cfg = load_league_config(LEAGUE)
    assert cfg.values == {"play_path": "D:/p"}
    assert cfg.lists == {"gameplan_rules": ("a.toml",)}


@pytest.mark.parametrize(
    "body",
    [
        "[league]\nplay_path = 1\n",
        "[league]\ngameplan_rules = ['a.toml', 1]\n",
        "[league]\nplay_path = { x = 1 }\n",
    ],
)
def test_league_value_wrong_type_errors(make_league: MakeLeague, body: str) -> None:
    folder = make_league(LEAGUE, body)
    with pytest.raises(ConfigFileError) as exc:
        load_league_config(LEAGUE)
    assert "expected a string or an array of strings" in str(exc.value)
    assert str(folder / "league.toml") in str(exc.value)


def test_league_section_not_a_table_errors(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "league = 1\n")
    with pytest.raises(ConfigFileError, match=r"\[league\] must be a table"):
        load_league_config(LEAGUE)


# ── [categories] → CategoryLabels ──


def test_categories_load(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n" + CATEGORIES_TOML)
    assert load_league_config(LEAGUE).categories == PNFL_LABELS


def test_categories_absent_is_no_labels(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n")
    assert load_league_config(LEAGUE).categories == CategoryLabels()


def test_one_side_only_loads(make_league: MakeLeague) -> None:
    make_league(LEAGUE, '[categories.defense]\n"Run Left" = "RunLeft"\n')
    cfg = load_league_config(LEAGUE)
    assert cfg.categories.offense == {}
    assert cfg.categories.defense_by_label("RunLeft") is not None


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ('[categories.offense]\n"Run Rite" = "RR"\n', "not a game category name"),
        ('[categories.offense]\n"Run Right" = ""\n', "non-empty string"),
        ('[categories.offense]\n"Run Right" = 1\n', "non-empty string"),
        ('[categories.offense]\n"Run Right" = "RR"\n"Run Left" = "RR"\n', "already used"),
        ('[categories.defense]\n"Run Right" = "Run Left"\n', "is a game category name"),
        ("[categories]\noffense = 1\n", r"\[categories.offense\] must be a table"),
        ("categories = 1\n", r"\[categories\] must be a table"),
    ],
)
def test_categories_errors_name_the_file(
    make_league: MakeLeague, body: str, message: str
) -> None:
    folder = make_league(LEAGUE, body)
    with pytest.raises(ConfigFileError, match=message) as exc:
        load_league_config(LEAGUE)
    assert str(folder / "league.toml") in str(exc.value)
```

In `test_release_league_loads` (line ~370) add a last line `assert cfg.categories.offense and cfg.categories.defense`.

- [ ] **Step 3: Run the config tests to verify they fail**

Run: `uv run pytest tests/integration/test_config.py -q`
Expected: failures (the loader still reads `league.ini`; `lists`/`categories` do not exist).

- [ ] **Step 4: Rewrite the loader in `src/athc/config.py`**

Imports: add `import tomllib`, `from collections.abc import Mapping`, `from typing import Any`, change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`, and add `from athc.fbpro98_play import CategoryLabels`.

Constants:

```python
LEAGUE_FILE = "league.toml"
LEAGUE_SECTION = "league"
CATEGORIES_SECTION = "categories"
```

`ConfigFileError` docstring:

```python
    """athc.ini or a league.toml cannot be read: malformed file, bad
    %-interpolation in athc.ini, a wrong value type or a bad category label."""
```

`LeagueConfig`:

```python
@dataclass(frozen=True)
class LeagueConfig:
    """One league folder: its name, path and the `[league]` table of its
    `league.toml` — string values in `values`, arrays of strings in `lists`
    (missing file -> empty) — plus the league's category labels."""

    name: str
    dir: Path
    values: dict[str, str]
    lists: dict[str, tuple[str, ...]] = field(default_factory=dict)
    categories: CategoryLabels = field(default_factory=CategoryLabels)
```

`rule_files`:

```python
    def rule_files(self, key: str, default: str) -> tuple[Path, ...]:
        """The ordered rule files for a tool: the array under `key` in
        `league.toml` when present (later files layer over earlier ones), else the
        fixed `<default>` file in the league folder when it exists, else nothing."""
        names = self.lists.get(key)
        if names:
            return tuple(self._resolve(name) for name in names)
        fixed = self.rules_file(default)
        return (fixed,) if fixed else ()
```

`load_league_config` and helpers (replace the whole function):

```python
def load_league_config(league: str | None = None) -> LeagueConfig:
    """Resolve the league and read `leagues\\<name>\\league.toml`.

    Set `ATHC_CONFIG_DIR` to override the config dir.
    """
    name = resolve_league(league)
    folder = league_dir(name)
    path = folder / LEAGUE_FILE
    if not path.is_file():
        return LeagueConfig(name=name, dir=folder, values={})
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ConfigFileError(f"{path}: {e}") from e
    values, lists = _league_values(_table(data, LEAGUE_SECTION, path), path)
    categories = _category_labels(_table(data, CATEGORIES_SECTION, path), path)
    return LeagueConfig(
        name=name, dir=folder, values=values, lists=lists, categories=categories
    )


def _table(
    data: Mapping[str, Any], key: str, path: Path, name: str | None = None
) -> Mapping[str, Any]:
    """`data[key]` as a TOML table (`{}` when absent); ConfigFileError otherwise.
    `name` is the table's full dotted name for the message."""
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise ConfigFileError(f"{path}: [{name or key}] must be a table")
    return value


def _league_values(
    table: Mapping[str, Any], path: Path
) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    """Split `[league]` into string values and string arrays; anything else is a
    ConfigFileError."""
    values: dict[str, str] = {}
    lists: dict[str, tuple[str, ...]] = {}
    for key, value in table.items():
        if isinstance(value, str):
            values[key] = value
        elif isinstance(value, list) and all(isinstance(v, str) for v in value):
            lists[key] = tuple(value)
        else:
            raise ConfigFileError(
                f"{path}: [{LEAGUE_SECTION}] {key}: expected a string or an array "
                "of strings"
            )
    return values, lists


def _category_labels(table: Mapping[str, Any], path: Path) -> CategoryLabels:
    """`[categories.offense]` / `[categories.defense]` as the league's labels."""
    offense = _table(table, "offense", path, f"{CATEGORIES_SECTION}.offense")
    defense = _table(table, "defense", path, f"{CATEGORIES_SECTION}.defense")
    try:
        return CategoryLabels.from_tables(offense, defense)
    except ValueError as e:
        raise ConfigFileError(f"{path}: {e}") from e
```

`load_league` docstring: ``"""The `[league]` string values of the resolved league's `league.toml`. Kept for callers that only need the raw mapping (athc-admin)."""``

Leave `load_config` / `set_config_value` (athc.ini) as they are.

- [ ] **Step 5: Messages and docstrings that name the file**

- `src/athc/gameplan/config.py`: import `LEAGUE_FILE` from `athc.config`; line 38 → `f"no play_path for the league; set play_path in {cfg.dir / LEAGUE_FILE}"`; module docstring: `the gameplan_rules list` stays, no file name there.
- `src/athc/cli/check_playpool.py`: import `LEAGUE_FILE` from `athc.config`; line 50 `cfg.dir / "league.ini"` → `cfg.dir / LEAGUE_FILE`.
- `src/athc/pdbtoexcel/main.py:27`: `(set play_path in the league's league.ini)` → `(set play_path in the league's league.toml)`.
- `src/athc/cli/check_ppp.py:87` docstring: `league.ini` → `league.toml`.

Verify nothing else in `src/` names the old file (standings references in the scheduler are a different file and stay):

```bash
grep -rn "league\.ini" src --include=*.py | grep -v "\.league\.ini\|scheduler"
```

Expected: no output.

- [ ] **Step 6: Shipped `league.toml` files**

Create `config/release/leagues/PNFL/league.toml`:

```toml
# PNFL league settings. Rules live here (gameplan.toml, profile.toml,
# playpool.toml, scheduler.toml) and season standings in standings\
# (<season>.league.ini). Reinstalling never overwrites this file.

[league]
# Needed for check-ppp on a directory -- the folder that holds this
# league's files (PNFL.lg2 and the rest).
path = 'C:\SIERRA\FBPRO98'
# REQUIRED for gameplan/profile/convert-pdb -- your FbPro98 league plays folder.
play_path = 'C:\SIERRA\FBPRO98\PNFL'
# Optional: ordered rule files replacing the fixed gameplan.toml / profile.toml;
# later files layer over earlier ones.
# gameplan_rules = ['gameplan.toml']
# profile_rules = ['profile.toml']

# The league's short names for the game's play categories, as the rule files
# and the play-pool folders use them. A category with no league name is
# commented out and goes by its game name.
[categories.offense]
"Run Right" = "RR"
"Pass Short Right" = "PSR"
"Run Left" = "RL"
"Pass Short Left" = "PSL"
"Run Middle" = "RM"
"Pass Short Middle" = "PSM"
# "Razzle Dazzle Run" = ""
"Razzle Dazzle Pass" = "PRD"
"Pass Medium Right" = "PMR"
"Pass Medium Left" = "PML"
"Pass Medium Middle" = "PMM"
"Pass Long Right" = "PLR"
# "Pass Long Left" = ""
# "Pass Long Middle" = ""
"Goal Line Run" = "GLR"
"Goal Line Pass" = "GLP"
# "User Specific" = ""

[categories.defense]
"Run Right" = "RunRight"
"Pass Short" = "PassShort"
"Run Left" = "RunLeft"
"Run Middle" = "RunMiddle"
"Run Dazzle" = "RunDazzle"
"Pass Dazzle" = "PassDazzle"
"Pass Medium" = "PassMedium"
"Pass Long" = "PassLong"
"Goal Line Run" = "GLrun"
"Goal Line Pass" = "GLpass"
# "User Specific" = ""
```

Create `config/release/leagues/PCFL/league.toml`: the same file with `PNFL` → `PCFL` in the two comments, `path = 'E:\SIERRA\FbPro98'`, `play_path = 'E:\SIERRA\FbPro98\PCFL'` (the values the PCFL file has today), and the same two category tables.

Create `config/dev/leagues/PNFL/league.toml` (no comments; the commented-out categories are the listing of unlabeled categories, not commentary, and stay):

```toml
[league]
path = 'E:\SIERRA\FbPro98'
play_path = 'E:\SIERRA\FbPro98\PNFL'
db_path = 'E:\PNFL\Game Log Database\49W4\pnfl_athc.db'

[categories.offense]
"Run Right" = "RR"
"Pass Short Right" = "PSR"
"Run Left" = "RL"
"Pass Short Left" = "PSL"
"Run Middle" = "RM"
"Pass Short Middle" = "PSM"
# "Razzle Dazzle Run" = ""
"Razzle Dazzle Pass" = "PRD"
"Pass Medium Right" = "PMR"
"Pass Medium Left" = "PML"
"Pass Medium Middle" = "PMM"
"Pass Long Right" = "PLR"
# "Pass Long Left" = ""
# "Pass Long Middle" = ""
"Goal Line Run" = "GLR"
"Goal Line Pass" = "GLP"
# "User Specific" = ""

[categories.defense]
"Run Right" = "RunRight"
"Pass Short" = "PassShort"
"Run Left" = "RunLeft"
"Run Middle" = "RunMiddle"
"Run Dazzle" = "RunDazzle"
"Pass Dazzle" = "PassDazzle"
"Pass Medium" = "PassMedium"
"Pass Long" = "PassLong"
"Goal Line Run" = "GLrun"
"Goal Line Pass" = "GLpass"
# "User Specific" = ""
```

Create `config/dev/leagues/PCFL/league.toml`: the same with `play_path = 'E:\SIERRA\FbPro98\PCFL'` and `db_path = 'E:\PNFL\Game Log Database\49W4\pcfl_athc.db'`.

Delete the old files:

```bash
git rm -q config/dev/leagues/PNFL/league.ini config/dev/leagues/PCFL/league.ini config/release/leagues/PNFL/league.ini config/release/leagues/PCFL/league.ini
```

Convert the four new files to CRLF:

```bash
python -c "import pathlib; [p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')) for p in pathlib.Path('config').glob('*/leagues/*/league.toml')]"
```

- [ ] **Step 7: Installer, athc.ini comments, rule-file headers**

`config/release/install.bat`:
- line 32: `REM   - athc.ini, each league's league.toml and standings\ are user-owned ->`
- line 46: `    if not exist "%DEST%\%%L\league.toml" copy /Y "%%L\league.toml" "%DEST%\%%L\league.toml" >NUL`

`config/release/release-build.ps1:54`: `# folder (each league's league.toml, rule files and standings\).`

`config/release/athc.ini` lines 4-9 become:

```ini
; Each league is a folder under leagues\ next to this file, holding its
; league.toml (path, play_path, the league's category names), rule files
; (gameplan.toml, profile.toml, playpool.toml, scheduler.toml) and standings\
; (<season>.league.ini). The one thing you must set is play_path in
; leagues\PNFL\league.toml: your FbPro98 league plays folder. To run check-ppp
; on a folder, also set path there: the folder that holds the league's files.
```

and line 29: `; leagues\<NAME>\league.toml plus playpool.toml.`

`config/dev/athc.ini:5`: `; rules and standings live under leagues\<NAME>\ (see leagues\PNFL\league.toml).`

Rule-file headers, all eight files:

```bash
sed -i 's/in league\.ini\./in league.toml./' config/dev/leagues/PNFL/gameplan.toml config/dev/leagues/PNFL/profile.toml config/dev/leagues/PCFL/gameplan.toml config/dev/leagues/PCFL/profile.toml config/release/leagues/PNFL/gameplan.toml config/release/leagues/PNFL/profile.toml config/release/leagues/PCFL/gameplan.toml config/release/leagues/PCFL/profile.toml
```

Verify with `grep -rn "league\.ini" config | grep -v "\.league\.ini"` → no output.

- [ ] **Step 8: Convert the other tests' league bodies**

Each body is INI today; the new text is TOML. Paths go in single quotes.

`tests/integration/test_check_playpool.py:42`: `f"[league]\nplay_path = {play_path}\n"` → `f"[league]\nplay_path = '{play_path}'\n"`.

`tests/integration/test_check_ppp.py`:
- import `CATEGORIES_TOML` from `tests.conftest` (alongside `LEAGUE`).
- lines 63-64:
  ```python
        lines = [f"{key} = '{value}'\n" for key, value in settings if value]
        body = "[league]\n" + "".join(lines) + CATEGORIES_TOML if lines else None
  ```
- lines 757-762 (test `test_cli_rule_lists_in_league_ini`; rename it `test_cli_rule_lists_in_league_toml`):
  ```python
    folder = make_league(
        LEAGUE,
        f"[league]\nplay_path = '{PLAYS}'\n"
        "profile_rules = ['my-profile.toml']\n"
        "gameplan_rules = ['my-gameplan.toml']\n" + CATEGORIES_TOML,
    )
  ```
- lines 781-784:
  ```python
    (folder / "league.toml").write_text(
        f"[league]\nplay_path = '{PLAYS}'\n{key} = ['gone.toml']\n" + CATEGORIES_TOML,
        encoding="utf-8",
    )
  ```

`tests/integration/test_convert_pdb.py`: lines 49, 114, 170 → wrap the f-string value in single quotes (`play_path = '{plays}'`, `play_path = '{not_a_dir}'`, `play_path = '{tmp_path}'`); line 195 → `"[league]\nplay_path = 'plays'\n"`.

`tests/integration/test_gameplan_check.py`: import `league_toml` and `CATEGORIES_TOML` from `tests.conftest`; line 39 → `folder = make_league(LEAGUE, league_toml(PLAYS))`; lines 294-296 →
```python
    (league / "league.toml").write_text(
        league_toml(tmp_path / "nope"), encoding="utf-8"
    )
```
line 315 and line 345 → `make_league(LEAGUE, league_toml(PLAYS))`; lines 358-361 →
```python
    folder = make_league(
        LEAGUE,
        f"[league]\nplay_path = '{PLAYS}'\n"
        f"gameplan_rules = ['{GP_RULES}', 'overlay.toml']\n" + CATEGORIES_TOML,
    )
```

`tests/integration/test_gameplan_replace_play.py`: import `league_toml`; line 38 → `return make_league(LEAGUE, league_toml(PLAYS))`; lines 459-461 → `(league / "league.toml").write_text(league_toml(tmp_path / "missing"), encoding="utf-8")`.

`tests/integration/test_gameplan_set_normals.py` and `test_gameplan_set_specials.py`: import `league_toml`; line 26 → `folder = make_league(LEAGUE, league_toml(PLAYS))`; the `"league.ini").write_text(` blocks → `(league / "league.toml").write_text(league_toml(tmp_path / "missing"), encoding="utf-8")`.

`tests/integration/test_profile_check.py`: line 342 → `"[league]\nprofile_rules = ['mine.toml']\n"`; lines 349-352 →
```python
    folder = make_league(
        LEAGUE,
        "[league]\nprofile_rules = ['base.toml', 'overlay.toml']\n",
    )
```
line 372 → `make_league(LEAGUE, f"[league]\nprofile_rules = ['{missing}']\n")`.

`tests/unit/pdbtoexcel/test_config.py:46` → `folder = make_league(LEAGUE, "[league]\nplay_path = 'D:\\plays'\n")`; line 38 comment `no league.ini` → `no league.toml`.

Verify: `grep -rn "league\.ini" tests --include=*.py | grep -v "\.league\.ini\|scheduler"` → no output.

- [ ] **Step 9: Run the suite**

Run: `uv run pytest -q`
Expected: all pass (gameplan rules and the pool still read `short` off the enum until Tasks 3-4, so the PNFL labels in `CATEGORIES_TOML` are not yet read by them; that is fine).

- [ ] **Step 10: Test matrices**

`tests/integration/README.md`:
- line 411: `| Rule lists in \`league.toml\` | \`profile_rules\` + \`gameplan_rules\` arrays | exit 1 | \`test_cli_rule_lists_in_league_toml\` | ☑ |`
- line 439: `<league.ini>` → `<league.toml>`.
- line 538 paragraph: `leagues/<NAME>/league.ini` → `leagues/<NAME>/league.toml`.
- rows 542-556: every `league.ini` → `league.toml`; `test_missing_league_ini_gives_empty_values` → `test_missing_league_toml_gives_empty_values`; the "Fixed rules file / rule list" row's input → `` `gameplan.toml`, `gameplan_rules` array ``; `test_malformed_league_ini_errors` → `test_malformed_league_toml_errors` with input "bad INI / bad TOML"; replace the last two rows with:

```markdown
| `%` in `league.toml` | `'%LOCALAPPDATA%\plays'` | loads literally (no interpolation) | `test_percent_in_league_toml_is_literal` / `test_no_interpolation_in_league_toml` | ☑ |
| `[league]` strings vs arrays | string + array | `values` / `lists` | `test_league_list_is_kept_apart_from_values` | ☑ |
| `[league]` wrong value type | int, array with int, inline table | `ConfigFileError` "expected a string or an array of strings", names the file | `test_league_value_wrong_type_errors` `[P]` | ☑ |
| `[league]` not a table | `league = 1` | `ConfigFileError` "[league] must be a table" | `test_league_section_not_a_table_errors` | ☑ |
| `[categories]` load | PNFL tables | `cfg.categories == PNFL_LABELS` | `test_categories_load` | ☑ |
| `[categories]` absent / one side | none; defense only | `CategoryLabels()`; offense empty | `test_categories_absent_is_no_labels` / `test_one_side_only_loads` | ☑ |
| `[categories]` errors | unknown key, empty / non-string label, duplicate, game-name label, non-table | `ConfigFileError` names the file | `test_categories_errors_name_the_file` `[P]` | ☑ |
```

`tests/unit/pdbtoexcel/README.md` rows 23-24: `league.ini` → `league.toml`.

- [ ] **Step 11: The four checks**

Run, one per call: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`. All green. Then check line endings of every changed and new file:

```bash
git status --porcelain | awk '{print $2}' | python -c "import sys, pathlib; bad = [f for f in sys.stdin.read().split() if pathlib.Path(f).is_file() and b'\n' in pathlib.Path(f).read_bytes().replace(b'\r\n', b'')]; print(bad or 'CRLF ok')"
```

Expected: `CRLF ok`. Fix any listed file with the conversion one-liner from Task 1, step 7.

- [ ] **Step 12: Commit**

```bash
git add -A config src tests
git commit -m "config: league settings move to league.toml with the league's category names"
```

---

### Task 3: Gameplan rules take the league's labels

**Files:**
- Modify: `src/athc/gameplan/rules.py` (module docstring; lines 95-104; `load_rules`; `_merge_file`; `_build_offense_section`; `_build_defense_section`)
- Modify: `src/athc/gameplan/config.py` (`Config.categories`)
- Modify: `src/athc/cli/gameplan/_common.py:118-140` (`resolve_rules`), `src/athc/cli/gameplan/check.py:59`, `src/athc/cli/check_ppp.py:330`
- Modify: `tests/unit/gameplan/test_rules.py`, `tests/integration/test_gameplan_check.py:30`, `tests/integration/test_config.py` (release tests), `tests/unit/gameplan/README.md`

**Interfaces:**
- Consumes: `CategoryLabels` (Task 1); `LeagueConfig.categories` (Task 2); `PNFL_LABELS` (Task 2 fixtures).
- Produces: `load_rules(paths: Iterable[Path | str], *, labels: CategoryLabels) -> Rules`; `athc.gameplan.config.Config.categories: CategoryLabels`; `resolve_rules(rule_files, labels, *, prog, logger)`.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/gameplan/test_rules.py` change the imports to:

```python
from functools import partial

from athc.fbpro98_play import CategoryLabels
from athc.gameplan import load_rules as _load_rules
from athc.gameplan.rules import RulesFileError
from tests.conftest import PNFL_LABELS, shipped_files, shipped_id

# Every test loads with the PNFL labels unless it says otherwise.
load_rules = partial(_load_rules, labels=PNFL_LABELS)
```

(`from fractions import Fraction`, `from pathlib import Path`, `import pytest` stay.) After the `# ── short-name labels ──` tests add:

```python
def test_league_label_section_needs_the_league_labels(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="not an offense category label"):
        _load_rules([write(tmp_path, MINIMAL + OFF_SECTION)], labels=CategoryLabels())


def test_game_name_section_loads_without_league_labels(tmp_path: Path) -> None:
    text = MINIMAL + '[offense."Run Middle"]\nrequired = true\n'
    rules = _load_rules([write(tmp_path, text)], labels=CategoryLabels())
    assert "Run Middle" in rules.offense_categories


def test_game_name_section_rejected_when_league_labels_it(tmp_path: Path) -> None:
    text = MINIMAL + '[offense."Run Middle"]\nrequired = true\n'
    with pytest.raises(RulesFileError, match="not an offense category label"):
        load_rules([write(tmp_path, text)])


def test_unknown_label_message_lists_the_league_labels(tmp_path: Path) -> None:
    text = MINIMAL + "[defense.Nonsense]\nrequired = true\n"
    with pytest.raises(RulesFileError, match="'RunDazzle'"):
        load_rules([write(tmp_path, text)])
```

In `tests/integration/test_gameplan_check.py`: import `PNFL_LABELS` from `tests.conftest` and change line 30 to `RULES = load_rules([str(GP_RULES)], labels=PNFL_LABELS)`.

In `tests/integration/test_config.py`, after `test_release_gameplan_config_loads`, add:

```python
@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_gameplan_rules_load_with_the_league_labels(name: str) -> None:
    from athc.gameplan import config as gameplan_config
    from athc.gameplan import load_rules

    cfg = gameplan_config.load_config(name)
    rules = load_rules(cfg.rule_files, labels=cfg.categories)
    assert "Run Middle" in rules.offense_categories
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/gameplan/test_rules.py tests/integration/test_gameplan_check.py tests/integration/test_config.py -q`
Expected: TypeError, `load_rules` got an unexpected keyword `labels`.

- [ ] **Step 3: Rewrite the loader**

`src/athc/gameplan/rules.py` module docstring:

```python
"""Gameplan validation rules and their TOML loader.

No rules ship with the package. `load_rules(paths, labels=...)` parses one or
more external TOML files into a `Rules` value; later files layer over earlier
ones (per-category replace, scalar overwrite). Categories are keyed by the
league's label from league.toml (`[offense.PSL]`, `[defense.RunDazzle]`); a
category the league does not label uses its game name, quoted
(`[offense."Pass Long Left"]`).
"""
```

Imports: add `CategoryLabels` to the `athc.fbpro98_play` import.

Replace lines 95-104 (the `_OFFENSE_BY_LABEL` … `_DEFENSE_LABELS` block) with:

```python
@dataclass(frozen=True, slots=True)
class _SectionLabels:
    """[offense.X] / [defense.X] section labels for one league: each category's
    league label, else its game name."""

    offense: Mapping[str, OffensiveCategory]
    defense: Mapping[str, DefensiveCategory]

    @classmethod
    def from_labels(cls, labels: CategoryLabels) -> _SectionLabels:
        return cls(
            {labels.label(c): c for c in OffensiveCategory},
            {labels.label(c): c for c in DefensiveCategory},
        )
```

`load_rules`:

```python
def load_rules(paths: Iterable[Path | str], *, labels: CategoryLabels) -> Rules:
    """Load one or more TOML rules files and merge them into a `Rules`. `labels`
    are the league's category labels, the section names a file may use.

    Files merge in order: top-level scalars/lists overwrite; per-category rules
    overwrite per category key.
    """
    path_list = [Path(p) for p in paths]
    if not path_list:
        raise RulesFileError("at least one rules file is required")

    sections = _SectionLabels.from_labels(labels)
    merged = _MergedData()
    errors: list[str] = []
    for path in path_list:
        try:
            data = _read_toml(path)
        except RulesFileError as e:
            errors.extend(e.errors)
            continue
        _merge_file(merged, data, errors, source=path, sections=sections)

    if errors:
        raise RulesFileError(errors)
    return _build_rules(merged)
```

`_merge_file` signature: `def _merge_file(merged, data, errors, *, source: Path, sections: _SectionLabels) -> None:`; its two section loops call `_build_offense_section(label, section, source, sections.offense)` and `_build_defense_section(label, section, source, sections.defense)`.

The two builders:

```python
def _build_offense_section(
    label: str,
    section: Mapping[str, Any],
    source: Path,
    by_label: Mapping[str, OffensiveCategory],
) -> tuple[str, OffenseCategoryRule]:
    member = by_label.get(label)
    if member is None:
        raise RulesFileError(
            f"{source}: [offense.{label}]: not an offense category label. "
            f"Valid: {sorted(by_label)}"
        )
    return member.long, _build_offense_rule(label, member, section, source)


def _build_defense_section(
    label: str,
    section: Mapping[str, Any],
    source: Path,
    by_label: Mapping[str, DefensiveCategory],
) -> tuple[str, DefenseCategoryRule]:
    member = by_label.get(label)
    if member is None:
        raise RulesFileError(
            f"{source}: [defense.{label}]: not a defense category label. "
            f"Valid: {sorted(by_label)}"
        )
    return member.long, _build_defense_rule(label, section, source)
```

- [ ] **Step 4: Gameplan config carries the labels**

`src/athc/gameplan/config.py`: import `field` from dataclasses and `CategoryLabels` from `athc.fbpro98_play`; add to `Config`:

```python
    categories: CategoryLabels = field(default_factory=CategoryLabels)
```

and in `load_config` pass `categories=cfg.categories`.

- [ ] **Step 5: CLI wiring**

`src/athc/cli/gameplan/_common.py`: import `CategoryLabels` from `athc.fbpro98_play`; `resolve_rules` becomes

```python
def resolve_rules(
    rule_files: Iterable[Path],
    labels: CategoryLabels,
    *,
    prog: str,
    logger: logging.Logger,
) -> Rules | None:
    """Load gameplan rules from `rule_files` with the league's category
    `labels`; return None (a hard error for the caller) when none are configured
    or loading fails."""
```

with the call `return load_rules(files, labels=labels)`.

`src/athc/cli/gameplan/check.py:59`: `rules = resolve_rules(config.rule_files, config.categories, prog=PROG, logger=logger)`.

`src/athc/cli/check_ppp.py`: add `from functools import partial` to the imports; line 330 →

```python
    rules = _load_rules(
        config.rule_files,
        partial(load_gameplan_rule_files, labels=config.categories),
        "gameplan.toml",
    )
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/gameplan tests/integration -q`
Expected: all pass.

- [ ] **Step 7: Test matrix**

`tests/unit/gameplan/README.md`: rename the `### Short-name labels` heading to `### Section labels (league labels from league.toml, else game names)` and add rows:

```markdown
| League label without league labels | `CategoryLabels()` + `[offense.RM]` | "not an offense category label" | `test_league_label_section_needs_the_league_labels` | ☑ |
| Game name without league labels | `CategoryLabels()` + `[offense."Run Middle"]` | loads | `test_game_name_section_loads_without_league_labels` | ☑ |
| Game name of a labeled category | PNFL + `[offense."Run Middle"]` | "not an offense category label" | `test_game_name_section_rejected_when_league_labels_it` | ☑ |
| Unknown-label message lists league labels | PNFL + `[defense.Nonsense]` | message contains `'RunDazzle'` | `test_unknown_label_message_lists_the_league_labels` | ☑ |
```

- [ ] **Step 8: The four checks, then commit**

Run, one per call: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`. All green; CRLF check from Task 2 step 11 prints `CRLF ok`.

```bash
git add -A src tests
git commit -m "gameplan: rule sections resolve through the league's category labels"
```

---

### Task 4: Play pool and `replace-play` take the league's labels

**Files:**
- Modify: `src/athc/playpool/pool.py` (docstring lines 1-9; imports; lines 50-51 comment; `_folder_info`; `folder_warnings`; `PlayPool.__init__`; `_process_play_file`; `read_play_pool`)
- Modify: `src/athc/pdbtoexcel/config.py` (`Config.categories`), `src/athc/pdbtoexcel/workbook_creator.py:68`
- Modify: `src/athc/cli/gameplan/_common.py` (`build_pool`), `src/athc/cli/gameplan/check.py:62`, `src/athc/cli/gameplan/set_normals.py:68`, `src/athc/cli/gameplan/set_specials.py:145`, `src/athc/cli/check_ppp.py:332`, `src/athc/cli/check_playpool.py:38-60`, `src/athc/cli/gameplan/replace_play.py`
- Modify: `tests/unit/playpool/conftest.py`, `tests/unit/playpool/test_pool.py`, `tests/integration/test_gameplan_check.py:31`, `tests/integration/test_gameplan_replace_play.py`, `tests/unit/playpool/README.md`, `tests/integration/README.md`

**Interfaces:**
- Consumes: `CategoryLabels` (Task 1), `Config.categories` on gameplan (Task 3) and pdbtoexcel (this task), `PNFL_LABELS` / `league_toml` (Task 2).
- Produces: `folder_warnings(rel_path, play, labels: CategoryLabels) -> list[str]`; `PlayPool(root_dir, *, rules=None, labels: CategoryLabels | None = None)` with `.labels`; `read_play_pool(root_dir, *, rules=None, labels=None)`; `build_pool(play_path, playpool_rules, labels, *, prog, logger)`; `format_replacement_lines(path, normal_hits, special_hits, entry, labels)`; `athc.pdbtoexcel.config.Config.categories`.

- [ ] **Step 1: Write the failing pool tests**

`tests/unit/playpool/conftest.py`: import `PNFL_LABELS` from `tests.conftest`; `league_pool` becomes `return read_play_pool(PLAYS, rules=rules, labels=PNFL_LABELS)`. `flat_pool` and `arbitrary_pool` stay without labels (no folder has a meaning there).

`tests/unit/playpool/test_pool.py`: import `CategoryLabels` from `athc.fbpro98_play` and `PNFL_LABELS` from `tests.conftest`. Then:
- `test_no_warnings_on_consistent_trees`: `read_play_pool(root)` → `read_play_pool(root, labels=PNFL_LABELS)`.
- every `read_play_pool(tmp_path)` in the issues tests (lines 192-232) and in `test_wrong_side_folder_file_wins_and_warns` / `test_wrong_category_folder_warns` → `read_play_pool(tmp_path, labels=PNFL_LABELS)`.
- every `folder_warnings(<rel>, play)` → `folder_warnings(<rel>, play, PNFL_LABELS)`.

Add after `test_no_warn_loose_or_unrecognized`:

```python
def test_no_labels_means_no_category_folders(make_play: MakePlay) -> None:
    """Without league labels a PNFL category folder is just a folder."""
    play = make_play("X", play_category=0x01, user_category=0x07)  # Pass Short Left
    assert folder_warnings("Offense/PML/X.ply", play, CategoryLabels()) == []


def test_shared_label_resolves_to_the_plays_side(make_play: MakePlay) -> None:
    """`RR` names Run Right on both sides: each side's Run Right sits in it quietly."""
    labels = CategoryLabels.from_tables({"Run Right": "RR"}, {"Run Right": "RR"})
    offense = make_play("X", play_category=0x01, user_category=0x01)
    defense = make_play("X", play_category=0x00, user_category=0x00)
    assert folder_warnings("RR/X.ply", offense, labels) == []
    assert folder_warnings("RR/X.ply", defense, labels) == []
    pass_play = make_play("X", play_category=0x00, user_category=0x02)  # Pass Short
    assert folder_warnings("RR/X.ply", pass_play, labels) == [
        "Pass Short play in a Run Right folder: RR/X.ply"
    ]


def test_other_sides_label_still_warns_wrong_side(make_play: MakePlay) -> None:
    """A folder named with the other side's label is that side's tree."""
    play = make_play("X", play_category=0x00, user_category=0x02)  # defense
    assert folder_warnings("PML/X.ply", play, PNFL_LABELS) == [
        "Defensive play in the offense tree: PML/X.ply"
    ]


def test_front_prefix_uses_defense_labels(make_play: MakePlay) -> None:
    play = make_play("X", play_category=0x00, user_category=0x22)  # Pass Long
    assert folder_warnings("34RunLeft/X.ply", play, PNFL_LABELS) == [
        "Pass Long play in a Run Left folder: 34RunLeft/X.ply"
    ]
    assert folder_warnings("34PML/X.ply", play, PNFL_LABELS) == []  # not a defense label
```

- [ ] **Step 2: Write the failing replace-play tests**

`tests/integration/test_gameplan_replace_play.py`: import `PNFL_LABELS` and `league_toml` from `tests.conftest` (keep `LEAGUE`). The two direct `format_replacement_lines(...)` calls (lines ~226 and in `test_format_lines_multiple_normal_slots`, plus any other direct call in the file — search `format_replacement_lines(`) get `PNFL_LABELS` as the last positional argument. Add after `test_cli_single_file_replaces_normal`:

```python
def test_cli_output_uses_game_names_without_league_labels(
    runner, league: Path, tmp_path: Path
) -> None:
    (league / "league.toml").write_text(
        league_toml(PLAYS, labels=False), encoding="utf-8"
    )
    old = _onorm("OLDRUN")
    p = _write(_offense_gameplan(normals={0: old}), tmp_path)
    result = runner.invoke(replace_play, ["OLDRUN", NORMAL_REPL, str(p)])
    assert result.exit_code == 0
    assert (
        f"'OLDRUN' (Run Left) replaced with '{NORMAL_REPL}' (Run Middle) [1-1]"
        in result.output
    )
```

`tests/integration/test_gameplan_check.py:31`: `POOL = read_play_pool(str(PLAYS), rules=load_pool_rules(str(POOL_RULES)), labels=PNFL_LABELS)`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/playpool tests/integration/test_gameplan_replace_play.py tests/integration/test_gameplan_check.py -q`
Expected: TypeError on the new `labels` arguments.

- [ ] **Step 4: Rewrite the pool's folder lookup**

`src/athc/playpool/pool.py`:

Module docstring, replace the sentence `a PNFL tree, an arbitrary tree, or a flat directory. Folders are optional: a PNFL folder adds ...` block so it reads:

```python
"""Build a PlayPool: walk a tree, classify each .ply from its file, index by name.

Side and category come from the parsed play file, so any folder layout works —
a league tree, an arbitrary tree, or a flat directory. Folders are optional: a
recognized folder adds an attribute the bytes can't carry (offense `screen`,
defense `defensive_front`) and lets the pool warn (with the play's path) when a
play sits in a folder that contradicts its file. Category folders are named by
the league's labels (`CategoryLabels`, from league.toml); the filename-derived
flags (`rollout`, `qb_draw`, `pass_logic`) come from the league's `PlaypoolRules`.
"""
```

Imports: replace `category_by_short,` with `CategoryLabels,` in the `athc.fbpro98_play` import (keep `OffensiveCategory`, `PlayCategory`, `PlayFile`, `InvalidPlayFileError`, `read_play`).

Lines 50-51 comment → `# Category folders use the league's labels (league.toml) — resolved per side.`

Replace `_folder_info` with:

```python
def _category_folder(
    name: str, file_side: str, labels: CategoryLabels
) -> PlayCategory | None:
    """`name` as a league category label — the play's own side first, so a label
    both sides use means the play's side; the other side next, so a play filed
    under the other side's label still gets its wrong-side warning."""
    lookups = [labels.offense_by_label, labels.defense_by_label]
    if file_side == "Defense":
        lookups.reverse()
    for lookup in lookups:
        member = lookup(name)
        if member is not None:
            return member
    return None


def _folder_info(
    parts: Sequence[str], file_side: str, labels: CategoryLabels
) -> _FolderInfo:
    """Read the league's folder conventions from a play's folder names (root→file
    order) for a play whose file says `file_side`. Deeper category folders win;
    unrecognized names are ignored."""
    side = None
    category: PlayCategory | None = None
    screen = False
    front: DefensiveFront | None = None
    for part in parts:
        if part in SIDE_FOLDERS:
            side = part
        elif part == SCREENS_FOLDER:
            side, screen = "Offense", True
        elif part == RNS_FOLDER:
            side, front = "Defense", DefensiveFront.TWO_DL
        elif part[:2] in ("34", "43"):
            side = "Defense"
            front = (
                DefensiveFront.THREE_FOUR
                if part[:2] == "34"
                else DefensiveFront.FOUR_THREE
            )
            member = labels.defense_by_label(part[2:])
            if member is not None:
                category = member
        else:
            member = _category_folder(part, file_side, labels)
            if member is not None:
                side = "Offense" if isinstance(member, OffensiveCategory) else "Defense"
                category = member
    return _FolderInfo(side, category, screen, front)
```

`folder_warnings`:

```python
def folder_warnings(
    rel_path: StrPath, play: PlayFile, labels: CategoryLabels
) -> list[str]:
    """Folder/file mismatch warnings for a play at `rel_path` (relative to the
    pool root), with the league's category `labels`; empty when nothing is wrong."""
    rel = PurePath(rel_path)
    info = _folder_info(rel.parent.parts, _file_side(play), labels)
    return _warnings(info, play, rel.as_posix())
```

`PlayPool.__init__`:

```python
    def __init__(
        self,
        root_dir: StrPath,
        *,
        rules: PlaypoolRules | None = None,
        labels: CategoryLabels | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.rules = rules if rules is not None else PlaypoolRules()
        self.labels = labels if labels is not None else CategoryLabels()
```

(the rest of `__init__` unchanged). In `_process_play_file`: `info = _folder_info(rel.parent.parts, _file_side(play_file), self.labels)`.

`read_play_pool`:

```python
def read_play_pool(
    root_dir: StrPath,
    *,
    rules: PlaypoolRules | None = None,
    labels: CategoryLabels | None = None,
) -> PlayPool:
    """Scan `root_dir` for .ply files and classify them; invalid files skipped.

    Each play's side and category come from the file itself. With no `rules`,
    filename-derived attributes stay off; with no `labels`, no folder name means
    anything.
    """
    pool = PlayPool(root_dir, rules=rules, labels=labels)
```

- [ ] **Step 5: convert-pdb carries the labels**

`src/athc/pdbtoexcel/config.py`: import `CategoryLabels` from `athc.fbpro98_play` (extend the existing import); add to `Config`:

```python
    categories: CategoryLabels = field(default_factory=CategoryLabels)
```

and in `load_config` pass `categories=cfg.categories`.

`src/athc/pdbtoexcel/workbook_creator.py:68`: `play_pool = read_play_pool(config.play_path, rules=rules, labels=config.categories)`.

- [ ] **Step 6: CLI wiring**

`src/athc/cli/gameplan/_common.py` `build_pool`:

```python
def build_pool(
    play_path: Path,
    playpool_rules: Path | None,
    labels: CategoryLabels,
    *,
    prog: str,
    logger: logging.Logger,
) -> PlayPool | None:
    """Build a PlayPool from `play_path` (each play classified from its file) with
    the league's category `labels` naming its folders. Optional `playpool_rules`
    is the playpool filename-filter TOML; returns None on a missing directory or
    unreadable rules file."""
```

with the call `return read_play_pool(play_path, rules=rules, labels=labels)`.

Callers:
- `check.py:62`, `set_normals.py:68`, `set_specials.py:145`, `check_ppp.py:332`: insert `config.categories` as the third positional argument: `build_pool(config.play_path, config.playpool_rules, config.categories, prog=PROG, logger=logger)`.
- `check_playpool.py`: import `CategoryLabels` from `athc.fbpro98_play`; before `if play_dir is None:` add `labels = CategoryLabels()`; inside that block, after `play_dir = cfg.path("play_path")`, add `labels = cfg.categories`; the call becomes `build_pool(play_dir, None, labels, prog=PROG, logger=logger)`. The docstring sentence `a given play_dir reads no league` already says why a given folder has no labels.
- `replace_play.py`:
  - import `CategoryLabels` from `athc.fbpro98_play` (extend the existing import).
  - replace `_short` with

    ```python
    def _label(play: PlayRef, labels: CategoryLabels) -> str:
        """The league's label for a slot's play category (e.g. `RL`); game name
        when the league has none (`Field Goal/PAT`)."""
        return labels.label(
            resolve_category(
                play.play_category, play.special_category, play.user_category
            )
        )
    ```

  - `format_replacement_lines(path, normal_hits, special_hits, entry, labels: CategoryLabels)`: every `_short(x)` → `_label(x, labels)`.
  - `_replace_one(path, target, entry, labels: CategoryLabels)` passes `labels` to `format_replacement_lines`.
  - in the command: `pool_path = load_config(league).play_path` → `config = load_config(league, rule_files=())` (keep the existing comment about needing no playpool rules; `rule_files=()` means no gameplan rules are read either); then `build_pool(config.play_path, None, config.categories, prog=PROG, logger=logger)` and `_replace_one(file, play, entry, config.categories)`.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 8: Test matrices**

`tests/unit/playpool/README.md`, `folder_warnings` table: heading sentence add "Category folders are the league's labels (`CategoryLabels`); the play's own side is looked up first." and rows:

```markdown
| No league labels | `CategoryLabels()`, `Offense/PML` | no warning (folder unrecognized) | `test_no_labels_means_no_category_folders` | ☑ |
| Label shared by both sides | `RR` offense + defense | each side's Run Right quiet; other category warns | `test_shared_label_resolves_to_the_plays_side` | ☑ |
| Other side's label | defense play in `PML/` | side warning | `test_other_sides_label_still_warns_wrong_side` | ☑ |
| `34`/`43` prefix uses defense labels | `34RunLeft`, `34PML` | category warning; unrecognized | `test_front_prefix_uses_defense_labels` | ☑ |
```

`tests/integration/README.md`, the `replace-play` table: add `| Output without league labels | league.toml with no \`[categories]\` | \`(Run Left)\` / \`(Run Middle)\` | \`test_cli_output_uses_game_names_without_league_labels\` | ☑ |`.

- [ ] **Step 9: The four checks, then commit**

Run, one per call: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`. All green; CRLF check prints `CRLF ok`.

```bash
git add -A src tests
git commit -m "playpool: folder names and replace-play output use the league's category labels"
```

---

### Task 5: Remove `short` and `category_by_short` from the enum

**Files:**
- Modify: `src/athc/fbpro98_play/model.py:1-27,39-108,115,141-159`
- Modify: `src/athc/fbpro98_play/__init__.py`
- Modify: `tests/unit/fbpro98_play/test_model.py`, `tests/unit/fbpro98_play/README.md:67-72`

**Interfaces:**
- Produces: `PlayCategory(code: int, long: str)`; enum members are `(code, long)` pairs; `category_by_short` no longer exists.

- [ ] **Step 1: Rewrite the model tests**

In `tests/unit/fbpro98_play/test_model.py` remove `category_by_short,` from the import; delete `test_short_falls_back_to_long_without_league_name` and `test_category_by_short`; replace `test_short_and_long_names` with:

```python
def test_long_is_the_game_name():
    assert OffensiveCategory.PASS_SHORT_RIGHT.long == "Pass Short Right"
    assert DefensiveCategory.RUN_LEFT.long == "Run Left"
    assert SpecialOffensiveCategory.PUNT.long == "Punt"


def test_category_has_no_league_label():
    assert not hasattr(OffensiveCategory.PASS_SHORT_RIGHT, "short")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/fbpro98_play/test_model.py -q`
Expected: `test_category_has_no_league_label` fails (`short` still exists).

- [ ] **Step 3: Strip the enum**

`src/athc/fbpro98_play/model.py`:
- Module docstring lines 3-6: `each member carrying its on-disk code, a short league label, and the long game name.` → `each member carrying its on-disk code and the long game name (league labels live in `labels.py`).`
- `PlayCategory`:

```python
class PlayCategory:
    """A play category: on-disk `code` and the `long` game name. Subclassed by
    the four per-side category enums."""

    code: int
    long: str

    def __init__(self, code: int, long: str) -> None:
        self.code = code
        self.long = long
```

- Every enum member drops its middle element, e.g. `RUN_RIGHT = (0x01, "Run Right")`, `PASS_SHORT_RIGHT = (0x03, "Pass Short Right")`, `RUN_RIGHT = (0x00, "Run Right")` on defense, `FIELD_GOAL_PAT = (0x01, "Field Goal/PAT")`, and so on for all four enums. Do it mechanically:

```bash
python - <<'EOF'
import pathlib, re
p = pathlib.Path("src/athc/fbpro98_play/model.py")
text = p.read_bytes().decode("utf-8")  # bytes in and out keep the CRLF endings
text, n = re.subn(r'= \((0x[0-9A-F]{2}), "[^"]*", ("[^"]*")\)', r"= (\1, \2)", text)
assert n == 50, n
p.write_bytes(text.encode("utf-8"))
EOF
```

(17 offense + 11 defense + 12 special offense + 10 special defense = 50 members.)

- `UNKNOWN_CATEGORY = PlayCategory(-1, "Unknown")`.
- Delete `_build_by_short`, the `_BY_SHORT` constant with its comment, and `category_by_short`.
- The enum docstring on `OffensiveCategory` etc. stays.

`src/athc/fbpro98_play/__init__.py`: remove `category_by_short,` from the import and `"category_by_short",` from `__all__`.

- [ ] **Step 4: Verify nothing else reads `short`**

```bash
grep -rn "\.short\b\|category_by_short" src tests --include=*.py
```

Expected: no output.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Test matrix**

`tests/unit/fbpro98_play/README.md`: replace rows 67-68 with
`| \`long\` is the game name | enum | \`Pass Short Right\`; \`Run Left\`; \`Punt\` | \`test_long_is_the_game_name\` | ☑ |` and
`| No league label on the enum | enum | no \`short\` attribute (labels are \`CategoryLabels\`) | \`test_category_has_no_league_label\` | ☑ |`;
delete row 72 (`category_by_short`).

- [ ] **Step 7: The four checks, then commit**

Run, one per call: `uv run pytest` · `uv run ruff check .` · `uv run ruff format .` · `uv run pyright`. All green; CRLF check prints `CRLF ok`.

```bash
git add -A src tests
git commit -m "fbpro98_play: category enum drops the league label"
```

---

### Task 6: Docs and project meta

**Files:**
- Modify: `docs/design/config.md`, `docs/design/installer.md:24,29`, `docs/design/overview.md:16,20,71`, `docs/fbpro98_play/ARCHITECTURE.md:25-33`, `docs/playpool/ARCHITECTURE.md:66-68`, `docs/gameplan/ARCHITECTURE.md:45,57-58`, `docs/gameplan/README.md:66-67`, `docs/profile/ARCHITECTURE.md:53-54`, `docs/profile/README.md:62-68`, `docs/pdbtoexcel/README.md:28-32`, `docs/pdbtoexcel/ARCHITECTURE.md:51`, `docs/check_ppp/README.md:24,75`, `README.md:23`, `config/release/docs/README.txt:52-58,65,99-100,115`, `config/release/docs/COMMANDS.txt:14,207`, `STATUS.md:44,56,59,72,80,185,233,282`, `CHANGELOG.md`, `WORKLOG.md`, `TODO.md`

No tests or checks: documentation only.

- [ ] **Step 1: `docs/design/config.md`**

Replace the `## Format and location` section's first bullet and the `### Why stdlib...` paragraph's first sentence so they read:

```markdown
- **Format**: `athc.ini` is INI via stdlib `configparser` (a Windows convention users edit in Notepad). Each league's `league.toml` is TOML via stdlib `tomllib`: it nests the category tables, quotes keys with spaces, carries comments, and is the format of the league's rule files.
- **Path**: `%LOCALAPPDATA%\athc\athc.ini` (resolved via `platformdirs.user_config_path("athc", appauthor=False)`).
```

In `## Layout`: the tree line → `league.toml               per-league settings ([league] path, play_path, …; [categories.*] labels)`; the paragraph: `go in \`league.ini\` under \`[league]\`` → `go in \`league.toml\` under \`[league]\``, and append this paragraph:

```markdown
A league's short names for the game's play categories are the `[categories.offense]` and `[categories.defense]` tables of `league.toml`, keyed by the game's category name (`"Run Right" = "RR"`). The shipped files list every category of each side in the game's order, the unlabeled ones commented out. The gameplan rule files name categories by these labels (game name where the league has none), the play pool recognizes category folders by them, and `replace-play` prints them. Special-teams categories have no labels. A key that is not a category of its side, an empty or repeated label, or a label equal to a category name of its side is a `ConfigFileError`. Code: `CategoryLabels` in `athc.fbpro98_play`, carried as `LeagueConfig.categories`.
```

In `## athc.ini`: `An unreadable \`athc.ini\` or \`league.ini\`` → `An unreadable \`athc.ini\` or \`league.toml\` (including a wrong value type or a bad category label)`.

In `## Rule files`: `An optional multi-line list in \`league.ini\`` → `An optional array in \`league.toml\``.

In `## Per-tool config code`: the sample `Config` gains `categories: CategoryLabels = field(default_factory=CategoryLabels)` and `load()` passes `categories=cfg.categories`; the bullet `\`path(key)\` for a value in \`league.ini\`` → `\`path(key)\` for a value in \`league.toml\``, and the last bullet becomes: `Missing file or key → dataclass defaults. \`[league]\` values are strings or arrays of strings; the loader rejects anything else.`

- [ ] **Step 2: Other design and tool docs**

Every `league.ini` that is not `<season>.league.ini` or `*.league.ini` becomes `league.toml` in: `docs/design/installer.md` (table row 24 and line 29), `docs/design/overview.md` (lines 16, 20, 71), `docs/gameplan/ARCHITECTURE.md:57-58` (also `one path per line` → `an array`), `docs/gameplan/README.md:66-67`, `docs/profile/ARCHITECTURE.md:53-54` (`one path per line` → `an array`), `docs/pdbtoexcel/ARCHITECTURE.md:51`, `docs/check_ppp/README.md:24,75`, `README.md:23`.

`docs/profile/README.md:62-68`: the example becomes

````markdown
`[athc] league`). To layer several files, list them in `league.toml`:

```toml
[league]
profile_rules = ['profile.toml', 'house-rules.toml']
```
````

`docs/pdbtoexcel/README.md:28-32`:

````markdown
```toml
# leagues\PNFL\league.toml
[league]
play_path = 'E:\SIERRA\FbPro98\PNFL'
```
````

`docs/fbpro98_play/ARCHITECTURE.md:25-33`: replace the category bullet with

```markdown
- Names play categories: four per-side enums (`OffensiveCategory`, `DefensiveCategory`,
  `SpecialOffensiveCategory`, `SpecialDefensiveCategory`), each member carrying its
  `code` and `long` (game name), plus `is_run`/`is_pass`.
  `resolve_category(play_category, special_category, user_category)` and
  `PlayFile.category` name a category from the raw bytes; `category_name` is `category.long`.
  An unrecognized code resolves to `UNKNOWN_CATEGORY` (never `None`); `read_play`
  rejects the file.
- Holds a league's category labels: `CategoryLabels` (`labels.py`), built from the
  `[categories.offense]` / `[categories.defense]` tables of `league.toml` by
  `CategoryLabels.from_tables` (ValueError on a bad entry). `label(category)` is the
  league label, else the game name; `offense_by_label` / `defense_by_label` resolve a
  label within one side. Special-teams categories never have labels.
```

`docs/playpool/ARCHITECTURE.md:66-68`: `PNFL category folders are matched against the league short labels on \`fbpro98_play\`'s category enum (via \`category_by_short\`); only these filename filters are league data.` → `Category folders are matched against the league's labels (\`CategoryLabels\`, passed to \`read_play_pool\` / \`folder_warnings\`), the play's own side first; the filename filters and the labels are league data.`

`docs/gameplan/ARCHITECTURE.md:45`: `Section labels are short category labels — \`[offense.RM]\` (Run Middle), \`[defense.RunDazzle]\` (Run Dazzle); a category with no league abbreviation is labeled by its game name, quoted` → `Section labels are the league's category labels from \`league.toml\` (\`load_rules(paths, labels=...)\`) — \`[offense.RM]\` (Run Middle), \`[defense.RunDazzle]\` (Run Dazzle); a category the league does not label is named by its game name, quoted`.

- [ ] **Step 3: Release docs**

`config/release/docs/README.txt`:
- lines 52-58:

```
set is your plays folder: open leagues\PNFL\league.toml in your settings
folder (see below) and set play_path to your FbPro98 league plays
folder, for example:

   [league]
   play_path = 'D:\SIERRA\FBPRO98\PNFL\plays'
```

- the `path` example: `   path = 'D:\SIERRA\FBPRO98'`
- line 65: `Each league is a folder under leagues\ with its league.toml, rule files`
- lines 99-100: `      league.toml          your plays folder (play_path), league files` / `                           folder (path) and the league's category names`
- line 115: `   leagues\*\league.toml YES -- preserved`

`config/release/docs/COMMANDS.txt`: line 14 `league.ini (play_path, path)` → `league.toml (path, play_path, category names)`; line 207 `path in league.ini` → `path in league.toml`.

- [ ] **Step 4: Project meta**

`STATUS.md`: lines 44, 56, 59, 72, 80, 185, 233, 282: `league.ini` → `league.toml`; line 72 → `league.toml               [league] path, play_path (dev also db_path); [categories.*]`; line 80 likewise; line 56 `list in` stays. Under the gameplan section add a bullet: `- A league's category labels come from \`league.toml\` (\`CategoryLabels\`); the category enum carries only codes and game names.`

`CHANGELOG.md`, top of `## athc`:

```markdown
- config: league settings moved from `league.ini` to `league.toml`; a league's short names for the play categories live there under `[categories.offense]` / `[categories.defense]`, no longer in code
```

`WORKLOG.md`, top entry:

```markdown
- 2026-10-07 — **config, fbpro98_play, gameplan, playpool**: the league's
  category labels were baked into the category enum, so every league got
  PNFL's names. They now come from the league's settings file, which became
  `league.toml` (TOML nests the two category tables and quotes keys with
  spaces); rule sections, play-pool folders and `replace-play` output resolve
  through `CategoryLabels`. `athc.ini` and the standings files stay INI.
```

`TODO.md`: no entry to add or remove unless one names `league.ini` (none does today); leave as is.

- [ ] **Step 5: Verify no stale mention remains**

```bash
grep -rn -i "league\.ini" --include=*.md --include=*.txt --include=*.ini --include=*.toml --include=*.bat --include=*.ps1 --include=*.py . | grep -v "\.league\.ini\|superpowers/\|CHANGELOG\.md\|WORKLOG\.md\|^\./build/\|^\./dist/\|^\./research/\|^\./\.claude/\|^\./\.venv/\|scheduler"
```

Expected: no output. (Historical CHANGELOG/WORKLOG lines, specs and plans, and the scheduler's `<season>.league.ini` keep the old name.)

Then the CRLF check from Task 2 step 11 prints `CRLF ok`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "athc: docs follow league.toml and the league's category labels"
```

---

## Hand-off

After Task 6, leave the worktree and return the session to the main checkout; then give the squash-merge block and, separately, the worktree-removal block, as AGENTS.md says. Do not merge.
