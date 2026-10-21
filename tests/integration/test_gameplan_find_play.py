"""Integration tests for `athc gameplan find-play`.

find-play reads nothing from the league for a path, so this file also carries
the team-layer tests the three batch commands share: your team, `--team`,
where the game plans come from and the lines for missing ones.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from click.testing import Result

from athc.cli.gameplan.find_play import (
    find_in_gameplan,
    find_play,
    format_hit_line,
)
from athc.errors import DIRECTORY_INVALID, FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
    read_gameplan,
    write_gameplan,
)
from athc.fbpro98_lge import read_lge
from tests.conftest import (
    LEAGUE,
    OTHER_LEAGUE,
    athc_toml,
    league_not_found,
    no_league_selected,
)
from tests.integration.conftest import DENVER_2049 as DENVER
from tests.integration.conftest import (
    DENVER_PLANS,
    GP_DEFENSE,
    GP_OFFENSE,
    PNFL_LGE,
    TEAM_NAMES,
    BuildLeague,
    build_gameplan,
    defense_special,
    offense_normal,
    offense_special,
    team,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

# Real plays in the fixtures (offense.pln = O_64_06a, defense.pln = D_50_09).
KNOWN_NORMAL = "OR45RL01"
KNOWN_SPECIAL = "SFFGXPAT"
KNOWN_SPECIAL_CATEGORY = "Field Goal/PAT"  # special hits end with the long category
MISSING = "NOSUCHPLAYXX"


# ── constructed-gameplan helpers ──────────────────────────────────────────────


def _set_normal_slots(gp: GamePlan, *placements: tuple[int, CustomPlayRef]) -> GamePlan:
    normals = list(gp.normal_plays)
    for index, play in placements:
        normals[index] = play
    return replace(gp, normal_plays=tuple(normals))


def _set_custom_special(gp: GamePlan, category: int, play: CustomPlayRef) -> GamePlan:
    """Place `play` in the custom slot of `category` (1-10)."""
    specials = list(gp.special_plays)
    specials[category - 1] = replace(specials[category - 1], custom=play)
    return replace(gp, special_plays=tuple(specials))


def _write(gp: GamePlan, tmp_path: Path, name: str = "gp.pln") -> Path:
    path = tmp_path / name
    write_gameplan(gp, path)
    return path


# ── find_in_gameplan ──────────────────────────────────────────────────────────


def test_find_no_match_returns_empty() -> None:
    assert find_in_gameplan(build_gameplan(ProfileType.OFFENSE), MISSING) == ([], [])


def test_find_matches_normal_slot() -> None:
    gp = _set_normal_slots(
        build_gameplan(ProfileType.OFFENSE), (0, offense_normal("OR45RL01"))
    )
    normals, specials = find_in_gameplan(gp, "OR45RL01")
    assert specials == []
    assert [(i, p.name) for i, p in normals] == [(0, "OR45RL01")]


def test_find_multiple_in_one_gameplan() -> None:
    """One play in several normal slots of a single gameplan."""
    play = offense_normal("DUPPLAY", user_category=0x09)
    gp = _set_normal_slots(
        build_gameplan(ProfileType.OFFENSE), (0, play), (5, play), (63, play)
    )
    normals, _ = find_in_gameplan(gp, "DUPPLAY")
    assert [i for i, _ in normals] == [0, 5, 63]


def test_find_multiple_different_plays() -> None:
    """Two different plays both present in one gameplan (find is per-play)."""
    gp = _set_normal_slots(
        build_gameplan(ProfileType.OFFENSE),
        (0, offense_normal("PLAYA")),
        (5, offense_normal("PLAYB", user_category=0x09)),
    )
    assert [i for i, _ in find_in_gameplan(gp, "PLAYA")[0]] == [0]
    assert [i for i, _ in find_in_gameplan(gp, "PLAYB")[0]] == [5]


def test_find_case_insensitive() -> None:
    gp = _set_normal_slots(
        build_gameplan(ProfileType.OFFENSE), (7, offense_normal("MixedCase"))
    )
    assert [i for i, _ in find_in_gameplan(gp, "mixedcase")[0]] == [7]
    assert [i for i, _ in find_in_gameplan(gp, "MIXEDCASE")[0]] == [7]


def test_find_matches_custom_special() -> None:
    gp = _set_custom_special(
        build_gameplan(ProfileType.OFFENSE), 3, offense_special("KICK1", 3)
    )
    normals, specials = find_in_gameplan(gp, "KICK1")
    assert normals == []
    assert [(n, p.name) for n, p in specials] == [(3, "KICK1")]


def test_find_skips_stock_special_slots() -> None:
    gp = build_gameplan(ProfileType.OFFENSE)
    stock = StockPlayRef(
        play_name="STOCKFG",
        map_offset=0,
        map_size=128,
        play_category=1,
        special_category=1,
        user_category=0,
    )
    specials = list(gp.special_plays)
    specials[0] = SpecialSlot(stock=stock)  # category 1's stock slot
    gp = replace(gp, special_plays=tuple(specials))
    assert find_in_gameplan(gp, "STOCKFG") == ([], [])


def test_find_skips_clock_slots() -> None:
    gp = build_gameplan(ProfileType.OFFENSE)
    assert find_in_gameplan(gp, "CLOCK11") == ([], [])
    assert find_in_gameplan(gp, "CLOCK12") == ([], [])


# ── format_hit_line ───────────────────────────────────────────────────────────


def test_format_normal_one_slot() -> None:
    """One normal slot: singular `slot`, no category."""
    play = offense_normal("OR45RL01")
    assert format_hit_line(Path("OFF.pln"), "OR45RL01", [(0, play)], []) == (
        "OFF.pln: 'OR45RL01' found in slot 1-1"
    )


def test_format_normal_two_slots() -> None:
    """Two normal slots: plural `slots`, comma-separated."""
    play = offense_normal("DUP")
    assert format_hit_line(Path("OFF.pln"), "DUP", [(0, play), (5, play)], []) == (
        "OFF.pln: 'DUP' found in slots 1-1, 2-2"
    )


def test_format_normal_three_slots() -> None:
    play = offense_normal("DUP")
    assert format_hit_line(
        Path("OFF.pln"), "DUP", [(0, play), (5, play), (63, play)], []
    ) == ("OFF.pln: 'DUP' found in slots 1-1, 2-2, 16-4")


def test_format_offense_special() -> None:
    """Special: `special slot N`, then the long category."""
    play = offense_special("BCFGPAT", 1)
    assert format_hit_line(Path("OFF.pln"), "BCFGPAT", [], [(1, play)]) == (
        "OFF.pln: 'BCFGPAT' found in special slot 1 (Field Goal/PAT)"
    )


def test_format_defense_special() -> None:
    play = defense_special("CINKR", 2)  # Kick Return
    assert format_hit_line(Path("DEF.pln"), "CINKR", [], [(2, play)]) == (
        "DEF.pln: 'CINKR' found in special slot 2 (Kick Return)"
    )


# ── command: arguments ────────────────────────────────────────────────────────


def run(runner, *args: Path | str) -> Result:
    return runner.invoke(find_play, [str(a) for a in args])


def test_cli_bare_is_missing_play(runner) -> None:
    result = run(runner)
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'PLAY...'.\n")


def test_cli_every_argument_is_a_play(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The location is `--path`; no positional is ever a path."""
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    monkeypatch.chdir(tmp_path)
    result = run(runner, KNOWN_NORMAL, KNOWN_SPECIAL, "--path", ".")
    assert result.exit_code == 0
    assert f"off.pln: '{KNOWN_NORMAL}' found in slot 1-1" in result.stdout
    assert f"off.pln: '{KNOWN_SPECIAL}' found in special slot 1" in result.stdout


