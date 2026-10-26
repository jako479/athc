"""Tests for athc.fbpro98_play.model — PlayFile properties, category_name and
the play attributes.

The category tests call `resolve_category` with raw bytes so every code can be
covered, the User Specific (0xFF/0xFE) markers included; the attribute tests
build a PlayFile directly (no IO) so each rule can be pinned with exact spots.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_play import (
    UNKNOWN_CATEGORY,
    Command,
    DefensiveCategory,
    DefensiveFront,
    LogicBox,
    OffensiveCategory,
    PlayCategory,
    PlayerHeader,
    PlayerLogic,
    PlayFile,
    SpecialDefensiveCategory,
    SpecialOffensiveCategory,
    resolve_category,
)
from athc.fbpro98_play.schema import (
    COMMAND_CHECK_RECEIVERS,
    COMMAND_MOVE_TO,
    COMMAND_RUN,
    COMMAND_TIMED_PASS,
    POSITION_C,
    POSITION_DE,
    POSITION_DT,
    POSITION_G,
    POSITION_QB,
    POSITION_T,
)


def _play(
    *,
    play_category: int = 0x01,
    special_category: int = 0x00,
    user_category: int = 0x01,
) -> PlayFile:
    """PlayFile carrying only the fields the side/category properties read."""
    return PlayFile(
        file_path=Path("<test>"),
        stream_length=0,
        play_category=play_category,
        special_category=special_category,
        user_category=user_category,
        player_offsets=[],
        player_headers=[],
    )


@pytest.mark.parametrize("play_category", [0x01, 0x03, 0x9B, 0xFF])
def test_odd_play_category_is_offensive(play_category):
    play = _play(play_category=play_category)
    assert play.is_offensive
    assert not play.is_defensive


@pytest.mark.parametrize("play_category", [0x00, 0x02, 0x82, 0xFE])
def test_even_play_category_is_defensive(play_category):
    play = _play(play_category=play_category)
    assert play.is_defensive
    assert not play.is_offensive


def test_is_special():
    assert _play(special_category=0x02).is_special
    assert not _play(special_category=0x00).is_special


def test_category_returns_enum_member():
    play = _play(play_category=0x01, user_category=0x03)
    assert play.category is OffensiveCategory.PASS_SHORT_RIGHT
    assert play.category_name == play.category.long == "Pass Short Right"


def test_category_name_of_an_unrecognized_code_is_unknown():
    play = _play(play_category=0x01, user_category=0x3F)
    assert play.category is UNKNOWN_CATEGORY
    assert play.category_name == "Unknown"


def test_is_run_is_pass():
    assert OffensiveCategory.RUN_LEFT.is_run and not OffensiveCategory.RUN_LEFT.is_pass
    psr = OffensiveCategory.PASS_SHORT_RIGHT
    assert psr.is_pass and not psr.is_run
    assert not OffensiveCategory.USER_SPECIFIC.is_run
    assert not OffensiveCategory.USER_SPECIFIC.is_pass


# ── resolve_category ──────────────────────────────────────────────────────────


def _bytes_of(category: PlayCategory) -> tuple[int, int, int]:
    """The play, special and user category bytes of a play saved as `category`:
    a normal play carries its code in the user byte, a special play in the
    special byte with the side's plain code in the other two."""
    match category:
        case OffensiveCategory():
            return 0x01, 0x00, category.code
        case DefensiveCategory():
            return 0x00, 0x00, category.code
        case SpecialOffensiveCategory():
            return 0x01, category.code, 0x01
        case SpecialDefensiveCategory():
            return 0x00, category.code, 0x00
    raise AssertionError(category)


@pytest.mark.parametrize(
    "category",
    [
        *OffensiveCategory,
        *DefensiveCategory,
        *SpecialOffensiveCategory,
        *SpecialDefensiveCategory,
    ],
)
def test_resolve_category_names_every_member(category: PlayCategory):
    """Side from the play byte's parity, then the special table or the side's
    normal table: every member resolves from its own code."""
    assert resolve_category(*_bytes_of(category)) is category


def test_high_bits_are_masked():
    """Bits 7-6 vary across plays of one category; the lookup ignores them."""
    assert resolve_category(0x01, 0x00, 0xC9) is OffensiveCategory.RUN_MIDDLE
    assert resolve_category(0x00, 0x00, 0xC8) is DefensiveCategory.RUN_MIDDLE


def test_user_specific_is_a_full_byte_code():
    """0xFF / 0xFE resolve as themselves, not as their masked 0x3F / 0x3E."""
    assert resolve_category(0x01, 0x00, 0xFF) is OffensiveCategory.USER_SPECIFIC
    assert resolve_category(0x00, 0x00, 0xFE) is DefensiveCategory.USER_SPECIFIC


