"""Tests for athc.fbpro98_play.model — PlayFile properties, category_name and
the play attributes.

These build a PlayFile directly (no IO) so every category code can be covered
exhaustively, including the User Specific (0xFF/0xFE) markers, and so each
attribute rule can be pinned with exact spots.
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
        player_offsets=(),
        player_headers=(),
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


def test_is_special_teams():
    assert _play(special_category=0x02).is_special_teams
    assert not _play(special_category=0x00).is_special_teams


@pytest.mark.parametrize("category", list(OffensiveCategory))
def test_offensive_category_name(category):
    play = _play(play_category=0x01, user_category=category.code)
    assert play.category_name == category.long


@pytest.mark.parametrize("category", list(DefensiveCategory))
def test_defensive_category_name(category):
    play = _play(play_category=0x00, user_category=category.code)
    assert play.category_name == category.long


@pytest.mark.parametrize("category", list(SpecialOffensiveCategory))
def test_offensive_special_teams_names(category):
    play = _play(play_category=0x01, special_category=category.code)
    assert play.category_name == category.long


@pytest.mark.parametrize("category", list(SpecialDefensiveCategory))
def test_defensive_special_teams_names(category):
    play = _play(play_category=0x00, special_category=category.code)
    assert play.category_name == category.long


def test_unknown_normal_code_is_unknown():
    off = _play(play_category=0x01, user_category=0x3F)
    assert off.category is UNKNOWN_CATEGORY and off.category_name == "Unknown"
    assert _play(play_category=0x00, user_category=0x3F).category is UNKNOWN_CATEGORY


def test_unknown_special_category_is_unknown():
    assert _play(play_category=0x01, special_category=0x7F).category is UNKNOWN_CATEGORY


def test_high_bits_are_masked():
    # bits 7-6 vary across plays in the same category; the lookup ignores them
    plain = _play(play_category=0x01, user_category=0x09).category_name
    high = _play(
        play_category=0x01, user_category=0xC9
    ).category_name  # 0xC9 & 0x3F == 0x09
    assert plain == high == "Run Middle"


def test_user_specific_resolves():
    # full-byte 0xFF/0xFE markers resolve despite the 0x3F mask
    assert (
        _play(play_category=0x01, user_category=0xFF).category_name == "User Specific"
    )
    assert (
        _play(play_category=0x00, user_category=0xFE).category_name == "User Specific"
    )


# ── category enum + resolve_category ──────────────────────────────────────────


def test_category_returns_enum_member():
    play = _play(play_category=0x01, user_category=0x03)
    assert play.category is OffensiveCategory.PASS_SHORT_RIGHT
    assert play.category_name == play.category.long == "Pass Short Right"


def test_long_is_the_game_name():
    assert OffensiveCategory.PASS_SHORT_RIGHT.long == "Pass Short Right"
    assert DefensiveCategory.RUN_LEFT.long == "Run Left"
    assert SpecialOffensiveCategory.PUNT.long == "Punt"


def test_category_has_no_league_label():
    assert not hasattr(OffensiveCategory.PASS_SHORT_RIGHT, "short")


def test_is_run_is_pass():
    assert OffensiveCategory.RUN_LEFT.is_run and not OffensiveCategory.RUN_LEFT.is_pass
    psr = OffensiveCategory.PASS_SHORT_RIGHT
    assert psr.is_pass and not psr.is_run
    assert not OffensiveCategory.USER_SPECIFIC.is_run
    assert not OffensiveCategory.USER_SPECIFIC.is_pass


def test_resolve_category_picks_side_and_special():
    assert resolve_category(0x01, 0x00, 0x03) is OffensiveCategory.PASS_SHORT_RIGHT
    assert resolve_category(0x00, 0x00, 0x02) is DefensiveCategory.PASS_SHORT
    assert resolve_category(0x01, 0x02, 0x00) is SpecialOffensiveCategory.KICKOFF
    assert resolve_category(0x00, 0x02, 0x00) is SpecialDefensiveCategory.KICK_RETURN


def test_resolve_category_mask_and_unknown():
    # 0xC9 & 0x3F == 0x09 (Run Middle); 0xFF is the full-byte User Specific marker
    assert resolve_category(0x01, 0x00, 0xC9) is OffensiveCategory.RUN_MIDDLE
    assert resolve_category(0x01, 0x00, 0xFF) is OffensiveCategory.USER_SPECIFIC
    assert resolve_category(0x01, 0x00, 0x3F) is UNKNOWN_CATEGORY


def test_clock_categories_are_offense_only():
    assert resolve_category(0x01, 0x0B, 0x00) is SpecialOffensiveCategory.RUN_CLOCK
    assert resolve_category(0x01, 0x0C, 0x00) is SpecialOffensiveCategory.STOP_CLOCK
    assert SpecialOffensiveCategory.RUN_CLOCK.long == "Run Clock"
    assert SpecialOffensiveCategory.STOP_CLOCK.long == "Stop Clock"
    # Defense has no clock plays, so the same bytes on the defense side are unknown.
    assert resolve_category(0x00, 0x0B, 0x00) is UNKNOWN_CATEGORY
    assert resolve_category(0x00, 0x0C, 0x00) is UNKNOWN_CATEGORY


# ── play attributes ───────────────────────────────────────────────────────────

HB, TE, LB, CB = 0x0042, 0x0081, 0x0200, 0x0400
TIMED = Command(COMMAND_TIMED_PASS, (0,))
CHECK = Command(COMMAND_CHECK_RECEIVERS, (3,))
RUN = Command(COMMAND_RUN, (2,))
SNAP_Y = -140


def _move(x: int) -> Command:
    return Command(COMMAND_MOVE_TO, (x, -400))


def _player(position: int, *after_snap: LogicBox) -> tuple[int, PlayerLogic]:
    start = after_snap[0] if after_snap else LogicBox(0, SNAP_Y, ())
    return position, PlayerLogic((LogicBox(start.x, start.y, ()),), after_snap)


def _lineman(position: int, x: int) -> tuple[int, PlayerLogic]:
    return _player(position, LogicBox(x, SNAP_Y, ()))


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
        player_offsets=(),
        player_headers=tuple(
            PlayerHeader(offset=0, rank=1, player_type=0, position=position)
            for position, _ in players
        ),
        player_logic=tuple(logic for _, logic in players),
    )


def _passer(*after_snap: LogicBox) -> PlayFile:
    """An offensive play: tackles at -300 and 300, and a QB with `after_snap`."""
    return _play_of(_tackle(-300), _tackle(300), _qb(*after_snap))


def test_timed_pass_is_the_qbs_timed_pass():
    assert _passer(LogicBox(0, -300, (TIMED,))).is_timed_pass
    assert not _passer(LogicBox(0, -300, (CHECK,))).is_timed_pass


def test_timed_pass_needs_the_qb():
    halfback_pass = _play_of(_qb(), _player(HB, LogicBox(0, -500, (TIMED,))))
    assert not halfback_pass.is_timed_pass


def test_timed_pass_reads_from_the_snap_on():
    """A Timed pass in a pre-snap box does not count."""
    qb = (
        POSITION_QB,
        PlayerLogic((LogicBox(0, -300, (TIMED,)),), (LogicBox(0, -300, ()),)),
    )
    assert not _play_of(qb).is_timed_pass


def test_qb_run_is_the_qbs_run():
    assert _play_of(_qb(LogicBox(0, -300, (RUN,)))).is_qb_run
    assert not _play_of(_qb(), _player(HB, LogicBox(0, -500, (RUN,)))).is_qb_run


def test_qb_run_reads_from_the_snap_on():
    """A Run in a pre-snap box does not count."""
    qb = (
        POSITION_QB,
        PlayerLogic((LogicBox(0, -300, (RUN,)),), (LogicBox(0, -300, ()),)),
    )
    assert not _play_of(qb).is_qb_run


def test_a_play_can_be_timed_and_a_rollout():
    play = _passer(LogicBox(0, -300, (_move(500),)), LogicBox(500, -400, (TIMED,)))
    assert play.is_timed_pass and play.is_rollout(100)


@pytest.mark.parametrize(
    ("qb_after_snap", "expected"),
    [
        ((LogicBox(0, -300, (_move(400), TIMED)),), False),  # right, at the margin
        ((LogicBox(0, -300, (_move(401), TIMED)),), True),  # right, one past
        ((LogicBox(0, -300, ()), LogicBox(-400, -300, (CHECK,))), False),  # left, at
        (
            (LogicBox(0, -300, ()), LogicBox(-401, -300, (CHECK,))),
            True,
        ),  # left, one past
    ],
    ids=["right-at-margin", "right-one-past", "left-at-margin", "left-one-past"],
)
def test_rollout_margin_on_both_sides(qb_after_snap, expected):
    """Tackles at -300 and 300, margin 100: a rollout goes beyond the margin, so
    a spot 101 units outside a tackle counts and 100 does not, whether reached
    by a Move to or a box's spot."""
    assert _passer(*qb_after_snap).is_rollout(100) is expected