def test_cli_single_arg_recursive(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = tmp_path / "team_a"
    sub.mkdir()
    shutil.copy2(GP_OFFENSE, sub / "off.pln")
    monkeypatch.chdir(tmp_path)
    result = run(runner, KNOWN_NORMAL, "--path", ".", "-r")
    assert result.exit_code == 0
    assert f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)" in result.stdout


def test_cli_single_arg_empty_directory_exit_1(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty directory is a warning; nothing was found, so exit 1."""
    monkeypatch.chdir(tmp_path)
    result = run(runner, KNOWN_NORMAL, "--path", ".")
    assert result.exit_code == 1
    assert result.stderr == "WARN .: No .pln files.\n"
    assert f"'{KNOWN_NORMAL}': found 0 instance(s) in 0 game plan(s)" in result.stdout


# ── command: single file ──────────────────────────────────────────────────────


def test_cli_single_file_hit(runner) -> None:
    result = run(runner, KNOWN_NORMAL, "--path", GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == f"{GP_OFFENSE}: '{KNOWN_NORMAL}' found in slot 1-1\n"


def test_cli_single_file_miss_exit_1(runner) -> None:
    result = run(runner, MISSING, "--path", GP_OFFENSE)
    assert result.exit_code == 1
    assert result.stdout == f"{GP_OFFENSE}: '{MISSING}' not found\n"


def test_cli_single_file_case_insensitive(runner) -> None:
    result = run(runner, KNOWN_NORMAL.lower(), "--path", GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == (  # hit despite lowercase, echoed as typed
        f"{GP_OFFENSE}: '{KNOWN_NORMAL.lower()}' found in slot 1-1\n"
    )


def test_cli_finds_custom_special(runner) -> None:
    result = run(runner, KNOWN_SPECIAL, "--path", GP_OFFENSE)
    assert result.exit_code == 0
    assert result.stdout == (
        f"{GP_OFFENSE}: '{KNOWN_SPECIAL}' found in special slot 1 "
        f"({KNOWN_SPECIAL_CATEGORY})\n"
    )


def test_cli_multiple_plays_all_hit(runner, tmp_path: Path) -> None:
    """Several plays across a directory: one play is in two slots of one gameplan,
    which also holds a second searched play."""
    gp1 = _set_normal_slots(
        build_gameplan(ProfileType.OFFENSE),
        (0, offense_normal("OR45RL01")),  # slot 1-1
        (6, offense_normal("OR45RL01")),  # slot 2-3 (same play, 2nd slot)
        (5, offense_normal("DUPRM", user_category=0x09)),  # slot 2-2 (2nd play)
    )
    gp2 = _set_normal_slots(
        build_gameplan(ProfileType.OFFENSE), (0, offense_normal("OR45RL01"))
    )
    _write(gp1, tmp_path, "gp1.pln")
    _write(gp2, tmp_path, "gp2.pln")
    result = run(runner, "OR45RL01", "DUPRM", "--path", tmp_path)
    assert result.exit_code == 0
    assert "'OR45RL01' found in slots 1-1, 2-3" in result.stdout  # two slots in gp1
    assert "'DUPRM' found in slot 2-2" in result.stdout  # a 2nd different play in gp1
    assert "'OR45RL01': found 3 instance(s) in 2 game plan(s)" in result.stdout
    assert "'DUPRM': found 1 instance(s) in 1 game plan(s)" in result.stdout


def test_cli_one_play_found_exit_0(runner) -> None:
    # Like grep: any hit is success, even when another play is missing.
    result = run(runner, KNOWN_NORMAL, MISSING, "--path", GP_OFFENSE)
    assert result.exit_code == 0
    assert (
        f"'{KNOWN_NORMAL}'" in result.stdout
        and f"'{MISSING}' not found" in result.stdout
    )


def test_cli_no_play_found_exit_1(runner) -> None:
    result = run(runner, MISSING, "NOSUCHPLAYYY", "--path", GP_OFFENSE)
    assert result.exit_code == 1
    assert f"'{MISSING}' not found" in result.stdout


# ── command: directory / tree / wildcard ──────────────────────────────────────


def test_cli_directory_reports_hits_only(runner, tmp_path: Path) -> None:
    """In a set only hits print, as grep does; the tally carries the count."""
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    shutil.copy2(GP_DEFENSE, tmp_path / "def.pln")
    result = run(runner, KNOWN_SPECIAL, "--path", tmp_path)
    assert result.exit_code == 0
    assert f"off.pln: '{KNOWN_SPECIAL}' found in special slot 1" in result.stdout
    assert "not found" not in result.stdout
    assert f"'{KNOWN_SPECIAL}': found 1 instance(s) in 1 game plan(s)" in result.stdout


def test_cli_directory_with_no_hits_prints_only_the_tally(
    runner, tmp_path: Path
) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    result = run(runner, MISSING, "--path", tmp_path)
    assert result.exit_code == 1
    assert result.stdout == f"\n'{MISSING}': found 0 instance(s) in 0 game plan(s)\n"


def test_cli_verbose_option_is_rejected(runner) -> None:
    """`--verbose` was removed; there is no switch for misses."""
    result = run(runner, KNOWN_NORMAL, "--path", GP_OFFENSE, "--verbose")
    assert result.exit_code == 2
    assert "No such option '--verbose'" in result.stderr


def test_cli_directory_summary_counts_multiple_hits(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off1.pln")
    shutil.copy2(GP_OFFENSE, tmp_path / "off2.pln")
    result = run(runner, KNOWN_NORMAL, "--path", tmp_path)
    assert result.exit_code == 0
    assert f"'{KNOWN_NORMAL}': found 2 instance(s) in 2 game plan(s)" in result.stdout


def test_cli_directory_per_play_summary(runner, tmp_path: Path) -> None:
    shutil.copy2(GP_OFFENSE, tmp_path / "off.pln")
    result = run(runner, KNOWN_NORMAL, KNOWN_SPECIAL, MISSING, "--path", tmp_path)
    assert result.exit_code == 0  # some plays found
    assert f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)" in result.stdout
    assert f"'{MISSING}': found 0 instance(s) in 0 game plan(s)" in result.stdout


def test_cli_recursive_finds_in_subdir(runner, tmp_path: Path) -> None:
    sub = tmp_path / "team_a"
    sub.mkdir()
    shutil.copy2(GP_OFFENSE, sub / "off.pln")
    result = run(runner, KNOWN_NORMAL, "--path", tmp_path, "-r")
    assert result.exit_code == 0
    assert f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)" in result.stdout


def test_cli_wildcard_path_works_like_a_folder(runner, tmp_path: Path) -> None:
    """athc expands the wildcard itself: the matching game plans, then the
    tally, as for a folder."""
    shutil.copy2(GP_OFFENSE, tmp_path / "Off1.pln")
    shutil.copy2(GP_OFFENSE, tmp_path / "Off2.pln")
    shutil.copy2(GP_DEFENSE, tmp_path / "def.pln")
    result = run(runner, KNOWN_NORMAL, "--path", tmp_path / "Off*.pln")
    assert result.exit_code == 0
    assert result.stdout == (
        f"{tmp_path / 'Off1.pln'}: '{KNOWN_NORMAL}' found in slot 1-1\n"
        f"{tmp_path / 'Off2.pln'}: '{KNOWN_NORMAL}' found in slot 1-1\n"
        "\n"
        f"'{KNOWN_NORMAL}': found 2 instance(s) in 2 game plan(s)\n"
    )


# ── command: error paths ──────────────────────────────────────────────────────


def test_cli_missing_path_exit_2(runner, tmp_path: Path) -> None:
    missing = tmp_path / "nope.pln"
    result = run(runner, KNOWN_NORMAL, "--path", missing)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {missing}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""  # a single path that failed: no tally


def test_cli_malformed_pln_exit_2(runner, tmp_path: Path) -> None:
    bad = tmp_path / "broken.pln"
    bad.write_bytes(b"\x00\x01\x02")
    result = run(runner, KNOWN_NORMAL, "--path", bad)
    assert result.exit_code == 2
    assert (
        result.stderr
        == f"FAIL {bad}: File too small to contain PLN header and offsets table.\n"
    )


def test_cli_bug_in_one_file_keeps_the_batch_going(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_dir: Path
) -> None:
    """A bug on one file is reported as unexpected, the other file is still
    searched, and the run exits 2 though the play was found."""
    doomed = tmp_path / "doomed.pln"
    good = tmp_path / "good.pln"
    shutil.copy2(GP_OFFENSE, doomed)
    shutil.copy2(GP_OFFENSE, good)

    def read(path: str) -> GamePlan:
        if Path(path) == doomed:
            raise RuntimeError("kaboom")
        return read_gameplan(path)

    monkeypatch.setattr("athc.cli.gameplan.find_play.read_gameplan", read)
    result = run(runner, KNOWN_NORMAL, "--path", tmp_path)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {doomed}: Unexpected error. See {log_dir / 'athc.log'} for details.\n"
    )
    assert result.stdout == (
        f"{good}: '{KNOWN_NORMAL}' found in slot 1-1\n"
        "\n"
        f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)\n"
    )


# ── --league: resolved when given, read only when needed ─────────────────────


def test_league_with_a_path_reads_nothing_from_it(
    runner, make_league: MakeLeague
) -> None:
    """The league must exist; with a path nothing in it is read, so a broken
    league.toml does not matter."""
    make_league(OTHER_LEAGUE, "[league\n")
    result = run(runner, KNOWN_NORMAL, "--path", GP_OFFENSE, "--league", OTHER_LEAGUE)
    assert result.exit_code == 0
    assert result.stdout == f"{GP_OFFENSE}: '{KNOWN_NORMAL}' found in slot 1-1\n"


def test_league_that_does_not_exist_fails_even_with_a_path(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()
    result = run(runner, KNOWN_NORMAL, "--path", GP_OFFENSE, "--league", "NOPE")
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)
    assert result.stdout == ""


def test_path_without_any_settings(runner, config_dir: Path) -> None:
    """No athc.toml, no league folder: a path needs neither."""
    assert not (config_dir / "athc.toml").exists()
    result = run(runner, KNOWN_NORMAL, "--path", GP_OFFENSE)
    assert result.exit_code == 0


def test_default_scope_needs_a_league(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert result.stdout == ""


# ── your team's game plans: PNFL.lg2 and its 2049 plans ──────────────────────

# Denver's game plans (DENVER_PLANS, in conftest.py) as a line lists them.
DENVER_NAMES = ", ".join(DENVER_PLANS)
# OR45RL01 is at 1-1 in Denver's (and Las Vegas's) offense game plans only; the
# defense game plans print nothing.
DENVER_OR45RL01 = ["found in slot 1-1", "found in slot 1-1"]
# Denver's offense game plans; DENVER_PLANS is in .lg2 order: off1, def1, off2, def2.
DENVER_OFFENSE = [DENVER_PLANS[0], DENVER_PLANS[2]]
# One game plan searched alone also says when OR45RL01 is not in it.
DENVER_OR45RL01_ONE_FILE = [
    "found in slot 1-1",
    "not found",
    "found in slot 1-1",
    "not found",
]
TEAM_NOT_SET = "Team is not set. Run 'athc config set team NAME' or pass --team or"
PATH_NOT_SET = (
    "League files folder is not set. Run 'athc config set path FOLDER' or pass"
)
LOCATION_HINT = "Run 'athc config set ppp_path FOLDER' or pass"


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


def at_league(tmp_path: Path, team_folder: str) -> Path:
    """A team's league location in `pnfl_league`: where PNFL.lg2 puts its files."""
    return tmp_path / "lg2" / "PNFL" / "2049" / "Plans" / team_folder


def report(folder: Path, names: Sequence[str], outcomes: list[str]) -> str:
    """find-play's hit line per game plan named: a set prints hits only."""
    return "".join(
        f"{folder / name}: '{KNOWN_NORMAL}' {outcome}\n"
        for name, outcome in zip(names, outcomes, strict=True)
    )


def lge_names() -> str:
    """Every team of PNFL.lge by both names, as the no-match lines list them."""
    teams = read_lge("PNFL", PNFL_LGE.parent).teams
    return ", ".join(t.official_name for t in teams)


@pytest.fixture
def denver(pnfl_league: Path) -> Path:
    """The PNFL league files and plans, with `team` set to Denver."""
    set_league(pnfl_league, team="Denver")
    return pnfl_league


def test_default_scope_is_your_teams_game_plans(
    runner, denver: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --path: your team's four are searched and their hits listed in .lg2
    order, then the tally; the current folder is not searched (that is
    --path .)."""
    here = tmp_path / "here"
    here.mkdir()
    shutil.copy2(GP_OFFENSE, here / "off.pln")
    monkeypatch.chdir(here)
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 0
    folder = at_league(tmp_path, "Denver (Brian)")
    assert result.stdout == (
        report(folder, DENVER_OFFENSE, DENVER_OR45RL01)
        + "\n"
        + f"'{KNOWN_NORMAL}': found 2 instance(s) in 2 game plan(s)\n"
    )


def test_default_scope_from_ppp_path(runner, pnfl_league: Path, tmp_path: Path) -> None:
    mine = shutil.copytree(DENVER, tmp_path / "mine")
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 0
    assert result.stdout.startswith(report(mine, DENVER_OFFENSE, DENVER_OR45RL01))
    assert result.stderr == ""


def test_ppp_path_names_ignore_case(runner, pnfl_league: Path, tmp_path: Path) -> None:
    """Found by their .lg2 names without case; shown as the folder spells them."""
    mine = tmp_path / "mine"
    mine.mkdir()
    for name in DENVER_PLANS:
        shutil.copy2(DENVER / name, mine / name.lower())
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL)
    lower = [name.lower() for name in DENVER_PLANS]
    offense = [lower[0], lower[2]]
    assert result.stdout.startswith(report(mine, offense, DENVER_OR45RL01))


def test_relative_ppp_path_is_in_the_league_folder(runner, pnfl_league: Path) -> None:
    mine = shutil.copytree(DENVER, pnfl_league / "mine")
    set_league(pnfl_league, team="Denver", ppp_path="mine")
    result = run(runner, KNOWN_NORMAL)
    assert result.stdout.startswith(report(mine, DENVER_OFFENSE, DENVER_OR45RL01))


@pytest.mark.parametrize("exists", [False, True], ids=["missing", "a file"])
def test_ppp_path_not_a_folder(
    runner, pnfl_league: Path, tmp_path: Path, exists: bool
) -> None:
    ppp_path = tmp_path / "mine"
    if exists:
        ppp_path.write_text("x", encoding="utf-8")
    set_league(pnfl_league, team="Denver", ppp_path=ppp_path)
    result = run(runner, KNOWN_NORMAL)
    reason = DIRECTORY_INVALID if exists else PATH_NOT_FOUND
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {ppp_path}: {reason} Run 'athc config set ppp_path FOLDER'.\n"
    )
    assert result.stdout == ""


def test_shared_game_plan_once(runner, pnfl_league: Path, tmp_path: Path) -> None:
    """Las Vegas uses one game plan per side for both halves: two files, each
    searched once; the offense one holds the play, the defense one prints
    nothing."""
    result = run(runner, KNOWN_NORMAL, "--team", "Las Vegas")
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    assert result.exit_code == 0
    assert result.stdout == (
        report(folder, ["RAIDEROFF.pln"], DENVER_OR45RL01[:1])
        + "\n"
        + f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)\n"
    )


# ── the four game plan keys ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("key", "index"),
    [("off1", 0), ("def1", 1), ("off2", 2), ("def2", 3), ("OFF1", 0), ("Def2", 3)],
)
def test_key_is_one_game_plan(
    runner, denver: Path, tmp_path: Path, key: str, index: int
) -> None:
    """Each key is its .lg2 entry, any case: one file, no tally."""
    result = run(runner, KNOWN_NORMAL, "--path", key)
    folder = at_league(tmp_path, "Denver (Brian)")
    assert result.stdout == report(
        folder, [DENVER_PLANS[index]], [DENVER_OR45RL01_ONE_FILE[index]]
    )


def test_two_keys_one_shared_game_plan(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    """off1 and off2 name Las Vegas's one offense game plan."""
    first = run(runner, KNOWN_NORMAL, "--path", "off1", "--team", "Las Vegas")
    second = run(runner, KNOWN_NORMAL, "--path", "off2", "--team", "Las Vegas")
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    assert (
        first.stdout
        == second.stdout
        == report(folder, ["RAIDEROFF.pln"], DENVER_OR45RL01[:1])
    )


@pytest.mark.parametrize("key", ["def2", "off3"], ids=["fourth key", "a fifth"])
def test_four_keys_only(
    runner, denver: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, key: str
) -> None:
    """The four keys are accepted; any other word is a path like any other."""
    monkeypatch.chdir(tmp_path)
    result = run(runner, KNOWN_NORMAL, "--path", key)
    if key == "def2":
        assert result.exit_code == 1
        assert result.stdout.endswith(f"DEN-DGP2.pln: '{KNOWN_NORMAL}' not found\n")
    else:
        assert result.exit_code == 2
        assert result.stderr == f"FAIL off3: {FILE_NOT_FOUND}\n"


def test_folder_named_like_a_key_is_searched(
    runner, denver: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "off1").mkdir()
    shutil.copy2(GP_OFFENSE, tmp_path / "off1" / "draft.pln")
    monkeypatch.chdir(tmp_path)
    result = run(runner, KNOWN_NORMAL, "--path", "off1")
    assert result.exit_code == 0
    assert result.stdout.startswith(
        f"{Path('off1') / 'draft.pln'}: '{KNOWN_NORMAL}' found in slot 1-1\n"
    )
    assert "game plan(s)" in result.stdout  # a folder: the tally


def test_file_named_like_a_key_is_that_file(
    runner, denver: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "off1").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = run(runner, KNOWN_NORMAL, "--path", "off1")
    assert result.exit_code == 2
    assert result.stderr == "FAIL off1: Not a .pln file.\n"


# ── the team: `team` and --team ───────────────────────────────────────────────


@pytest.mark.parametrize("source", ["team", "--team"])
@pytest.mark.parametrize(
    "name", ["Denver", "Broncos", "Denver Broncos", "dENVER bRONCOS"]
)
def test_team_by_name_nickname_or_both(
    runner, pnfl_league: Path, tmp_path: Path, source: str, name: str
) -> None:
    if source == "team":
        set_league(pnfl_league, team=name)
        result = run(runner, KNOWN_NORMAL)
    else:
        result = run(runner, KNOWN_NORMAL, "--team", name)
    folder = at_league(tmp_path, "Denver (Brian)")
    assert result.stdout.startswith(report(folder, DENVER_OFFENSE, DENVER_OR45RL01))


def test_team_matches_no_team(runner, pnfl_league: Path) -> None:
    set_league(pnfl_league, team="Denvr")
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {pnfl_league / 'league.toml'}: [league] team: No team named "
        f"'Denvr'. Teams: {lge_names()}.\n"
    )
    assert result.stdout == ""


def test_team_option_matches_no_team(runner, pnfl_league: Path) -> None:
    result = run(runner, KNOWN_NORMAL, "--team", "Denvr")
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: Invalid value for '--team': no team named 'Denvr'. Teams: "
        f"{lge_names()}.\n"
    )
    assert result.stdout == ""


