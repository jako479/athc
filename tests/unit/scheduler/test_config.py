from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from athc.scheduler import config
from athc.scheduler.config import (
    ConfigError,
    Phase2Config,
    RivalriesConfig,
    SchedulerConfig,
    check_opening_weeks,
    check_weeks,
    find_config_path,
    find_league_path,
    load_league,
    load_scheduler_config,
    resolve_rivalries,
)
from athc.scheduler.domain.league import AFC_EAST, NFC_WEST, League

from .conftest import LEAGUE_5_SLOTS, PCFL_LEAGUE, PCFL_RIVALRIES

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
    assert [t.metro for t in standings[AFC_EAST]] == [
        "New England",
        "Miami",
        "Jacksonville",
        "Buffalo",
    ]
    assert [t.metro for t in standings[NFC_WEST]] == [
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
    afc_east = [t.metro for t in league.teams if t.division == AFC_EAST]
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


# ---------------------------------------------------------------------------
# [league] weeks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weeks", [2, 12])
def test_load_scheduler_config_reads_weeks(config_dir: Path, weeks: int) -> None:
    _write_scheduler_toml(config_dir, f"[league]\nweeks = {weeks}\n")
    assert load_scheduler_config().league.weeks == weeks


def test_weeks_defaults_to_sixteen() -> None:
    assert SchedulerConfig().league.weeks == 16


@pytest.mark.parametrize("weeks", ["11", "0", "'12'"])
def test_load_scheduler_config_rejects_bad_weeks(config_dir: Path, weeks: str) -> None:
    _write_scheduler_toml(config_dir, f"[league]\nweeks = {weeks}\n")
    with pytest.raises(ConfigError, match="weeks"):
        load_scheduler_config()


def test_load_scheduler_config_rejects_unknown_league_key(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[league]\nteams = 18\n")
    with pytest.raises(ConfigError, match="unknown \\[league\\] key"):
        load_scheduler_config()


def test_load_scheduler_config_from_explicit_path(tmp_path: Path) -> None:
    path = _write(tmp_path / "other.toml", "[league]\nweeks = 12\n")
    assert load_scheduler_config(path).league.weeks == 12


def test_load_scheduler_config_explicit_path_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_scheduler_config(tmp_path / "missing.toml")


# ---------------------------------------------------------------------------
# [phase2] new keys
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_new_phase2_keys(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [phase2]
        max_consecutive_conference_home_or_away = 2
        opening_nonconference_weeks = 3
        require_home_balance_per_six_weeks = false
        require_home_away_streak_caps = false
        require_mixed_home_away_at_season_ends = false
        """,
    )
    phase2 = load_scheduler_config().phase2
    assert phase2.max_consecutive_conference_home_or_away == 2
    assert phase2.opening_nonconference_weeks == 3
    assert phase2.require_home_balance_per_six_weeks is False
    assert phase2.require_home_away_streak_caps is False
    assert phase2.require_mixed_home_away_at_season_ends is False


def test_new_phase2_keys_default_to_pnfl_behaviour() -> None:
    phase2 = Phase2Config()
    assert phase2.max_consecutive_conference_home_or_away == 0
    assert phase2.opening_nonconference_weeks == 0
    assert phase2.require_home_balance_per_six_weeks is True
    assert phase2.require_home_away_streak_caps is True
    assert phase2.require_mixed_home_away_at_season_ends is True


@pytest.mark.parametrize(
    "key", ["max_consecutive_conference_home_or_away", "opening_nonconference_weeks"]
)
def test_zero_is_off_and_negative_is_rejected(config_dir: Path, key: str) -> None:
    _write_scheduler_toml(config_dir, f"[phase2]\n{key} = 0\n")
    assert getattr(load_scheduler_config().phase2, key) == 0
    _write_scheduler_toml(config_dir, f"[phase2]\n{key} = -1\n")
    with pytest.raises(ConfigError, match=key):
        load_scheduler_config()


# ---------------------------------------------------------------------------
# [rivalries]
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_rivalries(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [rivalries]
        rotate_home_by_season = false
        pairs = [[" Michigan ", "Ohio State"], ["USC", "UCLA"]]
        """,
    )
    rivalries = load_scheduler_config().rivalries
    assert rivalries.pairs == (("Michigan", "Ohio State"), ("USC", "UCLA"))
    assert rivalries.rotate_home_by_season is False


def test_rivalries_default_to_none() -> None:
    assert SchedulerConfig().rivalries == RivalriesConfig()
    assert RivalriesConfig().rotate_home_by_season is True


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("[rivalries]\nrotate_home_by_season = true\n", id="no-pairs"),
        pytest.param("[rivalries]\npairs = []\n", id="empty"),
        pytest.param('[rivalries]\npairs = [["A"]]\n', id="one-name"),
        pytest.param('[rivalries]\npairs = [["A", "B", "C"]]\n', id="three-names"),
        pytest.param('[rivalries]\npairs = [["A", "A"]]\n', id="same-team"),
        pytest.param('[rivalries]\npairs = [["A", " "]]\n', id="blank-name"),
        pytest.param("[rivalries]\npairs = [[1, 2]]\n", id="non-string"),
        pytest.param('[rivalries]\npairs = "A, B"\n', id="not-a-list"),
        pytest.param(
            '[rivalries]\npairs = [["A", "B"]]\nweek = 12\n', id="unknown-key"
        ),
    ],
)
def test_load_scheduler_config_rejects_bad_rivalries(
    config_dir: Path, body: str
) -> None:
    _write_scheduler_toml(config_dir, body)
    with pytest.raises(ConfigError, match="rivalries"):
        load_scheduler_config()


