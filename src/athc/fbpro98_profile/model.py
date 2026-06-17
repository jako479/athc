"""In-memory data model for FbPro98 .prf coaching profile files.

Defines the immutable types that the reader produces and the writer consumes:
ProfileType, SubstitutionPair, SubstitutionSettings, CategoryWeights, and the
top-level Profile dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import ClassVar

OFFENSIVE_CATEGORIES = {
    0x01: "Run Right",
    0x03: "Pass Short Right",
    0x05: "Run Left",
    0x07: "Pass Short Left",
    0x09: "Run Middle",
    0x0B: "Pass Short Middle",
    0x0D: "Razzle Dazzle Run",
    0x0F: "Razzle Dazzle Pass",
    0x13: "Pass Medium Right",
    0x17: "Pass Medium Left",
    0x1B: "Pass Medium Middle",
    0x23: "Pass Long Right",
    0x27: "Pass Long Left",
    0x2B: "Pass Long Middle",
    0x31: "Goal Line Run",
    0x33: "Goal Line Pass",
    0xFF: "User Specific",
}

DEFENSIVE_CATEGORIES = {
    0x00: "Run Right",
    0x02: "Pass Short",
    0x04: "Run Left",
    0x08: "Run Middle",
    0x0C: "Run Dazzle",
    0x0E: "Pass Dazzle",
    0x12: "Pass Medium",
    0x22: "Pass Long",
    0x30: "Goal Line Run",
    0x32: "Goal Line Pass",
    0xFE: "User Specific",
}

SPECIAL_TEAMS_OFFENSIVE_CATEGORIES = {
    0x01: "Field Goal/PAT",
    0x02: "Kickoff",
    0x03: "Punt",
    0x04: "Onside Kick",
    0x05: "Fake FG Run",
    0x06: "Fake FG Pass",
    0x07: "Fake Punt Run",
    0x08: "Fake Punt Pass",
    0x09: "Free Kick",
    0x0A: "Squib Kick",
}

SPECIAL_TEAMS_DEFENSIVE_CATEGORIES = {
    0x01: "Field Goal/PAT Defense",
    0x02: "Kick Return",
    0x03: "Punt Return",
    0x04: "Onside Return",
    0x05: "Fake FG Run Defense",
    0x06: "Fake FG Pass Defense",
    0x07: "Fake Punt Run Defense",
    0x08: "Fake Punt Pass Defense",
    0x09: "Free Kick Return",
    0x0A: "Squib Return",
}


class ProfileType(IntEnum):
    """Whether a profile is for defense (0) or offense (1). Encoded in I95 data."""

    DEFENSE = 0
    OFFENSE = 1


@dataclass(frozen=True, slots=True)
class SubstitutionPair:
    """One position group's `out`/`in` substitution thresholds (each 0-100, out <= in).

    See specs/prf.md section 2.2 for the on-disk layout.
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
class Situation:
    """Game situation details and corresponding play-calling rules.

    Each Situation holds the game situation details (minutes remaining bucket, down,
    yard-to-go bucket, field position bucket, and point spread bucket) and the
    corresponding play-calling rules: three weighted play categories and whether the
    clock should be stopped such as by timeout or spiking the ball.

    `situation_number` is the situation's domain identifier (1-based, 1..2520);
    its game state is structurally determined by it. Construction validates
    that all six values are mutually consistent.
    """

    situation_number: int
    """Domain identifier, 1-based (1..2520); encodes the game state below."""

    # Game situation
    minutes_remaining: MinutesRemaining
    down: Down
    yards_to_go: YardsToGo
    field_position: FieldPosition
    point_spread: PointSpread

    # Play-calling rules
    stop_clock: bool
    category_weights: CategoryWeights

    def __post_init__(self) -> None:
        if not 1 <= self.situation_number <= 2520:
            raise ValueError(
                f"situation_number must be in [1, 2520), got {self.situation_number}"
            )
        expected = self._situation_number_from_game_state(
            self.minutes_remaining,
            self.down,
            self.yards_to_go,
            self.field_position,
            self.point_spread,
        )
        if expected != self.situation_number:
            raise ValueError(
                f"situation_number {self.situation_number} does not match "
                f"game state (expected {expected})"
            )

    @classmethod
    def from_situation_number(
        cls,
        situation_number: int,
        stop_clock: bool,
        category_weights: CategoryWeights,
    ) -> Situation:
        """Build a Situation by decoding situation_number into its game state."""
        minutes, down, yards, field, spread = cls._game_state_from_situation_number(
            situation_number
        )
        return cls(
            situation_number=situation_number,
            minutes_remaining=minutes,
            down=down,
            yards_to_go=yards,
            field_position=field,
            point_spread=spread,
            stop_clock=stop_clock,
            category_weights=category_weights,
        )

    @staticmethod
    def _game_state_from_situation_number(
        situation_number: int,
    ) -> tuple[MinutesRemaining, Down, YardsToGo, FieldPosition, PointSpread]:
        """Decode situation_number into the five game-state buckets.

        Raises ValueError if situation_number is outside [1, 2520].
        """
        if not 1 <= situation_number <= 2520:
            raise ValueError(
                f"situation_number must be in [1, 2520], got {situation_number}"
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

        return (
            MinutesRemaining(minutes_idx),
            Down(down_idx + 1),
            YardsToGo(yards_idx),
            FieldPosition(field_idx),
            PointSpread(spread_idx),
        )

    @staticmethod
    def _situation_number_from_game_state(
        minutes_remaining: MinutesRemaining,
        down: Down,
        yards_to_go: YardsToGo,
        field_position: FieldPosition,
        point_spread: PointSpread,
    ) -> int:
        """Encode the five game-state buckets into situation_number.

        Raises ValueError on the structurally-invalid combo (6-10 or >10
        yards-to-go from inside the DEF 5).
        """
        yards_idx = yards_to_go.value
        field_idx = field_position.value

        if yards_idx >= 2 and field_idx == 0:
            raise ValueError(
                f"invalid combo: {yards_to_go.name} yards-to-go "
                f"from {field_position.name}"
            )

        section_start = (minutes_remaining.value * 4 + (down.value - 1)) * 126

        if yards_idx == 0:
            within = field_idx * 7 + point_spread.value
        elif yards_idx == 1:
            within = 35 + field_idx * 7 + point_spread.value
        elif yards_idx == 2:
            within = 70 + (field_idx - 1) * 7 + point_spread.value
        else:  # yards_idx == 3
            within = 98 + (field_idx - 1) * 7 + point_spread.value

        # Math yields a 0-based offset; situation_number is 1-based.
        return section_start + within + 1


@dataclass(frozen=True, slots=True)
class PatSituation:
    """PAT (point-after-touchdown) game situation and its play-calling rule.

    PAT situations vary only by minutes remaining and point spread — down,
    yards-to-go, field position, and stop_clock don't apply.

    `situation_number` is the PAT situation's domain identifier (1-based, 1..60);
    its game state is structurally determined by it. Construction validates that
    the three values are mutually consistent.
    """

    situation_number: int
    """Domain identifier, 1-based (1..60); encodes the game state below."""

    # Game situation
    minutes_remaining: PatMinutesRemaining
    point_spread: PatPointSpread

    # Play-calling rules
    category_weights: CategoryWeights

    def __post_init__(self) -> None:
        if not 1 <= self.situation_number <= 60:
            raise ValueError(
                f"situation_number must be in [1, 60], got {self.situation_number}"
            )
        expected = self._situation_number_from_game_state(
            self.minutes_remaining, self.point_spread
        )
        if expected != self.situation_number:
            raise ValueError(
                f"situation_number {self.situation_number} does not match "
                f"game state (expected {expected})"
            )

    @classmethod
    def from_situation_number(
        cls,
        situation_number: int,
        category_weights: CategoryWeights,
    ) -> PatSituation:
        """Build a PatSituation by decoding situation_number into its game state."""
        minutes, spread = cls._game_state_from_situation_number(situation_number)
        return cls(
            situation_number=situation_number,
            minutes_remaining=minutes,
            point_spread=spread,
            category_weights=category_weights,
        )

    @staticmethod
    def _game_state_from_situation_number(
        situation_number: int,
    ) -> tuple[PatMinutesRemaining, PatPointSpread]:
        """Decode situation_number into the two PAT game-state buckets.

        Raises ValueError if situation_number is outside [1, 60].
        """
        if not 1 <= situation_number <= 60:
            raise ValueError(
                f"situation_number must be in [1, 60], got {situation_number}"
            )
        offset = situation_number - 1
        minutes_idx = offset // 15
        spread_idx = offset % 15
        return PatMinutesRemaining(minutes_idx), PatPointSpread(spread_idx)

    @staticmethod
    def _situation_number_from_game_state(
        minutes_remaining: PatMinutesRemaining,
        point_spread: PatPointSpread,
    ) -> int:
        """Encode the two PAT game-state buckets into situation_number."""
        return minutes_remaining.value * 15 + point_spread.value + 1


# Display-name lookup sets per specs/prf.md section 2.3.2. These describe which
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

    See specs/prf.md for the on-disk binary format. Construction validates
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

    @property
    def stop_clock_situations(self) -> tuple[tuple[int, Situation], ...]:
        """Return `(situation_number, Situation)` for situations with stop_clock set.

        Only the 2520 regular game-state situations are inspected. PAT situations
        are not included since they have no stop_clock concept.

        Returns:
            Tuple of `(situation_number, Situation)` pairs for situations where
            `stop_clock` is True, in ascending situation_number order.
        """
        return tuple((s.situation_number, s) for s in self.situations if s.stop_clock)