NEW_YORK = [("New York", "Giants"), ("New York", "Jets")]


def test_team_matches_two_teams(runner, lg2_league, config_dir: Path) -> None:
    lg2_league(team(), team(), names=NEW_YORK, team="New York")
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {config_dir / 'leagues' / LEAGUE / 'league.toml'}: [league] team: "
        "'New York' matches New York Giants and New York Jets. Use the nickname, "
        "or both names in quotes.\n"
    )


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("Giants", None),
        ("Raiders", "no team named 'Raiders'. Teams: New York Giants, New York Jets."),
        (
            "New York",
            "'New York' matches New York Giants and New York Jets. Use the "
            "nickname, or both names in quotes.",
        ),
    ],
    ids=["one", "none", "two"],
)
def test_team_option_match_count(
    runner, lg2_league, name: str, error: str | None
) -> None:
    """Exactly one team must match: one is accepted, none or two rejected."""
    lg2 = lg2_league(team(), team(), names=NEW_YORK)
    result = run(runner, KNOWN_NORMAL, "--team", name)
    assert result.exit_code == 2
    if error is None:  # accepted: on to its game plans, none of them there
        folder = lg2.parent / "PNFL" / "2049" / "Plans" / "Team"
        assert result.stderr == f"FAIL {folder}: {PATH_NOT_FOUND}\n"
    else:
        assert result.stderr.endswith(f"Error: Invalid value for '--team': {error}\n")