# ---------------------------------------------------------------------------
# League-resolved checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weeks", [10, 16])
def test_check_weeks_accepts_pcfl_range(weeks: int) -> None:
    check_weeks(PCFL_LEAGUE, weeks)


@pytest.mark.parametrize("weeks", [8, 18, 11])
def test_check_weeks_rejects_outside_pcfl_range(weeks: int) -> None:
    with pytest.raises(ConfigError, match="weeks"):
        check_weeks(PCFL_LEAGUE, weeks)


@pytest.mark.parametrize("weeks", [14, 20])
def test_check_weeks_accepts_pnfl_range(weeks: int) -> None:
    check_weeks(LEAGUE_5_SLOTS, weeks)


@pytest.mark.parametrize("weeks", [12, 22])
def test_check_weeks_rejects_outside_pnfl_range(weeks: int) -> None:
    with pytest.raises(ConfigError, match="weeks"):
        check_weeks(LEAGUE_5_SLOTS, weeks)


@pytest.mark.parametrize("opening", [0, 3])
def test_check_opening_weeks_accepts(opening: int) -> None:
    check_opening_weeks(PCFL_LEAGUE, 12, opening)


def test_check_opening_weeks_rejects_four_for_the_pcfl() -> None:
    with pytest.raises(ConfigError, match="opening_nonconference_weeks"):
        check_opening_weeks(PCFL_LEAGUE, 12, 4)


def test_resolve_rivalries_returns_team_pairs_in_listed_order() -> None:
    pairs = resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=PCFL_RIVALRIES))
    assert [(a.metro, b.metro) for a, b in pairs] == list(PCFL_RIVALRIES)
    assert sum(1 for a, b in pairs if a.conference != b.conference) == 1


def test_resolve_rivalries_with_no_pairs_is_empty() -> None:
    assert resolve_rivalries(PCFL_LEAGUE, RivalriesConfig()) == ()