@pytest.mark.parametrize(
    ("play_category", "user_category"),
    [(0x01, 0x3F), (0x00, 0x3E)],
    ids=["offense", "defense"],
)
def test_unknown_normal_code(play_category, user_category):
    assert resolve_category(play_category, 0x00, user_category) is UNKNOWN_CATEGORY


@pytest.mark.parametrize(
    ("play_category", "special_category"),
    [(0x01, 0x0D), (0x00, 0x0B), (0x00, 0x0C)],
    ids=["offense-past-stop-clock", "defense-run-clock", "defense-stop-clock"],
)
def test_unknown_special_code(play_category, special_category):
    """One past Stop Clock (0x0C), the last offense code; and the clock codes
    on defense, which has no clock plays."""
    unknown = resolve_category(play_category, special_category, play_category)
    assert unknown is UNKNOWN_CATEGORY


def test_play_file_is_edited_by_assignment():
    play = _play(play_category=0x01, user_category=0x01)
    play.user_category = 0x03
    play.player_offsets.append(25)
    assert play.category is OffensiveCategory.PASS_SHORT_RIGHT
    assert play.player_offsets == [25]


# ── play attributes ───────────────────────────────────────────────────────────

HB, TE, LB, CB = 0x0042, 0x0081, 0x0200, 0x0400
TIMED = Command(COMMAND_TIMED_PASS, [0])
CHECK = Command(COMMAND_CHECK_RECEIVERS, [3])
RUN = Command(COMMAND_RUN, [2])
SNAP_Y = -140


def _move(x: int) -> Command:
    return Command(COMMAND_MOVE_TO, [x, -400])


def _player(position: int, *after_snap: LogicBox) -> tuple[int, PlayerLogic]:
    start = after_snap[0] if after_snap else LogicBox(0, SNAP_Y, [])
    return position, PlayerLogic([LogicBox(start.x, start.y, [])], list(after_snap))


def _lineman(position: int, x: int) -> tuple[int, PlayerLogic]:
    return _player(position, LogicBox(x, SNAP_Y, []))


def _tackle(x: int) -> tuple[int, PlayerLogic]:
    return _lineman(POSITION_T, x)


def _qb(*after_snap: LogicBox) -> tuple[int, PlayerLogic]:
    return _player(POSITION_QB, *after_snap)


def _play_of(
    *players: tuple[int, PlayerLogic],
    play_category: int = 0x03,  # offense, Pass Short Right
    special_category: int = 0x00,
) -> PlayFile:
    """A PlayFile holding `players` (position, logic), in slot order."""
    return PlayFile(
        file_path=Path("<test>"),
        stream_length=0,
        play_category=play_category,
        special_category=special_category,
        user_category=play_category,
        player_offsets=[],
        player_headers=[
            PlayerHeader(offset=0, rank=1, player_type=0, position=position)
            for position, _ in players
        ],
        player_logic=[logic for _, logic in players],
    )


def _passer(*after_snap: LogicBox) -> PlayFile:
    """An offensive play: tackles at -300 and 300, and a QB with `after_snap`."""
    return _play_of(_tackle(-300), _tackle(300), _qb(*after_snap))


def test_timed_pass_is_the_qbs_timed_pass():
    assert _passer(LogicBox(0, -300, [TIMED])).is_timed_pass
    assert not _passer(LogicBox(0, -300, [CHECK])).is_timed_pass


def test_timed_pass_needs_the_qb():
    halfback_pass = _play_of(_qb(), _player(HB, LogicBox(0, -500, [TIMED])))
    assert not halfback_pass.is_timed_pass


def test_timed_pass_reads_from_the_snap_on():
    """A Timed pass in a pre-snap box does not count."""
    qb = (
        POSITION_QB,
        PlayerLogic([LogicBox(0, -300, [TIMED])], [LogicBox(0, -300, [])]),
    )
    assert not _play_of(qb).is_timed_pass


def test_qb_run_is_the_qbs_run():
    assert _play_of(_qb(LogicBox(0, -300, [RUN]))).is_qb_run
    assert not _play_of(_qb(), _player(HB, LogicBox(0, -500, [RUN]))).is_qb_run


def test_qb_run_reads_from_the_snap_on():
    """A Run in a pre-snap box does not count."""
    qb = (
        POSITION_QB,
        PlayerLogic([LogicBox(0, -300, [RUN])], [LogicBox(0, -300, [])]),
    )
    assert not _play_of(qb).is_qb_run


def test_a_play_can_be_timed_and_a_rollout():
    play = _passer(LogicBox(0, -300, [_move(500)]), LogicBox(500, -400, [TIMED]))
    assert play.is_timed_pass and play.is_rollout(100)