def test_team_blank_is_not_set(runner, lg2_league, config_dir: Path) -> None:
    lg2_league(team(), team="  ")
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    toml = config_dir / "leagues" / LEAGUE / "league.toml"
    assert result.stderr == f"FAIL {toml}: {TEAM_NOT_SET} --path.\n"


def test_team_array(runner, pnfl_league: Path) -> None:
    toml = pnfl_league / "league.toml"
    text = toml.read_text(encoding="utf-8")
    toml.write_text(
        text.replace("[league]\n", "[league]\nteam = ['Denver']\n"), "utf-8"
    )
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {toml}: [league] team: Expected a string, got an array.\n"
    )


def test_team_option_beats_team(runner, denver: Path, tmp_path: Path) -> None:
    result = run(runner, KNOWN_NORMAL, "--team", "Las Vegas")
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    assert result.stdout.startswith(f"{folder / 'RAIDEROFF.pln'}: ")


@pytest.mark.parametrize(
    ("name", "from_ppp_path"),
    [("Broncos", True), ("Las Vegas", False)],
    ids=["your team", "another team"],
)
def test_ppp_path_is_for_your_team(
    runner, pnfl_league: Path, tmp_path: Path, name: str, from_ppp_path: bool
) -> None:
    mine = shutil.copytree(DENVER, tmp_path / "mine")
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL, "--team", name)
    first = result.stdout.splitlines()[0]
    if from_ppp_path:
        assert first.startswith(f"{mine / 'DEN-OGP1.pln'}: ")
    else:
        assert first.startswith(f"{at_league(tmp_path, 'Las Vegas (Neil)')}")