def test_rollout_counts_spots_up_to_the_pass_only():
    play = _passer(LogicBox(0, -300, (TIMED, _move(1000))), LogicBox(1000, -300, ()))
    assert not play.is_rollout(100)


def test_rollout_ignores_a_move_to_with_no_arguments():
    bare_move = Command(COMMAND_MOVE_TO, ())
    assert not _passer(LogicBox(0, -300, (bare_move, TIMED))).is_rollout(100)


def test_rollout_reads_from_the_snap_on():
    """A QB who lines up wide but is back inside at the snap stays in the pocket."""
    qb = (
        POSITION_QB,
        PlayerLogic((LogicBox(1000, -300, ()),), (LogicBox(0, -300, (TIMED,)),)),
    )
    assert not _play_of(_tackle(-300), _tackle(300), qb).is_rollout(100)


def test_rollout_needs_a_pass():
    assert not _passer(LogicBox(0, -300, (_move(1000), RUN))).is_rollout(100)


def test_rollout_needs_a_line():
    assert not _play_of(_qb(LogicBox(0, -300, (_move(1000), TIMED)))).is_rollout(100)


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
        (CENTER_ON_THE_LEFT, 691, True),  # right tackle 590, one past
        (CENTER_ON_THE_LEFT, -111, False),  # center -11, at the margin
        (CENTER_ON_THE_LEFT, -112, True),  # one past
    ],
)
def test_rollout_edges_are_the_outermost_linemen(line, x, expected):
    """The edge on each side is the outermost C, G or T at the snap."""
    play = _play_of(*line, _qb(LogicBox(0, -300, (_move(x), TIMED))))
    assert play.is_rollout(100) is expected


