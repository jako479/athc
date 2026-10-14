from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from athc.config import LeagueError
from athc.errors import FILE_NOT_FOUND, ConfigFileError
from athc.scheduler import config
from athc.scheduler.config import (
    Phase2Config,
    RivalriesConfig,
    SchedulerConfig,
    check_opening_weeks,
    check_weeks,
    load_scheduler_config,
    resolve_rivalries,
    scheduler_rules_path,
)
from athc.scheduler.domain.league import lookup_team
from tests.conftest import ROOT, shipped_files, shipped_id

from .conftest import (
    CONFERENCES_LEAGUE,
    CONFERENCES_RIVALRIES,
    ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION,
)

LEAGUE = "divisions"  # the test league's name

# Every shipped scheduler rules file.
SHIPPED_RULES = shipped_files("*/scheduler.toml")


# ---------------------------------------------------------------------------
# Scheduler tunables live in leagues/<league>/scheduler.toml; the league itself
# comes from its .lge files (see test_league_files.py).
# ---------------------------------------------------------------------------


def _league_folder(config_dir: Path, name: str = LEAGUE) -> Path:
    """`leagues/<name>/` under the config dir."""
    folder = config_dir / "leagues" / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _load() -> SchedulerConfig:
    """The test league's rules file from its folder; defaults when absent."""
    return load_scheduler_config(scheduler_rules_path(LEAGUE), required=False)


def _write_scheduler_toml(config_dir: Path, body: str) -> Path:
    path = _league_folder(config_dir) / "scheduler.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_scheduler_config — scheduler.toml (optional; missing -> defaults)
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
    cfg = _load()
    assert cfg.difficulty.spread == 2.5
    assert cfg.solver.time_limit == 120.0
    assert cfg.solver.phase1_time_limit == 30.0
    assert cfg.solver.solver_workers == 12


def test_load_scheduler_config_defaults_when_no_file(config_dir: Path) -> None:
    _league_folder(config_dir)  # league exists, scheduler.toml does not
    cfg = _load()
    assert cfg.difficulty.spread == config.DEFAULT_DIFFICULTY_SPREAD
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT
    assert cfg.solver.phase1_time_limit == config.DEFAULT_PHASE1_TIME_LIMIT
    assert cfg.solver.solver_workers == config.DEFAULT_SOLVER_WORKERS
    assert cfg.phase2 == config.Phase2Config()