@pytest.mark.parametrize("setting", [None, "Denvr"], ids=["unset", "no match"])
def test_team_option_without_your_team(
    runner, pnfl_league: Path, tmp_path: Path, setting: str | None
) -> None:
    """`team` unset or naming no team: --team still works, at the league
    locations, even with `ppp_path` set."""
    mine = shutil.copytree(DENVER, tmp_path / "mine")
    set_league(pnfl_league, ppp_path=mine)
    if setting is not None:
        set_league(pnfl_league, team=setting)
    result = run(runner, KNOWN_NORMAL, "--team", "Denver")
    assert result.exit_code == 0
    folder = at_league(tmp_path, "Denver (Brian)")
    assert result.stdout.startswith(report(folder, DENVER_OFFENSE, DENVER_OR45RL01))


@pytest.mark.parametrize(
    ("args", "way"),
    [((), "--path"), (("--path", "off1"), "a .pln file")],
    ids=["default scope", "a key"],
)
def test_team_not_set(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    args: tuple[str, ...],
    way: str,
) -> None:
    """Neither `team` nor --team. `team` is read before `path`, which is not
    set either."""
    folder = build_league()
    write_config(athc_toml())
    result = run(runner, KNOWN_NORMAL, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'league.toml'}: {TEAM_NOT_SET} {way}.\n"


