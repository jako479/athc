"""Integration tests for `athc gameplan list-normals` / `list-specials`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import click
import pytest

from athc.cli.gameplan.list_normals import list_normals
from athc.cli.gameplan.list_specials import list_specials
from athc.errors import ACCESS_DENIED, ALREADY_EXISTS, FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_gameplan import ProfileType, write_gameplan
from tests.conftest import (
    LEAGUE,
    OTHER_LEAGUE,
    athc_toml,
    league_not_found,
    league_toml,
    no_league_selected,
    toml_error,
)
from tests.integration.conftest import (
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    TEAM_NAMES,
    build_gameplan,
    lge,
    offense_normal,
    team,
)

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league, carrying the PNFL category labels; list-normals
    needs nothing else from it."""
    write_config(athc_toml())
    return make_league(LEAGUE, league_toml())


def _expected(name: str) -> list[str]:
    return (EXPECTED / name).read_text(encoding="utf-8").splitlines()


# ── list-normals ──────────────────────────────────────────────────────────────


def test_normals_rejects_invalid_sort(runner, tmp_path: Path) -> None:
    gp = tmp_path / "OFF.pln"
    shutil.copy2(GP_OFFENSE, gp)
    result = runner.invoke(list_normals, [str(gp), "--sort", "bogus"])
    assert result.exit_code == 2
    assert "Error: Invalid value for '--sort': 'bogus' is not one of" in result.stderr
    assert not (tmp_path / "OFF.normals.txt").exists()


def test_normals_help_uses_uppercase_names(runner) -> None:
    result = runner.invoke(list_normals, ["--help"])
    assert result.exit_code == 0
    assert "[OPTIONS] GAME_PLAN [OUTPUT]" in " ".join(result.stdout.split())
    assert all(
        name not in result.stdout for name in ("GAMEPLAN", "OUTPUT_PATH", "OUTPUT_FILE")
    )


@pytest.mark.parametrize("option", ["--force", "--output"])
def test_normals_removed_options_rejected(runner, tmp_path: Path, option: str) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), option, str(out)])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