@pytest.mark.parametrize(
    "line", [GUARD_ON_THE_LEFT, CENTER_ON_THE_LEFT], ids=["guard", "center"]
)
def test_pocket_qb_behind_an_unbalanced_line_is_no_rollout(line):
    assert not _play_of(*line, _qb(LogicBox(0, -300, (CHECK,)))).is_rollout(100)


def test_a_tight_end_is_not_part_of_the_line():
    """A TE outside the tackle is no edge: the tackle at 300 is."""
    play = _play_of(
        _tackle(-300),
        _tackle(300),
        _lineman(TE, 450),
        _qb(LogicBox(0, -300, (_move(401), TIMED))),
    )
    assert play.is_rollout(100)


def test_no_qb_means_no_offense_attributes():
    halfback = _player(HB, LogicBox(0, -500, (RUN, _move(1000), TIMED)))
    play = _play_of(_tackle(-300), _tackle(300), halfback)
    assert not (play.is_timed_pass or play.is_qb_run or play.is_rollout(100))


def test_any_qb_counts():
    """With two QBs on the field, either one's Timed pass, Run or rollout counts."""
    passer = _qb(LogicBox(1000, -300, (TIMED,)))
    play = _play_of(_tackle(-300), _tackle(300), _qb(), passer)
    assert play.is_timed_pass and play.is_rollout(100)
    assert _play_of(_qb(), _qb(LogicBox(0, -300, (RUN,)))).is_qb_run