@pytest.mark.parametrize(
    ("args", "way"),
    [((), "--path."), (("--path", "off1"), "a .pln file.")],
    ids=["default scope", "a key"],
)
def test_path_not_set(
    runner,
    build_league: BuildLeague,
    write_config: WriteConfig,
    args: tuple[str, ...],
    way: str,
) -> None:
    folder = build_league(team="Denver")
    write_config(athc_toml())
    result = run(runner, KNOWN_NORMAL, *args)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'league.toml'}: {PATH_NOT_SET} {way}\n"


@pytest.mark.parametrize(
    "path", [GP_OFFENSE, ".", "*.pln"], ids=["a file", "a folder", "a wildcard"]
)
def test_team_with_a_path_is_a_usage_error(
    runner, denver: Path, path: Path | str
) -> None:
    result = run(runner, KNOWN_NORMAL, "--path", path, "--team", "Denver")
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team requires --path to be a game plan key (off1, def1, off2 or "
        "def2) or left out.\n"
    )
    assert result.stdout == ""


# ── league files: the .lg2 and the .lge ───────────────────────────────────────


def test_lge_missing(runner, lg2_league) -> None:
    lg2 = lg2_league(team(), team="Denver")
    lg2.with_suffix(".lge").unlink()
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2.with_suffix('.lge')}: {FILE_NOT_FOUND}\n"
    assert result.stdout == ""


