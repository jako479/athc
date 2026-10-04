"""The PNFL CP-SAT models must not drift.

A seed's schedule is a function of the exact model, so both phase models for
the golden league are hashed and pinned here (fast; no solve of phase 2). The
slow golden test in tests/integration is the end-to-end proof. Re-pin only
after an intentional PNFL model change, together with the goldens.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from ortools.sat.python import cp_model

from athc.scheduler.config import load_league, load_scheduler_config
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.fixed_cpsat_builder import FixedCpsatMatchupBuilder
from athc.scheduler.schedulers.schedule_builder import ScheduleBuilder

DATA = Path(__file__).resolve().parents[2] / "integration" / "data"
GOLDEN_LEAGUE = DATA / "league.ini"
GOLDEN_RULES = DATA / "PNFL.scheduler.toml"

PHASE1_SHA256 = "fca475dd405c803ade596bfda5422049b651e99e679e24f315f05813ddcd64a7"
PHASE2_SHA256 = "ef93b4a3f93b7656a87479294cfa914c8545e83832661b5d19e23226d4c2e60c"


def _sha256(model: cp_model.CpModel) -> str:
    # This ortools version's CpModelProto is a pybind wrapper with no
    # SerializeToString; export_to_file writes the same binary proto bytes.
    with tempfile.TemporaryDirectory() as tmp_dir:
        proto_path = Path(tmp_dir) / "model.pb"
        if not model.export_to_file(str(proto_path)):
            raise RuntimeError("failed to export CP-SAT model for fingerprinting")
        return hashlib.sha256(proto_path.read_bytes()).hexdigest()


def test_pnfl_phase_models_are_unchanged() -> None:
    league = load_league(GOLDEN_LEAGUE)
    config = load_scheduler_config(GOLDEN_RULES)

    builder = FixedCpsatMatchupBuilder(
        league,
        weeks=config.league.weeks,
        spread=config.difficulty.spread,
        phase1_time_limit=config.solver.phase1_time_limit,
        seed=0,
    )
    phase1 = _sha256(builder._nonconference_model(builder._fixed_place_pairs()).model)
    plan = builder.build_matchup_plan()

    schedule_builder = ScheduleBuilder(
        league, SchedulerError, config.phase2, weeks=config.league.weeks
    )
    schedule_builder._populate_model(plan.matchups)
    phase2 = _sha256(schedule_builder.model)

    assert (phase1, phase2) == (PHASE1_SHA256, PHASE2_SHA256), (
        f"PNFL model changed: phase1={phase1} phase2={phase2}"
    )
