from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from athc.scheduler import config
from athc.scheduler.config import (
    ConfigError,
    find_config_path,
    find_league_path,
    load_league,
    load_scheduler_config,
)
from athc.scheduler.domain.league import Division, League

RELEASE = Path(__file__).resolve().parents[3] / "release"
SEASON = 2048  # shipped config file is 2048.league.ini

# ---------------------------------------------------------------------------
# Scheduler tunables live in rules/PNFL.scheduler.toml; league data is a separate
# league.ini: [DivisionStandings] (per-division teams in finish order -- this
# defines division membership) plus [OverallStandings] (overall 1-18). Tests derive
# invalid variants from VALID_LEAGUE.
# ---------------------------------------------------------------------------


def _write_scheduler_toml(config_dir: Path, body: str) -> Path:
    rules = config_dir / "rules"
    rules.mkdir(exist_ok=True)
    path = rules / "PNFL.scheduler.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# [DivisionStandings] alone: each division's teams in finish order (best first).
DIVISION_STANDINGS = """\
[DivisionStandings]
AFC_EAST =
    New England
    Miami
    Jacksonville
    Buffalo
AFC_WEST =
    Cincinnati
    Pittsburgh
    Denver
    Los Angeles
    Las Vegas
NFC_EAST =
    Washington
    Atlanta
    New York
    Philadelphia
NFC_WEST =
    Chicago
    Minnesota
    San Francisco
    Green Bay
    Seattle
"""


# [OverallStandings] alone: the overall 1-18 finish (a valid file needs this too).
OVERALL_STANDINGS = """\
[OverallStandings]
Order =
    New England
    Washington
    Miami
    Atlanta
    Jacksonville
    New York
    Buffalo
    Philadelphia
    Cincinnati
    Chicago
    Pittsburgh
    Minnesota
    Denver
    San Francisco
    Los Angeles
    Green Bay
    Las Vegas
    Seattle
"""