@pytest.mark.parametrize(
    ("pairs", "message"),
    [
        pytest.param(PCFL_RIVALRIES[:8], "9 pairs", id="eight-pairs"),
        pytest.param((*PCFL_RIVALRIES, ("Michigan", "USC")), "9 pairs", id="ten-pairs"),
        pytest.param(
            (*PCFL_RIVALRIES[:8], ("Penn State", "Michigan")), "once", id="team-twice"
        ),
        pytest.param(
            (*PCFL_RIVALRIES[:8], ("Penn State", "Nowhere")),
            "Unknown team",
            id="unknown",
        ),
        pytest.param(
            (
                ("Michigan", "Texas"),
                ("USC", "Tennessee"),
                ("Washington", "Boston College"),
                ("Notre Dame", "Colorado"),
                ("Oklahoma", "Ohio State"),
                ("UCLA", "Oregon"),
                ("LSU", "Arkansas"),
                ("Georgia", "Clemson"),
                ("Miami", "Penn State"),
            ),
            "cross-conference",
            id="three-cross",
        ),
    ],
)
def test_resolve_rivalries_rejects(pairs, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        resolve_rivalries(PCFL_LEAGUE, RivalriesConfig(pairs=pairs))


# ---------------------------------------------------------------------------
# load_league — [ConferenceStandings] (a league without divisions)
# ---------------------------------------------------------------------------

DEV_PCFL = Path(__file__).resolve().parents[3] / "dev" / "leagues" / "PCFL"

CONFERENCE_STANDINGS = """\
[ConferenceStandings]
WESTERN =
    Ohio State
    Notre Dame
    UCLA
    Washington
    Oklahoma
    USC
    Colorado
    Oregon
    Michigan
EASTERN =
    Texas
    Tennessee
    Boston College
    Arkansas
    LSU
    Clemson
    Georgia
    Penn State
    Miami
"""

PCFL_OVERALL_STANDINGS = """\
[OverallStandings]
Order =
    Texas
    Tennessee
    Notre Dame
    Arkansas
    Ohio State
    Boston College
    LSU
    UCLA
    Washington
    Clemson
    Oklahoma
    Georgia
    Penn State
    USC
    Colorado
    Miami
    Oregon
    Michigan
"""


def test_load_league_reads_conference_standings(tmp_path: Path) -> None:
    ini = _write(
        tmp_path / "league.ini", CONFERENCE_STANDINGS + "\n" + PCFL_OVERALL_STANDINGS
    )
    league = load_league(ini)
    assert league == PCFL_LEAGUE
    assert not league.has_divisions


def test_load_league_errors_with_both_sections(tmp_path: Path) -> None:
    ini = _write(tmp_path / "league.ini", VALID_LEAGUE + "\n" + CONFERENCE_STANDINGS)
    with pytest.raises(ConfigError, match=r"DivisionStandings.*ConferenceStandings"):
        load_league(ini)


def test_load_league_errors_on_wrong_conference_size(tmp_path: Path) -> None:
    text = CONFERENCE_STANDINGS.replace("    Michigan\n", "") + PCFL_OVERALL_STANDINGS
    ini = _write(tmp_path / "league.ini", text)
    with pytest.raises(ConfigError, match="exactly 9 teams"):
        load_league(ini)


def test_dev_pcfl_league_file_loads() -> None:
    league = load_league(DEV_PCFL / "standings" / "2029.league.ini")
    assert league == PCFL_LEAGUE


def test_dev_pcfl_rules_file_loads() -> None:
    config = load_scheduler_config(DEV_PCFL / "rules" / "scheduler.toml")
    assert config.league.weeks == 12
    assert config.difficulty.spread == 0.0
    assert config.phase2.max_consecutive_home_or_away == 3
    assert config.phase2.max_consecutive_conference_home_or_away == 2
    assert config.phase2.opening_nonconference_weeks == 3
    assert config.phase2.require_home_balance_per_six_weeks is False
    assert config.phase2.require_home_away_streak_caps is False
    assert config.phase2.require_mixed_home_away_at_season_ends is False
    assert config.rivalries.rotate_home_by_season is True
    assert config.rivalries.pairs == PCFL_RIVALRIES
    check_weeks(PCFL_LEAGUE, config.league.weeks)
    check_opening_weeks(
        PCFL_LEAGUE, config.league.weeks, config.phase2.opening_nonconference_weeks
    )
    assert len(resolve_rivalries(PCFL_LEAGUE, config.rivalries)) == 9
