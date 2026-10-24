"""Integration tests for `athc gameplan set-normals`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.list_normals import list_normals
from athc.cli.gameplan.set_normals import set_normals
from athc.errors import FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_gameplan import CustomPlayRef, read_gameplan, write_gameplan
from tests.conftest import LEAGUE, athc_toml, league_not_found, league_toml
from tests.integration.conftest import (
    EMPTY_SLOTS_PLAYS,
    GP_DEFENSE,
    GP_EMPTY_SLOTS,
    GP_OFFENSE,
    PLAYS,
    TEAM_NAMES,
    lge,
    play_name,
    set_league,
    team,
)

NORMAL = "OR45RL01"  # a real normal offense play in the pool
SPECIAL = "SFFGXPAT"  # a real special offense play in the pool
DEFENSE = "NY31RL01"  # a real normal defense play in the pool
MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league: the curated test pool."""
    folder = make_league(LEAGUE, league_toml(PLAYS))
    write_config(athc_toml())
    return folder


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "offense.pln"
    shutil.copy2(GP_OFFENSE, dst)
    return dst


def _without_first_normal(path: Path) -> Path:
    """`path` rewritten with normal slot 0 empty."""
    gp = read_gameplan(path)
    write_gameplan(gp.with_normal_plays([None, *gp.normal_plays[1:]]), path)
    assert read_gameplan(path).normal_plays[0] is None
    return path


def _input(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "plays.txt"
    p.write_text(text, encoding="utf-8")
    return p


# ── usage ─────────────────────────────────────────────────────────────────────


def test_bare_is_missing_game_plan(runner) -> None:
    result = runner.invoke(set_normals, [])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'GAME_PLAN'.\n")


def test_requires_play_list(runner, tmp_path: Path) -> None:
    result = runner.invoke(set_normals, [str(_copy(tmp_path))])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'INPUT_FILE'.\n")


def test_key_alone_is_missing_input_file(runner) -> None:
    result = runner.invoke(set_normals, ["off1"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'INPUT_FILE'.\n")


def test_play_list_not_text(runner, tmp_path: Path) -> None:
    """A game plan given as the list: one FAIL line naming the list, the game
    plan untouched."""
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(set_normals, [str(p), str(GP_OFFENSE)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {GP_OFFENSE}: Not a valid play list.\n"
    assert p.read_bytes() == original


def test_team_with_a_path_is_a_usage_error(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp), "--team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team requires a game plan key (off1, def1, off2 or def2).\n"
    )


@pytest.mark.parametrize(
    "extra",
    [
        ["--stdin"],
        ["--no-backup"],
        ["--play-path", "plays"],
        ["--playpool-rules", "rules.toml"],
    ],
)
def test_removed_options_rejected(runner, tmp_path: Path, extra: list[str]) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp), *extra])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


# ── file input ────────────────────────────────────────────────────────────────


def test_writes_from_file(runner, tmp_path: Path) -> None:
    p = _without_first_normal(_copy(tmp_path))
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert rt.normal_plays[0] is not None and rt.normal_plays[0].name == NORMAL
    assert all(x is None for x in rt.normal_plays[1:])


def test_a_list_saved_with_a_bom_reads_its_first_play(runner, tmp_path: Path) -> None:
    """Notepad's "UTF-8 with BOM" puts a mark before the first play name."""
    p = _without_first_normal(_copy(tmp_path))
    inp = tmp_path / "plays.txt"
    inp.write_text(NORMAL + "\n", encoding="utf-8-sig")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert play_name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_slot_path_starts_with_play_pool_folder(runner, tmp_path: Path) -> None:
    """A slot's path starts with the play pool's folder name, not a fixed league."""
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    play = read_gameplan(str(p)).normal_plays[0]
    assert isinstance(play, CustomPlayRef)
    assert play.filename == f"{PLAYS.name}\\Offense\\RL\\{NORMAL}.ply"


def test_writes_no_backup(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {p}: updated (1 normal play(s))\n"
    assert list(tmp_path.glob("*.bak")) == []


# ── comment parsing ───────────────────────────────────────────────────────────


def test_skips_comment_lines(runner, tmp_path: Path) -> None:
    p = _without_first_normal(_copy(tmp_path))
    inp = _input(tmp_path, f":: header\n{NORMAL}\n:: another\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 0
    assert play_name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_strips_inline_comments(runner, tmp_path: Path) -> None:
    p = _without_first_normal(_copy(tmp_path))
    inp = _input(tmp_path, f"{NORMAL} :: my favorite play\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 0
    assert play_name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_inline_comment_requires_space(runner, tmp_path: Path) -> None:
    """`name::comment` (no space) is not split, so the whole token fails to resolve."""
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL}::comment\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {inp}: line 1: '{NORMAL}::comment' is not in the play pool (slot 1-1).\n"
    )


# ── blank lines ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_blank_lines_leave_their_slots_empty(
    runner, tmp_path: Path, newline: str
) -> None:
    p = _copy(tmp_path)
    lines = [NORMAL, "", "DN28RM01", "", "", "AT21Draw"]
    inp = tmp_path / "plays.txt"
    inp.write_bytes((newline.join(lines) + newline).encode("utf-8"))
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {p}: updated (3 normal play(s))\n"
    slots = read_gameplan(str(p)).normal_plays
    assert [i for i, s in enumerate(slots) if s is not None] == [0, 2, 5]
    assert [play_name(slots[i]) for i in (0, 2, 5)] == [NORMAL, "DN28RM01", "AT21Draw"]


def test_only_blank_lines_clear_every_slot(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, "\n\n:: none\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {p}: updated (0 normal play(s))\n"
    assert all(s is None for s in read_gameplan(str(p)).normal_plays)


def test_last_play_on_slot_64_accepted(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, "\n" * 63 + NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert play_name(read_gameplan(str(p)).normal_plays[63]) == NORMAL


def test_last_play_on_slot_65_rejected(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, "\n" * 64 + NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {inp}: Too many plays (65). The most is 64.\n"
    assert p.read_bytes() == original


def test_trailing_blank_lines_after_64_plays_accepted(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, (NORMAL + "\n") * 64 + "\n\n  \n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {p}: updated (64 normal play(s))\n"


def test_slot_listing_reads_back_to_the_same_slots(
    runner, league: Path, tmp_path: Path
) -> None:
    """A defense game plan saved by the game with empty slots, listed by
    `list-normals` (slot order, blanks kept) and read back by set-normals,
    gives the same slots."""
    (league / "league.toml").write_text(
        league_toml(EMPTY_SLOTS_PLAYS), encoding="utf-8"
    )
    listing = runner.invoke(list_normals, [str(GP_EMPTY_SLOTS), "-"])
    target = tmp_path / "defense.pln"
    shutil.copy2(GP_DEFENSE, target)
    result = runner.invoke(set_normals, [str(target), "-"], input=listing.stdout)
    assert result.exit_code == 0

    def names(path: Path) -> list[str | None]:
        return [s.name if s else None for s in read_gameplan(str(path)).normal_plays]

    assert names(target) == names(GP_EMPTY_SLOTS)


# ── quiet / console input ─────────────────────────────────────────────────────


def test_quiet_is_rejected(runner, tmp_path: Path) -> None:
    """No athc command has a quiet flag; `> nul` hides the OK line."""
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), "-q"]
    )
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: No such option '-q'.\n")
    assert p.read_bytes() == original


def test_dash_reads_from_console(runner, tmp_path: Path) -> None:
    p = _without_first_normal(_copy(tmp_path))
    result = runner.invoke(set_normals, [str(p), "-"], input=NORMAL + "\n")
    assert result.exit_code == 0
    assert play_name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_dash_input_errors_name_no_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), "-"], input="NOTAREALPLAY\n")
    assert result.exit_code == 2
    assert (
        "FAIL line 1: 'NOTAREALPLAY' is not in the play pool (slot 1-1).\n"
        in result.stderr
    )
    assert "FAIL - " not in result.stderr