def test_lg2_missing(runner, lg2_league) -> None:
    lg2 = lg2_league(team(), team="Denver")
    lg2.unlink()
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2}: {FILE_NOT_FOUND}\n"


def test_stock_league(runner, lg2_league) -> None:
    lg2 = lg2_league(team(folder=""), team="Denver")
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {lg2}: Stock league not supported.\n"


@pytest.mark.parametrize(
    ("lg2_teams", "line"),
    [
        (2, None),
        (1, f"Lists 1 team(s), but {LEAGUE}.lge has 2."),
        (3, f"Lists 3 team(s), but {LEAGUE}.lge has 2."),
    ],
    ids=["equal", "one fewer", "one more"],
)
def test_league_team_counts(
    runner, lg2_league, lg2_teams: int, line: str | None
) -> None:
    """The two league files must list the same teams."""
    lg2 = lg2_league(*(team() for _ in range(lg2_teams)), names=TEAM_NAMES[:2])
    result = run(runner, KNOWN_NORMAL, "--team", "Denver")
    assert result.exit_code == 2
    if line is None:  # accepted: on to Denver's game plans, none of them there
        assert "No Denver game plans" not in result.stderr
        assert PATH_NOT_FOUND in result.stderr
    else:
        assert result.stderr == f"FAIL {lg2}: {line}\n"


# ── missing game plans: at the league locations ───────────────────────────────


def test_league_one_game_plan_missing(runner, denver: Path, tmp_path: Path) -> None:
    """A FAIL, counted as failed; the others are searched."""
    folder = at_league(tmp_path, "Denver (Brian)")
    (folder / "DEN-OGP2.pln").unlink()
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'DEN-OGP2.pln'}: {FILE_NOT_FOUND}\n"
    # Of the three searched, only DEN-OGP1.pln holds the play.
    assert result.stdout == (
        report(folder, DENVER_PLANS[:1], DENVER_OR45RL01[:1])
        + "\n"
        + f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)\n"
    )


def test_league_recursive_is_ignored(runner, denver: Path) -> None:
    assert run(runner, KNOWN_NORMAL, "-r").stdout == run(runner, KNOWN_NORMAL).stdout


TEAM_FOLDER = ("PNFL", "2049", "Plans", "Team")  # where team() puts every file


def plans_team() -> bytes:
    """A team record whose four game plans are named after their keys."""
    return team(
        ("o1.prf", "OFF1.pln"),
        ("d1.prf", "DEF1.pln"),
        ("o2.prf", "OFF2.pln"),
        ("d2.prf", "DEF2.pln"),
    )


@pytest.mark.parametrize("present", [False, True], ids=["absent", "empty"])
def test_league_no_game_plans_for_your_team(runner, lg2_league, present: bool) -> None:
    """One line for the folder, with the `ppp_path` hint, one failed item."""
    lg2 = lg2_league(plans_team(), team="Denver")
    folder = lg2.parent.joinpath(*TEAM_FOLDER)
    if present:
        folder.mkdir(parents=True)
    reason = "No Denver game plans." if present else PATH_NOT_FOUND
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder}: {reason} {LOCATION_HINT} --path.\n"
    assert (
        result.stdout == f"\n'{KNOWN_NORMAL}': found 0 instance(s) in 0 game plan(s)\n"
    )


@pytest.mark.parametrize("present", [False, True], ids=["absent", "empty"])
def test_league_no_game_plans_for_another_team(
    runner, lg2_league, present: bool
) -> None:
    """--team naming another team: the same line, no hint."""
    lg2 = lg2_league(plans_team(), plans_team(), team="Denver")
    folder = lg2.parent.joinpath(*TEAM_FOLDER)
    if present:
        folder.mkdir(parents=True)
    reason = "No Las Vegas game plans." if present else PATH_NOT_FOUND
    result = run(runner, KNOWN_NORMAL, "--team", "Las Vegas")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder}: {reason}\n"


@pytest.mark.parametrize("count", [0, 1], ids=["none", "one"])
def test_league_no_game_plans_limit(runner, lg2_league, count: int) -> None:
    """None there gives the one folder line; one there gives none, only a
    FAIL for each missing game plan."""
    lg2 = lg2_league(plans_team(), team="Denver")
    folder = lg2.parent.joinpath(*TEAM_FOLDER)
    folder.mkdir(parents=True)
    if count:
        shutil.copy2(GP_OFFENSE, folder / "OFF1.pln")
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 2
    if count:
        assert result.stderr == "".join(
            f"FAIL {folder / name}: {FILE_NOT_FOUND}\n"
            for name in ("DEF1.pln", "OFF2.pln", "DEF2.pln")
        )
        assert result.stdout.startswith(f"{folder / 'OFF1.pln'}: ")
    else:
        assert result.stderr == (
            f"FAIL {folder}: No Denver game plans. {LOCATION_HINT} --path.\n"
        )


