from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from athc.scheduler import config
from athc.scheduler.config import (
    ConfigError,
    find_config_path,
    find_history_path,
    find_league_path,
    load_league,
    load_scheduler_config,
)
from athc.scheduler.domain.league import League

# ---------------------------------------------------------------------------
# Scheduler tunables live in rules/PNFL.scheduler.toml; league data (divisions +
# conference ranking) is a separate league.ini. Tests derive invalid variants.
# ---------------------------------------------------------------------------


def _write_scheduler_toml(config_dir: Path, body: str) -> Path:
    rules = config_dir / "rules"
    rules.mkdir(exist_ok=True)
    path = rules / "PNFL.scheduler.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


VALID_LEAGUE = """\
[Divisions]
AFC_EAST =
    Buffalo
    Jacksonville
    Miami
    New England
AFC_WEST =
    Cincinnati
    Denver
    Las Vegas
    Los Angeles
    Pittsburgh
NFC_EAST =
    Atlanta
    New York
    Philadelphia
    Washington
NFC_WEST =
    Chicago
    Green Bay
    Minnesota
    San Francisco
    Seattle

[Standings]
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


# The older per-conference format, still accepted (drives the fixed-matchup
# scheduler). Reuses the same [Divisions] block.
VALID_LEAGUE_CONF = VALID_LEAGUE[: VALID_LEAGUE.index("[Standings]")] + (
    "[ConferenceRanking]\n"
    "AFC =\n"
    "    New England\n"
    "    Miami\n"
    "    Jacksonville\n"
    "    Buffalo\n"
    "    Cincinnati\n"
    "    Pittsburgh\n"
    "    Denver\n"
    "    Los Angeles\n"
    "    Las Vegas\n"
    "NFC =\n"
    "    Washington\n"
    "    Atlanta\n"
    "    New York\n"
    "    Philadelphia\n"
    "    Chicago\n"
    "    Minnesota\n"
    "    San Francisco\n"
    "    Green Bay\n"
    "    Seattle\n"
)


# Both rankings present: overall from [Standings] + an explicit conference order
# (deliberately different from the order derived from [Standings]).
VALID_LEAGUE_BOTH = VALID_LEAGUE + (
    "\n[ConferenceRanking]\n"
    "AFC =\n"
    "    Las Vegas\n"
    "    Los Angeles\n"
    "    Denver\n"
    "    Pittsburgh\n"
    "    Cincinnati\n"
    "    Buffalo\n"
    "    Jacksonville\n"
    "    Miami\n"
    "    New England\n"
    "NFC =\n"
    "    Seattle\n"
    "    Green Bay\n"
    "    San Francisco\n"
    "    Minnesota\n"
    "    Chicago\n"
    "    Philadelphia\n"
    "    New York\n"
    "    Atlanta\n"
    "    Washington\n"
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
        spread = 2.0
        shape = 3
        [solver]
        time_limit = 120
        phase1_time_limit = 30
        """,
    )
    cfg = load_scheduler_config()
    assert cfg.difficulty.spread == 2.0
    assert cfg.difficulty.shape == 3.0
    assert cfg.solver.time_limit == 120.0
    assert cfg.solver.phase1_time_limit == 30.0


def test_load_scheduler_config_defaults_when_no_file() -> None:
    cfg = load_scheduler_config()  # autouse empty config_dir
    assert cfg.difficulty.spread == config.DEFAULT_DIFFICULTY_SPREAD
    assert cfg.difficulty.shape == config.DEFAULT_DIFFICULTY_SHAPE
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT
    assert cfg.solver.phase1_time_limit == config.DEFAULT_PHASE1_TIME_LIMIT
    assert cfg.phase2 == config.Phase2Config()


def test_load_scheduler_config_defaults_when_keys_missing(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[difficulty]\nspread = 2.0\n")
    cfg = load_scheduler_config()
    assert cfg.difficulty.spread == 2.0
    assert cfg.difficulty.shape == config.DEFAULT_DIFFICULTY_SHAPE
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT


def test_load_scheduler_config_errors_on_invalid_value(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[solver]\ntime_limit = "fast"\n')
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
        week_16_divisional_games = 6
        max_consecutive_divisional = 2
        """,
    )
    cfg = load_scheduler_config()
    assert cfg.phase2.week_16_divisional_games == 6
    assert cfg.phase2.max_consecutive_divisional == 2
    # untouched keys keep their defaults
    assert cfg.phase2.five_team_max_divisional_in_10 == 7


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
        find_league_path()


def test_find_league_path_resolves_config_dir_file(config_dir: Path) -> None:
    present = _valid_league(config_dir)
    assert find_league_path() == present


# ---------------------------------------------------------------------------
# load_league — required sections and keys
# ---------------------------------------------------------------------------


def test_load_league_reads_valid_config(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    assert isinstance(league, League)
    assert len(league.teams) == 18
    assert league.rankings.overall is not None  # [Standings] -> overall known


def test_load_league_reads_conference_ranking_format(tmp_path: Path) -> None:
    # Back-compat: the old [ConferenceRanking] format loads, with no overall order.
    league = load_league(_write(tmp_path / "league.ini", VALID_LEAGUE_CONF))
    assert len(league.teams) == 18
    assert league.rankings.overall is None
    new_england = next(t for t in league.teams if t.metro == "New England")
    assert league.rankings.rank_of(new_england) == 1


def test_load_league_reads_both_rankings(tmp_path: Path) -> None:
    # Both sections: overall from [Standings]; the explicit conference order is
    # kept as-is (not derived from overall).
    league = load_league(_write(tmp_path / "league.ini", VALID_LEAGUE_BOTH))
    assert league.rankings.overall is not None
    las_vegas = next(t for t in league.teams if t.metro == "Las Vegas")
    assert league.rankings.rank_of(las_vegas) == 1  # explicit conference order
    assert league.rankings.overall_rank(las_vegas) == 17  # [Standings] position


def test_load_league_errors_when_divisions_section_missing(tmp_path: Path) -> None:
    text = VALID_LEAGUE[VALID_LEAGUE.index("[Standings]") :]  # standings only
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_standings_section_missing(tmp_path: Path) -> None:
    text = VALID_LEAGUE[: VALID_LEAGUE.index("[Standings]")]  # divisions only
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_order_key_missing(tmp_path: Path) -> None:
    text = VALID_LEAGUE[: VALID_LEAGUE.index("Order =")]  # [Standings] but no Order
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
        VALID_LEAGUE.replace("    New England\nAFC_WEST =", "AFC_WEST ="),
    )
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_invalid_ini(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", "[Divisions\nbroken")
    with pytest.raises(ConfigError):
        load_league(ini)


# ---------------------------------------------------------------------------
# find_history_path — config-dir nonconf_history.json
# ---------------------------------------------------------------------------


def test_find_history_path_points_at_config_dir(config_dir: Path) -> None:
    assert find_history_path() == config_dir / "nonconf_history.json"
