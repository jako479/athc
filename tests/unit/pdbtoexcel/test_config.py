"""Unit tests for convert-pdb config: the workbook options from athc.ini and the
league's pdbtoexcel.toml (category order, deleted plays)."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.config import ConfigFileError, LeagueError
from athc.fbpro98_play import DefensiveCategory as D
from athc.fbpro98_play import OffensiveCategory as O
from athc.pdbtoexcel import load_config
from athc.pdbtoexcel.pdb import PLAY_DATA
from tests.conftest import (
    LEAGUE,
    PDBTOEXCEL_TOML,
    ROOT,
    league_toml,
    write_pdbtoexcel_toml,
)

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]

RUN = PLAY_DATA.PLAY_TYPE.RUN
PASS = PLAY_DATA.PLAY_TYPE.PASS
DEFENSE = PLAY_DATA.PLAY_TYPE.DEFENSE

# Every workbook option flipped away from its default.
WORKBOOK_OPTIONS_INI = (
    "[convert-pdb]\ncalculate_percentages = false\n"
    "include_category_worksheets = true\nexclude_sacks_from_pass_attempts = false\n"
)

ORDER_ONLY = '[category_order]\nrun = ["RL"]\npass = ["PSL"]\ndefense = ["RunLeft"]\n'


@pytest.fixture
def league(make_league: MakeLeague) -> Path:
    """The test league with the PNFL labels and the PNFL order."""
    folder = make_league(LEAGUE, league_toml())
    write_pdbtoexcel_toml(folder)
    return folder


def _order(folder: Path, body: str) -> None:
    write_pdbtoexcel_toml(folder, body)


def _raises(message: str):
    return pytest.raises(ConfigFileError, match=re.escape(message))


# ── league folder ─────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_load_config_defaults() -> None:
    cfg = load_config(LEAGUE)
    assert cfg.play_path == ""
    assert cfg.playpool_rules is None
    assert cfg.calculate_percentages is True
    assert cfg.deleted_plays == frozenset()


def test_load_config_from_league_folder(league: Path) -> None:
    (league / "league.toml").write_text(league_toml("D:\\plays"), encoding="utf-8")
    (league / "playpool.toml").write_text("", encoding="utf-8")
    cfg = load_config(LEAGUE)
    assert cfg.play_path == "D:\\plays"
    assert cfg.playpool_rules == league / "playpool.toml"


def test_load_config_needs_a_league() -> None:
    with pytest.raises(LeagueError, match="no league selected"):
        load_config()


def test_playpool_toml_next_to_athc_ini_is_ignored(
    league: Path, config_dir: Path
) -> None:
    (config_dir / "playpool.toml").write_text("", encoding="utf-8")
    assert load_config(LEAGUE).playpool_rules is None


# ── category order from pdbtoexcel.toml ───────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_category_order_in_file_order() -> None:
    order = load_config(LEAGUE).category_order
    assert order[RUN] == (O.RUN_LEFT, O.RUN_MIDDLE, O.RUN_RIGHT, O.GOAL_LINE_RUN)
    assert order[PASS] == (
        O.PASS_SHORT_LEFT,
        O.PASS_SHORT_MIDDLE,
        O.PASS_SHORT_RIGHT,
        O.PASS_MEDIUM_LEFT,
        O.PASS_MEDIUM_MIDDLE,
        O.PASS_MEDIUM_RIGHT,
        O.PASS_LONG_RIGHT,
        O.RAZZLE_DAZZLE_PASS,
        O.GOAL_LINE_PASS,
    )
    assert order[DEFENSE] == (
        D.RUN_LEFT,
        D.RUN_MIDDLE,
        D.RUN_RIGHT,
        D.RUN_DAZZLE,
        D.PASS_SHORT,
        D.PASS_MEDIUM,
        D.PASS_LONG,
        D.PASS_DAZZLE,
        D.GOAL_LINE_RUN,
        D.GOAL_LINE_PASS,
    )


def test_unlabeled_category_goes_by_its_game_name(league: Path) -> None:
    # PNFL leaves Razzle Dazzle Run unlabeled; the game name names it.
    _order(
        league, ORDER_ONLY.replace('run = ["RL"]', 'run = ["RL", "Razzle Dazzle Run"]')
    )
    assert load_config(LEAGUE).category_order[RUN] == (O.RUN_LEFT, O.RAZZLE_DAZZLE_RUN)


def test_labeled_category_by_game_name_is_unknown(league: Path) -> None:
    _order(league, ORDER_ONLY.replace('"RL"', '"Run Left"'))
    with _raises(
        "[category_order] run: 'Run Left' is not a run category of this league"
    ):
        load_config(LEAGUE)


def test_unknown_name_lists_the_valid_ones(league: Path) -> None:
    _order(league, ORDER_ONLY.replace('"RunLeft"', '"Nope"'))
    with _raises(
        "[category_order] defense: 'Nope' is not a defense category of this league. Valid: ['GLpass', 'GLrun', 'PassDazzle', 'PassLong', 'PassMedium', 'PassShort', 'RunDazzle', 'RunLeft', 'RunMiddle', 'RunRight', 'User Specific']"
    ):
        load_config(LEAGUE)


def test_empty_list_is_allowed(league: Path) -> None:
    _order(league, ORDER_ONLY.replace('run = ["RL"]', "run = []"))
    assert load_config(LEAGUE).category_order[RUN] == ()


@pytest.mark.parametrize(
    ("key", "name", "message"),
    [
        ("run", "PSL", "[category_order] run: 'PSL' is a pass category"),
        ("pass", "RL", "[category_order] pass: 'RL' is a run category"),
        ("defense", "RL", "[category_order] defense: 'RL' is not a defense category"),
        # Offense but neither run nor pass: unknown for both keys, not "a pass category".
        ("run", "User Specific", "'User Specific' is not a run category"),
        ("pass", "User Specific", "'User Specific' is not a pass category"),
    ],
)
def test_wrong_side_is_an_error(
    league: Path, key: str, name: str, message: str
) -> None:
    body = ORDER_ONLY.replace(f"{key} = [", f'{key} = ["{name}", ')
    _order(league, body)
    with _raises(message):
        load_config(LEAGUE)


def test_repeated_name_is_an_error(league: Path) -> None:
    _order(league, ORDER_ONLY.replace('run = ["RL"]', 'run = ["RL", "RM", "RL"]'))
    with _raises("[category_order] run: 'RL' is listed twice"):
        load_config(LEAGUE)


def test_missing_key_is_an_error(league: Path) -> None:
    _order(league, ORDER_ONLY.replace('defense = ["RunLeft"]\n', ""))
    with _raises("[category_order] defense: missing"):
        load_config(LEAGUE)


def test_missing_table_is_an_error(league: Path) -> None:
    _order(league, "[deleted_plays]\nnames = []\n")
    with _raises("[category_order] is missing"):
        load_config(LEAGUE)


@pytest.mark.parametrize("table", ["category_order", "deleted_plays"])
def test_table_written_as_a_value_is_an_error(league: Path, table: str) -> None:
    _order(league, f"{table} = 1\n" + (ORDER_ONLY if table != "category_order" else ""))
    with _raises(f"[{table}] must be a table"):
        load_config(LEAGUE)


@pytest.mark.parametrize("value", ['"RL"', "[1]", '["RL", 2]'])
def test_list_must_be_an_array_of_strings(league: Path, value: str) -> None:
    _order(league, ORDER_ONLY.replace('run = ["RL"]', f"run = {value}"))
    with _raises("[category_order] run: expected an array of strings"):
        load_config(LEAGUE)


def test_unknown_key_is_an_error(league: Path) -> None:
    _order(league, ORDER_ONLY + "special = []\n")
    with _raises("[category_order] special: unknown key (expected defense, pass, run)"):
        load_config(LEAGUE)


def test_unknown_table_is_an_error(league: Path) -> None:
    _order(league, ORDER_ONLY + "[filters]\nx = 1\n")
    with _raises("unknown key 'filters' (expected category_order, deleted_plays)"):
        load_config(LEAGUE)


def test_missing_file_is_an_error(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, league_toml())
    with _raises(f"{folder / 'pdbtoexcel.toml'}: not found"):
        load_config(LEAGUE)


def test_bad_toml_is_an_error(league: Path) -> None:
    _order(league, "[category_order\n")
    with pytest.raises(ConfigFileError, match=r"pdbtoexcel\.toml"):
        load_config(LEAGUE)


def test_bom_is_skipped(league: Path) -> None:
    (league / "pdbtoexcel.toml").write_text(PDBTOEXCEL_TOML, encoding="utf-8-sig")
    assert load_config(LEAGUE).category_order[RUN][0] is O.RUN_LEFT


# ── deleted plays ─────────────────────────────────────────────────────────────


def test_deleted_plays_read_as_written(league: Path) -> None:
    _order(league, ORDER_ONLY + '[deleted_plays]\nnames = ["atf0elob", "XY"]\n')
    assert load_config(LEAGUE).deleted_plays == frozenset({"atf0elob", "XY"})


def test_deleted_plays_table_without_names_is_empty(league: Path) -> None:
    _order(league, ORDER_ONLY + "[deleted_plays]\n")
    assert load_config(LEAGUE).deleted_plays == frozenset()


@pytest.mark.parametrize("value", ['"ATF0ELOB"', "[1]"])
def test_deleted_plays_must_be_an_array_of_strings(league: Path, value: str) -> None:
    _order(league, ORDER_ONLY + f"[deleted_plays]\nnames = {value}\n")
    with _raises("[deleted_plays] names: expected an array of strings"):
        load_config(LEAGUE)


def test_deleted_plays_unknown_key_is_an_error(league: Path) -> None:
    _order(league, ORDER_ONLY + "[deleted_plays]\nplays = []\n")
    with _raises("[deleted_plays] plays: unknown key (expected names)"):
        load_config(LEAGUE)


# ── workbook options from [convert-pdb] in athc.ini ───────────────────────────


@pytest.mark.usefixtures("league")
def test_load_config_reads_workbook_options(write_config: WriteConfig) -> None:
    write_config(WORKBOOK_OPTIONS_INI)
    cfg = load_config(LEAGUE)
    assert cfg.calculate_percentages is False
    assert cfg.include_category_worksheets is True
    assert cfg.exclude_sacks_from_pass_attempts is False


@pytest.mark.usefixtures("league")
def test_workbook_options_default_without_section() -> None:
    cfg = load_config(LEAGUE)
    assert cfg.calculate_percentages is True
    assert cfg.include_category_worksheets is False
    assert cfg.exclude_sacks_from_pass_attempts is True


@pytest.mark.usefixtures("league")
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("yes", True),
        ("TRUE", True),
        ("On", True),
        ("0", False),
        ("no", False),
        ("False", False),
        ("OFF", False),
    ],
)
def test_workbook_option_accepts_configparser_booleans(
    write_config: WriteConfig, raw: str, expected: bool
) -> None:
    write_config(f"[convert-pdb]\ncalculate_percentages = {raw}\n")
    assert load_config(LEAGUE).calculate_percentages is expected


@pytest.mark.usefixtures("league")
def test_workbook_option_rejects_other_values(write_config: WriteConfig) -> None:
    write_config("[convert-pdb]\ncalculate_percentages = maybe\n")
    with pytest.raises(ConfigFileError, match="calculate_percentages"):
        load_config(LEAGUE)


@pytest.mark.usefixtures("league")
def test_calculate_total_stats_is_no_longer_read(write_config: WriteConfig) -> None:
    # Totals are always on; a leftover key is ignored, even with a bad value.
    write_config("[convert-pdb]\ncalculate_total_stats = maybe\n")
    assert not hasattr(load_config(LEAGUE), "calculate_total_stats")


# ── every shipped league loads ────────────────────────────────────────────────


@pytest.mark.parametrize("folder", ["dev", "release"])
@pytest.mark.parametrize("name", ["PNFL", "PCFL"])
def test_shipped_league_loads(
    monkeypatch: pytest.MonkeyPatch, folder: str, name: str
) -> None:
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(ROOT / "config" / folder))
    cfg = load_config(name)
    assert [len(cfg.category_order[t]) for t in (RUN, PASS, DEFENSE)] == [4, 9, 10]
    assert cfg.deleted_plays == frozenset({"ATF0ELOB"})