@pytest.mark.parametrize(
    ("margin", "qb_after_snap", "expected"),
    [
        (100, (LogicBox(0, -300, [_move(400), TIMED]),), False),  # right, at
        (100, (LogicBox(0, -300, [_move(401), TIMED]),), True),  # right, one past
        (100, (LogicBox(0, -300, []), LogicBox(-400, -300, [CHECK])), False),
        (100, (LogicBox(0, -300, []), LogicBox(-401, -300, [CHECK])), True),
        (200, (LogicBox(0, -300, [_move(500), TIMED]),), False),  # at
        (200, (LogicBox(0, -300, [_move(501), TIMED]),), True),  # one past
    ],
    ids=[
        "right-at-margin",
        "right-one-past",
        "left-at-margin",
        "left-one-past",
        "margin-200-at",
        "margin-200-one-past",
    ],
)
def test_rollout_margin_on_both_sides(margin, qb_after_snap, expected):
    """Tackles at -300 and 300: a rollout goes beyond the caller's margin, so
    with margin 100 a spot 101 units outside a tackle counts and 100 does not,
    whether reached by a Move to or a box's spot; margin 200 moves the line
    to 500."""
    assert _passer(*qb_after_snap).is_rollout(margin) is expected


def test_rollout_counts_spots_up_to_the_pass_only():
    play = _passer(LogicBox(0, -300, [TIMED, _move(1000)]), LogicBox(1000, -300, []))
    assert not play.is_rollout(100)


def test_rollout_ignores_a_move_to_with_no_arguments():
    bare_move = Command(COMMAND_MOVE_TO, [])
    assert not _passer(LogicBox(0, -300, [bare_move, TIMED])).is_rollout(100)


def test_rollout_reads_from_the_snap_on():
    """A QB who lines up wide but is back inside at the snap stays in the pocket."""
    qb = (
        POSITION_QB,
        PlayerLogic([LogicBox(1000, -300, [])], [LogicBox(0, -300, [TIMED])]),
    )
    assert not _play_of(_tackle(-300), _tackle(300), qb).is_rollout(100)


def test_rollout_needs_a_pass():
    assert not _passer(LogicBox(0, -300, [_move(1000), RUN])).is_rollout(100)


@pytest.mark.parametrize(
    "line",
    [(), ((POSITION_T, PlayerLogic()), (POSITION_T, PlayerLogic()))],
    ids=["no-linemen", "linemen-with-no-snap-spot"],
)
def test_rollout_needs_a_line(line):
    """No C, G or T with a spot at the snap means no edge to get outside."""
    qb = _qb(LogicBox(0, -300, [_move(1000), TIMED]))
    assert not _play_of(*line, qb).is_rollout(100)


# Unbalanced lines: both tackles right of the ball, so a guard or the center is
# the outermost lineman on the left.
GUARD_ON_THE_LEFT = (
    _lineman(POSITION_G, -150),
    _lineman(POSITION_C, 0),
    _lineman(POSITION_G, 150),
    _tackle(300),
    _tackle(450),
)
CENTER_ON_THE_LEFT = (
    _lineman(POSITION_C, -11),
    _lineman(POSITION_G, 140),
    _lineman(POSITION_G, 290),
    _tackle(440),
    _tackle(590),
)


@pytest.mark.parametrize(
    ("line", "x", "expected"),
    [
        (GUARD_ON_THE_LEFT, 550, False),  # right tackle 450, at the margin
        (GUARD_ON_THE_LEFT, 551, True),  # one past
        (GUARD_ON_THE_LEFT, -250, False),  # left guard -150, at the margin
        (GUARD_ON_THE_LEFT, -251, True),  # one past
        (CENTER_ON_THE_LEFT, 690, False),  # right tackle 590, at the margin
        (CENTER_ON_THE_LEFT, 691, True),  # one past
        (CENTER_ON_THE_LEFT, -111, False),  # center -11, at the margin
        (CENTER_ON_THE_LEFT, -112, True),  # one past
    ],
)
def test_rollout_edges_are_the_outermost_linemen(line, x, expected):
    """The edge on each side is the outermost C, G or T at the snap."""
    play = _play_of(*line, _qb(LogicBox(0, -300, [_move(x), TIMED])))
    assert play.is_rollout(100) is expected


@pytest.mark.parametrize(
    "line", [GUARD_ON_THE_LEFT, CENTER_ON_THE_LEFT], ids=["guard", "center"]
)
def test_pocket_qb_behind_an_unbalanced_line_is_no_rollout(line):
    assert not _play_of(*line, _qb(LogicBox(0, -300, [CHECK]))).is_rollout(100)


def test_a_tight_end_is_not_part_of_the_line():
    """A TE outside the tackle is no edge: the tackle at 300 is."""
    play = _play_of(
        _tackle(-300),
        _tackle(300),
        _lineman(TE, 450),
        _qb(LogicBox(0, -300, [_move(401), TIMED])),
    )
    assert play.is_rollout(100)


