"""Integration tests for `athc gameplan set-specials`."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.set_specials import set_specials
from athc.errors import FILE_NOT_FOUND, PATH_NOT_FOUND
from athc.fbpro98_gameplan import PlayRef, read_gameplan, write_gameplan
from tests.conftest import LEAGUE, league_toml
from tests.integration.conftest import (
    GP_DEFENSE,
    GP_OFFENSE,
    PLAYS,
    TEAM_NAMES,
    lge,
    team,
)

SPECIAL = "LIONKICK"  # offense Kickoff, special_category 2 -> custom slot index 1
NORMAL = "OR45RL01"  # a normal offense play (not special teams)
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


def _copy(tmp_path: Path, name: str = "offense.pln", src: Path = GP_OFFENSE) -> Path:
    dst = tmp_path / name
    shutil.copy2(src, dst)
    return dst


def _without_special(path: Path, category: int = 2) -> Path:
    """`path` rewritten with special category `category`'s custom slot empty."""
    gp = read_gameplan(path)
    kept = [
        c
        for c in gp.custom_special_plays
        if c is not None and c.special_category != category
    ]
    write_gameplan(gp.with_custom_special_plays(kept), path)
    assert read_gameplan(path).custom_special_plays[category - 1] is None
    return path


def _input(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "spec.txt"
    p.write_text(text, encoding="utf-8")
    return p


def _plans(tmp_path: Path) -> Path:
    """A folder for bulk runs, apart from the input file and the config dir."""
    folder = tmp_path / "plans"
    folder.mkdir()
    return folder


# ── usage ─────────────────────────────────────────────────────────────────────


def test_requires_input_file(runner) -> None:
    result = runner.invoke(set_specials, [])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'INPUT_FILE'.\n")


def test_play_list_not_text(runner, tmp_path: Path) -> None:
    """A game plan given as the list, its only argument: one FAIL line naming
    the list, the game plan untouched."""
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(set_specials, [str(p)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {p}: Not a valid play list.\n"
    assert p.read_bytes() == original


def test_extra_argument_rejected(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_specials, [str(inp), "extra"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (extra).\n")


def test_no_quiet_option(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, ["--path", str(p), str(_input(tmp_path, SPECIAL + "\n")), "-q"]
    )
    assert result.exit_code == 2


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
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(set_specials, ["--path", str(p), str(inp), *extra])
    assert result.exit_code == 2
    assert "No such option" in result.stderr


# ── single file ───────────────────────────────────────────────────────────────


def test_writes_special_from_file(runner, tmp_path: Path) -> None:
    p = _without_special(_copy(tmp_path))
    result = runner.invoke(
        set_specials, ["--path", str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    placed = read_gameplan(str(p)).custom_special_plays[1]
    assert placed is not None and placed.name == SPECIAL


def test_a_list_saved_with_a_bom_reads_its_first_play(runner, tmp_path: Path) -> None:
    """Notepad's "UTF-8 with BOM" puts a mark before the first play name."""
    p = _without_special(_copy(tmp_path))
    inp = tmp_path / "spec.txt"
    inp.write_text(SPECIAL + "\n", encoding="utf-8-sig")
    result = runner.invoke(set_specials, ["--path", str(p), str(inp)])
    assert result.exit_code == 0
    placed = read_gameplan(str(p)).custom_special_plays[1]
    assert placed is not None and placed.name == SPECIAL


def test_merge_preserves_other_categories(runner, tmp_path: Path) -> None:
    p = _without_special(_copy(tmp_path))
    before = read_gameplan(str(p)).custom_special_plays
    result = runner.invoke(
        set_specials, ["--path", str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    after = read_gameplan(str(p)).custom_special_plays
    assert after[1] is not None and after[1].name == SPECIAL
    for i in range(len(after)):
        if i == 1:
            continue
        assert (after[i] is None) == (before[i] is None)
        if before[i] is not None:
            assert _name(after[i]) == _name(before[i])


def test_writes_no_backup(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, ["--path", str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    assert list(tmp_path.glob("*.bak")) == []
    assert "; backup " not in result.stdout  # the old "(N special play(s); backup X)"


def test_skips_and_strips_comments(runner, tmp_path: Path) -> None:
    p = _without_special(_copy(tmp_path))
    inp = _input(tmp_path, f":: header\n{SPECIAL} :: kickoff\n")
    result = runner.invoke(set_specials, ["--path", str(p), str(inp)])
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).custom_special_plays[1]) == SPECIAL


def test_dash_reads_from_console(runner, tmp_path: Path) -> None:
    p = _without_special(_copy(tmp_path))
    result = runner.invoke(set_specials, ["--path", str(p), "-"], input=SPECIAL + "\n")
    assert result.exit_code == 0
    assert _name(read_gameplan(str(p)).custom_special_plays[1]) == SPECIAL


def test_dash_input_errors_name_no_file(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_specials, ["--path", str(p), "-"], input=NORMAL + "\n")
    assert result.exit_code == 2
    assert (
        f"FAIL line 1: '{NORMAL}' is not a special-teams play. Run 'athc gameplan set-normals'.\n"
        in result.stderr
    )
    assert "FAIL - " not in result.stderr


def test_gameplan_problem_names_the_gameplan_and_the_list_line(
    runner, tmp_path: Path
) -> None:
    """A play the pool lacks fails per gameplan; the list line comes last, so
    it never reads as a line of the .pln."""
    p = _copy(tmp_path)
    inp = _input(tmp_path, ":: header\n\nNOPEPLAY\n")
    result = runner.invoke(set_specials, ["--path", str(p), str(inp)])
    assert result.exit_code == 2
    assert (
        f"FAIL {p}: 'NOPEPLAY' is not in the play pool ({inp} line 3).\n"
        in result.stderr
    )


def test_gameplan_problem_from_the_console(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    result = runner.invoke(set_specials, ["--path", str(p), "-"], input="NOPEPLAY\n")
    assert result.exit_code == 2
    assert (
        f"FAIL {p}: 'NOPEPLAY' is not in the play pool (play list line 1).\n"
        in result.stderr
    )


# ── validation (no file written) ──────────────────────────────────────────────


def test_rejects_normal_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    original = p.read_bytes()
    result = runner.invoke(
        set_specials, ["--path", str(p), str(_input(tmp_path, NORMAL + "\n"))]
    )
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1].startswith("FAIL ")  # after the WARN lines
    assert (
        "not a special-teams play" in result.stderr
        and "athc gameplan set-normals" in result.stderr
    )
    assert p.read_bytes() == original


def test_rejects_duplicate_play(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, f"{SPECIAL}\n\n{SPECIAL}\n")
    result = runner.invoke(set_specials, ["--path", str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr.splitlines()[-1] == (
        f"FAIL {inp}: line 3: Duplicate play '{SPECIAL}' (already on line 1)."
    )


def test_as_many_plays_as_slots_pass_the_count(runner, tmp_path: Path) -> None:
    """Ten plays are within the limit: the run gets past the count check (here
    to the duplicate check, since the pool has one play to repeat)."""
    p = _copy(tmp_path)
    inp = _input(tmp_path, (SPECIAL + "\n") * 10)
    result = runner.invoke(set_specials, ["--path", str(p), str(inp)])
    assert "Too many plays" not in result.stderr
    assert result.stderr.splitlines()[-1].startswith(f"FAIL {inp}: line 10: Duplicate")


def test_too_many_plays_rejected(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, (SPECIAL + "\n") * 11)
    result = runner.invoke(set_specials, ["--path", str(p), str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {inp}: Too many plays (11). The most is 10.\n"


def test_missing_target(runner, tmp_path: Path) -> None:
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(
        set_specials, ["--path", str(tmp_path / "nope.pln"), str(inp)]
    )
    assert result.exit_code == 2


def test_missing_play_list(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    result = runner.invoke(
        set_specials, ["--path", str(plans), str(tmp_path / "nope.txt")]
    )
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {tmp_path / 'nope.txt'}: {FILE_NOT_FOUND}\n"


def test_invalid_play_path(runner, league: Path, tmp_path: Path) -> None:
    (league / "league.toml").write_text(
        league_toml(tmp_path / "missing"), encoding="utf-8"
    )
    p = _copy(tmp_path)
    result = runner.invoke(
        set_specials, ["--path", str(p), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {tmp_path / 'missing'}: {PATH_NOT_FOUND} "
        "Run 'athc config set play_path FOLDER'.\n"
    )


# ── bulk: directory / tree / side-skip / per-file failure ─────────────────────


def test_directory_top_level_only(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    _copy(plans, "a.pln")
    _copy(plans, "b.pln")
    sub = plans / "sub"
    sub.mkdir()
    deep = _copy(sub, "deep.pln")
    deep_pre = deep.read_bytes()
    result = runner.invoke(
        set_specials, ["--path", str(plans), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.stdout and "2 updated" in result.stdout
    assert deep.read_bytes() == deep_pre


def test_directory_recursive(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    _copy(plans, "top.pln")
    sub = plans / "sub"
    sub.mkdir()
    _copy(sub, "deep.pln")
    result = runner.invoke(
        set_specials,
        ["--path", str(plans), str(_input(tmp_path, SPECIAL + "\n")), "-r"],
    )
    assert result.exit_code == 0
    assert "2 file(s) processed" in result.stdout


def test_offense_input_skips_defense_files(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    _copy(plans, "off.pln")
    deff = _copy(plans, "def.pln", src=GP_DEFENSE)
    def_pre = deff.read_bytes()
    result = runner.invoke(
        set_specials, ["--path", str(plans), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 0
    assert f"SKIP {deff}: defense game plan" in result.stdout
    assert "2 file(s) processed, 1 updated, 1 skipped, 0 failed" in result.stdout
    assert deff.read_bytes() == def_pre


def test_continues_past_failed_file(runner, tmp_path: Path) -> None:
    plans = _plans(tmp_path)
    good = _copy(plans, "good.pln")
    bad = plans / "bad.pln"
    bad.write_bytes(b"\x00" * 2636)  # even size so it isn't side-skipped, but malformed
    result = runner.invoke(
        set_specials, ["--path", str(plans), str(_input(tmp_path, SPECIAL + "\n"))]
    )
    assert result.exit_code == 2
    assert f"OK   {good}: updated" in result.stdout
    assert f"FAIL {bad}: Invalid header" in result.stderr
    assert result.stderr.count(str(bad)) == 1
    assert "2 file(s) processed, 1 updated, 0 skipped, 1 failed" in result.stdout


def test_wildcard_path(runner, tmp_path: Path) -> None:
    """athc expands the wildcard itself: the matching game plans only."""
    plans = _plans(tmp_path)
    off = _copy(plans, "Off1.pln")
    other = _copy(plans, "other.pln")
    other_pre = other.read_bytes()
    result = runner.invoke(
        set_specials,
        ["--path", str(plans / "Off*.pln"), str(_input(tmp_path, SPECIAL + "\n"))],
    )
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {off}: updated (6 special play(s))\n"
        "\n"
        "1 file(s) processed, 1 updated, 0 skipped, 0 failed\n"
    )
    assert other.read_bytes() == other_pre


def test_too_many_plays_fail_before_the_league(
    runner, write_config: WriteConfig, tmp_path: Path
) -> None:
    """The list is read and counted before any league read: here no league is
    selected at all."""
    write_config("[athc]\n")
    inp = _input(tmp_path, (SPECIAL + "\n") * 11)
    result = runner.invoke(set_specials, [str(inp)])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {inp}: Too many plays (11). The most is 10.\n"


# ── your team's game plans ────────────────────────────────────────────────────

# Denver's four game plans, named after their keys, in .lg2 order.
TEAM_PLANS = ("OFF1.pln", "DEF1.pln", "OFF2.pln", "DEF2.pln")


def set_league(folder: Path, **settings: str | Path) -> None:
    """Add `[league]` settings to the league folder's league.toml."""
    toml = folder / "league.toml"
    lines = "".join(f"{key} = '{value}'\n" for key, value in settings.items())
    text = toml.read_text(encoding="utf-8").replace("[league]\n", "[league]\n" + lines)
    toml.write_text(text, encoding="utf-8")


def team_league(
    league: Path, tmp_path: Path, names: tuple[str, ...] = TEAM_PLANS, **settings
) -> Path:
    """The league's .lg2 and .lge in `tmp_path/lg2`, Denver's four game plans
    named `names` and there (copies of the test game plans), `path` and
    `settings` set; returns Denver's league folder."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    off1, def1, off2, def2 = names
    record = team(
        ("o1.prf", off1), ("d1.prf", def1), ("o2.prf", off2), ("d2.prf", def2)
    )
    (lg2_dir / f"{LEAGUE}.lg2").write_bytes(record)
    (lg2_dir / f"{LEAGUE}.lge").write_bytes(lge(TEAM_NAMES[0]))
    set_league(league, path=lg2_dir, **settings)
    folder = lg2_dir / "PNFL" / "2049" / "Plans" / "Team"
    folder.mkdir(parents=True)
    for name in dict.fromkeys(names):
        _copy(folder, name, GP_OFFENSE if name.startswith("OFF") else GP_DEFENSE)
    return folder


@pytest.mark.parametrize(
    ("names", "tally"),
    [
        (TEAM_PLANS, "4 file(s) processed, 2 updated, 2 skipped, 0 failed"),
        (
            ("OFF.pln", "DEF.pln", "OFF.pln", "DEF.pln"),
            "2 file(s) processed, 1 updated, 1 skipped, 0 failed",
        ),
    ],
    ids=["four game plans", "one per side"],
)
def test_default_scope_is_your_teams_game_plans(
    runner, league: Path, tmp_path: Path, names: tuple[str, ...], tally: str
) -> None:
    """An offense list updates the offense game plans and skips the defense
    ones, in .lg2 order, then the tally."""
    folder = team_league(league, tmp_path, names, team="Denver")
    for name in dict.fromkeys(names):
        if name.startswith("OFF"):
            _without_special(folder / name)
    result = runner.invoke(set_specials, [str(_input(tmp_path, SPECIAL + "\n"))])
    assert result.exit_code == 0
    lines = []
    for name in dict.fromkeys(names):
        if name.startswith("OFF"):
            lines.append(f"OK   {folder / name}: updated (6 special play(s))")
            assert _name(read_gameplan(folder / name).custom_special_plays[1]) == (
                SPECIAL
            )
        else:
            lines.append(f"SKIP {folder / name}: defense game plan")
    assert result.stdout == "\n".join(lines) + f"\n\n{tally}\n"


def test_key_keeps_its_tally(runner, league: Path, tmp_path: Path) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    result = runner.invoke(
        set_specials, [str(_input(tmp_path, SPECIAL + "\n")), "--path", "off2"]
    )
    assert result.exit_code == 0
    assert result.stdout == (
        f"OK   {folder / 'OFF2.pln'}: updated (6 special play(s))\n"
        "\n"
        "1 file(s) processed, 1 updated, 0 skipped, 0 failed\n"
    )


def test_ppp_path_with_no_game_plans(runner, league: Path, tmp_path: Path) -> None:
    """The one scope line, a WARN: nothing failed, so exit 0."""
    mine = tmp_path / "mine"
    mine.mkdir()
    team_league(league, tmp_path, team="Denver", ppp_path=mine)
    result = runner.invoke(set_specials, [str(_input(tmp_path, SPECIAL + "\n"))])
    assert result.exit_code == 0
    assert result.stderr.endswith(
        f"WARN {mine}: No Denver game plans. The league file names "
        f"{', '.join(TEAM_PLANS)}.\n"
    )
    assert result.stdout == "\n0 file(s) processed, 0 updated, 0 skipped, 0 failed\n"


def test_league_location_missing_game_plan_counts_as_failed(
    runner, league: Path, tmp_path: Path
) -> None:
    folder = team_league(league, tmp_path, team="Denver")
    (folder / "DEF2.pln").unlink()
    result = runner.invoke(set_specials, [str(_input(tmp_path, SPECIAL + "\n"))])
    assert result.exit_code == 2
    assert result.stderr.endswith(f"FAIL {folder / 'DEF2.pln'}: {FILE_NOT_FOUND}\n")
    assert result.stdout.endswith(
        "\n3 file(s) processed, 2 updated, 1 skipped, 1 failed\n"
    )


def test_team_with_a_path_is_a_usage_error(runner, tmp_path: Path) -> None:
    p = _copy(tmp_path)
    inp = _input(tmp_path, SPECIAL + "\n")
    result = runner.invoke(
        set_specials, [str(inp), "--path", str(p), "--team", "Denver"]
    )
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: --team requires --path to be a game plan key (off1, def1, off2 or "
        "def2) or left out.\n"
    )
