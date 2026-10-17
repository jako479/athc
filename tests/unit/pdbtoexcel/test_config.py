"""Unit tests for convert-pdb config: `[convert-pdb]` in athc.toml, laid over
key by key by the same table in the league's league.toml (the workbook
options, the category order, the deleted plays), plus the league's play_path
and labels."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.config import ConfigFileError, LeagueError, config_file
from athc.fbpro98_play import DefensiveCategory as D
from athc.fbpro98_play import OffensiveCategory as O
from athc.pdbtoexcel import load_config
from athc.pdbtoexcel.pdb import PLAY_DATA
from tests.conftest import (
    CONVERT_PDB_TOML,
    LEAGUE,
    ROOT,
    athc_toml,
    league_toml,
)

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]
WriteBody = Callable[[str], Path]

RUN = PLAY_DATA.PLAY_TYPE.RUN
PASS = PLAY_DATA.PLAY_TYPE.PASS
DEFENSE = PLAY_DATA.PLAY_TYPE.DEFENSE

OPTIONS = (
    "calculate_percentages",
    "include_category_worksheets",
    "exclude_sacks_from_pass_attempts",
)
# What each option is without athc.toml or league.toml.
DEFAULTS = {
    "calculate_percentages": True,
    "include_category_worksheets": False,
    "exclude_sacks_from_pass_attempts": True,
}
# Every workbook option flipped away from its default.
FLIPPED = (
    "[convert-pdb]\ncalculate_percentages = false\n"
    "include_category_worksheets = true\nexclude_sacks_from_pass_attempts = false\n"
)
ORDER = "[convert-pdb.category_order]\n"
ORDER_ONLY = f'{ORDER}run = ["RL"]\npass = ["PSL"]\ndefense = ["RunLeft"]\n'
VALID_KEYS = (
    "calculate_percentages, category_order, deleted_plays, "
    "exclude_sacks_from_pass_attempts, include_category_worksheets"
)


@pytest.fixture
def league(make_league: MakeLeague, write_config: WriteConfig, tmp_path: Path) -> Path:
    """The test league with the PNFL labels and a play path, selected in an
    athc.toml that gives the PNFL order; nothing for convert-pdb in its
    league.toml."""
    folder = make_league(LEAGUE, league_toml(tmp_path))
    write_config(athc_toml(LEAGUE) + CONVERT_PDB_TOML)
    return folder


@pytest.fixture
def base(league: Path, write_config: WriteConfig) -> WriteBody:
    """Rewrite athc.toml: the league selected, then `body`."""

    def _base(body: str) -> Path:
        return write_config(athc_toml(LEAGUE) + body)

    return _base


@pytest.fixture
def override(league: Path, tmp_path: Path) -> WriteBody:
    """Rewrite the league's league.toml: its play path and labels, then
    `body`, the league's own convert-pdb tables."""

    def _override(body: str) -> Path:
        path = league / "league.toml"
        path.write_text(league_toml(tmp_path, convert_pdb=body), encoding="utf-8")
        return path

    return _override


def _raises(message: str):
    return pytest.raises(ConfigFileError, match=re.escape(message))


def _fails(message: str) -> None:
    """load_config raises ConfigFileError whose whole text is `message`."""
    with pytest.raises(ConfigFileError) as exc:
        load_config(LEAGUE)
    assert str(exc.value) == message


def _options() -> dict[str, bool]:
    cfg = load_config(LEAGUE)
    return {key: getattr(cfg, key) for key in OPTIONS}


# ── league folder ─────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("league")
def test_load_config_defaults(tmp_path: Path) -> None:
    cfg = load_config(LEAGUE)
    assert cfg.play_path == str(tmp_path)
    assert cfg.calculate_percentages is True
    assert cfg.deleted_plays == frozenset()


def test_load_config_from_league_folder(league: Path) -> None:
    (league / "league.toml").write_text(league_toml("D:\\plays"), encoding="utf-8")
    cfg = load_config(LEAGUE)
    assert cfg.play_path == "D:\\plays"


def test_load_config_needs_a_league() -> None:
    with pytest.raises(LeagueError, match="League is not set"):
        load_config()