def test_no_qb_means_no_offense_attributes():
    halfback = _player(HB, LogicBox(0, -500, [RUN, _move(1000), TIMED]))
    play = _play_of(_tackle(-300), _tackle(300), halfback)
    assert not (play.is_timed_pass or play.is_qb_run or play.is_rollout(100))


def test_any_qb_counts():
    """With two QBs on the field, either one's Timed pass, Run or rollout counts."""
    passer = _qb(LogicBox(1000, -300, [TIMED]))
    play = _play_of(_tackle(-300), _tackle(300), _qb(), passer)
    assert play.is_timed_pass and play.is_rollout(100)
    assert _play_of(_qb(), _qb(LogicBox(0, -300, [RUN]))).is_qb_run


def _defense(down_linemen: int, code: int) -> PlayFile:
    """A defensive play of category `code` with `down_linemen` DE/DT, then
    LB/CB."""
    positions = [POSITION_DE, POSITION_DT] * 3
    linemen = [_player(p) for p in positions[:down_linemen]]
    others = [_player(LB if i % 2 else CB) for i in range(11 - down_linemen)]
    return _play_of(*linemen, *others, play_category=code)


RUN_FRONT_CATEGORIES = [
    DefensiveCategory.RUN_LEFT,
    DefensiveCategory.RUN_MIDDLE,
    DefensiveCategory.RUN_RIGHT,
]
PASS_CATEGORIES = [
    DefensiveCategory.PASS_SHORT,
    DefensiveCategory.PASS_MEDIUM,
    DefensiveCategory.PASS_LONG,
    DefensiveCategory.RAZZLE_DAZZLE_PASS,
    DefensiveCategory.GOAL_LINE_PASS,
]


@pytest.mark.parametrize("category", RUN_FRONT_CATEGORIES)
@pytest.mark.parametrize(
    ("down_linemen", "front"),
    [
        (2, None),
        (3, DefensiveFront.THREE_FOUR),
        (4, DefensiveFront.FOUR_THREE),
        (5, None),
    ],
)
def test_run_defense_front_from_down_linemen(category, down_linemen, front):
    """On Run Left, Run Middle and Run Right, 3 down linemen are a 3-4 and 4 a
    4-3; any other count has no front."""
    assert _defense(down_linemen, category.code).defensive_front is front


@pytest.mark.parametrize("category", PASS_CATEGORIES)
@pytest.mark.parametrize(
    ("down_linemen", "front"), [(1, None), (2, DefensiveFront.TWO_DL), (3, None)]
)
def test_pass_defense_front_from_down_linemen(category, down_linemen, front):
    """On every pass defense, 2 down linemen are a 2-DL; any other count has no
    front."""
    assert _defense(down_linemen, category.code).defensive_front is front


@pytest.mark.parametrize("down_linemen", [2, 3, 4])
@pytest.mark.parametrize(
    "code",
    [
        DefensiveCategory.RAZZLE_DAZZLE_RUN.code,
        DefensiveCategory.GOAL_LINE_RUN.code,
        DefensiveCategory.USER_SPECIFIC.code,
        0x3E,
    ],
    ids=["run-dazzle", "goal-line-run", "user-specific", "unrecognized"],
)
def test_no_front_for_other_defenses(code, down_linemen):
    """Razzle Dazzle Run, Goal Line Run, User Specific and an unrecognized category
    have no front at any count that names one elsewhere."""
    assert _defense(down_linemen, code).defensive_front is None


@pytest.mark.parametrize(
    ("play_category", "special_category"),
    [(0x02, 0x00), (0x01, 0x06)],
    ids=["defense", "fake-fg-pass"],
)
def test_offense_attributes_only_on_normal_offense(play_category, special_category):
    qb = _qb(LogicBox(0, -300, [RUN, _move(1000), TIMED]))
    play = _play_of(
        _tackle(-300),
        _tackle(300),
        qb,
        play_category=play_category,
        special_category=special_category,
    )
    assert not (play.is_timed_pass or play.is_qb_run or play.is_rollout(100))


@pytest.mark.parametrize(
    ("play_category", "special_category"),
    [(0x01, 0x00), (0x00, 0x02)],
    ids=["offense", "kick-return"],
)
def test_front_only_on_normal_defense(play_category, special_category):
    linemen = [_player(POSITION_DT)] * 3
    play = _play_of(
        *linemen, play_category=play_category, special_category=special_category
    )
    assert play.defensive_front is None


def test_no_logic_means_no_attributes():
    """A PlayFile built without player logic has no QB moves to read."""
    play = _play(play_category=0x03, user_category=0x03)
    assert not (play.is_timed_pass or play.is_qb_run or play.is_rollout(100))
    assert _play(play_category=0x02, user_category=0x02).defensive_front is None