def test_dash_input_line_is_the_real_line(runner, tmp_path: Path) -> None:
    """Blank and `::` lines count, CRLF or not, as in a file; a blank line
    also takes a slot."""
    p = _copy(tmp_path)
    text = "\r\n:: my list\r\nNOTAREALPLAY\r\n"
    result = runner.invoke(set_normals, [str(p), "-"], input=text)
    assert result.exit_code == 2
    assert (
        "FAIL line 3: 'NOTAREALPLAY' is not in the play pool (slot 1-2).\n"
        in result.stderr
    )


def test_file_input_line_is_the_real_line(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n\n{NORMAL}\nNOTAREALPLAY\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp}: line 4: 'NOTAREALPLAY' is not in the play pool (slot 1-3).\n"
        in result.stderr
    )


# ── validation / errors (target left untouched) ───────────────────────────────


def test_rejects_special_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp}: line 1: '{SPECIAL}' is a special play. Run 'athc gameplan set-specials'.\n"
        in result.stderr
    )
    assert p.read_bytes() == original


def test_special_play_does_not_hide_other_bad_lines(runner, tmp_path: Path) -> None:
    """Every bad line is a FAIL in one run, in list order, the special one
    pointing to set-specials."""
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, f"NOTAREALPLAY\n{SPECIAL}\n{DEFENSE}\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {inp}: line 1: 'NOTAREALPLAY' is not in the play pool (slot 1-1).\n"
        f"FAIL {inp}: line 2: '{SPECIAL}' is a special play. Run 'athc gameplan "
        "set-specials'.\n"
        f"FAIL {inp}: line 3: '{DEFENSE}' is a defensive play, but the game plan "
        "is offensive.\n"
    )
    assert result.stdout == ""
    assert p.read_bytes() == original


