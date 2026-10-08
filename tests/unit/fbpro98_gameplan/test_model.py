from __future__ import annotations

import pytest

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
)

CLOCK_CATEGORIES = (11, 12)


def _empty_normals() -> tuple[PlayRef | None, ...]:
    return (None,) * GamePlan.NUMBER_NORMAL_PLAYS


def _make_custom(*, special_category: int = 1, play_category: int = 0) -> CustomPlayRef:
    return CustomPlayRef(
        filename="X.PLY",
        play_category=play_category,
        special_category=special_category,
        user_category=0,
    )


def _make_stock(*, special_category: int = 1, play_category: int = 0) -> StockPlayRef:
    return StockPlayRef(
        play_name="X",
        map_offset=0,
        map_size=0,
        play_category=play_category,
        special_category=special_category,
        user_category=0,
    )


def _specials(**slots: SpecialSlot) -> tuple[SpecialSlot, ...]:
    """Twelve empty slots, with `c<N>=SpecialSlot(...)` overriding category N."""
    out = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for key, slot in slots.items():
        out[int(key[1:]) - 1] = slot
    return tuple(out)


def _offense_specials(**slots: SpecialSlot) -> tuple[SpecialSlot, ...]:
    """Like `_specials`, but with the two stock clock plays an offense plan needs."""
    clock = {
        f"c{c}": SpecialSlot(stock=_make_stock(special_category=c, play_category=1))
        for c in CLOCK_CATEGORIES
    }
    return _specials(**{**clock, **slots})  # a test's c11/c12 overrides the default


def _defense(
    normals: tuple[PlayRef | None, ...] | None = None,
    specials: tuple[SpecialSlot, ...] | None = None,
) -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals() if normals is None else normals,
        special_plays=_specials() if specials is None else specials,
    )


def _offense(
    normals: tuple[PlayRef | None, ...] | None = None,
    specials: tuple[SpecialSlot, ...] | None = None,
) -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=_empty_normals() if normals is None else normals,
        special_plays=_offense_specials() if specials is None else specials,
    )


# ── slot counts ───────────────────────────────────────────────────────────────


def test_special_plays_has_12_entries():
    assert GamePlan.NUMBER_SPECIAL_CATEGORIES == 12
    assert len(_defense().special_plays) == 12


@pytest.mark.parametrize("count", [11, 13])
def test_special_plays_wrong_length_raises(count: int):
    with pytest.raises(ValueError, match="special_plays must have exactly 12"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=tuple(SpecialSlot() for _ in range(count)),
        )


def test_normal_plays_wrong_length_raises():
    with pytest.raises(ValueError, match="normal_plays must have exactly"):
        _defense(normals=(None, None))


# ── clock categories (11-12): stock-only, offense-only ────────────────────────


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_custom_play_in_clock_category_raises(category: int):
    custom = _make_custom(special_category=category, play_category=1)
    with pytest.raises(ValueError, match=f"Special category {category} is stock-only"):
        _offense(
            specials=_offense_specials(**{f"c{category}": SpecialSlot(custom=custom)})
        )


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_offense_missing_clock_play_raises(category: int):
    with pytest.raises(
        ValueError, match=f"require a stock play in special category {category}"
    ):
        _offense(specials=_offense_specials(**{f"c{category}": SpecialSlot()}))


def test_offense_without_any_clock_plays_raises():
    with pytest.raises(ValueError, match="require a stock play in special category 11"):
        _offense(specials=_specials())


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_defense_with_clock_play_raises(category: int):
    stock = _make_stock(special_category=category, play_category=0)
    with pytest.raises(
        ValueError, match=f"must not have a play in special category {category}"
    ):
        _defense(specials=_specials(**{f"c{category}": SpecialSlot(stock=stock)}))


def test_custom_special_categories_are_1_to_10():
    assert list(GamePlan.CUSTOM_SPECIAL_CATEGORIES) == list(range(1, 11))


# ── slot typing and category alignment ────────────────────────────────────────


def test_stock_in_custom_field_raises():
    bad = SpecialSlot(custom=_make_stock())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="custom must be CustomPlayRef"):
        _defense(specials=_specials(c1=bad))


def test_custom_in_stock_field_raises():
    bad = SpecialSlot(stock=_make_custom())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="stock must be StockPlayRef"):
        _defense(specials=_specials(c1=bad))


def test_custom_category_mismatch_raises():
    slot = SpecialSlot(custom=_make_custom(special_category=5))
    with pytest.raises(
        ValueError, match="Special category 2: custom play has special_category=5"
    ):
        _defense(specials=_specials(c2=slot))


def test_stock_category_mismatch_raises():
    slot = SpecialSlot(stock=_make_stock(special_category=5))
    with pytest.raises(
        ValueError, match="Special category 3: stock play has special_category=5"
    ):
        _defense(specials=_specials(c3=slot))


# ── views ─────────────────────────────────────────────────────────────────────


def test_custom_special_plays_has_10_entries():
    assert len(_defense().custom_special_plays) == 10


def test_custom_special_plays_picks_custom_of_categories_1_to_10():
    custom = _make_custom(special_category=1)
    stock = _make_stock(special_category=3)
    gameplan = _defense(
        specials=_specials(c1=SpecialSlot(custom=custom), c3=SpecialSlot(stock=stock))
    )
    assert gameplan.custom_special_plays[0] is custom
    assert all(p is None for p in gameplan.custom_special_plays[1:])
    assert gameplan.special_plays[2].stock is stock


# ── with_custom_special_plays ─────────────────────────────────────────────────


