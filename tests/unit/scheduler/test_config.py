from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from athc.scheduler import config
from athc.scheduler.config import (
    ConfigError,
    find_config_path,
    find_history_path,
    find_league_path,
    load_history,
    load_league,
    load_scheduler_config,
)
from athc.scheduler.domain.league import Division, League

RELEASE = Path(__file__).resolve().parents[3] / "release"
SEASON = 2048  # shipped config files are 2048.league.ini / 2048.nonconf_history.json

# ---------------------------------------------------------------------------
# Scheduler tunables live in rules/PNFL.scheduler.toml; league data (divisions +
# overall standings) is a separate league.ini. Tests derive invalid variants.
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

LEAGUE_WITH_DIVISION_STANDINGS = VALID_LEAGUE + DIVISION_STANDINGS


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _valid_league(tmp_path: Path) -> Path:
    return _write(tmp_path / "league.ini", VALID_LEAGUE)


def _complete_matchups(league: League, year: int = 2047) -> dict[str, int]:
    """All 81 AFC x NFC pairs -> `year`, the complete history the loader requires."""
    return {
        f"{afc.metro}|{nfc.metro}": year
        for afc in league.rankings.afc
        for nfc in league.rankings.nfc
    }


# ---------------------------------------------------------------------------
# load_scheduler_config — rules/PNFL.scheduler.toml (optional; missing -> defaults)
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_values(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [difficulty]
        spread = 2.0
        amplitude = 0.4
        period = 6
        c_spread = 2.5
        d_spread = 0.5
        [solver]
        time_limit = 120
        phase1_time_limit = 30
        """,
    )
    cfg = load_scheduler_config()
    assert cfg.difficulty.spread == 2.0
    assert cfg.difficulty.amplitude == 0.4
    assert cfg.difficulty.period == 6.0
    assert cfg.difficulty.c_spread == 2.5
    assert cfg.difficulty.d_spread == 0.5
    assert cfg.solver.time_limit == 120.0
    assert cfg.solver.phase1_time_limit == 30.0


def test_load_scheduler_config_defaults_when_no_file() -> None:
    cfg = load_scheduler_config()  # autouse empty config_dir
    assert cfg.difficulty.spread == config.DEFAULT_DIFFICULTY_SPREAD
    assert cfg.difficulty.amplitude == config.DEFAULT_DIFFICULTY_AMPLITUDE
    assert cfg.difficulty.period == config.DEFAULT_DIFFICULTY_PERIOD
    assert cfg.difficulty.c_spread == config.DEFAULT_DIFFICULTY_C_SPREAD
    assert cfg.difficulty.d_spread == config.DEFAULT_DIFFICULTY_D_SPREAD
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT
    assert cfg.solver.phase1_time_limit == config.DEFAULT_PHASE1_TIME_LIMIT
    assert cfg.phase2 == config.Phase2Config()


def test_load_scheduler_config_defaults_when_keys_missing(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[difficulty]\nspread = 2.0\n")
    cfg = load_scheduler_config()
    assert cfg.difficulty.spread == 2.0
    assert cfg.difficulty.amplitude == config.DEFAULT_DIFFICULTY_AMPLITUDE
    assert cfg.difficulty.period == config.DEFAULT_DIFFICULTY_PERIOD
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT


def test_load_scheduler_config_errors_on_invalid_value(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[solver]\ntime_limit = "fast"\n')
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_errors_on_invalid_c_spread(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[difficulty]\nc_spread = "steep"\n')
    with pytest.raises(ConfigError):
        load_scheduler_config()


def test_load_scheduler_config_errors_on_invalid_d_spread(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[difficulty]\nd_spread = "steep"\n')
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
    assert league.rankings.overall is not None  # [Standings] -> overall known


def test_load_league_derives_conference_rank_from_standings(tmp_path: Path) -> None:
    # Conference 1-9 ranks come from the overall [Standings] order, not a separate
    # section. New England is 1st overall and the top AFC team; Washington 2nd
    # overall and the top NFC team.
    league = load_league(_valid_league(tmp_path))
    new_england = next(t for t in league.teams if t.metro == "New England")
    washington = next(t for t in league.teams if t.metro == "Washington")
    assert league.rankings.overall_rank(new_england) == 1
    assert league.rankings.rank_of(new_england) == 1
    assert league.rankings.overall_rank(washington) == 2
    assert league.rankings.rank_of(washington) == 1


def test_load_league_errors_when_divisions_section_missing(tmp_path: Path) -> None:
    text = VALID_LEAGUE[VALID_LEAGUE.index("[Standings]") :]  # standings only
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_standings_section_missing(tmp_path: Path) -> None:
    text = VALID_LEAGUE[: VALID_LEAGUE.index("[Standings]")]  # divisions only
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError, match="Standings"):
        load_league(ini)


def test_load_league_errors_on_duplicate_team(tmp_path: Path) -> None:
    # Same metro listed in two divisions.
    text = VALID_LEAGUE.replace("    Cincinnati\n", "    Miami\n", 1)
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_standings_team_not_in_divisions(
    tmp_path: Path,
) -> None:
    # [Standings] names a team that isn't in [Divisions] (drops New England from
    # the order and adds a bogus team in its place).
    text = VALID_LEAGUE.replace("Order =\n    New England", "Order =\n    Nowhere")
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


def test_load_league_errors_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_league(tmp_path / "absent.ini")


def test_load_league_errors_on_unknown_division_key(tmp_path: Path) -> None:
    text = VALID_LEAGUE.replace("AFC_EAST =", "AFC_EASTX =", 1)
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_standings_duplicate(tmp_path: Path) -> None:
    # Duplicate a team in [Standings] (Seattle twice; Las Vegas dropped).
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
# load_league — optional [DivisionStandings] (required by Scheduler C)
# ---------------------------------------------------------------------------


def test_load_league_reads_division_standings(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", LEAGUE_WITH_DIVISION_STANDINGS)
    league = load_league(ini)
    standings = league.division_standings
    assert standings is not None
    afc_east = standings[Division.AFC_EAST]
    assert [t.metro for t in afc_east] == [
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


def test_load_league_division_standings_none_when_section_absent(
    tmp_path: Path,
) -> None:
    league = load_league(_valid_league(tmp_path))
    assert league.division_standings is None


def test_load_league_errors_when_division_standings_incomplete(tmp_path: Path) -> None:
    # Section present but a division key missing.
    text = LEAGUE_WITH_DIVISION_STANDINGS.replace(
        "NFC_WEST =\n    Chicago\n    Minnesota\n    San Francisco\n"
        "    Green Bay\n    Seattle\n",
        "",
        1,
    )
    # Only replace within [DivisionStandings]: the [Divisions] copy differs, so
    # the text above matches the standings block alone.
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_unknown_division_standings_team(tmp_path: Path) -> None:
    text = LEAGUE_WITH_DIVISION_STANDINGS.replace(
        "[DivisionStandings]\nAFC_EAST =\n    New England",
        "[DivisionStandings]\nAFC_EAST =\n    Nowhere",
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_division_standings_team_misplaced(
    tmp_path: Path,
) -> None:
    # Chicago (NFC_WEST) listed in AFC_EAST's standings.
    text = LEAGUE_WITH_DIVISION_STANDINGS.replace(
        "[DivisionStandings]\nAFC_EAST =\n    New England",
        "[DivisionStandings]\nAFC_EAST =\n    Chicago",
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_on_division_standings_duplicate(tmp_path: Path) -> None:
    text = LEAGUE_WITH_DIVISION_STANDINGS.replace(
        "[DivisionStandings]\nAFC_EAST =\n    New England\n    Miami",
        "[DivisionStandings]\nAFC_EAST =\n    New England\n    New England",
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_load_league_errors_when_division_standings_team_missing(
    tmp_path: Path,
) -> None:
    # AFC_EAST standings list only three of its four teams.
    text = LEAGUE_WITH_DIVISION_STANDINGS.replace(
        "[DivisionStandings]\nAFC_EAST =\n    New England\n    Miami\n",
        "[DivisionStandings]\nAFC_EAST =\n    New England\n",
    )
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError):
        load_league(ini)


def test_release_league_has_division_standings() -> None:
    league = load_league(RELEASE / f"{SEASON}.league.ini")
    assert league.division_standings is not None
    assert len(league.division_standings) == 4


# ---------------------------------------------------------------------------
# find_history_path — config-dir nonconf_history.json
# ---------------------------------------------------------------------------


def test_find_history_path_resolves_season_prefixed_file(config_dir: Path) -> None:
    present = _write(config_dir / f"{SEASON}.nonconf_history.json", "{}")
    assert find_history_path(SEASON) == present


def test_find_history_path_errors_when_missing(config_dir: Path) -> None:
    with pytest.raises(ConfigError):
        find_history_path(SEASON)


# ---------------------------------------------------------------------------
# load_history — nonconf_history.json (optional; structure + team alignment)
# ---------------------------------------------------------------------------


def test_load_history_reads_valid_aligned_file(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    good = _write(
        tmp_path / "h.json", json.dumps({"matchups": _complete_matchups(league, 2046)})
    )
    history = load_history(good, league)
    buffalo = next(t for t in league.teams if t.metro == "Buffalo")
    atlanta = next(t for t in league.teams if t.metro == "Atlanta")
    assert history.last_played(buffalo, atlanta) == 2046


def test_load_history_errors_when_absent_or_empty(tmp_path: Path) -> None:
    # History must cover all 81 pairs, so an absent (-> empty) file is incomplete.
    league = load_league(_valid_league(tmp_path))
    with pytest.raises(ConfigError):
        load_history(tmp_path / "absent.json", league)


def test_load_history_errors_when_incomplete(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    matchups = _complete_matchups(league)
    matchups.pop(next(iter(matchups)))  # drop one pair
    bad = _write(tmp_path / "h.json", json.dumps({"matchups": matchups}))
    with pytest.raises(ConfigError, match="missing"):
        load_history(bad, league)


def test_load_history_errors_on_invalid_json(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    bad = _write(tmp_path / "h.json", "{not json")
    with pytest.raises(ConfigError):
        load_history(bad, league)


def test_load_history_errors_on_bad_structure(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    bad = _write(tmp_path / "h.json", '{"matchups": [1, 2, 3]}')
    with pytest.raises(ConfigError):
        load_history(bad, league)


def test_load_history_errors_on_non_integer_season(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    bad = _write(tmp_path / "h.json", '{"matchups": {"Buffalo|Atlanta": "soon"}}')
    with pytest.raises(ConfigError):
        load_history(bad, league)


def test_load_history_errors_on_unknown_team(tmp_path: Path) -> None:
    league = load_league(_valid_league(tmp_path))
    bad = _write(tmp_path / "h.json", '{"matchups": {"Nowhere|Atlanta": 2046}}')
    with pytest.raises(ConfigError, match="unknown or misplaced"):
        load_history(bad, league)


def test_load_history_errors_on_wrong_conference_side(tmp_path: Path) -> None:
    # Atlanta is NFC; on the AFC (first) side it's misplaced.
    league = load_league(_valid_league(tmp_path))
    bad = _write(tmp_path / "h.json", '{"matchups": {"Atlanta|Buffalo": 2046}}')
    with pytest.raises(ConfigError, match="unknown or misplaced"):
        load_history(bad, league)


def test_release_example_history_aligns_with_release_league() -> None:
    """The shipped release/nonconf_history.json matches release/league.ini."""
    league = load_league(RELEASE / f"{SEASON}.league.ini")
    history = load_history(RELEASE / f"{SEASON}.nonconf_history.json", league)
    assert history.validate_teams(league) is None
