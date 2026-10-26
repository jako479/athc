from __future__ import annotations

import copy

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


def _empty_normals() -> list[PlayRef | None]:
    return [None] * GamePlan.NUMBER_NORMAL_PLAYS


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


def _specials(**slots: SpecialSlot) -> list[SpecialSlot]:
    """Twelve empty slots, with `c<N>=SpecialSlot(...)` overriding category N."""
    out = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for key, slot in slots.items():
        out[int(key[1:]) - 1] = slot
    return out


def _offense_specials(**slots: SpecialSlot) -> list[SpecialSlot]:
    """Like `_specials`, but with the two stock clock plays an offense plan needs."""
    clock = {
        f"c{c}": SpecialSlot(stock=_make_stock(special_category=c, play_category=1))
        for c in CLOCK_CATEGORIES
    }
    return _specials(**{**clock, **slots})  # a test's c11/c12 overrides the default


def _defense(
    normals: list[PlayRef | None] | None = None,
    specials: list[SpecialSlot] | None = None,
) -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals() if normals is None else normals,
        special_plays=_specials() if specials is None else specials,
    )


def _offense(
    normals: list[PlayRef | None] | None = None,
    specials: list[SpecialSlot] | None = None,
) -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=_empty_normals() if normals is None else normals,
        special_plays=_offense_specials() if specials is None else specials,
    )