VALID_LEAGUE = DIVISION_STANDINGS + "\n" + OVERALL_STANDINGS
LEAGUE_MISSING_DIVISION_STANDINGS = (
    OVERALL_STANDINGS  # no [DivisionStandings] -> invalid
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _valid_league(tmp_path: Path) -> Path:
    return _write(tmp_path / "league.ini", VALID_LEAGUE)


# ---------------------------------------------------------------------------
# load_scheduler_config — rules/PNFL.scheduler.toml (optional; missing -> defaults)
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_values(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [difficulty]
        spread = 2.5
        [solver]
        time_limit = 120
        phase1_time_limit = 30
        solver_workers = 12
        """,
    )
    cfg = load_scheduler_config()
    assert cfg.difficulty.spread == 2.5
    assert cfg.solver.time_limit == 120.0
    assert cfg.solver.phase1_time_limit == 30.0
    assert cfg.solver.solver_workers == 12


def test_load_scheduler_config_defaults_when_no_file() -> None:
    cfg = load_scheduler_config()  # autouse empty config_dir
    assert cfg.difficulty.spread == config.DEFAULT_DIFFICULTY_SPREAD
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT
    assert cfg.solver.phase1_time_limit == config.DEFAULT_PHASE1_TIME_LIMIT
    assert cfg.solver.solver_workers == config.DEFAULT_SOLVER_WORKERS
    assert cfg.phase2 == config.Phase2Config()


def test_load_scheduler_config_defaults_when_keys_missing(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[difficulty]\nspread = 2.0\n")
    cfg = load_scheduler_config()
    assert cfg.difficulty.spread == 2.0
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT


def test_load_scheduler_config_errors_on_invalid_value(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[solver]\ntime_limit = "fast"\n')
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_errors_on_non_integer_workers(config_dir: Path) -> None:
    # solver_workers is an integer count; a fractional value is invalid.
    _write_scheduler_toml(config_dir, "[solver]\nsolver_workers = 1.5\n")
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_errors_on_invalid_spread(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[difficulty]\nspread = "steep"\n')
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_errors_on_invalid_toml(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[solver\nbroken")
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_reads_phase2_amounts(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [phase2]
        require_final_week_divisional = false
        max_consecutive_divisional = 2
        """,
    )
    cfg = load_scheduler_config()
    assert cfg.phase2.require_final_week_divisional is False
    assert cfg.phase2.max_consecutive_divisional == 2
    # untouched keys keep their defaults
    assert cfg.phase2.require_divisional_in_final_two_weeks is True
    assert cfg.phase2.five_team_max_divisional_in_9 == 6


def test_load_scheduler_config_reads_soft_objective(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [phase2]
        soft_home_streak_lo = 4
        soft_close_rematches_weight = 300
        """,
    )
    cfg = load_scheduler_config()
    assert cfg.phase2.soft_home_streak_lo == 4
    assert cfg.phase2.soft_close_rematches_weight == 300
    # untouched soft keys keep their defaults
    assert cfg.phase2.soft_home_streak_hi == 7
    assert cfg.phase2.soft_open_weeks_1_2_weight == 100


def test_soft_objective_defaults() -> None:
    p = config.Phase2Config()
    assert (
        p.soft_home_streak_lo,
        p.soft_home_streak_hi,
        p.soft_home_streak_weight,
    ) == (
        5,
        7,
        155,
    )
    assert (
        p.soft_close_rematches_lo,
        p.soft_close_rematches_hi,
        p.soft_close_rematches_weight,
    ) == (0, 2, 215)


def test_load_scheduler_config_rejects_unknown_phase2_key(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[phase2]\nbogus = 1\n")
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_errors_on_non_integer_phase2(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[phase2]\nweek_16_divisional_games = 8.5\n")
    with pytest.raises(ConfigError):
        load_scheduler_config()


# ---------------------------------------------------------------------------
# path resolution — athc.ini optional, league.ini required
# ---------------------------------------------------------------------------


def test_find_config_path_returns_scheduler_rules_file(config_dir: Path) -> None:
    # The scheduler config is optional, so this never raises -- it names the path.
    assert find_config_path() == config_dir / "rules" / "PNFL.scheduler.toml"


def test_find_league_path_errors_when_none_exist(config_dir: Path) -> None:
    with pytest.raises(ConfigError):
        find_league_path(SEASON)


def test_find_league_path_resolves_season_prefixed_file(config_dir: Path) -> None:
    present = _write(config_dir / f"{SEASON}.league.ini", VALID_LEAGUE)
    assert find_league_path(SEASON) == present


# ---------------------------------------------------------------------------
# load_league — required sections and keys
# ---------------------------------------------------------------------------


def test_load_league_reads_valid_config(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    assert isinstance(league, League)
    assert len(league.teams) == 18
    assert league.rankings.overall is not None  # [OverallStandings] -> overall known


def test_load_league_derives_conference_rank_from_standings(tmp_path: Path) -> None:
    # Conference 1-9 ranks come from the overall [OverallStandings] order, not a separate
    # section. New England is 1st overall and the top AFC team; Washington 2nd
    # overall and the top NFC team.
    league = load_league(_valid_league(tmp_path))
    new_england = next(t for t in league.teams if t.metro == "New England")
    washington = next(t for t in league.teams if t.metro == "Washington")
    assert league.rankings.overall_rank(new_england) == 1
    assert league.rankings.rank_of(new_england) == 1
    assert league.rankings.overall_rank(washington) == 2
    assert league.rankings.rank_of(washington) == 1


def test_load_league_errors_when_division_standings_section_missing(
    tmp_path: Path,
) -> None:
    # [DivisionStandings] defines membership; without it there is no league.
    ini = _write(tmp_path / "league.ini", LEAGUE_MISSING_DIVISION_STANDINGS)
    with pytest.raises(ConfigError, match="DivisionStandings"):
        load_league(ini)


def test_load_league_errors_when_standings_section_missing(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", DIVISION_STANDINGS)  # no [OverallStandings]
    with pytest.raises(ConfigError, match="OverallStandings"):
        load_league(ini)


def test_load_league_errors_on_duplicate_team(tmp_path: Path) -> None:
    # Same metro in two divisions (Miami replaces Cincinnati in AFC_WEST).
    text = VALID_LEAGUE.replace("    Cincinnati\n", "    Miami\n", 1)
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_standings_team_not_in_divisions(
    tmp_path: Path,
) -> None:
    # [OverallStandings] names a team absent from [DivisionStandings] (Nowhere replaces
    # New England in the overall order).
    text = VALID_LEAGUE.replace("Order =\n    New England", "Order =\n    Nowhere")
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_order_key_missing(tmp_path: Path) -> None:
    text = VALID_LEAGUE[
        : VALID_LEAGUE.index("Order =")
    ]  # [OverallStandings] but no Order
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_order_empty(tmp_path: Path) -> None:
    text = VALID_LEAGUE[: VALID_LEAGUE.index("Order =")] + "Order =\n"
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_invalid_league_data(tmp_path: Path) -> None:
    # Drop a team from AFC_EAST so the division is the wrong size.
    ini = _write(
        tmp_path / "league.ini",
        VALID_LEAGUE.replace("    Buffalo\nAFC_WEST =", "AFC_WEST ="),
    )
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_invalid_ini(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", "[DivisionStandings\nbroken")
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_league(tmp_path / "absent.ini")


def test_load_league_errors_on_unknown_division_key(tmp_path: Path) -> None:
    text = VALID_LEAGUE.replace("AFC_EAST =", "AFC_EASTX =", 1)
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_standings_duplicate(tmp_path: Path) -> None:
    # Duplicate a team in [OverallStandings] (Seattle twice; Las Vegas dropped).
    text = VALID_LEAGUE.replace(
        "    Las Vegas\n    Seattle", "    Seattle\n    Seattle"
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_release_example_league_loads() -> None:
    """The shipped release/league.ini is valid."""
    league = load_league(RELEASE / f"{SEASON}.league.ini")
    assert len(league.teams) == 18
    assert league.rankings.overall is not None


# ---------------------------------------------------------------------------
# load_league — [DivisionStandings] defines membership + per-division finish
# ---------------------------------------------------------------------------


def test_load_league_reads_division_standings(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    standings = league.division_standings
    assert [t.metro for t in standings[Division.AFC_EAST]] == [
        "New England",
        "Miami",
        "Jacksonville",
        "Buffalo",
    ]
    assert [t.metro for t in standings[Division.NFC_WEST]] == [
        "Chicago",
        "Minnesota",
        "San Francisco",
        "Green Bay",
        "Seattle",
    ]


def test_load_league_teams_are_alphabetical_within_division(tmp_path: Path) -> None:
    # Membership comes from [DivisionStandings] (finish order), but the teams
    # tuple is canonical: alphabetical within each division.
    league = load_league(_valid_league(tmp_path))
    afc_east = [t.metro for t in league.teams if t.division == Division.AFC_EAST]
    assert afc_east == ["Buffalo", "Jacksonville", "Miami", "New England"]


def test_load_league_errors_when_division_missing(tmp_path: Path) -> None:
    # A whole division absent from [DivisionStandings].
    text = VALID_LEAGUE.replace(
        "NFC_WEST =\n    Chicago\n    Minnesota\n    San Francisco\n"
        "    Green Bay\n    Seattle\n",
        "",
        1,
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_division_standings_duplicate(tmp_path: Path) -> None:
    # A division lists the same team twice.
    text = VALID_LEAGUE.replace(
        "AFC_EAST =\n    New England\n    Miami",
        "AFC_EAST =\n    New England\n    New England",
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_release_league_has_division_standings() -> None:
    league = load_league(RELEASE / f"{SEASON}.league.ini")
    assert len(league.division_standings) == 4