def test_missing_play_path_is_an_error(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league(LEAGUE, league_toml())
    write_config(athc_toml(LEAGUE) + CONVERT_PDB_TOML)
    message = (
        f"{folder / 'league.toml'}: Play pool folder is not set. "
        "Run 'athc config set play_path FOLDER'."
    )
    with _raises(message) as exc:
        load_config(LEAGUE)
    assert str(exc.value) == message


# ── the category order ────────────────────────────────────────────────────────


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


def test_unlabeled_category_goes_by_its_game_name(base: WriteBody) -> None:
    # PNFL leaves Razzle Dazzle Run unlabeled; the game name names it.
    base(ORDER_ONLY.replace('run = ["RL"]', 'run = ["RL", "Razzle Dazzle Run"]'))
    assert load_config(LEAGUE).category_order[RUN] == (O.RUN_LEFT, O.RAZZLE_DAZZLE_RUN)


def test_labeled_category_by_game_name_is_unknown(base: WriteBody) -> None:
    base(ORDER_ONLY.replace('"RL"', '"Run Left"'))
    with _raises(
        "[convert-pdb.category_order] run: 'Run Left' is not a run category of "
        "this league"
    ):
        load_config(LEAGUE)


def test_unknown_name_lists_the_valid_ones(base: WriteBody) -> None:
    toml = base(ORDER_ONLY.replace('"RunLeft"', '"Nope"'))
    _fails(
        f"{toml}: [convert-pdb.category_order] defense: 'Nope' is not a defense "
        "category of this league. Valid: GLpass, GLrun, PassDazzle, PassLong, "
        "PassMedium, PassShort, RunDazzle, RunLeft, RunMiddle, RunRight, "
        "User Specific."
    )


def test_empty_list_is_allowed(base: WriteBody) -> None:
    base(ORDER_ONLY.replace('run = ["RL"]', "run = []"))
    assert load_config(LEAGUE).category_order[RUN] == ()


@pytest.mark.parametrize(
    ("key", "name", "message"),
    [
        ("run", "PSL", "[convert-pdb.category_order] run: 'PSL' is a pass category"),
        ("pass", "RL", "[convert-pdb.category_order] pass: 'RL' is a run category"),
        (
            "defense",
            "RL",
            "[convert-pdb.category_order] defense: 'RL' is not a defense category",
        ),
        # Offense but neither run nor pass: unknown for both keys, not "a pass category".
        ("run", "User Specific", "'User Specific' is not a run category"),
        ("pass", "User Specific", "'User Specific' is not a pass category"),
    ],
)
def test_wrong_side_is_an_error(
    base: WriteBody, key: str, name: str, message: str
) -> None:
    base(ORDER_ONLY.replace(f"{key} = [", f'{key} = ["{name}", '))
    with _raises(message):
        load_config(LEAGUE)


def test_repeated_name_is_an_error(base: WriteBody) -> None:
    base(ORDER_ONLY.replace('run = ["RL"]', 'run = ["RL", "RM", "RL"]'))
    with _raises("[convert-pdb.category_order] run: 'RL' is listed twice."):
        load_config(LEAGUE)


@pytest.mark.parametrize("value", ['"RL"', "[1]", '["RL", 2]'])
def test_list_must_be_an_array_of_strings(base: WriteBody, value: str) -> None:
    toml = base(ORDER_ONLY.replace('run = ["RL"]', f"run = {value}"))
    _fails(f"{toml}: [convert-pdb.category_order] run: Expected an array of strings.")


def test_unknown_key_is_an_error(base: WriteBody) -> None:
    toml = base(ORDER_ONLY + "special = []\nzap = []\n")
    _fails(
        f"{toml}: [convert-pdb.category_order]: Unknown key(s): special, zap. "
        "Valid: defense, pass, run."
    )


def test_unknown_top_level_key_is_an_error(base: WriteBody) -> None:
    toml = base(CONVERT_PDB_TOML + "[convert-pdb.filters]\nx = 1\n[convert-pdb.zap]\n")
    _fails(f"{toml}: [convert-pdb]: Unknown key(s): filters, zap. Valid: {VALID_KEYS}.")


# ── the base alone ────────────────────────────────────────────────────────────


def test_every_key_from_the_base(base: WriteBody) -> None:
    toml = base(
        FLIPPED + 'deleted_plays = ["XY"]\n' + ORDER_ONLY.replace('"RL"', '"RM"')
    )
    cfg = load_config(LEAGUE)
    assert _options() == {key: not DEFAULTS[key] for key in OPTIONS}
    assert cfg.category_order == {
        RUN: (O.RUN_MIDDLE,),
        PASS: (O.PASS_SHORT_LEFT,),
        DEFENSE: (D.RUN_LEFT,),
    }
    assert cfg.deleted_plays == frozenset({"XY"})
    assert cfg.deleted_plays_file == toml


def test_missing_lists_default_to_empty(base: WriteBody) -> None:
    """No category_order in either file: nothing of any type exported."""
    base("")
    assert load_config(LEAGUE).category_order == {RUN: (), PASS: (), DEFENSE: ()}


def test_a_missing_list_is_empty(base: WriteBody) -> None:
    """The table there without one of its lists: that list is empty."""
    base(ORDER_ONLY.replace('run = ["RL"]\n', ""))
    assert load_config(LEAGUE).category_order == {
        RUN: (),
        PASS: (O.PASS_SHORT_LEFT,),
        DEFENSE: (D.RUN_LEFT,),
    }


def test_missing_deleted_plays_is_empty(base: WriteBody) -> None:
    base(CONVERT_PDB_TOML)
    cfg = load_config(LEAGUE)
    assert cfg.deleted_plays == frozenset()
    assert cfg.deleted_plays_file == config_file()


def test_workbook_options_default_without_section(base: WriteBody) -> None:
    base("")
    assert _options() == DEFAULTS


def test_load_config_reads_workbook_options(base: WriteBody) -> None:
    base(FLIPPED)
    assert _options() == {key: not DEFAULTS[key] for key in OPTIONS}


# ── the league alone ──────────────────────────────────────────────────────────


def test_every_key_from_the_league(base: WriteBody, override: WriteBody) -> None:
    base("")
    toml = override(
        FLIPPED + 'deleted_plays = ["XY"]\n' + ORDER_ONLY.replace('"RL"', '"RM"')
    )
    cfg = load_config(LEAGUE)
    assert _options() == {key: not DEFAULTS[key] for key in OPTIONS}
    assert cfg.category_order == {
        RUN: (O.RUN_MIDDLE,),
        PASS: (O.PASS_SHORT_LEFT,),
        DEFENSE: (D.RUN_LEFT,),
    }
    assert cfg.deleted_plays == frozenset({"XY"})
    assert cfg.deleted_plays_file == toml


def test_league_alone_without_athc_toml(
    make_league: MakeLeague, config_dir: Path, tmp_path: Path
) -> None:
    """No athc.toml at all: the league's table and the defaults."""
    body = "[convert-pdb]\ncalculate_percentages = false\n" + ORDER_ONLY
    make_league(LEAGUE, league_toml(tmp_path, convert_pdb=body))
    assert not (config_dir / "athc.toml").exists()
    cfg = load_config(LEAGUE)
    assert cfg.calculate_percentages is False
    assert cfg.include_category_worksheets is False
    assert cfg.category_order[RUN] == (O.RUN_LEFT,)


# ── mixed: the league overrides a key at a time ───────────────────────────────


@pytest.mark.parametrize("key", OPTIONS)
def test_league_overrides_one_option_and_keeps_the_rest(
    base: WriteBody, override: WriteBody, key: str
) -> None:
    base(FLIPPED + CONVERT_PDB_TOML)
    override(f"[convert-pdb]\n{key} = {str(DEFAULTS[key]).lower()}\n")
    expected = {k: not DEFAULTS[k] for k in OPTIONS} | {key: DEFAULTS[key]}
    assert _options() == expected


@pytest.mark.parametrize(
    ("key", "names", "members"),
    [
        ("run", '["RM", "RL"]', (O.RUN_MIDDLE, O.RUN_LEFT)),
        ("pass", '["PLR"]', (O.PASS_LONG_RIGHT,)),
        ("defense", '["GLpass", "GLrun"]', (D.GOAL_LINE_PASS, D.GOAL_LINE_RUN)),
    ],
)
def test_league_overrides_one_list_and_keeps_the_rest(
    league: Path, override: WriteBody, key: str, names: str, members: tuple
) -> None:
    base_order = load_config(LEAGUE).category_order
    override(f"{ORDER}{key} = {names}\n")
    order = load_config(LEAGUE).category_order
    play_type = {"run": RUN, "pass": PASS, "defense": DEFENSE}[key]
    assert order[play_type] == members
    assert {t: v for t, v in order.items() if t != play_type} == {
        t: v for t, v in base_order.items() if t != play_type
    }


def test_league_empty_list_overrides_the_base(
    league: Path, override: WriteBody
) -> None:
    """An empty array is a value: the league exports no run plays."""
    override(f"{ORDER}run = []\n")
    order = load_config(LEAGUE).category_order
    assert order[RUN] == ()
    assert len(order[PASS]) == 9 and len(order[DEFENSE]) == 10


def test_league_overrides_deleted_plays_whole(
    base: WriteBody, override: WriteBody
) -> None:
    base('[convert-pdb]\ndeleted_plays = ["A", "C"]\n' + CONVERT_PDB_TOML)
    override('[convert-pdb]\ndeleted_plays = ["B"]\n')
    assert load_config(LEAGUE).deleted_plays == frozenset({"B"})


def test_league_options_and_base_lists(base: WriteBody, override: WriteBody) -> None:
    """The base gives the lists, the league one option: both apply."""
    base(CONVERT_PDB_TOML)
    override("[convert-pdb]\ncalculate_percentages = false\n")
    cfg = load_config(LEAGUE)
    assert cfg.calculate_percentages is False
    assert [len(cfg.category_order[t]) for t in (RUN, PASS, DEFENSE)] == [4, 9, 10]


@pytest.mark.parametrize(
    "body",
    ["[convert-pdb]\n", ORDER, "[convert-pdb]\n" + ORDER],
    ids=["options table", "order table", "both"],
)
def test_empty_league_table_keeps_the_base(
    base: WriteBody, override: WriteBody, body: str
) -> None:
    base(FLIPPED + 'deleted_plays = ["A"]\n' + CONVERT_PDB_TOML)
    override(body)
    cfg = load_config(LEAGUE)
    assert _options() == {key: not DEFAULTS[key] for key in OPTIONS}
    assert [len(cfg.category_order[t]) for t in (RUN, PASS, DEFENSE)] == [4, 9, 10]
    assert cfg.deleted_plays == frozenset({"A"})


def test_overridden_base_list_is_not_checked(
    base: WriteBody, override: WriteBody
) -> None:
    """A bad name the league's list replaces is never read."""
    base(ORDER_ONLY.replace('"RL"', '"Nope"'))
    override(f'{ORDER}run = ["RL"]\n')
    assert load_config(LEAGUE).category_order[RUN] == (O.RUN_LEFT,)


def test_overridden_base_option_is_not_checked(
    base: WriteBody, override: WriteBody
) -> None:
    base('[convert-pdb]\ncalculate_percentages = "maybe"\n')
    override("[convert-pdb]\ncalculate_percentages = false\n")
    assert load_config(LEAGUE).calculate_percentages is False


# ── a value's message names the file it came from ─────────────────────────────


@pytest.mark.parametrize("raw", ['"true"', "1", '"maybe"'])
def test_workbook_option_rejects_non_booleans(base: WriteBody, raw: str) -> None:
    """Only a TOML boolean: a string or a number, even one that reads as
    true, is not."""
    toml = base(f"[convert-pdb]\ncalculate_percentages = {raw}\n")
    _fails(f"{toml}: [convert-pdb] calculate_percentages: Expected true or false.")


def test_bad_option_names_the_base_file(base: WriteBody, override: WriteBody) -> None:
    toml = base('[convert-pdb]\ncalculate_percentages = "true"\n')
    override("[convert-pdb]\ninclude_category_worksheets = true\n")
    _fails(f"{toml}: [convert-pdb] calculate_percentages: Expected true or false.")


def test_bad_option_names_the_league_file(base: WriteBody, override: WriteBody) -> None:
    base(FLIPPED)
    toml = override('[convert-pdb]\ncalculate_percentages = "true"\n')
    _fails(f"{toml}: [convert-pdb] calculate_percentages: Expected true or false.")


def test_bad_list_names_its_file(league: Path, override: WriteBody) -> None:
    toml = override(f'{ORDER}run = "RL"\n')
    _fails(f"{toml}: [convert-pdb.category_order] run: Expected an array of strings.")


def test_unknown_name_names_its_file(league: Path, override: WriteBody) -> None:
    toml = override(f'{ORDER}pass = ["PSL", "Nope"]\n')
    with pytest.raises(ConfigFileError) as exc:
        load_config(LEAGUE)
    assert str(exc.value).startswith(
        f"{toml}: [convert-pdb.category_order] pass: 'Nope' is not a pass category "
        "of this league."
    )


def test_unknown_key_names_its_file(league: Path, override: WriteBody) -> None:
    toml = override("[convert-pdb]\nzap = 1\n")
    _fails(f"{toml}: [convert-pdb]: Unknown key(s): zap. Valid: {VALID_KEYS}.")


def test_unknown_order_key_names_its_file(league: Path, override: WriteBody) -> None:
    toml = override(f'{ORDER}special = ["RL"]\n')
    _fails(
        f"{toml}: [convert-pdb.category_order]: Unknown key(s): special. "
        "Valid: defense, pass, run."
    )


def test_unknown_keys_in_both_files_name_one_file(
    base: WriteBody, override: WriteBody
) -> None:
    """Each line names one file and only its own keys: athc.toml's first."""
    toml = base(CONVERT_PDB_TOML + "[convert-pdb]\naaa = 1\n")
    override("[convert-pdb]\nzap = 1\n")
    _fails(f"{toml}: [convert-pdb]: Unknown key(s): aaa. Valid: {VALID_KEYS}.")


def test_order_written_as_a_value_names_its_file(
    league: Path, override: WriteBody
) -> None:
    toml = override("[convert-pdb]\ncategory_order = 1\n")
    _fails(f"{toml}: [convert-pdb.category_order]: Must be a table.")


def test_order_written_as_a_value_in_the_base(base: WriteBody) -> None:
    toml = base("[convert-pdb]\ncategory_order = 1\n")
    _fails(f"{toml}: [convert-pdb.category_order]: Must be a table.")


def test_section_written_as_a_value_in_the_league_file(
    league: Path, tmp_path: Path
) -> None:
    # A top-level key goes above the first table header.
    toml = league / "league.toml"
    toml.write_text("convert-pdb = 1\n" + league_toml(tmp_path), encoding="utf-8")
    _fails(f"{toml}: [convert-pdb]: Must be a table.")


def test_section_written_as_a_value_in_the_base(
    league: Path, write_config: WriteConfig
) -> None:
    toml = write_config("convert-pdb = 1\n" + athc_toml(LEAGUE))
    _fails(f"{toml}: [convert-pdb]: Must be a table.")


@pytest.mark.parametrize("value", ['"ATF0ELOB"', "[1]"])
def test_deleted_plays_must_be_an_array_of_strings(base: WriteBody, value: str) -> None:
    toml = base(f"[convert-pdb]\ndeleted_plays = {value}\n")
    _fails(f"{toml}: [convert-pdb] deleted_plays: Expected an array of strings.")


def test_bad_deleted_plays_names_the_league_file(
    league: Path, override: WriteBody
) -> None:
    toml = override('[convert-pdb]\ndeleted_plays = "ATF0ELOB"\n')
    _fails(f"{toml}: [convert-pdb] deleted_plays: Expected an array of strings.")


def test_deleted_plays_read_as_written(base: WriteBody) -> None:
    base('[convert-pdb]\ndeleted_plays = ["atf0elob", "XY"]\n')
    assert load_config(LEAGUE).deleted_plays == frozenset({"atf0elob", "XY"})


def test_deleted_plays_file_is_where_the_list_came_from(
    base: WriteBody, override: WriteBody
) -> None:
    athc = base('[convert-pdb]\ndeleted_plays = ["A"]\n')
    assert load_config(LEAGUE).deleted_plays_file == athc
    toml = override('[convert-pdb]\ndeleted_plays = ["B"]\n')
    assert load_config(LEAGUE).deleted_plays_file == toml


def test_calculate_total_stats_is_an_unknown_key(base: WriteBody) -> None:
    # Totals are always on; the old key is not a setting.
    toml = base("[convert-pdb]\ncalculate_total_stats = true\n")
    _fails(
        f"{toml}: [convert-pdb]: Unknown key(s): calculate_total_stats. "
        f"Valid: {VALID_KEYS}."
    )


# ── every shipped league loads ────────────────────────────────────────────────


@pytest.mark.parametrize("folder", ["dev", "release"])
@pytest.mark.parametrize("name", ["PNFL", "PCFL"])
def test_shipped_league_loads(
    monkeypatch: pytest.MonkeyPatch, folder: str, name: str
) -> None:
    root = ROOT / "config" / folder
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(root))
    cfg = load_config(name)
    assert [len(cfg.category_order[t]) for t in (RUN, PASS, DEFENSE)] == [4, 9, 10]
    assert cfg.deleted_plays == frozenset({"ATF0ELOB"})
    assert cfg.deleted_plays_file == root / "athc.toml"
