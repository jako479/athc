"""The CP-SAT models must not drift: one pinned checksum pair per league.

A seed's schedule is a function of the exact model, so both phase models for
each golden league are hashed and pinned here (fast; no solve of phase 2). The
slow golden test in tests/integration is the end-to-end proof. Re-pin only after
an intentional model change, together with that league's goldens.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from athc.scheduler.config import load_scheduler_config, resolve_rivalries
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.matchup_builder import MatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder
from tests.integration.league_files import CASE_BY_LEAGUE, case_league

# (league name, phase-1 sha256, phase-2 sha256)
PINNED = [
    pytest.param(
        "divisions",
        "ea944d39a327f6e4e70d74e09f593edc4ffd340118c4f8240a5a8a881f82d34d",
        "41d55300fdfacfb76dc9535fabef867d0a5a610b4a7f32722054197fc77fbaf0",
        id="divisions",
    ),
    pytest.param(
        "conferences",
        "85066772f3f2a71093b82d0b1f23a1f44b0ca437ab7088c5b700cec00b1bb9ae",
        "f53c3b57a8efce4e75941a4146ab6d69747dc61a900fbbd17e36d9854496faa7",
        id="conferences",
    ),
]


def _sha256(model: cp_model.CpModel) -> str:
    # This ortools version's CpModelProto is a pybind wrapper with no
    # SerializeToString; export_to_file writes the same binary proto bytes.
    with tempfile.TemporaryDirectory() as tmp_dir:
        proto_path = Path(tmp_dir) / "model.pb"
        if not model.export_to_file(str(proto_path)):
            raise RuntimeError("failed to export CP-SAT model for the checksum")
        return hashlib.sha256(proto_path.read_bytes()).hexdigest()


@pytest.mark.parametrize(("league_name", "phase1", "phase2"), PINNED)
def test_phase_models_are_unchanged(
    league_name: str, phase1: str, phase2: str, tmp_path: Path
) -> None:
    case = CASE_BY_LEAGUE[league_name]
    league = case_league(case, tmp_path)
    config = load_scheduler_config(case.rules)
    rivalries = resolve_rivalries(league, config.rivalries)

    builder = MatchupBuilder(
        league,
        weeks=config.league.weeks,
        rivalries=rivalries,
        spread=config.difficulty.spread,
        phase1_time_limit=config.solver.phase1_time_limit,
        workers=config.solver.solver_workers,  # the frozen count, not "auto"
        seed=0,
    )
    fixed = builder._same_place_pairs() | builder._rivalry_pairs()
    actual1 = _sha256(builder._nonconference_model(fixed).model)
    plan = builder.build_matchup_plan()

    schedule_builder = ScheduleBuilder(
        league,
        SchedulerError,
        config.phase2,
        weeks=config.league.weeks,
        rivalries=rivalries,
        rotate_rivalry_home_by_season=config.rivalries.rotate_home_by_season,
        season=case.season,
    )
    schedule_builder._populate_model(plan.matchups)
    actual2 = _sha256(schedule_builder.model)

    assert (actual1, actual2) == (phase1, phase2), (
        f"{league_name} model changed: phase1={actual1} phase2={actual2}"
    )
