"""Unit tests for the PDB binary parser."""

from __future__ import annotations

import ctypes
import json
from pathlib import Path

import pytest

from athc.pdbtoexcel.pdb import PDB, PLAY_DATA, InvalidPDBError
from tests.unit.pdbtoexcel.conftest import (
    PLAYS_SNAPSHOT,
    REAL_PDB,
    make_play_data,
    make_pool,
    make_record,
    write_pdb,
)

_FIELDS = [f[0] for f in PLAY_DATA._fields_ if f[0] not in ("team_name", "play_name")]


def _normalize(pdb: PDB) -> dict:
    out: dict = {}
    for play_type, plays in pdb.plays.items():
        out[play_type.name] = {
            f"{team}|{name}": {fn: int(getattr(pd, fn)) for fn in _FIELDS}
            for (team, name), pd in sorted(plays.items())
        }
    return out


# ── real fixture ──────────────────────────────────────────────────────────────


def test_real_pdb_matches_snapshot() -> None:
    expected = json.loads(PLAYS_SNAPSHOT.read_text(encoding="utf-8"))
    assert _normalize(PDB(str(REAL_PDB))) == expected


def test_real_pdb_tendencies_and_samples() -> None:
    pdb = PDB(str(REAL_PDB))
    assert len(pdb.tendencies) == 23
    assert ("Pittsburgh", "SF62wish") in pdb.plays[PLAY_DATA.PLAY_TYPE.RUN]
    assert ("Chicago", "KC2AFLYZ") in pdb.plays[PLAY_DATA.PLAY_TYPE.PASS]
    assert ("Minnesota", "LV32rmQ2") in pdb.plays[PLAY_DATA.PLAY_TYPE.DEFENSE]


# ── structure / parsing ───────────────────────────────────────────────────────


def test_invalid_data_type_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.pdb"
    path.write_bytes(bytes([9]) + b"\x00" * ctypes.sizeof(PLAY_DATA))
    with pytest.raises(InvalidPDBError):
        PDB(str(path))


def test_duplicate_play_merges(tmp_path: Path) -> None:
    a = make_play_data(
        PLAY_DATA.PLAY_TYPE.RUN, "Team", "RUNPLAY", play_count=3, total_yards=12
    )
    b = make_play_data(
        PLAY_DATA.PLAY_TYPE.RUN, "Team", "RUNPLAY", play_count=2, total_yards=8
    )
    pdb = PDB(str(write_pdb(tmp_path / "dup.pdb", plays=[a, b])))
    merged = pdb.plays[PLAY_DATA.PLAY_TYPE.RUN][("Team", "RUNPLAY")]
    assert (int(merged.play_count), int(merged.total_yards)) == (5, 20)


def test_renamed_play_is_rewritten(tmp_path: Path) -> None:
    play = make_play_data(PLAY_DATA.PLAY_TYPE.PASS, "Team", "WR47PT01", play_count=1)
    pdb = PDB(str(write_pdb(tmp_path / "ren.pdb", plays=[play])))
    assert ("Team", "WR27PT01") in pdb.plays[PLAY_DATA.PLAY_TYPE.PASS]
    assert ("Team", "WR47PT01") not in pdb.plays[PLAY_DATA.PLAY_TYPE.PASS]


def test_clock_plays_skipped(tmp_path: Path) -> None:
    play = make_play_data(PLAY_DATA.PLAY_TYPE.RUN, "Team", "RUNCLOCK", play_count=1)
    pdb = PDB(str(write_pdb(tmp_path / "clock.pdb", plays=[play])))
    assert pdb.plays[PLAY_DATA.PLAY_TYPE.RUN] == {}


def test_play_data_iadd_and_is_valid() -> None:
    a = make_play_data(
        PLAY_DATA.PLAY_TYPE.RUN, "T", "P", play_count=3, sacks=1, interceptions=2
    )
    a += make_play_data(
        PLAY_DATA.PLAY_TYPE.RUN, "T", "P", play_count=4, sacks=2, interceptions=1
    )
    assert (int(a.play_count), int(a.sacks), int(a.interceptions)) == (7, 3, 3)
    assert a.is_valid()
    assert not PLAY_DATA().is_valid()  # empty names


# ── convert_invalid_play_data ─────────────────────────────────────────────────


def test_convert_invalid_moves_misclassified_run_to_pass(tmp_path: Path) -> None:
    # PDB records "PASSPLAY" as a RUN, but the pool says it's a pass play.
    play = make_play_data(
        PLAY_DATA.PLAY_TYPE.RUN, "Team", "PASSPLAY", play_count=5, total_yards=-10
    )
    pdb = PDB(str(write_pdb(tmp_path / "mis.pdb", plays=[play])))
    pool = make_pool(
        [make_record("PASSPLAY", play_category=0x01, user_category=0x03)]
    )  # offense pass

    pdb.convert_invalid_play_data(pool)

    assert ("Team", "PASSPLAY") not in pdb.plays[PLAY_DATA.PLAY_TYPE.RUN]
    moved = pdb.plays[PLAY_DATA.PLAY_TYPE.PASS][("Team", "PASSPLAY")]
    assert int(moved.play_count) == 5
    assert (
        int(moved.sacks) == 5
    )  # all-negative yards on a misclassified run become sacks