def test_load_scheduler_config_defaults_when_keys_missing(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[difficulty]\nspread = 2.0\n")
    cfg = _load()
    assert cfg.difficulty.spread == 2.0
    assert cfg.solver.time_limit == config.DEFAULT_TIME_LIMIT


def test_load_scheduler_config_errors_on_invalid_value(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[solver]\ntime_limit = "fast"\n')
    with pytest.raises(ConfigFileError):
        _load()


def test_solver_time_limit_must_be_positive(tmp_path: Path) -> None:
    # One validator for time_limit and phase1_time_limit, tested once.
    path = _write(tmp_path / "s.toml", "[solver]\ntime_limit = 1\n")
    assert load_scheduler_config(path).solver.time_limit == 1.0
    _write(path, "[solver]\ntime_limit = 0\n")
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value) == f"{path}: [solver] time_limit: Must be a positive number."


def test_load_scheduler_config_errors_on_non_integer_workers(config_dir: Path) -> None:
    # solver_workers is an integer count; a fractional value is invalid.
    _write_scheduler_toml(config_dir, "[solver]\nsolver_workers = 1.5\n")
    with pytest.raises(ConfigFileError):
        _load()


def test_solver_workers_defaults_to_auto(config_dir: Path) -> None:
    _league_folder(config_dir)  # no rules file: every default
    assert _load().solver.solver_workers == "auto"


def test_solver_workers_accepts_auto(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[solver]\nsolver_workers = "auto"\n')
    assert _load().solver.solver_workers == "auto"


def test_solver_workers_accepts_one(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[solver]\nsolver_workers = 1\n")
    assert _load().solver.solver_workers == 1


def test_solver_workers_rejects_zero(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[solver]\nsolver_workers = 0\n")
    with pytest.raises(ConfigFileError, match="solver_workers"):
        _load()


def test_solver_workers_rejects_other_text(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[solver]\nsolver_workers = "Auto"\n')
    with pytest.raises(ConfigFileError, match="solver_workers"):
        _load()


def test_load_scheduler_config_errors_on_invalid_spread(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, '[difficulty]\nspread = "steep"\n')
    with pytest.raises(ConfigFileError):
        _load()


def test_load_scheduler_config_errors_on_invalid_toml(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[solver\nbroken")
    with pytest.raises(ConfigFileError):
        _load()


def test_load_scheduler_config_skips_bom(config_dir: Path) -> None:
    """A UTF-8 byte-order mark (Notepad, Excel) is dropped, not a parse error."""
    path = _league_folder(config_dir) / "scheduler.toml"
    path.write_text("[difficulty]\nspread = 2.0\n", encoding="utf-8-sig")
    assert _load().difficulty.spread == 2.0


def test_load_scheduler_config_reads_phase2_amounts(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [phase2]
        require_final_week_divisional = false
        max_consecutive_divisional = 2
        """,
    )
    cfg = _load()
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
    cfg = _load()
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
    with pytest.raises(ConfigFileError):
        _load()


def test_load_scheduler_config_errors_on_non_integer_phase2(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[phase2]\nweek_16_divisional_games = 8.5\n")
    with pytest.raises(ConfigFileError):
        _load()


# ---------------------------------------------------------------------------
# path resolution — the rules file sits in the league folder
# ---------------------------------------------------------------------------


def test_scheduler_rules_path_is_named_by_league(config_dir: Path) -> None:
    # The rules file is optional, so this never raises for an existing league --
    # it names the path.
    folder = _league_folder(config_dir)
    assert scheduler_rules_path(LEAGUE) == folder / "scheduler.toml"


def test_scheduler_rules_path_needs_the_league_folder() -> None:
    with pytest.raises(LeagueError, match=f"League '{LEAGUE}' not found"):
        scheduler_rules_path(LEAGUE)


# ---------------------------------------------------------------------------
# [league] weeks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weeks", [2, 12])
def test_load_scheduler_config_reads_weeks(config_dir: Path, weeks: int) -> None:
    _write_scheduler_toml(config_dir, f"[league]\nweeks = {weeks}\n")
    assert _load().league.weeks == weeks


def test_weeks_defaults_to_sixteen() -> None:
    assert SchedulerConfig().league.weeks == 16


@pytest.mark.parametrize("weeks", ["11", "0", "'12'"])
def test_load_scheduler_config_rejects_bad_weeks(config_dir: Path, weeks: str) -> None:
    _write_scheduler_toml(config_dir, f"[league]\nweeks = {weeks}\n")
    with pytest.raises(ConfigFileError, match="weeks"):
        _load()


def test_load_scheduler_config_rejects_unknown_league_key(config_dir: Path) -> None:
    _write_scheduler_toml(config_dir, "[league]\nteams = 18\n")
    with pytest.raises(ConfigFileError, match="\\[league\\]: Unknown key"):
        _load()


def test_load_scheduler_config_from_explicit_path(tmp_path: Path) -> None:
    path = _write(tmp_path / "other.toml", "[league]\nweeks = 12\n")
    assert load_scheduler_config(path).league.weeks == 12


def test_load_scheduler_config_explicit_path_must_exist(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(missing)
    assert str(exc.value) == f"{missing}: {FILE_NOT_FOUND}"
    assert exc.value.path == missing


def test_unknown_key_names_the_table_and_the_keys(tmp_path: Path) -> None:
    path = _write(tmp_path / "s.toml", "[league]\nweeks = 12\nbogus = 1\nzap = 2\n")
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value) == (
        f"{path}: [league]: Unknown key(s): bogus, zap. Valid: weeks."
    )


def test_a_bad_rivalry_pair_shows_plain_names(tmp_path: Path) -> None:
    path = _write(tmp_path / "s.toml", '[rivalries]\npairs = [["A", "B", "C"]]\n')
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value) == (
        f"{path}: [rivalries] pairs: Each pair must be two team names, got A, B, C."
    )


def test_cross_checks_name_the_rules_file() -> None:
    rules = Path("scheduler.toml")
    with pytest.raises(ConfigFileError) as exc:
        check_weeks(CONFERENCES_LEAGUE, 8, path=rules)
    team = CONFERENCES_LEAGUE.teams[0]
    assert str(exc.value) == (
        "scheduler.toml: [league] weeks: Must be 9..17, got 8. "
        f"{team.metro} plays 8 structural games."
    )
    with pytest.raises(ConfigFileError) as exc:
        check_weeks(CONFERENCES_LEAGUE, 11, path=rules)
    assert str(exc.value) == (
        "scheduler.toml: [league] weeks: Must be a positive even integer, got 11."
    )
    with pytest.raises(ConfigFileError) as exc:
        check_opening_weeks(CONFERENCES_LEAGUE, 12, 4, path=rules)
    assert str(exc.value) == (
        "scheduler.toml: [phase2] opening_nonconference_weeks: Too many, got 4. "
        "The other 8 weeks hold at most 8 same-conference games each, and the "
        "league plays 72."
    )
    with pytest.raises(ConfigFileError) as exc:
        resolve_rivalries(
            CONFERENCES_LEAGUE,
            RivalriesConfig(pairs=CONFERENCES_RIVALRIES[:8]),
            path=rules,
        )
    assert (
        str(exc.value) == "scheduler.toml: [rivalries] pairs: Must list 9 pairs, got 8."
    )


def test_unknown_team_lists_plain_names() -> None:
    with pytest.raises(ValueError) as exc:
        lookup_team(CONFERENCES_LEAGUE.teams, "Nowhere")
    message = str(exc.value)
    assert message.startswith("Unknown team: 'Nowhere'. Valid: ")
    assert "[" not in message and "'Michigan'" not in message


def test_load_scheduler_config_bad_toml_names_the_file(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.toml", "[league\n")
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value).startswith(f"{path}: Not valid TOML: ")


def test_load_scheduler_config_bad_value_names_the_file(tmp_path: Path) -> None:
    path = _write(tmp_path / "bad.toml", "[difficulty]\nspread = 'x'\n")
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value) == f"{path}: [difficulty] spread: Must be a number."


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ("[league]\nweeks = '12'\n", "[league] weeks: Must be an integer."),
        ("[league]\nweeks = 11\n", "[league] weeks: Must be a positive even integer."),
        (
            "[solver]\nsolver_workers = 0\n",
            '[solver] solver_workers: Must be a positive integer or "auto".',
        ),
        (
            "[phase2]\nrequire_home_away_streak_caps = 1\n",
            "[phase2] require_home_away_streak_caps: Must be true or false.",
        ),
        (
            "[phase2]\nopening_nonconference_weeks = -1\n",
            "[phase2] opening_nonconference_weeks: Must be 0 (off) or positive.",
        ),
        ("[rivalries]\npairs = []\n", "[rivalries] pairs: Must be a non-empty list."),
        (
            '[rivalries]\npairs = [["A", "A"]]\n',
            "[rivalries] pairs: A pair names the same team twice: 'A'.",
        ),
    ],
)
def test_a_bad_value_names_its_table_and_key_first(
    tmp_path: Path, body: str, reason: str
) -> None:
    path = _write(tmp_path / "s.toml", body)
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value) == f"{path}: {reason}"


def test_load_scheduler_config_optional_path_defaults_when_missing(
    tmp_path: Path,
) -> None:
    assert (
        load_scheduler_config(tmp_path / "missing.toml", required=False)
        == SchedulerConfig()
    )


def test_load_scheduler_config_optional_path_reads_when_present(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "rules.toml", "[league]\nweeks = 12\n")
    assert load_scheduler_config(path, required=False).league.weeks == 12


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
    phase2 = _load().phase2
    assert phase2.max_consecutive_conference_home_or_away == 2
    assert phase2.opening_nonconference_weeks == 3
    assert phase2.require_home_balance_per_six_weeks is False
    assert phase2.require_home_away_streak_caps is False
    assert phase2.require_mixed_home_away_at_season_ends is False


def test_new_phase2_keys_default_to_divisional_behaviour() -> None:
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
    assert getattr(_load().phase2, key) == 0
    _write_scheduler_toml(config_dir, f"[phase2]\n{key} = -1\n")
    with pytest.raises(ConfigFileError, match=key):
        _load()


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
    rivalries = _load().rivalries
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
    with pytest.raises(ConfigFileError, match="rivalries"):
        _load()


# ---------------------------------------------------------------------------
# [renames.<season>] — previous name = new name
# ---------------------------------------------------------------------------


def test_load_scheduler_config_reads_renames(config_dir: Path) -> None:
    _write_scheduler_toml(
        config_dir,
        """
        [renames.2048]
        Baltimore = "Los Angeles"
        [renames.2049]
        "Los Angeles" = " Baltimore "
        Seattle = "Detroit"
        """,
    )
    assert _load().renames == {
        2048: {"Baltimore": "Los Angeles"},
        2049: {"Los Angeles": "Baltimore", "Seattle": "Detroit"},
    }


def test_renames_default_to_none() -> None:
    assert SchedulerConfig().renames == {}


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ("renames = 1\n", "[renames]: Must be a table."),
        ("[renames]\nabc = 1\n", "[renames] abc: Must be a season year, e.g. 2048."),
        (
            '[renames.abc]\nA = "B"\n',
            "[renames] abc: Must be a season year, e.g. 2048.",
        ),
        ('[renames]\n2048 = "x"\n', "[renames.2048]: Must be a table."),
        ("[renames.2048]\nA = 1\n", "[renames.2048] A: Must be a team name."),
        ('[renames.2048]\nA = " "\n', "[renames.2048] A: Must be a team name."),
        ('[renames.2048]\n" " = "B"\n', "[renames.2048]: A team name is blank."),
        ('[renames.2048]\nA = "A"\n', "[renames.2048] A: Renames the team to itself."),
        ('[renames.2048]\n"A " = "B"\nA = "C"\n', "[renames.2048] A: Listed twice."),
        # A Unicode digit passes str.isdigit but is no year.
        ('[renames."²"]\nA = "B"\n', "[renames] ²: Must be a season year, e.g. 2048."),
        (
            '[renames.2048]\nA = "C"\nB = "C"\n',
            "[renames.2048]: Two teams renamed to C.",
        ),
    ],
)
def test_bad_renames_name_the_table_and_key(
    tmp_path: Path, body: str, reason: str
) -> None:
    path = _write(tmp_path / "s.toml", body)
    with pytest.raises(ConfigFileError) as exc:
        load_scheduler_config(path)
    assert str(exc.value) == f"{path}: {reason}"


# ---------------------------------------------------------------------------
# League-resolved checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weeks", [10, 16])
def test_check_weeks_accepts_conferences_range(weeks: int) -> None:
    check_weeks(CONFERENCES_LEAGUE, weeks)


@pytest.mark.parametrize("weeks", [8, 18, 11])
def test_check_weeks_rejects_outside_conferences_range(weeks: int) -> None:
    with pytest.raises(ConfigFileError, match="weeks"):
        check_weeks(CONFERENCES_LEAGUE, weeks)


@pytest.mark.parametrize("weeks", [14, 20])
def test_check_weeks_accepts_divisional_range(weeks: int) -> None:
    check_weeks(ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION, weeks)


@pytest.mark.parametrize("weeks", [12, 22])
def test_check_weeks_rejects_outside_divisional_range(weeks: int) -> None:
    with pytest.raises(ConfigFileError, match="weeks"):
        check_weeks(ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION, weeks)


@pytest.mark.parametrize("opening", [0, 3])
def test_check_opening_weeks_accepts(opening: int) -> None:
    check_opening_weeks(CONFERENCES_LEAGUE, 12, opening)


def test_check_opening_weeks_rejects_four_for_the_conferences_league() -> None:
    with pytest.raises(ConfigFileError, match="opening_nonconference_weeks"):
        check_opening_weeks(CONFERENCES_LEAGUE, 12, 4)


def test_resolve_rivalries_returns_team_pairs_in_listed_order() -> None:
    pairs = resolve_rivalries(
        CONFERENCES_LEAGUE, RivalriesConfig(pairs=CONFERENCES_RIVALRIES)
    )
    assert [(a.metro, b.metro) for a, b in pairs] == list(CONFERENCES_RIVALRIES)
    assert sum(1 for a, b in pairs if a.conference != b.conference) == 1


def test_resolve_rivalries_with_no_pairs_is_empty() -> None:
    assert resolve_rivalries(CONFERENCES_LEAGUE, RivalriesConfig()) == ()


@pytest.mark.parametrize(
    ("pairs", "message"),
    [
        pytest.param(
            CONFERENCES_RIVALRIES[:8],
            r"^\[rivalries\] pairs: Must list 9 pairs, got 8\.$",
            id="eight-pairs",
        ),
        pytest.param(
            (*CONFERENCES_RIVALRIES, ("Michigan", "USC")),
            r"^\[rivalries\] pairs: Must list 9 pairs, got 10\.$",
            id="ten-pairs",
        ),
        pytest.param(
            (*CONFERENCES_RIVALRIES[:8], ("Penn State", "Michigan")),
            r"^\[rivalries\] pairs: Must name every team once; \w[\w ]* repeats\.$",
            id="team-twice",
        ),
        pytest.param(
            (*CONFERENCES_RIVALRIES[:8], ("Penn State", "Nowhere")),
            r"^\[rivalries\] pairs: Unknown team: 'Nowhere'\. Valid: .+\.$",
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
            r"^\[rivalries\] pairs: Must have exactly one cross-conference pair, "
            r"got 3\.$",
            id="three-cross",
        ),
    ],
)
def test_resolve_rivalries_rejects(pairs, message: str) -> None:
    with pytest.raises(ConfigFileError, match=message):
        resolve_rivalries(CONFERENCES_LEAGUE, RivalriesConfig(pairs=pairs))


# ---------------------------------------------------------------------------
# Shipped files — every config/dev/ and config/release/ scheduler.toml
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SHIPPED_RULES, ids=shipped_id)
def test_shipped_rules_file_fits_its_league_shape(path: Path) -> None:
    # A rules file with rivalries is the conference league's; one without is a
    # divisional league's. Each must fit the test league of that shape.
    config = load_scheduler_config(path)
    league = (
        CONFERENCES_LEAGUE
        if config.rivalries.pairs
        else (ONE_PLAYOFF_TEAM_FROM_4_TEAM_DIVISION)
    )
    check_weeks(league, config.league.weeks)
    check_opening_weeks(
        league, config.league.weeks, config.phase2.opening_nonconference_weeks
    )
    resolve_rivalries(league, config.rivalries)


def test_shipped_file_sets_match_between_dev_and_release() -> None:
    # The two config twins ship the same rules files.
    by_folder = {
        folder: {
            p.relative_to(ROOT / "config" / folder)
            for p in SHIPPED_RULES
            if p.is_relative_to(ROOT / "config" / folder)
        }
        for folder in ("dev", "release")
    }
    assert by_folder["dev"] == by_folder["release"]
    assert len(by_folder["dev"]) == 2


def test_shipped_conference_league_rules_match_the_test_league() -> None:
    # The conference test league copies a shipped league; keep them in step.
    matches = [
        p
        for p in SHIPPED_RULES
        if load_scheduler_config(p).rivalries.pairs == CONFERENCES_RIVALRIES
    ]
    assert matches
    for path in matches:
        config = load_scheduler_config(path)
        assert config.league.weeks == 12
        assert config.difficulty.spread == 0.0
        assert config.phase2.max_consecutive_conference_home_or_away == 2
        assert config.phase2.opening_nonconference_weeks == 3
        assert config.phase2.require_home_balance_per_six_weeks is False
        assert config.phase2.require_home_away_streak_caps is False
        assert config.phase2.require_mixed_home_away_at_season_ends is False