def test_with_custom_special_plays_preserves_stock():
    stock_a = _make_stock(special_category=1)
    stock_b = _make_stock(special_category=2)
    gameplan = _defense(
        specials=_specials(c1=SpecialSlot(stock=stock_a), c2=SpecialSlot(stock=stock_b))
    )
    new_a = _make_custom(special_category=1)
    new_e = _make_custom(special_category=5)

    updated = gameplan.with_custom_special_plays([new_a, None, new_e])

    assert updated.special_plays[0] == SpecialSlot(custom=new_a, stock=stock_a)
    assert updated.special_plays[1] == SpecialSlot(stock=stock_b)
    assert updated.special_plays[4] == SpecialSlot(custom=new_e)


def test_with_custom_special_plays_preserves_clock_slots():
    gameplan = _offense()
    updated = gameplan.with_custom_special_plays(
        [_make_custom(special_category=2, play_category=1)]
    )
    assert updated.special_plays[10] == gameplan.special_plays[10]
    assert updated.special_plays[11] == gameplan.special_plays[11]


def test_with_custom_special_plays_clears_uncovered_customs():
    gameplan = _defense(
        specials=_specials(c4=SpecialSlot(custom=_make_custom(special_category=4)))
    )
    updated = gameplan.with_custom_special_plays([_make_custom(special_category=2)])
    placed = updated.custom_special_plays
    assert placed[1] is not None and placed[1].special_category == 2
    assert all(p is None for i, p in enumerate(placed) if i != 1)


def test_with_custom_special_plays_order_independent():
    gameplan = _defense()
    a = _make_custom(special_category=3)
    b = _make_custom(special_category=7)
    c = _make_custom(special_category=1)
    assert (
        gameplan.with_custom_special_plays([a, b, c]).custom_special_plays
        == gameplan.with_custom_special_plays([c, b, a]).custom_special_plays
    )


def test_with_custom_special_plays_rejects_stock_via_post_init():
    with pytest.raises(ValueError, match="custom must be CustomPlayRef"):
        _defense().with_custom_special_plays([_make_stock()])  # type: ignore[list-item]


@pytest.mark.parametrize("category", [1, 10])
def test_with_custom_special_plays_accepts_range_ends(category: int):
    updated = _defense().with_custom_special_plays(
        [_make_custom(special_category=category)]
    )
    assert updated.special_plays[category - 1].custom is not None


@pytest.mark.parametrize("category", [0, 11])
def test_with_custom_special_plays_out_of_range_category_raises(category: int):
    with pytest.raises(ValueError, match=r"must be 1\.\.10"):
        _defense().with_custom_special_plays([_make_custom(special_category=category)])


def test_with_custom_special_plays_duplicate_category_raises():
    with pytest.raises(
        ValueError, match="Two custom special plays target special_category=3"
    ):
        _defense().with_custom_special_plays(
            [_make_custom(special_category=3), _make_custom(special_category=3)]
        )


# ── side-of-ball parity ───────────────────────────────────────────────────────


def test_offensive_play_in_defensive_gameplan_raises():
    normals: list[PlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=0, play_category=1)  # odd = offensive
    with pytest.raises(ValueError, match=r"Normal slot 0:.*profile_type is DEFENSE"):
        _defense(normals=tuple(normals))


def test_defensive_play_in_offensive_gameplan_raises():
    normals: list[PlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=0, play_category=0)  # even = defensive
    with pytest.raises(ValueError, match="profile_type is OFFENSE"):
        _offense(normals=tuple(normals))


def test_defensive_special_play_in_offensive_gameplan_raises():
    slot = SpecialSlot(custom=_make_custom(special_category=1, play_category=0))
    with pytest.raises(
        ValueError, match=r"Special category 1 custom:.*profile_type is OFFENSE"
    ):
        _offense(specials=_offense_specials(c1=slot))


def test_defensive_clock_play_in_offensive_gameplan_raises():
    slot = SpecialSlot(stock=_make_stock(special_category=11, play_category=0))
    with pytest.raises(
        ValueError, match=r"Special category 11 stock:.*profile_type is OFFENSE"
    ):
        _offense(specials=_offense_specials(c11=slot))


def test_special_teams_play_in_normal_slot_raises():
    normals: list[PlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=2, play_category=0)
    with pytest.raises(ValueError, match="Normal slot 0 contains a special-teams play"):
        _defense(normals=tuple(normals))


# ── misc ──────────────────────────────────────────────────────────────────────


def test_is_offense_and_is_defense_match_profile_type():
    offense = _offense()
    assert offense.is_offense is True
    assert offense.is_defense is False
    defense = _defense()
    assert defense.is_offense is False
    assert defense.is_defense is True


def test_with_normal_plays_too_many_raises():
    with pytest.raises(ValueError, match="Expected at most 64 normal plays"):
        _defense().with_normal_plays([_make_custom(special_category=0)] * 65)


def test_with_normal_plays_returns_new_instance():
    gameplan = _defense()
    updated = gameplan.with_normal_plays([_make_custom(special_category=0)])
    assert updated is not gameplan
    assert gameplan.normal_plays[0] is None
    assert updated.normal_plays[0] is not None


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("plays\\Offense\\PSR\\OR45RL01.PLY", "OR45RL01"),
        ("X.ply", "X"),
        ("X", "X"),
        ("dir\\sub\\PLAY.PLY", "PLAY"),
    ],
)
def test_custom_play_name_extracts_stem(filename: str, expected: str) -> None:
    play = CustomPlayRef(
        filename=filename, play_category=0, special_category=0, user_category=0
    )
    assert play.name == expected