def test_normals_default_writes_next_to_gameplan(runner, tmp_path: Path) -> None:
    gp = tmp_path / "OFF.pln"
    shutil.copy2(GP_OFFENSE, gp)
    result = runner.invoke(list_normals, [str(gp)])
    assert result.exit_code == 0
    out = tmp_path / "OFF.normals.txt"
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(gp.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_normals_slot.txt")


def test_normals_creates_missing_folder(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_slot.txt"
    )


def test_normals_creates_missing_folders_in_full(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "2049" / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


def test_normals_output_folder_is_a_file_exit_2(runner, tmp_path: Path) -> None:
    (tmp_path / "lists").write_text("x", encoding="utf-8")
    out = tmp_path / "lists" / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {out.parent}: {ALREADY_EXISTS}\n"


def test_normals_overwrites_existing_file(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_slot.txt"
    )


def test_normals_dash_offense_slot(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("offense_normals_slot.txt")


def test_normals_dash_defense_slot(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_DEFENSE), "-"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("defense_normals_slot.txt")


def test_normals_dash_sort_name(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-", "--sort", "name"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("offense_normals_name.txt")


def test_normals_dash_sort_category_offense(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-", "--sort", "category"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("offense_normals_category.txt")


def test_normals_dash_sort_category_defense(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_DEFENSE), "-", "--sort", "category"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("defense_normals_category.txt")


def test_normals_sort_category_game_name_without_label(runner, tmp_path: Path) -> None:
    """A category the league has no label for is headed by its game name; Pass
    Long Left/Middle sit before PLR, Razzle Dazzle Run before PRD, User Specific
    last; an empty category gets no header; slot order holds within one."""
    plays = [
        offense_normal("USR1", 0xFF),  # User Specific
        offense_normal("PRD1", 0x0F),
        offense_normal("RRD1", 0x0D),
        offense_normal("PLR1", 0x23),
        offense_normal("PLM1", 0x2B),
        offense_normal("PLL1", 0x27),
        offense_normal("PLL2", 0xA7),  # bits 7-6 vary within a category
    ]
    gp = build_gameplan(ProfileType.OFFENSE, normals=dict(enumerate(plays)))
    path = tmp_path / "OFF.pln"
    write_gameplan(gp, path)
    result = runner.invoke(list_normals, [str(path), "-", "--sort", "category"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        ":: Pass Long Left", "PLL1", "PLL2",
        ":: Pass Long Middle", "PLM1",
        ":: PLR", "PLR1",
        ":: Razzle Dazzle Run", "RRD1",
        ":: PRD", "PRD1",
        ":: User Specific", "USR1",
    ]  # fmt: skip


def test_normals_sort_name_drops_blanks_and_ignores_case(
    runner, tmp_path: Path
) -> None:
    """A plain sort would put CHARLIE before bravo."""
    plays = {
        5: offense_normal("bravo"),
        9: offense_normal("Alpha"),
        20: offense_normal("CHARLIE"),
    }
    path = tmp_path / "OFF.pln"
    write_gameplan(build_gameplan(ProfileType.OFFENSE, normals=plays), path)
    result = runner.invoke(list_normals, [str(path), "-", "--sort", "name"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["Alpha", "bravo", "CHARLIE"]


def test_normals_sort_category_without_league_labels(runner, league: Path) -> None:
    (league / "league.toml").write_text(league_toml(labels=False), encoding="utf-8")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-", "--sort", "category"])
    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    assert lines[0] == ":: Run Left"
    assert ":: Goal Line Pass" in lines
    assert ":: RL" not in lines


def test_normals_league_option_picks_league(runner, make_league: MakeLeague) -> None:
    make_league(OTHER_LEAGUE, league_toml(labels=False))
    result = runner.invoke(
        list_normals,
        [str(GP_OFFENSE), "-", "--sort", "category", "--league", OTHER_LEAGUE],
    )
    assert result.exit_code == 0
    assert result.stdout.splitlines()[0] == ":: Run Left"


def test_normals_league_that_does_not_exist_fails_first(
    runner, config_dir: Path, tmp_path: Path
) -> None:
    """Before the game plan, which is missing too."""
    result = runner.invoke(
        list_normals, [str(tmp_path / "nope.pln"), "-", "--league", "NOPE"]
    )
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)
    assert result.stdout == ""


def test_normals_no_league_exit_2(
    runner, config_dir: Path, write_config: WriteConfig
) -> None:
    write_config("[athc]\n")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert result.stdout == ""


def test_normals_bad_league_toml_exit_2(runner, league: Path) -> None:
    (league / "league.toml").write_text("[league\n", encoding="utf-8")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'league.toml'}: {toml_error('[league' + chr(10))}\n"
    )


def test_normals_file_sort_category(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(
        list_normals, [str(GP_OFFENSE), str(out), "--sort", "category"]
    )
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_category.txt"
    )


def test_normals_file_sort_category_counts_plays_not_headers(
    runner, tmp_path: Path
) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(
        list_normals, [str(GP_OFFENSE), str(out), "--sort", "category"]
    )
    assert result.exit_code == 0
    assert result.stdout == f"OK   {out}: 64 normal play(s)\n"


def test_normals_file_writes_header_and_plays(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(GP_OFFENSE.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_normals_slot.txt")


def test_normals_file_sort_name(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out), "--sort", "name"])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_name.txt"
    )


def test_normals_file_logs_count(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {out}: 64 normal play(s)\n"


def test_normals_missing_gameplan(runner, tmp_path: Path) -> None:
    result = runner.invoke(list_normals, [str(tmp_path / "nope.pln")])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.pln'}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_specials_missing_gameplan(runner, tmp_path: Path) -> None:
    result = runner.invoke(list_specials, [str(tmp_path / "nope.pln")])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.pln'}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_normals_malformed_file_mode_no_output(runner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00\x01\x02")
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(bad), str(out)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
    )
    assert not out.exists()


# ── list-specials ─────────────────────────────────────────────────────────────


def test_specials_help_uses_uppercase_names(runner) -> None:
    result = runner.invoke(list_specials, ["--help"])
    assert result.exit_code == 0
    assert "[OPTIONS] GAME_PLAN [OUTPUT]" in " ".join(result.stdout.split())
    assert all(
        name not in result.stdout for name in ("GAMEPLAN", "OUTPUT_PATH", "OUTPUT_FILE")
    )


@pytest.mark.parametrize("option", ["--force", "--output"])
def test_specials_removed_options_rejected(runner, tmp_path: Path, option: str) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), option, str(out)])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


def test_specials_default_writes_next_to_gameplan(runner, tmp_path: Path) -> None:
    gp = tmp_path / "OFF.pln"
    shutil.copy2(GP_OFFENSE, gp)
    result = runner.invoke(list_specials, [str(gp)])
    assert result.exit_code == 0
    out = tmp_path / "OFF.specials.txt"
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(gp.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_specials.txt")


def test_specials_creates_missing_folder(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


def test_specials_creates_missing_folders_in_full(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "2049" / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


def test_specials_overwrites_existing_file(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_specials.txt"
    )


def test_specials_dash_offense(runner) -> None:
    result = runner.invoke(list_specials, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("offense_specials.txt")


def test_specials_dash_defense(runner) -> None:
    result = runner.invoke(list_specials, [str(GP_DEFENSE), "-"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("defense_specials.txt")


def test_specials_file_writes_header_and_plays(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(GP_OFFENSE.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_specials.txt")


def test_specials_file_logs_count(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {out}: 6 special play(s)\n"


def test_specials_malformed_file_mode_no_output(runner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00\x01\x02")
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(bad), str(out)])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
    )
    assert not out.exists()


# ── arguments ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("command", [list_normals, list_specials])
def test_bare_is_missing_game_plan(runner, command: click.Command) -> None:
    result = runner.invoke(command, [])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'GAME_PLAN'.\n")


def test_normals_extra_argument_rejected(runner, tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out), "extra"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (extra).\n")
    assert not out.exists()


@pytest.mark.parametrize("command", [list_normals, list_specials])
def test_team_with_a_path_is_a_usage_error(runner, command: click.Command) -> None:
    result = runner.invoke(command, [str(GP_OFFENSE), "-", "--team", "Denver"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team requires a game plan key (off1, def1, off2 or def2).\n"
    )
    assert result.stdout == ""


OUTPUTS = [(list_normals, ".normals.txt"), (list_specials, ".specials.txt")]
OUTPUT_IDS = ["list-normals", "list-specials"]


@pytest.mark.parametrize(("command", "suffix"), OUTPUTS, ids=OUTPUT_IDS)
def test_output_folder_gets_the_default_name(
    runner, tmp_path: Path, command: click.Command, suffix: str
) -> None:
    lists = tmp_path / "lists"
    lists.mkdir()
    result = runner.invoke(command, [str(GP_OFFENSE), str(lists)])
    assert result.exit_code == 0
    assert (lists / f"{GP_OFFENSE.stem}{suffix}").is_file()


@pytest.mark.parametrize(("command", "suffix"), OUTPUTS, ids=OUTPUT_IDS)
def test_output_ending_in_a_backslash_is_a_new_folder(
    runner, tmp_path: Path, command: click.Command, suffix: str
) -> None:
    lists = tmp_path / "lists"
    result = runner.invoke(command, [str(GP_OFFENSE), f"{lists}\\"])
    assert result.exit_code == 0
    assert (lists / f"{GP_OFFENSE.stem}{suffix}").is_file()


@pytest.mark.parametrize("command", [list_normals, list_specials], ids=OUTPUT_IDS)
def test_output_without_an_extension_gets_txt(
    runner, tmp_path: Path, command: click.Command
) -> None:
    result = runner.invoke(command, [str(GP_OFFENSE), str(tmp_path / "plays")])
    assert result.exit_code == 0
    assert (tmp_path / "plays.txt").is_file()
    assert not (tmp_path / "plays").exists()


# ── --league on list-specials: resolved, read only for a key ──────────────────


def test_specials_league_with_a_path_reads_nothing_from_it(
    runner, make_league: MakeLeague
) -> None:
    """The league must exist; with a path nothing in it is read, so a broken
    league.toml does not matter."""
    make_league(OTHER_LEAGUE, "[league\n")
    result = runner.invoke(
        list_specials, [str(GP_OFFENSE), "-", "--league", OTHER_LEAGUE]
    )
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("offense_specials.txt")


def test_specials_league_that_does_not_exist_fails_even_with_a_path(
    runner, config_dir: Path
) -> None:
    result = runner.invoke(list_specials, [str(GP_OFFENSE), "-", "--league", "NOPE"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)
    assert result.stdout == ""


def test_specials_path_without_any_settings(runner, config_dir: Path) -> None:
    (config_dir / "athc.toml").unlink()
    result = runner.invoke(list_specials, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 0


def test_specials_key_needs_a_league(
    runner, config_dir: Path, write_config: WriteConfig
) -> None:
    write_config("[athc]\n")
    result = runner.invoke(list_specials, ["off1"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)


# ── a game plan key ───────────────────────────────────────────────────────────


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


def team_league(
    league: Path,
    tmp_path: Path,
    off: str = "OFF1.pln",
    off2: str = "OFF2.pln",
    **settings: str | Path,
) -> Path:
    """The league's .lg2 and .lge in `tmp_path/lg2` (Denver, then Las Vegas,
    both in one folder), `path` and `settings` set. Denver's offense game
    plans are `off` and `off2`, its defense ones DEF1.pln and DEF2.pln, all
    there (copies of the test game plans); Las Vegas's are never there.
    Returns the teams' league folder."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    denver = team(
        ("o1.prf", off),
        ("d1.prf", "DEF1.pln"),
        ("o2.prf", off2),
        ("d2.prf", "DEF2.pln"),
    )
    las_vegas = team(("lo.prf", "RAIDEROFF.pln"), ("ld.prf", "RAIDERDEF.pln"))
    (lg2_dir / f"{LEAGUE}.lg2").write_bytes(denver + las_vegas)
    (lg2_dir / f"{LEAGUE}.lge").write_bytes(lge(*TEAM_NAMES[:2]))
    set_league(league, path=lg2_dir, **settings)
    folder = lg2_dir / "PNFL" / "2049" / "Plans" / "Team"
    folder.mkdir(parents=True)
    for name in {off, off2}:
        shutil.copy2(GP_OFFENSE, folder / name)
    for name in ("DEF1.pln", "DEF2.pln"):
        shutil.copy2(GP_DEFENSE, folder / name)
    return folder


@pytest.mark.parametrize(
    ("key", "name", "count"),
    [
        ("off1", "OFF1.pln", 64),
        ("def1", "DEF1.pln", 50),
        ("off2", "OFF2.pln", 64),
        ("DEF2", "DEF2.pln", 50),
    ],
)
def test_normals_key_writes_beside_the_game_plan(
    runner, league: Path, tmp_path: Path, key: str, name: str, count: int
) -> None:
    """Each key is its .lg2 entry, any case; the list lands beside the game
    plan and the OK line names its full path."""
    folder = team_league(league, tmp_path, team="Denver")
    result = runner.invoke(list_normals, [key])
    assert result.exit_code == 0
    out = folder / name.replace(".pln", ".normals.txt")
    assert result.stdout == f"OK   {out}: {count} normal play(s)\n"
    assert str((folder / name).resolve()) in out.read_text(encoding="utf-8")


def test_specials_key_to_the_console(runner, league: Path, tmp_path: Path) -> None:
    team_league(league, tmp_path, team="Denver")
    result = runner.invoke(list_specials, ["def1", "-"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("defense_specials.txt")


def test_two_keys_one_shared_game_plan_write_one_file_twice(
    runner, league: Path, tmp_path: Path
) -> None:
    folder = team_league(league, tmp_path, "OFF.pln", "OFF.pln", team="Denver")
    first = runner.invoke(list_normals, ["off1"])
    second = runner.invoke(list_normals, ["off2"])
    out = folder / "OFF.normals.txt"
    assert first.stdout == second.stdout == f"OK   {out}: 64 normal play(s)\n"


def test_key_from_ppp_path(runner, league: Path, tmp_path: Path) -> None:
    """In ppp_path a key's game plan is found by its .lg2 name, any case, and
    the list lands beside it, in the coach's own folder."""
    mine = tmp_path / "mine"
    mine.mkdir()
    shutil.copy2(GP_OFFENSE, mine / "off1.PLN")
    team_league(league, tmp_path, team="Denver", ppp_path=mine)
    result = runner.invoke(list_normals, ["off1"])
    assert result.exit_code == 0
    assert result.stdout == f"OK   {mine / 'off1.normals.txt'}: 64 normal play(s)\n"


def test_key_team_option_names_another_team(
    runner, league: Path, tmp_path: Path
) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    result = runner.invoke(list_specials, ["off1", "-", "--team", "Las Vegas"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'RAIDEROFF.pln'}: {FILE_NOT_FOUND}\n"


def test_key_missing_at_your_league_location(
    runner, league: Path, tmp_path: Path
) -> None:
    """The run's error, with the ppp_path hint: the team is yours."""
    folder = team_league(league, tmp_path, team="Denver")
    (folder / "OFF2.pln").unlink()
    result = runner.invoke(list_specials, ["off2", "-"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'OFF2.pln'}: {FILE_NOT_FOUND} Run 'athc config set "
        "ppp_path FOLDER' or pass a .pln file.\n"
    )
    assert result.stdout == ""


def test_key_missing_folder_is_the_path_phrase(
    runner, league: Path, tmp_path: Path
) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    shutil.rmtree(folder)
    result = runner.invoke(list_specials, ["off1", "-"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'OFF1.pln'}: {PATH_NOT_FOUND} Run 'athc config set "
        "ppp_path FOLDER' or pass a .pln file.\n"
    )


def test_key_missing_in_ppp_path(runner, league: Path, tmp_path: Path) -> None:
    mine = tmp_path / "mine"
    mine.mkdir()
    team_league(league, tmp_path, team="Denver", ppp_path=mine)
    result = runner.invoke(list_specials, ["off1", "-"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {mine / 'OFF1.pln'}: {FILE_NOT_FOUND}\n"


def test_key_team_not_set(runner, league: Path, tmp_path: Path) -> None:
    team_league(league, tmp_path)
    result = runner.invoke(list_specials, ["off1", "-"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'league.toml'}: Team is not set. Run 'athc config set "
        "team NAME' or pass --team or a .pln file.\n"
    )


def test_key_path_not_set(runner, league: Path) -> None:
    set_league(league, team="Denver")
    result = runner.invoke(list_specials, ["off1", "-"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {league / 'league.toml'}: League files folder is not set. Run "
        "'athc config set path FOLDER' or pass a .pln file.\n"
    )


def test_folder_named_like_a_key_is_that_folder(
    runner, league: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    team_league(league, tmp_path, team="Denver")
    (tmp_path / "off1").mkdir()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(list_specials, ["off1", "-"])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL off1: {ACCESS_DENIED}\n"


def test_file_named_like_a_key_is_that_file(
    runner, league: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    team_league(league, tmp_path, team="Denver")
    shutil.copy2(GP_DEFENSE, tmp_path / "off1")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(list_specials, ["off1", "-"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == _expected("defense_specials.txt")


@pytest.mark.parametrize("key", ["def2", "off3"], ids=["fourth key", "a fifth"])
def test_four_keys_only(
    runner, league: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    """The four keys are accepted; any other word is a path like any other."""
    team_league(league, tmp_path, team="Denver")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(list_specials, [key, "-"])
    if key == "def2":
        assert result.exit_code == 0
        assert result.stdout.splitlines() == _expected("defense_specials.txt")
    else:
        assert result.exit_code == 2
        assert result.stderr == f"FAIL off3: {FILE_NOT_FOUND}\n"
