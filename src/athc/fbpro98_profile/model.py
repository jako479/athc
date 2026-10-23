"""In-memory data model for FbPro98 .prf coaching profile files.

Defines the immutable types that the reader produces and the writer consumes:
ProfileType, SubstitutionPair, SubstitutionSettings, Situation, PatSituation,
CategoryWeights, and the top-level Profile dataclass, plus the GameState and
PatGameState that Profile decodes from a situation's position.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import ClassVar


class ProfileType(IntEnum):
    """Whether a profile is for defense (0) or offense (1). Encoded in I95 data."""

    DEFENSE = 0
    OFFENSE = 1


@dataclass(frozen=True, slots=True)
class SubstitutionPair:
    """One position group's `out`/`in` substitution thresholds (each 0-100, out <= in).

    See docs/formats/prf.md section 2.2 for the on-disk layout.
    """

    out_percent: int
    """Fatigue threshold, 0-100."""

    in_percent: int
    """Recovery threshold, 0-100; must be >= out_percent."""

    def __post_init__(self) -> None:
        if not 0 <= self.out_percent <= 100:
            raise ValueError(f"out_percent must be in [0, 100], got {self.out_percent}")
        if not 0 <= self.in_percent <= 100:
            raise ValueError(f"in_percent must be in [0, 100], got {self.in_percent}")
        if self.out_percent > self.in_percent:
            raise ValueError(
                f"out_percent ({self.out_percent}) must be <= "
                f"in_percent ({self.in_percent})"
            )


@dataclass(frozen=True, slots=True)
class SubstitutionSettings:
    """All eight position groups' substitution thresholds.

    All eight pairs are physically present in both offense and defense profiles.
    The game UI exposes only the five offensive groups (OL, QB, RB, WR, K) when
    editing an offense profile and the three defensive groups (DL, LB, DB) when
    editing a defense profile; the rest hold the game's `80/90` default.
    """

    offensive_linemen: SubstitutionPair
    quarterbacks: SubstitutionPair
    running_backs: SubstitutionPair
    receivers: SubstitutionPair
    defensive_linemen: SubstitutionPair
    linebackers: SubstitutionPair
    defensive_backs: SubstitutionPair
    kickers: SubstitutionPair

    @classmethod
    def default(cls) -> SubstitutionSettings:
        """Return a SubstitutionSettings with every pair at the game's default 80/90.

        Returns:
            A SubstitutionSettings whose every pair is `SubstitutionPair(80, 90)`.
        """
        default = SubstitutionPair(out_percent=80, in_percent=90)
        return cls(
            offensive_linemen=default,
            quarterbacks=default,
            running_backs=default,
            receivers=default,
            defensive_linemen=default,
            linebackers=default,
            defensive_backs=default,
            kickers=default,
        )


class Down(IntEnum):
    """Down number"""

    FIRST = 1
    SECOND = 2
    THIRD = 3
    FOURTH = 4


class MinutesRemaining(IntEnum):
    """Bucket for time remaining in the current half, ordered most to least"""

    OVER_FIVE = 0  # >5
    TWO_TO_FIVE = 1  # >2-5
    ONE_TO_TWO = 2  # >1-2
    FIFTEEN_SEC_TO_ONE = 3  # >:15-1
    ZERO_TO_FIFTEEN_SEC = 4  # 0-:15


class YardsToGo(Enum):
    """Bucket for yards needed for a first down"""

    ZERO_TO_ONE = 0  # 0-1
    TWO_TO_FIVE = 1  # 2-5
    SIX_TO_TEN = 2  # 6-10
    OVER_TEN = 3  # >10


class FieldPosition(Enum):
    """Bucket for current field position"""

    INSIDE_DEF_5 = 0  # <DEF 5
    DEF_5_TO_DEF_35 = 1  # DEF 5 - DEF 35
    DEF_35_TO_OFF_35 = 2  # DEF 35 - OFF 35
    OFF_35_TO_OFF_5 = 3  # OFF 35 - OFF 5
    INSIDE_OFF_5 = 4  # <OFF 5


class PointSpread(Enum):
    """Bucket for current point spread"""

    AHEAD_8_OR_MORE = 0  # Ahead by 8+
    AHEAD_4_TO_7 = 1  # Ahead by 4-7
    AHEAD_1_TO_3 = 2  # Ahead by 1-3
    TIED = 3  # Tied
    BEHIND_1_TO_3 = 4  # Behind by 1-3
    BEHIND_4_TO_7 = 5  # Behind by 4-7
    BEHIND_8_OR_MORE = 6  # Behind by 8+


class PatMinutesRemaining(IntEnum):
    """Bucket for time remaining in the half (PAT-specific), ordered most to least.

    Differs from MinutesRemaining: PAT collapses the >:15-1 and 0-:15 buckets
    into a single 0-1 bucket. 4 buckets total instead of 5.
    """

    OVER_FIVE = 0  # >5
    TWO_TO_FIVE = 1  # >2-5
    ONE_TO_TWO = 2  # >1-2
    ZERO_TO_ONE = 3  # 0-1


class PatPointSpread(Enum):
    """Bucket for current point spread (PAT-specific granularity, 15 buckets)."""

    AHEAD_12_OR_MORE = 0  # Ahead by 12+
    AHEAD_9_TO_11 = 1  # Ahead by 9-11
    AHEAD_8 = 2  # Ahead by 8
    AHEAD_6_TO_7 = 3  # Ahead by 6-7
    AHEAD_5 = 4  # Ahead by 5
    AHEAD_2_TO_4 = 5  # Ahead by 2-4
    AHEAD_1 = 6  # Ahead by 1
    TIED = 7  # Tied
    BEHIND_1 = 8  # Behind by 1
    BEHIND_2 = 9  # Behind by 2
    BEHIND_3_TO_4 = 10  # Behind by 3-4
    BEHIND_5 = 11  # Behind by 5
    BEHIND_6_TO_8 = 12  # Behind by 6-8
    BEHIND_9_TO_12 = 13  # Behind by 9-12
    BEHIND_13_OR_MORE = 14  # Behind by 13+


@dataclass(frozen=True, slots=True)
class GameState:
    """The five game-state buckets one regular situation slot stands for.

    `Profile.game_state` decodes a situation number into one.
    """

    minutes_remaining: MinutesRemaining
    down: Down
    yards_to_go: YardsToGo
    field_position: FieldPosition
    point_spread: PointSpread


@dataclass(frozen=True, slots=True)
class PatGameState:
    """The two game-state buckets one PAT situation slot stands for.

    `Profile.pat_game_state` decodes a PAT situation number into one.
    """

    minutes_remaining: PatMinutesRemaining
    point_spread: PatPointSpread


@dataclass(frozen=True, slots=True)
class Situation:
    """One regular situation's play-calling rules.

    Three weighted play categories and whether the clock should be stopped, such
    as by timeout or spiking the ball. The situation is its position in
    `Profile.situations`; `Profile.game_state` decodes that position into the
    game state.
    """

    stop_clock: bool
    category_weights: CategoryWeights


@dataclass(frozen=True, slots=True)
class PatSituation:
    """One PAT (point-after-touchdown) situation's play-calling rule.

    PAT situations have no stop_clock. The situation is its position in
    `Profile.pat_situations`; `Profile.pat_game_state` decodes that position
    into the game state.
    """

    category_weights: CategoryWeights


# Display-name lookup sets per docs/formats/prf.md section 2.3.2. These describe which
# play_category values the in-game UI labels under each side; they are NOT a
# wire-format constraint, so neither the model nor the reader rejects bytes
# from outside the side's set. Defense covers 0x00-0x15 (the directional pass
# codes 0x07-0x0F all collapse to PASS_LONG/MEDIUM/SHORT in the defense UI);
# 0x16-0x1A are unused on defense. Exposed for downstream consumers that
# want to surface "this code isn't user-facing for this profile type" hints.
OFFENSE_DISPLAY_CATEGORIES: frozenset[int] = frozenset(range(0x00, 0x1B))
DEFENSE_DISPLAY_CATEGORIES: frozenset[int] = frozenset(range(0x00, 0x16))


@dataclass(frozen=True, slots=True)
class CategoryWeights:
    """Three weighted play-category picks used to drive AI play selection.

    Each Profile holds one CategoryWeights record per game situation (indexed by
    the game's internal situation number). `weightN` values are in [0, 10].
    `play_categoryN` values are in [0x00, 0x1A] regardless of the parent
    Profile's side; see `OFFENSE_DISPLAY_CATEGORIES` /
    `DEFENSE_DISPLAY_CATEGORIES` for which codes the game UI labels per side.
    """

    play_category1: int
    """First play-category code, 0x00-0x1A."""

    weight1: int
    """Weight of play_category1, 0-10."""

    play_category2: int
    """Second play-category code, 0x00-0x1A."""

    weight2: int
    """Weight of play_category2, 0-10."""

    play_category3: int
    """Third play-category code, 0x00-0x1A."""

    weight3: int
    """Weight of play_category3, 0-10."""

    def __post_init__(self) -> None:
        for label, value in (
            ("play_category1", self.play_category1),
            ("play_category2", self.play_category2),
            ("play_category3", self.play_category3),
        ):
            if not 0x00 <= value <= 0x1A:
                raise ValueError(f"{label} must be in [0x00, 0x1A], got 0x{value:02X}")
        for label, value in (
            ("weight1", self.weight1),
            ("weight2", self.weight2),
            ("weight3", self.weight3),
        ):
            if not 0 <= value <= 10:
                raise ValueError(f"{label} must be in [0, 10], got {value}")


@dataclass(frozen=True, slots=True)
class Profile:
    """Full in-memory representation of a `.prf` coaching profile file.

    See docs/formats/prf.md for the on-disk binary format. Construction validates
    structural invariants (record counts and field-goal range) via
    __post_init__; ValueError is raised for any violation.
    """

    NUMBER_SITUATIONS: ClassVar[int] = 2520
    NUMBER_PAT_SITUATIONS: ClassVar[int] = 60
    FIELD_GOAL_RANGE_MIN: ClassVar[int] = 5
    FIELD_GOAL_RANGE_MAX: ClassVar[int] = 50
    profile_type: ProfileType
    substitutions: SubstitutionSettings
    situations: tuple[Situation, ...]
    pat_situations: tuple[PatSituation, ...]
    field_goal_range: int
    """Max FG attempt distance; in [FIELD_GOAL_RANGE_MIN, FIELD_GOAL_RANGE_MAX]."""

    use_audibles: bool

    def __post_init__(self) -> None:
        if len(self.situations) != self.NUMBER_SITUATIONS:
            raise ValueError(
                f"situations must have exactly {self.NUMBER_SITUATIONS} "
                f"entries, got {len(self.situations)}"
            )
        if len(self.pat_situations) != self.NUMBER_PAT_SITUATIONS:
            raise ValueError(
                f"pat_situations must have exactly {self.NUMBER_PAT_SITUATIONS} "
                f"entries, got {len(self.pat_situations)}"
            )
        if (
            not self.FIELD_GOAL_RANGE_MIN
            <= self.field_goal_range
            <= self.FIELD_GOAL_RANGE_MAX
        ):
            raise ValueError(
                f"field_goal_range must be in "
                f"[{self.FIELD_GOAL_RANGE_MIN}, {self.FIELD_GOAL_RANGE_MAX}], "
                f"got {self.field_goal_range}"
            )

    @property
    def is_offense(self) -> bool:
        return self.profile_type == ProfileType.OFFENSE

    @property
    def is_defense(self) -> bool:
        return self.profile_type == ProfileType.DEFENSE

    @staticmethod
    def game_state(situation_number: int) -> GameState:
        """Decode a 1-based situation number into its game state.

        The layout is docs/formats/prf.md section 2.3.4.

        Raises:
            ValueError: situation_number is outside [1, 2520].
        """
        if not 1 <= situation_number <= Profile.NUMBER_SITUATIONS:
            raise ValueError(
                f"situation_number must be in [1, {Profile.NUMBER_SITUATIONS}], "
                f"got {situation_number}"
            )

        # Convert 1-based situation_number to 0-based offset for the math, then
        # decode by peeling off each bucket largest-stride-first.
        offset = situation_number - 1
        minutes_idx = offset // 504
        rem = offset % 504
        down_idx = rem // 126  # 0-based
        rem = rem % 126

        if rem < 35:
            yards_idx, field_idx, spread_idx = 0, rem // 7, rem % 7
        elif rem < 70:
            rem -= 35
            yards_idx, field_idx, spread_idx = 1, rem // 7, rem % 7
        elif rem < 98:
            rem -= 70
            yards_idx, field_idx, spread_idx = 2, (rem // 7) + 1, rem % 7
        else:  # rem < 126
            rem -= 98
            yards_idx, field_idx, spread_idx = 3, (rem // 7) + 1, rem % 7

        return GameState(
            minutes_remaining=MinutesRemaining(minutes_idx),
            down=Down(down_idx + 1),
            yards_to_go=YardsToGo(yards_idx),
            field_position=FieldPosition(field_idx),
            point_spread=PointSpread(spread_idx),
        )

    @staticmethod
    def pat_game_state(situation_number: int) -> PatGameState:
        """Decode a 1-based PAT situation number into its game state.

        The layout is docs/formats/prf.md section 2.5.1.

        Raises:
            ValueError: situation_number is outside [1, 60].
        """
        if not 1 <= situation_number <= Profile.NUMBER_PAT_SITUATIONS:
            raise ValueError(
                f"situation_number must be in [1, {Profile.NUMBER_PAT_SITUATIONS}], "
                f"got {situation_number}"
            )
        offset = situation_number - 1
        return PatGameState(
            minutes_remaining=PatMinutesRemaining(offset // 15),
            point_spread=PatPointSpread(offset % 15),
        )

    def iter_situations(self) -> Iterator[tuple[int, GameState, Situation]]:
        """Walk the situations in slot order with each one's number and game state.

        Yields:
            `(situation_number, GameState, Situation)` for every slot, numbers
            from 1.
        """
        for number, situation in enumerate(self.situations, start=1):
            yield number, self.game_state(number), situation

    def iter_pat_situations(
        self,
    ) -> Iterator[tuple[int, PatGameState, PatSituation]]:
        """Walk the PAT situations in slot order with each one's number and state.

        Yields:
            `(situation_number, PatGameState, PatSituation)` for every slot,
            numbers from 1.
        """
        for number, pat in enumerate(self.pat_situations, start=1):
            yield number, self.pat_game_state(number), pat

    @property
    def stop_clock_situations(self) -> tuple[tuple[int, GameState, Situation], ...]:
        """Return the walk's entries for the situations with stop_clock set.

        Only the 2520 regular game-state situations are inspected. PAT situations
        are not included since they have no stop_clock concept.

        Returns:
            Tuple of `(situation_number, GameState, Situation)` triples for
            situations where `stop_clock` is True, in ascending situation_number
            order.
        """
        return tuple(
            (number, state, situation)
            for number, state, situation in self.iter_situations()
            if situation.stop_clock
        )
