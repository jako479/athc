"""Tests for athc.fbpro98_lg2.model."""

import dataclasses

import pytest

from athc.fbpro98_lg2 import FilePair, HalfFiles, Lg2File, TeamFiles


def _team() -> TeamFiles:
    return TeamFiles(
        first_half=HalfFiles(
            offense=FilePair(profile="P\\O1.prf", gameplan="P\\O1.pln"),
            defense=FilePair(profile="P\\D1.prf", gameplan="P\\D1.pln"),
        ),
        second_half=HalfFiles(
            offense=FilePair(profile="P\\O2.prf", gameplan="P\\O2.pln"),
            defense=FilePair(profile="P\\D2.prf", gameplan="P\\D2.pln"),
        ),
    )


def test_nested_access():
    lg2 = Lg2File(teams=(_team(),))
    assert lg2.teams[0].first_half.offense.profile == "P\\O1.prf"
    assert lg2.teams[0].second_half.defense.gameplan == "P\\D2.pln"


def test_frozen():
    pair = FilePair(profile="a.prf", gameplan="a.pln")
    with pytest.raises(dataclasses.FrozenInstanceError):
        pair.profile = "b.prf"  # type: ignore[misc]