def _rejects(gameplan: GamePlan, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        gameplan.validate()


# ── editing ───────────────────────────────────────────────────────────────────


def test_edit_by_assignment_then_validate():
    gameplan = _defense()
    play = _make_custom(special_category=0)
    gameplan.normal_plays[0] = play
    gameplan.special_plays[2].stock = _make_stock(special_category=3)
    gameplan.validate()
    expected = _defense()
    expected.normal_plays[0] = play
    expected.special_plays[2].stock = _make_stock(special_category=3)
    assert gameplan == expected


def test_deep_copy_edits_apart():
    original = _defense()
    edited = copy.deepcopy(original)
    edited.normal_plays[0] = _make_custom(special_category=0)
    assert original.normal_plays[0] is None


# ── slot counts ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("count", [11, 13])
def test_special_plays_wrong_length_raises(count: int):
    gameplan = _defense(specials=[SpecialSlot() for _ in range(count)])
    _rejects(gameplan, "special_plays must have exactly 12")


@pytest.mark.parametrize("count", [63, 65])
def test_normal_plays_wrong_length_raises(count: int):
    normals: list[PlayRef | None] = [None] * count
    _rejects(_defense(normals=normals), "normal_plays must have exactly 64")


# ── clock categories (11-12): stock-only, offense-only ────────────────────────


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_custom_play_in_clock_category_raises(category: int):
    custom = _make_custom(special_category=category, play_category=1)
    gameplan = _offense(
        specials=_offense_specials(**{f"c{category}": SpecialSlot(custom=custom)})
    )
    _rejects(gameplan, f"Special category {category} is stock-only")


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_offense_missing_clock_play_raises(category: int):
    gameplan = _offense(specials=_offense_specials(**{f"c{category}": SpecialSlot()}))
    _rejects(
        gameplan,
        f"Offense game plans require a stock play in special category {category}",
    )


@pytest.mark.parametrize("category", CLOCK_CATEGORIES)
def test_defense_with_clock_play_raises(category: int):
    stock = _make_stock(special_category=category, play_category=0)
    gameplan = _defense(
        specials=_specials(**{f"c{category}": SpecialSlot(stock=stock)})
    )
    _rejects(
        gameplan,
        f"Defense game plans must not have a play in special category {category}",
    )


# ── slot typing and category alignment ────────────────────────────────────────


def test_stock_in_custom_field_raises():
    bad = SpecialSlot(custom=_make_stock())  # type: ignore[arg-type]
    _rejects(_defense(specials=_specials(c1=bad)), "custom must be CustomPlayRef")


def test_custom_in_stock_field_raises():
    bad = SpecialSlot(stock=_make_custom())  # type: ignore[arg-type]
    _rejects(_defense(specials=_specials(c1=bad)), "stock must be StockPlayRef")


def test_custom_category_mismatch_raises():
    slot = SpecialSlot(custom=_make_custom(special_category=5))
    _rejects(
        _defense(specials=_specials(c2=slot)),
        "Special category 2: custom play has special_category=5",
    )


def test_stock_category_mismatch_raises():
    slot = SpecialSlot(stock=_make_stock(special_category=5))
    _rejects(
        _defense(specials=_specials(c3=slot)),
        "Special category 3: stock play has special_category=5",
    )


# ── views ─────────────────────────────────────────────────────────────────────


def test_custom_special_plays_has_10_entries():
    assert len(_defense().custom_special_plays) == 10


def test_custom_special_plays_picks_custom_of_categories_1_to_10():
    custom = _make_custom(special_category=1)
    stock = _make_stock(special_category=3)
    gameplan = _defense(
        specials=_specials(c1=SpecialSlot(custom=custom), c3=SpecialSlot(stock=stock))
    )
    assert gameplan.custom_special_plays == [custom, *[None] * 9]
    assert gameplan.special_plays[2] == SpecialSlot(stock=stock)


# ── side-of-ball parity ───────────────────────────────────────────────────────


def test_offensive_play_in_defensive_gameplan_raises():
    normals = _empty_normals()
    normals[0] = _make_custom(special_category=0, play_category=1)  # odd = offensive
    _rejects(_defense(normals=normals), r"Normal slot 0:.*profile_type is DEFENSE")


def test_defensive_play_in_offensive_gameplan_raises():
    normals = _empty_normals()
    normals[0] = _make_custom(special_category=0, play_category=0)  # even = defensive
    _rejects(_offense(normals=normals), "profile_type is OFFENSE")


def test_defensive_special_play_in_offensive_gameplan_raises():
    slot = SpecialSlot(custom=_make_custom(special_category=1, play_category=0))
    _rejects(
        _offense(specials=_offense_specials(c1=slot)),
        r"Special category 1 custom:.*profile_type is OFFENSE",
    )


def test_defensive_clock_play_in_offensive_gameplan_raises():
    slot = SpecialSlot(stock=_make_stock(special_category=11, play_category=0))
    _rejects(
        _offense(specials=_offense_specials(c11=slot)),
        r"Special category 11 stock:.*profile_type is OFFENSE",
    )


def test_special_play_in_normal_slot_raises():
    normals = _empty_normals()
    normals[0] = _make_custom(special_category=2, play_category=0)
    _rejects(_defense(normals=normals), "Normal slot 0 contains a special play")


# ── field widths ──────────────────────────────────────────────────────────────


def _with_normal(play: PlayRef) -> GamePlan:
    normals = _empty_normals()
    normals[0] = play
    return _defense(normals=normals)


def _with_stock(**fields: object) -> GamePlan:
    stock = StockPlayRef(
        play_name="RUNRIGHT",
        map_offset=0,
        map_size=0,
        play_category=0,
        special_category=0,
        user_category=0,
    )
    for name, value in fields.items():
        setattr(stock, name, value)
    return _with_normal(stock)


@pytest.mark.parametrize("value", [-1, 2])
def test_validate_rejects_a_profile_type_past_the_limits(value: int):
    gameplan = _defense()
    gameplan.profile_type = value  # type: ignore[assignment]
    _rejects(gameplan, f"profile_type: Must be 0 or 1, got {value}")


def test_validate_accepts_a_category_byte_of_0():
    play = _make_custom(special_category=0)  # defense Run Right: 0x00
    _with_normal(play).validate()


def test_validate_accepts_a_category_byte_of_255():
    # Offense User Specific is 0xFF, the highest byte and a known category.
    play = _make_custom(special_category=0, play_category=1)
    play.user_category = 0xFF
    normals = _empty_normals()
    normals[0] = play
    _offense(normals=normals).validate()


def test_validate_rejects_a_category_byte_past_255():
    play = _make_custom(special_category=0)
    play.user_category = 256
    _rejects(_with_normal(play), "Normal slot 0: user_category: Must be 0-255, got 256")


def test_validate_rejects_a_category_byte_below_0():
    play = _make_custom(special_category=0)
    play.user_category = -1
    _rejects(_with_normal(play), "Normal slot 0: user_category: Must be 0-255, got -1")


def test_validate_rejects_an_unrecognized_category():
    play = _make_custom(special_category=0)
    play.user_category = 0x3E  # no defense category has code 0x3E
    _rejects(
        _with_normal(play),
        r"Normal slot 0: Unrecognized play category \(play_category=0x00, "
        r"special_category=0x00, user_category=0x3E\)",
    )


def test_validate_rejects_a_non_ascii_filename():
    play = _make_custom(special_category=0)
    play.filename = "é.PLY"
    _rejects(_with_normal(play), "Normal slot 0: filename: Must be ASCII")


def test_validate_rejects_a_nul_in_a_filename():
    play = _make_custom(special_category=0)
    play.filename = "A\x00.PLY"
    _rejects(_with_normal(play), "Normal slot 0: filename: Must not contain NUL")


def test_validate_accepts_an_8_character_stock_play_name():
    _with_stock(play_name="A" * 8).validate()


def test_validate_rejects_a_stock_play_name_over_8():
    _rejects(
        _with_stock(play_name="A" * 9),
        "Normal slot 0: play_name: Must be at most 8 characters, got 9",
    )


def test_validate_rejects_a_non_ascii_stock_play_name():
    _rejects(_with_stock(play_name="é"), "Normal slot 0: play_name: Must be ASCII")


def test_validate_accepts_map_offset_and_size_at_their_maximum():
    _with_stock(map_offset=0xFFFF_FFFF, map_size=0xFFFF).validate()


def test_validate_rejects_map_offset_past_u32():
    _rejects(
        _with_stock(map_offset=0x1_0000_0000),
        "Normal slot 0: map_offset: Must be 0-4294967295, got 4294967296",
    )


def test_validate_rejects_map_size_past_u16():
    _rejects(
        _with_stock(map_size=0x1_0000),
        "Normal slot 0: map_size: Must be 0-65535, got 65536",
    )


def test_validate_rejects_other_audible_bytes():
    gameplan = _defense()
    gameplan.audible = b"\x00\x01\x02\x04"
    _rejects(gameplan, "audible: Must be 00 01 02 03, got 00 01 02 04")


def test_validate_rejects_another_map_filename():
    gameplan = _defense()
    gameplan.map_filename = "STOCK97.MAP"
    _rejects(gameplan, "map_filename: Must be STOCK98.MAP, got STOCK97.MAP")


# The second record's offset: the table (172 bytes), then the first record
# (a 4-byte header, the filename and its NUL).
_TABLE = 172
_HEADER = 5


def test_validate_accepts_a_record_offset_at_u16():
    normals = _empty_normals()
    normals[0] = CustomPlayRef("A" * (0xFFFF - _TABLE - _HEADER), 0, 0, 0)
    normals[1] = _make_custom(special_category=0)
    _defense(normals=normals).validate()


def test_validate_rejects_a_record_offset_past_u16():
    normals = _empty_normals()
    normals[0] = CustomPlayRef("A" * (0xFFFF - _TABLE - _HEADER + 1), 0, 0, 0)
    normals[1] = _make_custom(special_category=0)
    _rejects(
        _defense(normals=normals),
        "Normal slot 1: Record offset must be at most 65535, got 65536",
    )


# ── misc ──────────────────────────────────────────────────────────────────────


def test_is_offense_and_is_defense_match_profile_type():
    offense = _offense()
    assert offense.is_offense is True
    assert offense.is_defense is False
    defense = _defense()
    assert defense.is_offense is False
    assert defense.is_defense is True


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


def test_stock_play_name_is_its_play_name() -> None:
    play = StockPlayRef(
        play_name="RUNCLOCK",
        map_offset=0,
        map_size=0,
        play_category=1,
        special_category=11,
        user_category=1,
    )
    assert play.name == "RUNCLOCK"