# ── missing game plans: in ppp_path ───────────────────────────────────────────


def test_ppp_path_one_game_plan_missing(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    """A WARN; the code is what the game plans found give."""
    mine = shutil.copytree(DENVER, tmp_path / "mine")
    (mine / "DEN-OGP2.pln").unlink()
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 0
    assert result.stderr == f"WARN {mine / 'DEN-OGP2.pln'}: {FILE_NOT_FOUND}\n"
    assert f"'{KNOWN_NORMAL}': found 1 instance(s) in 1 game plan(s)" in result.stdout


@pytest.mark.parametrize("count", [0, 1], ids=["none", "one"])
def test_ppp_path_no_game_plans_limit(
    runner, pnfl_league: Path, tmp_path: Path, count: int
) -> None:
    """None there gives the one scope line (exit 1, nothing found); one there
    gives a WARN for each missing game plan instead."""
    mine = tmp_path / "mine"
    mine.mkdir()
    if count:
        shutil.copy2(DENVER / "DEN-OGP1.pln", mine)
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL)
    if count:
        assert result.exit_code == 0
        assert result.stderr == "".join(
            f"WARN {mine / name}: {FILE_NOT_FOUND}\n" for name in DENVER_PLANS[1:]
        )
    else:
        assert result.exit_code == 1
        assert result.stderr == (
            f"WARN {mine}: No Denver game plans. The league file names "
            f"{DENVER_NAMES}.\n"
        )
        assert result.stdout == (
            f"\n'{KNOWN_NORMAL}': found 0 instance(s) in 0 game plan(s)\n"
        )


def test_ppp_path_no_game_plans_names_each_once(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    """Las Vegas's shared game plans are named once each."""
    mine = tmp_path / "mine"
    mine.mkdir()
    set_league(pnfl_league, team="Las Vegas", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL)
    assert result.stderr == (
        f"WARN {mine}: No Las Vegas game plans. The league file names "
        "RAIDEROFF.pln, RAIDERDEF.pln.\n"
    )


def test_ppp_path_tree(runner, pnfl_league: Path, tmp_path: Path) -> None:
    """With -r each folder of the tree stands alone: a folder with some of the
    four warns about the rest, a folder with none says nothing."""
    mine = tmp_path / "mine"
    week1 = shutil.copytree(DENVER, mine / "week1")
    (mine / "week2").mkdir()
    shutil.copy2(DENVER / "DEN-OGP1.pln", mine / "week2")
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL, "-r")
    assert result.exit_code == 0
    assert result.stdout == (
        report(week1, DENVER_OFFENSE, DENVER_OR45RL01)
        + report(mine / "week2", DENVER_PLANS[:1], DENVER_OR45RL01[:1])
        + "\n"
        + f"'{KNOWN_NORMAL}': found 3 instance(s) in 3 game plan(s)\n"
    )
    assert result.stderr == "".join(
        f"WARN {mine / 'week2' / name}: {FILE_NOT_FOUND}\n" for name in DENVER_PLANS[1:]
    )


def test_ppp_path_tree_with_no_game_plans(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    """The scope line once, for the whole tree."""
    mine = tmp_path / "mine"
    (mine / "week1").mkdir(parents=True)
    (mine / "week2").mkdir()
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL, "-r")
    assert result.exit_code == 1
    assert result.stderr == (
        f"WARN {mine}: No Denver game plans. The league file names {DENVER_NAMES}.\n"
    )


def test_ppp_path_without_recursive_skips_subfolders(
    runner, pnfl_league: Path, tmp_path: Path
) -> None:
    mine = tmp_path / "mine"
    shutil.copytree(DENVER, mine / "week1")
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL)
    assert result.exit_code == 1
    assert result.stderr.startswith(f"WARN {mine}: No Denver game plans.")


# ── missing game plans: a key ─────────────────────────────────────────────────


def test_key_missing_at_your_league_location(
    runner, denver: Path, tmp_path: Path
) -> None:
    folder = at_league(tmp_path, "Denver (Brian)")
    (folder / "DEN-OGP1.pln").unlink()
    result = run(runner, KNOWN_NORMAL, "--path", "off1")
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'DEN-OGP1.pln'}: {FILE_NOT_FOUND} {LOCATION_HINT} "
        "a .pln file.\n"
    )
    assert result.stdout == ""  # one file: no tally


def test_key_missing_for_another_team(runner, denver: Path, tmp_path: Path) -> None:
    folder = at_league(tmp_path, "Las Vegas (Neil)")
    (folder / "RAIDEROFF.pln").unlink()
    result = run(runner, KNOWN_NORMAL, "--path", "off1", "--team", "Las Vegas")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'RAIDEROFF.pln'}: {FILE_NOT_FOUND}\n"


def test_key_missing_in_ppp_path(runner, pnfl_league: Path, tmp_path: Path) -> None:
    mine = tmp_path / "mine"
    mine.mkdir()
    set_league(pnfl_league, team="Denver", ppp_path=mine)
    result = run(runner, KNOWN_NORMAL, "--path", "off1")
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {mine / 'DEN-OGP1.pln'}: {FILE_NOT_FOUND}\n"