def _defense(down_linemen: int, category: DefensiveCategory) -> PlayFile:
    """A defensive play of `category` with `down_linemen` DE/DT, then LB/CB."""
    positions = [POSITION_DE, POSITION_DT] * 3
    linemen = [_player(p) for p in positions[:down_linemen]]
    others = [_player(LB if i % 2 else CB) for i in range(11 - down_linemen)]
    return _play_of(*linemen, *others, play_category=category.code)


@pytest.mark.parametrize(
    ("down_linemen", "front"),
    [
        (2, None),
        (3, DefensiveFront.THREE_FOUR),
        (4, DefensiveFront.FOUR_THREE),
        (5, None),
    ],
)
def test_run_defense_front_from_down_linemen(down_linemen, front):
    assert _defense(down_linemen, DefensiveCategory.RUN_LEFT).defensive_front is front


@pytest.mark.parametrize(
    ("down_linemen", "front"), [(1, None), (2, DefensiveFront.TWO_DL), (3, None)]
)
def test_pass_defense_front_from_down_linemen(down_linemen, front):
    assert _defense(down_linemen, DefensiveCategory.PASS_SHORT).defensive_front is front


@pytest.mark.parametrize(
    "category",
    [
        DefensiveCategory.RUN_LEFT,
        DefensiveCategory.RUN_MIDDLE,
        DefensiveCategory.RUN_RIGHT,
    ],
)
def test_3_4_and_4_3_are_run_left_middle_right_fronts(category):
    assert _defense(3, category).defensive_front is DefensiveFront.THREE_FOUR
    assert _defense(4, category).defensive_front is DefensiveFront.FOUR_THREE
    assert _defense(2, category).defensive_front is None


@pytest.mark.parametrize(
    "category",
    [
        DefensiveCategory.PASS_SHORT,
        DefensiveCategory.PASS_MEDIUM,
        DefensiveCategory.PASS_LONG,
        DefensiveCategory.PASS_DAZZLE,
        DefensiveCategory.GOAL_LINE_PASS,
    ],
)
def test_2_dl_is_a_pass_front(category):
    assert _defense(2, category).defensive_front is DefensiveFront.TWO_DL
    assert _defense(3, category).defensive_front is None
    assert _defense(4, category).defensive_front is None


@pytest.mark.parametrize(
    "category",
    [
        DefensiveCategory.RUN_DAZZLE,
        DefensiveCategory.GOAL_LINE_RUN,
        DefensiveCategory.USER_SPECIFIC,
    ],
)
def test_no_front_for_other_defenses(category):
    for down_linemen in (2, 3, 4):
        assert _defense(down_linemen, category).defensive_front is None


def test_offense_attributes_only_on_normal_offense():
    qb = _qb(LogicBox(0, -300, (RUN, _move(1000), TIMED)))
    tackles = (_tackle(-300), _tackle(300))
    for play in (
        _play_of(*tackles, qb, play_category=0x02),  # defense
        _play_of(*tackles, qb, play_category=0x01, special_category=0x06),  # fake FG
    ):
        assert not play.is_timed_pass
        assert not play.is_qb_run
        assert not play.is_rollout(100)


def test_front_only_on_normal_defense():
    linemen = [_player(POSITION_DT)] * 3
    assert _play_of(*linemen, play_category=0x01).defensive_front is None  # offense
    kick_return = _play_of(*linemen, play_category=0x00, special_category=0x02)
    assert kick_return.defensive_front is None


def test_no_logic_means_no_attributes():
    """A PlayFile built without player logic has no QB moves to read."""
    play = _play(play_category=0x03, user_category=0x03)
    assert not (play.is_timed_pass or play.is_qb_run or play.is_rollout(100))
    assert _play(play_category=0x02, user_category=0x02).defensive_front is None
