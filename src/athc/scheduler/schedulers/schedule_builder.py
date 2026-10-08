"""Phase 2 of the scheduler: the CP-SAT model that places a fixed matchup
inventory into weeks and picks each game's host. The rules it enforces, which
of them apply to a given league, and their provenance are documented once, in
docs/scheduler/phase-2-schedule.md.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from ortools.sat.python import cp_model

from athc.scheduler.config import (
    DEFAULT_SOLVER_WORKERS,
    DEFAULT_TIME_LIMIT,
    DEFAULT_WEEKS,
    ConfigError,
    Phase2Config,
    SolverWorkers,
)
from athc.scheduler.domain.league import League, RivalryPair, Team
from athc.scheduler.domain.schedule import Game, Schedule
from athc.scheduler.schedulers.types import Matchup, Matchups, make_matchup
from athc.scheduler.schedulers.utils import make_solver


class ScheduleBuilder:
    """The phase-2 CP-SAT model: weeks and hosts for a fixed matchup inventory."""

    def __init__(
        self,
        league: League,
        error_cls: type[RuntimeError],
        amounts: Phase2Config | None = None,
        *,
        weeks: int = DEFAULT_WEEKS,
        rivalries: Sequence[RivalryPair] = (),
        rotate_rivalry_home_by_season: bool = True,
        season: int | None = None,
    ) -> None:
        self.model = cp_model.CpModel()
        self.league = league
        self.teams = tuple(league.teams)
        self.error_cls = error_cls
        self.amounts = amounts or Phase2Config()
        self.num_weeks = weeks
        self.weeks = range(weeks)
        self.home_games_per_team = weeks // 2
        self.rivalries = tuple(rivalries)
        self.rotate_rivalry_home_by_season = rotate_rivalry_home_by_season
        self.season = season

        if league.has_divisions and not self.amounts.require_home_away_streak_caps:
            raise ConfigError(
                "require_home_away_streak_caps must be true for a league with "
                "divisions: the soft objective needs the streak flags."
            )
        if self.rivalries and rotate_rivalry_home_by_season and season is None:
            raise error_cls("A season is required to rotate rivalry hosting.")

        self.div_opponents: dict[Team, list[Team]] = {
            team: list(league.divisional_opponents(team)) for team in self.teams
        }

        self.four_team_set: set[Team] = {
            t
            for t in self.teams
            if t.division is not None and t.division.expected_size == 4
        }
        self.five_team_set: set[Team] = {
            t
            for t in self.teams
            if t.division is not None and t.division.expected_size == 5
        }
        # Canonical-order tuples for constraint building. Iterating the sets
        # above would follow Python's per-process hash-randomized order, making
        # the built model (and thus the solved schedule) non-reproducible across
        # runs. The sets stay for membership tests; iterate these for building.
        self.four_team_teams: tuple[Team, ...] = tuple(
            t for t in self.teams if t in self.four_team_set
        )
        self.five_team_teams: tuple[Team, ...] = tuple(
            t for t in self.teams if t in self.five_team_set
        )

        self.divisional_pairs: list[Matchup] = []
        self.conference_pairs: list[Matchup] = []
        self.non_conference_pairs: list[Matchup] = []
        for idx, team_i in enumerate(self.teams):
            for team_j in self.teams[idx + 1 :]:
                pair = make_matchup(team_i, team_j)
                if team_i.same_division(team_j):
                    self.divisional_pairs.append(pair)
                elif team_i.conference == team_j.conference:
                    self.conference_pairs.append(pair)
                else:
                    self.non_conference_pairs.append(pair)

        self.x: dict[tuple[Team, Team, int], cp_model.IntVar] = {}
        for team_i in self.teams:
            for team_j in self.teams:
                if team_i == team_j:
                    continue
                for w in self.weeks:
                    self.x[team_i, team_j, w] = self.model.new_bool_var(
                        f"x_{team_i.metro}_{team_j.metro}_w{w}"
                    )

        self.h: dict[tuple[Team, int], cp_model.IntVar] = {}
        for team_i in self.teams:
            for w in self.weeks:
                self.h[team_i, w] = self.model.new_bool_var(f"h_{team_i.metro}_w{w}")
                self.model.add(
                    self.h[team_i, w]
                    == sum(
                        self.x[team_i, team_j, w]
                        for team_j in self.teams
                        if team_j != team_i
                    )
                )

        # d is only meaningful with divisions; a divisionless league gets none.
        self.d: dict[tuple[Team, int], cp_model.IntVar] = {}
        if league.has_divisions:
            for team_i in self.teams:
                for w in self.weeks:
                    self.d[team_i, w] = self.model.new_bool_var(
                        f"d_{team_i.metro}_w{w}"
                    )
                    self.model.add(
                        self.d[team_i, w]
                        == sum(
                            self.x[team_i, opp, w] + self.x[opp, team_i, w]
                            for opp in self.div_opponents[team_i]
                        )
                    )

    def _constraint_one_game_per_week(self) -> None:
        for team_i in self.teams:
            for w in self.weeks:
                self.model.add(
                    sum(
                        self.x[team_i, team_j, w] + self.x[team_j, team_i, w]
                        for team_j in self.teams
                        if team_j != team_i
                    )
                    == 1
                )

    def _constraint_home_balance(self) -> None:
        for team_i in self.teams:
            self.model.add(
                sum(
                    self.x[team_i, team_j, w]
                    for team_j in self.teams
                    if team_j != team_i
                    for w in self.weeks
                )
                == self.home_games_per_team
            )

    def _constraint_max_consecutive_home_or_away(self) -> None:
        # Every (cap + 1)-week window holds at most cap home games and at least
        # one, so neither a home nor an away streak exceeds cap.
        cap = self.amounts.max_consecutive_home_or_away
        window = cap + 1
        for team_i in self.teams:
            for w in range(self.num_weeks - cap):
                self.model.add(self._window_sum(self.h, team_i, w, window) <= cap)
            for w in range(self.num_weeks - cap):
                self.model.add(self._window_sum(self.h, team_i, w, window) >= 1)

    def _window_sum(
        self,
        var: dict[tuple[Team, int], cp_model.IntVar],
        team: Team,
        start: int,
        length: int,
    ) -> cp_model.LinearExprT:
        # Chained addition (not sum()) keeps the expression shape the pinned
        # divisional model was built with.
        expr: cp_model.LinearExprT = var[team, start]
        for k in range(1, length):
            expr = expr + var[team, start + k]
        return expr

    def _constraint_home_away_balance_in_six_game_windows(self) -> None:
        if not self.amounts.require_home_balance_per_six_weeks:
            return
        for team_i in self.teams:
            for w in range(self.num_weeks - 5):
                six_game_home_total = sum(self.h[team_i, w + k] for k in range(6))
                self.model.add(
                    six_game_home_total <= self.amounts.max_home_per_six_weeks
                )
                self.model.add(
                    six_game_home_total >= self.amounts.min_home_per_six_weeks
                )

    def _constraint_no_three_game_home_or_away_streak_at_season_start_or_end(
        self,
    ) -> None:
        if not self.amounts.require_mixed_home_away_at_season_ends:
            return
        for team_i in self.teams:
            self.model.add(
                self.h[team_i, 0] + self.h[team_i, 1] + self.h[team_i, 2] <= 2
            )
            self.model.add(
                self.h[team_i, 0] + self.h[team_i, 1] + self.h[team_i, 2] >= 1
            )
            self.model.add(
                self.h[team_i, self.num_weeks - 3]
                + self.h[team_i, self.num_weeks - 2]
                + self.h[team_i, self.num_weeks - 1]
                <= 2
            )
            self.model.add(
                self.h[team_i, self.num_weeks - 3]
                + self.h[team_i, self.num_weeks - 2]
                + self.h[team_i, self.num_weeks - 1]
                >= 1
            )

    def _constraint_max_one_total_three_game_home_or_away_streak(self) -> None:
        # Streak vars are kept for the league-wide count caps.
        self._streak3h: dict[Team, list[cp_model.IntVar]] = {}
        self._streak3a: dict[Team, list[cp_model.IntVar]] = {}
        if not self.amounts.require_home_away_streak_caps:
            return
        for team_i in self.teams:
            streak3h: list[cp_model.IntVar] = []
            for w in range(self.num_weeks - 2):
                streak = self.model.new_bool_var(f"s3h_{team_i.metro}_w{w}")
                self.model.add_bool_and(
                    [self.h[team_i, w], self.h[team_i, w + 1], self.h[team_i, w + 2]]
                ).only_enforce_if(streak)
                self.model.add_bool_or(
                    [
                        self.h[team_i, w].Not(),
                        self.h[team_i, w + 1].Not(),
                        self.h[team_i, w + 2].Not(),
                    ]
                ).only_enforce_if(streak.Not())
                streak3h.append(streak)

            streak3a: list[cp_model.IntVar] = []
            for w in range(self.num_weeks - 2):
                streak = self.model.new_bool_var(f"s3a_{team_i.metro}_w{w}")
                self.model.add_bool_and(
                    [
                        self.h[team_i, w].Not(),
                        self.h[team_i, w + 1].Not(),
                        self.h[team_i, w + 2].Not(),
                    ]
                ).only_enforce_if(streak)
                self.model.add_bool_or(
                    [self.h[team_i, w], self.h[team_i, w + 1], self.h[team_i, w + 2]]
                ).only_enforce_if(streak.Not())
                streak3a.append(streak)

            self.model.add(
                sum(streak3h) + sum(streak3a)
                <= self.amounts.max_three_game_home_away_streaks
            )
            self._streak3h[team_i] = streak3h
            self._streak3a[team_i] = streak3a

    def _constraint_no_back_to_back(self) -> None:
        if not self.league.has_divisions:
            return
        for idx, team_i in enumerate(self.teams):
            for team_j in self.teams[idx + 1 :]:
                for w in range(self.num_weeks - 1):
                    self.model.add(
                        self.x[team_i, team_j, w]
                        + self.x[team_j, team_i, w]
                        + self.x[team_i, team_j, w + 1]
                        + self.x[team_j, team_i, w + 1]
                        <= 1
                    )

    def _constraint_phase_one_inventory(self, phase_one_inventory: Matchups) -> None:
        expected_counts = Counter(phase_one_inventory)
        all_pairs = (
            self.divisional_pairs + self.conference_pairs + self.non_conference_pairs
        )

        unknown_pairs = set(expected_counts) - set(all_pairs)
        if unknown_pairs:
            pretty = sorted((a.metro, b.metro) for a, b in unknown_pairs)
            raise self.error_cls(
                f"Phase-1 inventory contains unknown team pairs: {pretty}"
            )

        for team_i, team_j in all_pairs:
            total_meetings = sum(
                self.x[team_i, team_j, w] + self.x[team_j, team_i, w]
                for w in self.weeks
            )
            self.model.add(total_meetings == expected_counts.get((team_i, team_j), 0))

    def _constraint_divisional_home_balance(self) -> None:
        if not self.league.has_divisions:
            return
        for team_i, team_j in self.divisional_pairs:
            self.model.add(sum(self.x[team_i, team_j, w] for w in self.weeks) == 1)
            self.model.add(sum(self.x[team_j, team_i, w] for w in self.weeks) == 1)

    def _constraint_conference_home_balance(self) -> None:
        for team_i in self.teams:
            opponents = self.league.conference_opponents(team_i)
            self._add_half_home(team_i, opponents, len(opponents))

    def _constraint_nonconference_home_balance(self) -> None:
        # The sum spans every other-conference team; the inventory decides which
        # of them are played, so the bounds come from the team's game count.
        for team_i in self.teams:
            opponents = [t for t in self.teams if t.conference != team_i.conference]
            count = self.league.nonconference_games(team_i, self.num_weeks)
            self._add_half_home(team_i, opponents, count)

    def _add_half_home(
        self, team_i: Team, opponents: Sequence[Team], count: int
    ) -> None:
        # One `==` when the half is exact, else `>=` then `<=`: the shapes the
        # pinned divisional model was built with.
        home_games = sum(
            self.x[team_i, team_j, w] for team_j in opponents for w in self.weeks
        )
        lo, hi = count // 2, (count + 1) // 2
        if lo == hi:
            self.model.add(home_games == lo)
        else:
            self.model.add(home_games >= lo)
            self.model.add(home_games <= hi)

    def _constraint_max_consecutive_division(self) -> None:
        if not self.league.has_divisions:
            return
        for team_i in self.teams:
            for w in range(self.num_weeks - 3):
                self.model.add(
                    self.d[team_i, w]
                    + self.d[team_i, w + 1]
                    + self.d[team_i, w + 2]
                    + self.d[team_i, w + 3]
                    <= self.amounts.max_consecutive_divisional
                )

    def _constraint_max_teams_divisional_weeks_1_and_2(self) -> None:
        self._opening_two_div_flags: list[cp_model.IntVar] = []
        if not self.league.has_divisions:
            return
        opening_back_to_back: list[cp_model.IntVar] = []
        four_team_openers: list[cp_model.IntVar] = []
        five_team_openers: list[cp_model.IntVar] = []
        for team_i in self.teams:
            opens_with_two_div = self.model.new_bool_var(f"open2div_{team_i.metro}")
            self.model.add(opens_with_two_div <= self.d[team_i, 0])
            self.model.add(opens_with_two_div <= self.d[team_i, 1])
            self.model.add(
                opens_with_two_div >= self.d[team_i, 0] + self.d[team_i, 1] - 1
            )
            opening_back_to_back.append(opens_with_two_div)
            if team_i in self.five_team_set:
                five_team_openers.append(opens_with_two_div)
            else:
                four_team_openers.append(opens_with_two_div)

        self.model.add(
            sum(opening_back_to_back) <= self.amounts.max_teams_divisional_weeks_1_and_2
        )
        self.model.add(
            sum(four_team_openers)
            <= self.amounts.four_team_max_teams_open_divisional_pair
        )
        self.model.add(
            sum(five_team_openers)
            <= self.amounts.five_team_max_teams_open_divisional_pair
        )
        self._opening_two_div_flags = opening_back_to_back

    def _constraint_no_three_game_divisional_streak_at_season_start_or_end(
        self,
    ) -> None:
        if not self.league.has_divisions:
            return
        for team_i in self.teams:
            self.model.add(
                self.d[team_i, 0] + self.d[team_i, 1] + self.d[team_i, 2] <= 2
            )
            self.model.add(
                self.d[team_i, self.num_weeks - 3]
                + self.d[team_i, self.num_weeks - 2]
                + self.d[team_i, self.num_weeks - 1]
                <= 2
            )

    def _constraint_max_one_total_three_game_divisional_streak(self) -> None:
        # Streak vars are kept for the league-wide count cap.
        self._streak3d: dict[Team, list[cp_model.IntVar]] = {}
        if not self.league.has_divisions:
            return
        for team_i in self.teams:
            streak3d: list[cp_model.IntVar] = []
            for w in range(self.num_weeks - 2):
                streak = self.model.new_bool_var(f"s3d_{team_i.metro}_w{w}")
                self.model.add_bool_and(
                    [self.d[team_i, w], self.d[team_i, w + 1], self.d[team_i, w + 2]]
                ).only_enforce_if(streak)
                self.model.add_bool_or(
                    [
                        self.d[team_i, w].Not(),
                        self.d[team_i, w + 1].Not(),
                        self.d[team_i, w + 2].Not(),
                    ]
                ).only_enforce_if(streak.Not())
                streak3d.append(streak)
            self.model.add(
                sum(streak3d) <= self.amounts.max_three_game_divisional_streaks
            )
            self._streak3d[team_i] = streak3d

    def _constraint_max_teams_with_streaks(self) -> None:
        # The per-team streak caps alone would let every team have one at once.
        self._streak_team_flags: dict[str, list[cp_model.IntVar]] = {}
        caps: list[tuple[dict[Team, list[cp_model.IntVar]], str, int]] = []
        if self.amounts.require_home_away_streak_caps:
            caps.append(
                (self._streak3h, "has3h", self.amounts.max_teams_with_home_streak)
            )
            caps.append(
                (self._streak3a, "has3a", self.amounts.max_teams_with_away_streak)
            )
        if self.league.has_divisions:
            caps.append(
                (
                    self._streak3d,
                    "has3d",
                    self.amounts.max_teams_with_divisional_streak,
                )
            )
        for streaks, label, cap in caps:
            flags: list[cp_model.IntVar] = []
            for team_i in self.teams:
                flag = self.model.new_bool_var(f"{label}_{team_i.metro}")
                self.model.add_max_equality(flag, streaks[team_i])
                flags.append(flag)
            self.model.add(sum(flags) <= cap)
            # Keep the per-team "has a streak" flags for the soft objective.
            self._streak_team_flags[label] = flags

    def _constraint_division_density(self) -> None:
        if not self.league.has_divisions:
            return
        for team_i in self.five_team_teams:
            for w in range(self.num_weeks - 8):
                self.model.add(
                    sum(self.d[team_i, w + k] for k in range(9))
                    <= self.amounts.five_team_max_divisional_in_9
                )
        for team_i in self.four_team_teams:
            for w in range(self.num_weeks - 6):
                self.model.add(
                    sum(self.d[team_i, w + k] for k in range(7))
                    <= self.amounts.four_team_max_divisional_in_7
                )

    def _front_load_windows(self, team_i: Team) -> list[tuple[int, int]]:
        # (window, cap) pairs limiting early divisional games, by division size.
        if team_i in self.five_team_set:
            return [
                (5, self.amounts.five_team_max_divisional_first_5),
                (6, self.amounts.five_team_max_divisional_first_6),
                (8, self.amounts.five_team_max_divisional_first_8),
                (10, self.amounts.five_team_max_divisional_first_10),
            ]
        return [
            (4, self.amounts.four_team_max_divisional_first_4),
            (8, self.amounts.four_team_max_divisional_first_8),
            (10, self.amounts.four_team_max_divisional_first_10),
        ]

    def _constraint_divisional_front_load(self) -> None:
        if not self.league.has_divisions:
            return
        for team_i in self.teams:
            for window, cap in self._front_load_windows(team_i):
                self.model.add(sum(self.d[team_i, w] for w in range(window)) <= cap)

    def _constraint_max_close_rematches(self) -> None:
        # A gap of 2 is the only close rematch left: back-to-back is already
        # forbidden.
        self._close_rematch_flags: list[cp_model.IntVar] = []
        if not self.league.has_divisions:
            return
        close_flags: list[cp_model.IntVar] = []
        for team_i, team_j in self.divisional_pairs:
            wh = sum(w * self.x[team_i, team_j, w] for w in self.weeks)
            wa = sum(w * self.x[team_j, team_i, w] for w in self.weeks)
            gap = self.model.new_int_var(
                0, self.num_weeks - 1, f"gap_{team_i.metro}_{team_j.metro}"
            )
            self.model.add_abs_equality(gap, wh - wa)
            flag = self.model.new_bool_var(f"close_{team_i.metro}_{team_j.metro}")
            self.model.add(gap <= 2).only_enforce_if(flag)
            self.model.add(gap >= 3).only_enforce_if(flag.Not())
            close_flags.append(flag)
        self.model.add(sum(close_flags) <= self.amounts.max_close_rematches)
        self._close_rematch_flags = close_flags

    def _constraint_max_two_non_interleaved_divisional_opponents(self) -> None:
        # A divisional opponent is interleaved if another rival's first or second
        # meeting falls between the team's two meetings with that opponent.
        self._two_bunched_flags: list[cp_model.IntVar] = []
        if not self.league.has_divisions:
            return
        bunch_flags: list[cp_model.IntVar] = []
        for team_i in self.teams:
            opps = self.div_opponents[team_i]
            first_meet: dict[Team, cp_model.IntVar] = {}
            second_meet: dict[Team, cp_model.IntVar] = {}
            for opp in opps:
                wh = self.model.new_int_var(
                    0, self.num_weeks - 1, f"wh_{team_i.metro}_{opp.metro}"
                )
                wa = self.model.new_int_var(
                    0, self.num_weeks - 1, f"wa_{team_i.metro}_{opp.metro}"
                )
                self.model.add(
                    wh == sum(w * self.x[team_i, opp, w] for w in self.weeks)
                )
                self.model.add(
                    wa == sum(w * self.x[opp, team_i, w] for w in self.weeks)
                )
                w1 = self.model.new_int_var(
                    0, self.num_weeks - 1, f"fm_{team_i.metro}_{opp.metro}"
                )
                w2 = self.model.new_int_var(
                    0, self.num_weeks - 1, f"sm_{team_i.metro}_{opp.metro}"
                )
                self.model.add_min_equality(w1, [wh, wa])
                self.model.add_max_equality(w2, [wh, wa])
                first_meet[opp] = w1
                second_meet[opp] = w2

            interleaved: list[cp_model.IntVar] = []
            for opp in opps:
                il = self.model.new_bool_var(f"il_{team_i.metro}_{opp.metro}")
                between_vars: list[cp_model.IntVar] = []
                for other in opps:
                    if other == opp:
                        continue
                    bk1 = self.model.new_bool_var(
                        f"btw_{team_i.metro}_{opp.metro}_{other.metro}_1"
                    )
                    self.model.add(first_meet[other] > first_meet[opp]).only_enforce_if(
                        bk1
                    )
                    self.model.add(
                        first_meet[other] < second_meet[opp]
                    ).only_enforce_if(bk1)
                    between_vars.append(bk1)
                    bk2 = self.model.new_bool_var(
                        f"btw_{team_i.metro}_{opp.metro}_{other.metro}_2"
                    )
                    self.model.add(
                        second_meet[other] > first_meet[opp]
                    ).only_enforce_if(bk2)
                    self.model.add(
                        second_meet[other] < second_meet[opp]
                    ).only_enforce_if(bk2)
                    between_vars.append(bk2)
                self.model.add_bool_or(between_vars).only_enforce_if(il)
                interleaved.append(il)

            self.model.add(
                sum(interleaved)
                >= len(opps) - self.amounts.max_non_interleaved_divisional_opponents
            )

            # Flag teams with 2+ non-interleaved rivals for the league-wide cap.
            flag = self.model.new_bool_var(f"bunch2_{team_i.metro}")
            self.model.add(sum(interleaved) <= len(opps) - 2).only_enforce_if(flag)
            self.model.add(sum(interleaved) >= len(opps) - 1).only_enforce_if(
                flag.Not()
            )
            bunch_flags.append(flag)

        self.model.add(
            sum(bunch_flags) <= self.amounts.max_teams_with_two_bunched_rivals
        )
        self._two_bunched_flags = bunch_flags

    def _constraint_final_week_divisional(self) -> None:
        if (
            not self.league.has_divisions
            or not self.amounts.require_final_week_divisional
        ):
            return
        last_week = self.num_weeks - 1
        self.model.add(
            sum(
                self.x[team_i, team_j, last_week] + self.x[team_j, team_i, last_week]
                for team_i, team_j in self.divisional_pairs
            )
            == self.league.max_divisional_games_per_week
        )

    def _constraint_late_divisional_presence(self) -> None:
        if not self.league.has_divisions:
            return
        if not self.amounts.require_divisional_in_final_two_weeks:
            return
        for team_i in self.teams:
            self.model.add(
                self.d[team_i, self.num_weeks - 2] + self.d[team_i, self.num_weeks - 1]
                >= 1
            )

    def _constraint_opening_nonconference_weeks(self) -> None:
        n = self.amounts.opening_nonconference_weeks
        if n == 0:
            return
        for team_i in self.teams:
            opponents = self.league.same_conference_opponents(team_i)
            for w in range(n):
                self.model.add(
                    sum(
                        self.x[team_i, opp, w] + self.x[opp, team_i, w]
                        for opp in opponents
                    )
                    == 0
                )

    def _constraint_max_consecutive_conference_home_or_away(self) -> None:
        # A streak runs along the team's conference games only, so non-conference
        # weeks between them do not break it. For every window at least cap + 1
        # long, the conference home games are capped unless the window also holds
        # a conference away game (which makes the bound slack), and the mirror.
        cap = self.amounts.max_consecutive_conference_home_or_away
        if cap == 0:
            return
        for team_i in self.teams:
            opponents = self.league.same_conference_opponents(team_i)
            home = [
                sum(self.x[team_i, opp, w] for opp in opponents) for w in self.weeks
            ]
            away = [
                sum(self.x[opp, team_i, w] for opp in opponents) for w in self.weeks
            ]
            for length in range(cap + 1, self.num_weeks + 1):
                for start in range(self.num_weeks - length + 1):
                    span = range(start, start + length)
                    home_in = sum(home[w] for w in span)
                    away_in = sum(away[w] for w in span)
                    self.model.add(home_in <= cap + length * away_in)
                    self.model.add(away_in <= cap + length * home_in)

    def _constraint_rivalry_final_week(self) -> None:
        if not self.rivalries:
            return
        last = self.num_weeks - 1
        for first, second in self.rivalries:
            if self.rotate_rivalry_home_by_season:
                assert self.season is not None  # checked in __init__
                home, away = (
                    (first, second) if self.season % 2 == 0 else (second, first)
                )
                self.model.add(self.x[home, away, last] == 1)
            else:
                self.model.add(
                    self.x[first, second, last] + self.x[second, first, last] == 1
                )

    def _add_soft_objective(self) -> None:
        # Without an objective the solver camps at the hard caps. Each metric pays
        # `weight` per step outside its band [lo, hi] and nothing inside.
        if not self.league.has_divisions:
            return
        a = self.amounts
        n = len(self.teams)
        penalties: list[cp_model.LinearExpr] = []

        def band(count, lo: int, hi: int, weight: int, name: str, ub: int) -> None:
            over = self.model.new_int_var(0, ub, f"soft_over_{name}")
            under = self.model.new_int_var(0, ub, f"soft_under_{name}")
            self.model.add(over >= count - hi)
            self.model.add(under >= lo - count)
            penalties.append(weight * over)
            penalties.append(weight * under)

        # Flags for teams at the front-load ceiling, so the objective can keep that
        # count NFL-typical instead of letting every team max it.
        four_team_frontload_flags: list[cp_model.IntVar] = []
        for team_i in self.four_team_teams:
            early8 = sum(self.d[team_i, w] for w in range(8))
            flag = self.model.new_bool_var(f"front8at3_{team_i.metro}")
            self.model.add(early8 >= 3).only_enforce_if(flag)
            self.model.add(early8 <= 2).only_enforce_if(flag.Not())
            four_team_frontload_flags.append(flag)
        five_team_frontload_flags: list[cp_model.IntVar] = []
        for team_i in self.five_team_teams:
            early10 = sum(self.d[team_i, w] for w in range(10))
            flag = self.model.new_bool_var(f"front10at6_{team_i.metro}")
            self.model.add(early10 >= 6).only_enforce_if(flag)
            self.model.add(early10 <= 5).only_enforce_if(flag.Not())
            five_team_frontload_flags.append(flag)

        band(
            sum(self._streak_team_flags["has3h"]),
            a.soft_home_streak_lo,
            a.soft_home_streak_hi,
            a.soft_home_streak_weight,
            "home_streak",
            n,
        )
        band(
            sum(self._streak_team_flags["has3a"]),
            a.soft_away_streak_lo,
            a.soft_away_streak_hi,
            a.soft_away_streak_weight,
            "away_streak",
            n,
        )
        band(
            sum(self._streak_team_flags["has3d"]),
            a.soft_divisional_streak_lo,
            a.soft_divisional_streak_hi,
            a.soft_divisional_streak_weight,
            "divisional_streak",
            n,
        )
        band(
            sum(four_team_frontload_flags),
            a.soft_four_team_frontload_lo,
            a.soft_four_team_frontload_hi,
            a.soft_four_team_frontload_weight,
            "four_team_frontload",
            len(self.four_team_set),
        )
        band(
            sum(five_team_frontload_flags),
            a.soft_five_team_frontload_lo,
            a.soft_five_team_frontload_hi,
            a.soft_five_team_frontload_weight,
            "five_team_frontload",
            len(self.five_team_set),
        )
        band(
            sum(self._two_bunched_flags),
            a.soft_non_interleaved_lo,
            a.soft_non_interleaved_hi,
            a.soft_non_interleaved_weight,
            "non_interleaved",
            n,
        )
        band(
            sum(self._close_rematch_flags),
            a.soft_close_rematches_lo,
            a.soft_close_rematches_hi,
            a.soft_close_rematches_weight,
            "close_rematches",
            len(self.divisional_pairs),
        )
        band(
            sum(self._opening_two_div_flags),
            a.soft_open_weeks_1_2_lo,
            a.soft_open_weeks_1_2_hi,
            a.soft_open_weeks_1_2_weight,
            "open_weeks_1_2",
            n,
        )

        self.model.minimize(sum(penalties))

    def _populate_model(self, matchups: Matchups) -> None:
        self._constraint_one_game_per_week()
        self._constraint_home_balance()
        self._constraint_max_consecutive_home_or_away()
        self._constraint_home_away_balance_in_six_game_windows()
        self._constraint_no_three_game_home_or_away_streak_at_season_start_or_end()
        self._constraint_max_one_total_three_game_home_or_away_streak()
        self._constraint_no_back_to_back()
        self._constraint_max_close_rematches()
        self._constraint_phase_one_inventory(matchups)
        self._constraint_divisional_home_balance()
        self._constraint_conference_home_balance()
        self._constraint_nonconference_home_balance()
        self._constraint_max_consecutive_division()
        self._constraint_max_teams_divisional_weeks_1_and_2()
        self._constraint_no_three_game_divisional_streak_at_season_start_or_end()
        self._constraint_max_one_total_three_game_divisional_streak()
        self._constraint_max_teams_with_streaks()
        self._constraint_division_density()
        self._constraint_divisional_front_load()
        self._constraint_max_two_non_interleaved_divisional_opponents()
        self._constraint_final_week_divisional()
        self._constraint_late_divisional_presence()
        self._constraint_opening_nonconference_weeks()
        self._constraint_max_consecutive_conference_home_or_away()
        self._constraint_rivalry_final_week()
        self._add_soft_objective()

    def _solve_model(
        self,
        seed: int = 0,
        time_limit: float = DEFAULT_TIME_LIMIT,
        workers: SolverWorkers = DEFAULT_SOLVER_WORKERS,
    ) -> Schedule:
        solver = make_solver(seed=seed, time_limit=time_limit, workers=workers)
        status = solver.solve(self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise self.error_cls(
                f"CP-SAT returned status {solver.status_name(status)} - no feasible "
                f"schedule"
            )

        games: list[Game] = []
        for (team_i, team_j, w), var in self.x.items():
            if solver.value(var) == 1:
                games.append(Game(week=w + 1, home=team_i, away=team_j))

        return Schedule(games=tuple(games))

    def build_schedule(
        self,
        matchups: Matchups,
        seed: int = 0,
        time_limit: float = DEFAULT_TIME_LIMIT,
        workers: SolverWorkers = DEFAULT_SOLVER_WORKERS,
    ) -> Schedule:
        self._populate_model(matchups=matchups)
        return self._solve_model(seed=seed, time_limit=time_limit, workers=workers)
