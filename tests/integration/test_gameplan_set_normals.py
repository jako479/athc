"""Integration tests for `athc gameplan set-normals`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.set_normals import set_normals
from athc.errors import FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_gameplan import CustomPlayRef, PlayRef, read_gameplan
from tests.conftest import LEAGUE, league_toml
from tests.integration.conftest import GP_OFFENSE, PLAYS, TEAM_NAMES, lge, team

NORMAL = "OR45RL01"  # a real normal offense play in the pool
SPECIAL = "SFFGXPAT"  # a real special-teams offense play in the pool
MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league: the curated test pool."""
    folder = make_league(LEAGUE, league_toml(PLAYS))
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return folder


def _name(play: PlayRef | None) -> str:
    assert play is not None
    return play.name


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "offense.pln"
    shutil.copy2(GP_OFFENSE, dst)
    return dst


def _input(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "plays.txt"
    p.write_text(text, encoding="utf-8")
    return p


# ── usage ─────────────────────────────────────────────────────────────────────


def test_requires_gameplan(runner) -> None:
    assert runner.invoke(set_normals, []).exit_code == 2


def test_bare_is_missing_game_plan(runner) -> None:
    result = runner.invoke(set_normals, [])
    assert result.stderr.endswith("Error: Missing argument 'GAME_PLAN'.\n")


def test_requires_play_list(runner, tmp_path: Path) -> None:
    assert runner.invoke(set_normals, [str(_copy(tmp_path))]).exit_code == 2


def test_key_alone_is_missing_input_file(runner) -> None:
    result = runner.invoke(set_normals, ["off1"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'INPUT_FILE'.\n")


def test_extra_argument_rejected(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n")), "extra"]
    )
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (extra).\n")


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
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), str(_input(tmp_path, NORMAL + "\n"))])
    assert result.exit_code == 0
    rt = read_gameplan(str(p))
    assert rt.normal_plays[0] is not None and rt.normal_plays[0].name == NORMAL
    assert all(x is None for x in rt.normal_plays[1:])


def test_a_list_saved_with_a_bom_reads_its_first_play(runner, tmp_path: Path) -> None:
    """Notepad's "UTF-8 with BOM" puts a mark before the first play name."""
    p = _copy(tmp_path)
    inp = tmp_path / "plays.txt"
    inp.write_text(NORMAL + "\n", encoding="utf-8-sig")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


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
    assert result.stdout == f"OK   {p}: 1 normal play(s)\n"
    assert list(tmp_path.glob("*.bak")) == []


# ── comment parsing ───────────────────────────────────────────────────────────


def test_skips_comment_lines(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n{NORMAL}\n:: another\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_strips_inline_comments(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL} :: my favorite play\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_inline_comment_requires_space(runner, tmp_path: Path) -> None:
    """`name::comment` (no space) is not split, so the whole token fails to resolve."""
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{NORMAL}::comment\n")
    assert runner.invoke(set_normals, [str(p), str(inp)]).exit_code == 2


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
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), "-"], input=NORMAL + "\n")
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).normal_plays[0]) == NORMAL


def test_dash_input_errors_name_no_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_normals, [str(p), "-"], input="NOTAREALPLAY\n")
    assert result.exit_code == 2
    assert (
        "FAIL line 1: 'NOTAREALPLAY' not found in the play pool (slot 1-1).\n"
        in result.stderr
    )
    assert "FAIL - " not in result.stderr


def test_dash_input_line_is_the_real_line(runner, tmp_path: Path) -> None:
    """Blank and `::` lines count, CRLF or not, as in a file."""
    p = _copy(tmp_path)
    text = "\r\n:: my list\r\nNOTAREALPLAY\r\n"
    result = runner.invoke(set_normals, [str(p), "-"], input=text)
    assert result.exit_code == 2
    assert (
        "FAIL line 3: 'NOTAREALPLAY' not found in the play pool (slot 1-1).\n"
        in result.stderr
    )


def test_file_input_line_is_the_real_line(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f":: header\n\n{NORMAL}\nNOTAREALPLAY\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp}: line 4: 'NOTAREALPLAY' not found in the play pool (slot 1-2).\n"
        in result.stderr
    )


# ── validation / errors (target left untouched) ───────────────────────────────


def test_rejects_special_teams_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp}: line 1: '{SPECIAL}' is a special teams play. Use set-specials.\n"
        in result.stderr
    )
    assert p.read_bytes() == original


def test_missing_play_aborts(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    inp = _input(tmp_path, "NOTAREALPLAY\n")
    result = runner.invoke(set_normals, [str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {inp}: line 1: 'NOTAREALPLAY' not found in the play pool (slot 1-1).\n"
        in result.stderr
    )
    assert p.read_bytes() == original


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
    assert result.stdout == f"OK   {p}: 64 normal play(s)\n"


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


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


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
    inp = _input(tmp_path, NORMAL + "\n")
    result = runner.invoke(set_normals, ["off1", str(inp)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {folder / 'OFF1.pln'}: 1 normal play(s)\n"
    assert _name(read_gameplan(folder / "OFF1.pln").normal_plays[0]) == NORMAL


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
