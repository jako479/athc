"""`rule_warnings`: the names a playpool rules file lists under include / exclude
checked against the pool they will be applied to."""

from __future__ import annotations

import pytest

from athc.playpool import (
    DefensivePlay,
    OffensivePlay,
    PlayPool,
    SpecialTeamsPlay,
    build_rules,
    rule_warnings,
)
from tests.unit.playpool.conftest import MakePlay

RUN_LEFT, PASS_SHORT_RIGHT = 0x05, 0x03


@pytest.fixture
def pool(make_play: MakePlay) -> PlayPool:
    pool = PlayPool("root")
    pool.add(OffensivePlay("RUNNER", make_play("RUNNER", user_category=RUN_LEFT)))
    pool.add(
        OffensivePlay("PASSER", make_play("PASSER", user_category=PASS_SHORT_RIGHT))
    )
    pool.add(DefensivePlay("DEFENDER", make_play("DEFENDER", play_category=0x00)))
    pool.add(SpecialTeamsPlay("KICKER", make_play("KICKER", special_category=2)))
    return pool


def _rules(section: str, **lists: list[str]):
    return build_rules({section: lists})


def test_clean_rules_give_no_warnings(pool: PlayPool) -> None:
    rules = build_rules(
        {
            "TimedPass": {"include": ["PASSER"], "exclude": ["passer2"]},
            "RolloutPass": {"include": ["PASSER"]},
            "QBRun": {"include": ["RUNNER"]},
        }
    )
    pool.add(
        OffensivePlay("passer2", pool.find_by_name("PASSER").play_file)  # type: ignore[union-attr]
    )
    assert rule_warnings(pool, rules) == []


@pytest.mark.parametrize("key", ["include", "exclude"])
def test_name_not_in_the_pool(pool: PlayPool, key: str) -> None:
    rules = _rules("TimedPass", **{key: ["NOPE"]})
    assert rule_warnings(pool, rules) == [
        f"[TimedPass] {key} 'NOPE' is not in the play pool"
    ]


@pytest.mark.parametrize(
    ("section", "name", "kind"),
    [
        ("TimedPass", "RUNNER", "run"),
        ("RolloutPass", "RUNNER", "run"),
        ("QBRun", "PASSER", "pass"),
        ("TimedPass", "DEFENDER", "defensive"),
        ("QBRun", "KICKER", "special-teams"),
    ],
)
def test_wrong_side_is_reported(
    pool: PlayPool, section: str, name: str, kind: str
) -> None:
    rules = _rules(section, include=[name])
    assert rule_warnings(pool, rules) == [
        f"[{section}] include '{name}' is a {kind} play; it has no effect"
    ]


def test_exclude_on_the_wrong_side_is_reported(pool: PlayPool) -> None:
    rules = _rules("QBRun", exclude=["PASSER"])
    assert rule_warnings(pool, rules) == [
        "[QBRun] exclude 'PASSER' is a pass play; it has no effect"
    ]


@pytest.mark.parametrize("name", ["RUNNER", "NOPE"])
def test_name_in_both_include_and_exclude_reported_once(
    pool: PlayPool, name: str
) -> None:
    # Once whether or not the name is in the pool: the other checks skip it.
    rules = _rules("QBRun", include=[name], exclude=[name])
    assert rule_warnings(pool, rules) == [
        f"[QBRun] '{name}' is in both include and exclude; exclude wins"
    ]


def test_warnings_are_sorted_by_section_then_name(pool: PlayPool) -> None:
    rules = build_rules(
        {
            "QBRun": {"include": ["ZZZ", "AAA"]},
            "TimedPass": {"include": ["MMM"]},
        }
    )
    assert rule_warnings(pool, rules) == [
        "[TimedPass] include 'MMM' is not in the play pool",
        "[QBRun] include 'AAA' is not in the play pool",
        "[QBRun] include 'ZZZ' is not in the play pool",
    ]
