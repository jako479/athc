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

from athc.scheduler.config import load_league, load_scheduler_config, resolve_rivalries
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.matchup_builder import MatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder

DATA = Path(__file__).resolve().parents[2] / "integration" / "data"

# (league name, season, phase-1 sha256, phase-2 sha256)
PINNED = [
    pytest.param(
        "divisions",
        2026,
        "fca475dd405c803ade596bfda5422049b651e99e679e24f315f05813ddcd64a7",
        "ef93b4a3f93b7656a87479294cfa914c8545e83832661b5d19e23226d4c2e60c",
        id="divisions",
    ),
    pytest.param(
        "conferences",
        2029,
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


@pytest.mark.parametrize(("league_name", "season", "phase1", "phase2"), PINNED)
def test_phase_models_are_unchanged(
    league_name: str, season: int, phase1: str, phase2: str
) -> None:
    league = load_league(DATA / f"{league_name}.{season}.ini")
    config = load_scheduler_config(DATA / f"{league_name}.scheduler.toml")
    rivalries = resolve_rivalries(league, config.rivalries)

    builder = MatchupBuilder(
        league,
        weeks=config.league.weeks,
        rivalries=rivalries,
        spread=config.difficulty.spread,
        phase1_time_limit=config.solver.phase1_time_limit,
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
        season=season,
    )
    schedule_builder._populate_model(plan.matchups)
    actual2 = _sha256(schedule_builder.model)

    assert (actual1, actual2) == (phase1, phase2), (
        f"{league_name} model changed: phase1={actual1} phase2={actual2}"
    )