def test_missing_play_aborts(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, "NOTAREALPLAY\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp}: line 1: 'NOTAREALPLAY' is not in the play pool (slot 1-1).\n"
        in result.stderr
    )
    assert p.read_bytes() == original


def test_every_bad_line_is_a_fail_line(runner, tmp_path: Path) -> None:
    """One FAIL per bad line, in list order; the good line is not written."""
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, f"NOTAREALPLAY\n{NORMAL}\n{DEFENSE}\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {inp}: line 1: 'NOTAREALPLAY' is not in the play pool (slot 1-1).\n"
        f"FAIL {inp}: line 3: '{DEFENSE}' is a defensive play, but the game plan "
        "is offensive.\n"
    )
    assert result.stdout == ""
    assert p.read_bytes() == original


def test_play_names_match_any_case(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL.lower() + "\n"))]
    )
    assert result.exit_code == 0
    assert play_name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_malformed_game_plan(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = runner.invoke(set_normals, [str(bad), str(_input(tmp_path, NORMAL))])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
    )
    assert bad.read_bytes() == b"\x00\x01\x02"


def test_league_that_does_not_exist_fails_first(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    """Before the game plan and the list, which are missing too."""
    result = runner.invoke(
        set_normals,
        [str(tmp_path / "nope.pln"), str(tmp_path / "nope.txt"), "--league", "NOPE"],
    )
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_too_many_plays_rejected(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, (NORMAL + "\n") * 65)
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {inp}: Too many plays (65). The most is 64.\n"


def test_too_many_plays_from_the_console_names_no_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), "-"], input=(NORMAL + "\n") * 65)
    assert result.exit_code == 2
    assert result.stderr == "FAIL Too many plays (65). The most is 64.\n"


def test_as_many_plays_as_slots_accepted(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, (NORMAL + "\n") * 64)
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {p}: updated (64 normal play(s))\n"


def test_missing_pln(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(tmp_path / "nope.pln"), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.pln'}: {FILE_NOT_FOUND}\n"


def test_missing_play_list(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(tmp_path / "nope.txt")])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.txt'}: {FILE_NOT_FOUND}\n"


def test_invalid_play_path(runner, league: Path, tmp_path: Path) -> None:
    (league / "league.toml").write_text(
        league_toml(tmp_path / "missing"), encoding="utf-8"
    )
    p = _copy(tmp_path)
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {tmp_path / 'missing'}: {PATH_NOT_FOUND} "
        "Run 'athc config set play_path FOLDER'.\n"
    )


# ── a game plan key ───────────────────────────────────────────────────────────


def team_league(league: Path, tmp_path: Path, **settings: str | Path) -> Path:
    """The league's .lg2 and .lge in `tmp_path/lg2`, Denver's four game plans
    named after their keys (off1 there, an offense copy), `path` and
    `settings` set; returns Denver's league folder."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    record = team(
        ("o1.prf", "OFF1.pln"),
        ("d1.prf", "DEF1.pln"),
        ("o2.prf", "OFF2.pln"),
        ("d2.prf", "DEF2.pln"),
    )
    (lg2_dir / f"{LEAGUE}.lg2").write_bytes(record)
    (lg2_dir / f"{LEAGUE}.lge").write_bytes(lge(TEAM_NAMES[0]))
    set_league(league, path=lg2_dir, **settings)
    folder = lg2_dir / "PNFL" / "2049" / "Plans" / "Team"
    folder.mkdir(parents=True)
    shutil.copy2(GP_OFFENSE, folder / "OFF1.pln")
    return folder


def test_key_sets_your_game_plan(runner, league: Path, tmp_path: Path) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    _without_first_normal(folder / "OFF1.pln")
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, ["off1", str(inp)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {folder / 'OFF1.pln'}: updated (1 normal play(s))\n"
    assert play_name(read_gameplan(folder / "OFF1.pln").normal_plays[0]) == NORMAL


def test_key_missing_names_the_game_plan(runner, league: Path, tmp_path: Path) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, ["off2", str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'OFF2.pln'}: {FILE_NOT_FOUND} Run 'athc config set "
        "ppp_path FOLDER' or pass a .pln file.\n"
    )


def test_too_many_plays_with_a_path_fail_before_the_league(
    runner, write_config: WriteConfig, tmp_path: Path
) -> None:
    """A path reads no league before the list: here no league is selected."""
    write_config("[athc]\n")
    p = _copy(tmp_path)
    inp = _input(tmp_path, (NORMAL + "\n") * 65)
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {inp}: Too many plays (65). The most is 64.\n"


def test_key_reads_the_league_before_the_list(
    runner, league: Path, tmp_path: Path
) -> None:
    """A key comes first on the usage line, so the team is read before the
    list is: no `team` fails before the list is counted."""
    inp = _input(tmp_path, (NORMAL + "\n") * 65)
    result = runner.invoke(set_normals, ["off1", str(inp)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'league.toml'}: Team is not set. Run 'athc config set "
        "team NAME' or pass --team or a .pln file.\n"
    )
