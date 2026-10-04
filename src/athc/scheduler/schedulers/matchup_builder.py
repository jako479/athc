"""Phase-1 matchup builder for the scheduler (two-phase CP-SAT).

Structure fixes the same-conference games: every divisional rival twice (a
league with divisions) and every other conference team once. The rest of each
team's `weeks` are non-conference games. Some are fixed -- the same-place pairs
(each division place plays the same place in every other-conference division
that has that place) and any cross-conference rivalry -- and one CP-SAT solve
picks the remainder, tilting each team's average opponent conference rank (1-9,
whole slate) by `spread`: best team hardest, worst easiest, linear between.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from ortools.sat.python import cp_model

from athc.scheduler.config import (
    DEFAULT_DIFFICULTY_SPREAD,
    DEFAULT_PHASE1_TIME_LIMIT,
    DEFAULT_SOLVER_WORKERS,
    DEFAULT_WEEKS,
)
from athc.scheduler.domain.league import (
    TEAMS_PER_CONFERENCE,
    League,
    RivalryPair,
    Team,
)
from athc.scheduler.domain.schedule import GAMES_PER_WEEK
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.types import Matchup, MatchupPlan, make_matchup
from athc.scheduler.schedulers.utils import make_solver

TOP_HALF_MAX_RANK = 5
BOTTOM_HALF_MIN_RANK = 5

# Difficulty line: target average opponent conference rank (1-9). spread
# tilts it (0 = flat at 5; 2.5 = max useful tilt).
CONF_RANK_CENTER = 5
CONF_RANK_HALF_RANGE = 4

# Deviations are scored in 1/scale-rank units. The scale is the LCM of this and
# every non-conference game count, so opponent_rank_sum * (scale / games) is an
# exact integer for every team (20 for both leagues' 4- and 5-game teams).
DIFFICULTY_SCALE = 20


def difficulty_target(
    conf_rank: int, spread: float = DEFAULT_DIFFICULTY_SPREAD
) -> float:
    """Target average opponent conference rank for a team of `conf_rank` (1-9)."""
    return CONF_RANK_CENTER + spread * (conf_rank - CONF_RANK_CENTER) / (
        CONF_RANK_HALF_RANGE
    )


class _NonConferenceModel:
    """Select every cross-conference matchup with the fixed pairs forced in.

    `rows` are the first conference's teams and `columns` the second's, both in
    conference-rank order (the grid order is part of the pinned models).
    `fixed_pairs` are pinned to 1 before solving, so the line objective only
    chooses the remaining slots around them.
    """

    def __init__(
        self,
        rows: Sequence[Team],
        columns: Sequence[Team],
        conf_rank: Mapping[Team, int],
        nonconference_games: Mapping[Team, int],
        fixed_pairs: frozenset[Matchup],
        spread: float = DEFAULT_DIFFICULTY_SPREAD,
    ) -> None:
        self.model = cp_model.CpModel()
        self.conf_rank = conf_rank
        self.nonconference_games = nonconference_games
        self.fixed_pairs = fixed_pairs
        self.spread = spread
        self.rows = list(rows)
        self.columns = list(columns)
        self.row_conference = self.rows[0].conference
        self.teams = tuple(self.rows + self.columns)
        self.scale = math.lcm(DIFFICULTY_SCALE, *nonconference_games.values())
        # Name "x" is OR-Tools convention; key is [row team, column team].
        self.x: dict[tuple[Team, Team], cp_model.IntVar] = {}
        self.opponent_rank_sum: dict[Team, cp_model.IntVar] = {}

        for row in self.rows:
            for column in self.columns:
                self.x[row, column] = self.model.new_bool_var(
                    f"nc_{row.metro}_{column.metro}"
                )

    def _var_for_pair(self, team: Team, opponent: Team) -> cp_model.IntVar:
        if team.conference == self.row_conference:
            return self.x[team, opponent]
        return self.x[opponent, team]

    def _opponents_for(self, team: Team) -> list[Team]:
        return self.columns if team.conference == self.row_conference else self.rows

    def _add_fixed_pair_constraints(self) -> None:
        # Sorted: a frozenset iterates in hash order, which differs per process,
        # and the built model must be identical for a seed to reproduce.
        for team_a, team_b in sorted(
            self.fixed_pairs, key=lambda pair: (pair[0].metro, pair[1].metro)
        ):
            row, column = (
                (team_a, team_b)
                if team_a.conference == self.row_conference
                else (team_b, team_a)
            )
            self.model.add(self.x[row, column] == 1)

    def _add_degree_constraints(self) -> None:
        for row in self.rows:
            self.model.add(
                sum(self.x[row, column] for column in self.columns)
                == self.nonconference_games[row]
            )
        for column in self.columns:
            self.model.add(
                sum(self.x[row, column] for row in self.rows)
                == self.nonconference_games[column]
            )

    def _add_top_bottom_constraints(self) -> None:
        for team in self.teams:
            opponents = self._opponents_for(team)
            top_half_vars = [
                self._var_for_pair(team, opponent)
                for opponent in opponents
                if self.conf_rank[opponent] <= TOP_HALF_MAX_RANK
            ]
            bottom_half_vars = [
                self._var_for_pair(team, opponent)
                for opponent in opponents
                if self.conf_rank[opponent] >= BOTTOM_HALF_MIN_RANK
            ]
            self.model.add(sum(top_half_vars) >= 1)
            self.model.add(sum(bottom_half_vars) >= 1)

    def _add_opponent_rank_sum_constraints(self) -> None:
        for team in self.teams:
            opponents = self._opponents_for(team)
            games = self.nonconference_games[team]
            score = self.model.new_int_var(
                games, TEAMS_PER_CONFERENCE * games, f"nc_rank_sum_{team.metro}"
            )
            self.model.add(
                score
                == sum(
                    self.conf_rank[opponent] * self._var_for_pair(team, opponent)
                    for opponent in opponents
                )
            )
            self.opponent_rank_sum[team] = score

    def _set_line_objective(self) -> None:
        # Score each team's deviation from its line target in 1/scale-rank
        # units, then minimize the largest deviation (minimax) and, as a
        # tie-break, the total (minisum). The tie-break weight exceeds any
        # possible total, so the largest is minimized first.
        deviations: list[cp_model.IntVar] = []
        max_dev = self.scale * TEAMS_PER_CONFERENCE
        for team in self.teams:
            games = self.nonconference_games[team]
            scaled_sum = self.opponent_rank_sum[team] * (self.scale // games)
            target = round(
                difficulty_target(self.conf_rank[team], self.spread) * self.scale
            )
            dev = self.model.new_int_var(0, max_dev, f"nc_dev_{team.metro}")
            self.model.add(dev >= scaled_sum - target)
            self.model.add(dev >= target - scaled_sum)
            deviations.append(dev)
        worst = self.model.new_int_var(0, max_dev, "nc_worst_dev")
        for dev in deviations:
            self.model.add(worst >= dev)
        tie_break = len(self.teams) * max_dev + 1
        self.model.minimize(tie_break * worst + sum(deviations))

    def build(self) -> None:
        self._add_fixed_pair_constraints()
        self._add_degree_constraints()
        self._add_top_bottom_constraints()
        self._add_opponent_rank_sum_constraints()
        self._set_line_objective()

    def solve(
        self,
        seed: int = 0,
        time_limit: float = DEFAULT_PHASE1_TIME_LIMIT,
        workers: int = DEFAULT_SOLVER_WORKERS,
    ) -> set[Matchup]:
        # The seed picks among equally-optimal matchup sets.
        solver = make_solver(seed=seed, time_limit=time_limit, workers=workers)
        status = solver.solve(self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulerError(
                f"Two-phase CP-SAT non-conference model returned status "
                f"{solver.status_name(status)} - no feasible inventory"
            )

        return {
            make_matchup(row, column)
            for (row, column), var in self.x.items()
            if solver.value(var) == 1
        }


class MatchupBuilder:
    def __init__(
        self,
        league: League,
        *,
        weeks: int = DEFAULT_WEEKS,
        rivalries: Sequence[RivalryPair] = (),
        spread: float = DEFAULT_DIFFICULTY_SPREAD,
        phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT,
        workers: int = DEFAULT_SOLVER_WORKERS,
        seed: int = 0,
    ) -> None:
        self.league = league
        self.teams = league.teams
        self.rankings = league.rankings
        self.weeks = weeks
        self.rivalries = tuple(rivalries)
        self.spread = spread
        self.phase1_time_limit = phase1_time_limit
        self.workers = workers
        self.seed = seed

        self.conf_rank = {team: league.rankings.rank_of(team) for team in self.teams}
        self.nonconference_games = {
            team: league.nonconference_games(team, weeks) for team in self.teams
        }
        self.matchups: list[Matchup] = []
        self.selected_nonconference: set[Matchup] = set()
        self.remaining_nonconference = dict(self.nonconference_games)
        self.fixed_nonconference_pairs: set[Matchup] = set()

    def _add_divisional_matchups(self) -> None:
        for i, team_i in enumerate(self.teams):
            for team_j in self.teams[i + 1 :]:
                if team_i.same_division(team_j):
                    pair = make_matchup(team_i, team_j)
                    self.matchups.append(pair)
                    self.matchups.append(pair)

    def _add_conference_matchups(self) -> None:
        for i, team_i in enumerate(self.teams):
            for team_j in self.teams[i + 1 :]:
                if team_i.conference == team_j.conference and not team_i.same_division(
                    team_j
                ):
                    self.matchups.append(make_matchup(team_i, team_j))

    def _add_nonconference_pairs(self, pairs: set[Matchup]) -> None:
        for i, j in sorted(pairs, key=lambda p: (p[0].metro, p[1].metro)):
            pair = (i, j)
            if pair in self.selected_nonconference:
                raise SchedulerError(
                    f"Duplicate non-conference pair in phase-1 inventory: {pair}"
                )
            self.matchups.append(pair)
            self.selected_nonconference.add(pair)
            self.remaining_nonconference[i] -= 1
            self.remaining_nonconference[j] -= 1
            if (
                self.remaining_nonconference[i] < 0
                or self.remaining_nonconference[j] < 0
            ):
                raise SchedulerError(
                    f"Non-conference slot count went negative after reserving pair "
                    f"{pair}"
                )

    def _same_place_pairs(self) -> set[Matchup]:
        """Each division place plays the same place in every other-conference
        division that has that place; none for a league without divisions."""
        standings = self.league.division_standings
        return {
            make_matchup(team, other_order[place])
            for division, order in standings.items()
            for other, other_order in standings.items()
            if other.conference != division.conference
            for place, team in enumerate(order)
            if place < len(other_order)
        }

    def _rivalry_pairs(self) -> set[Matchup]:
        """Cross-conference rivalries are non-conference games the solver must keep."""
        return {
            make_matchup(a, b)
            for a, b in self.rivalries
            if a.conference != b.conference
        }

    def _nonconference_model(self, fixed_pairs: set[Matchup]) -> _NonConferenceModel:
        """The built (unsolved) non-conference model; tests fingerprint it."""
        first, second = self.league.conferences
        model = _NonConferenceModel(
            rows=self.rankings.ranked(first),
            columns=self.rankings.ranked(second),
            conf_rank=self.conf_rank,
            nonconference_games=self.nonconference_games,
            fixed_pairs=frozenset(fixed_pairs),
            spread=self.spread,
        )
        model.build()
        return model

    def build_matchup_plan(self) -> MatchupPlan:
        self._add_divisional_matchups()
        self._add_conference_matchups()

        fixed_pairs = self._same_place_pairs() | self._rivalry_pairs()
        self.fixed_nonconference_pairs = set(fixed_pairs)
        nonconference_pairs = self._nonconference_model(fixed_pairs).solve(
            seed=self.seed, time_limit=self.phase1_time_limit, workers=self.workers
        )
        if not fixed_pairs <= nonconference_pairs:
            raise SchedulerError("CP-SAT solve dropped a fixed non-conference pair")
        self._add_nonconference_pairs(nonconference_pairs)

        if any(slots != 0 for slots in self.remaining_nonconference.values()):
            unresolved = {
                team.metro: slots
                for team, slots in self.remaining_nonconference.items()
                if slots != 0
            }
            raise SchedulerError(
                f"Non-conference inventory left unresolved slots: {unresolved}"
            )
        expected_nonconference = sum(self.nonconference_games.values()) // 2
        if len(self.selected_nonconference) != expected_nonconference:
            raise SchedulerError(
                f"Expected {expected_nonconference} non-conference games, got "
                f"{len(self.selected_nonconference)}"
            )
        expected_total = self.weeks * GAMES_PER_WEEK
        if len(self.matchups) != expected_total:
            raise SchedulerError(
                f"Expected {expected_total} total matchups in phase-1 inventory, got "
                f"{len(self.matchups)}"
            )

        return MatchupPlan(
            matchups=tuple(self.matchups),
            fixed_nonconference_pairs=frozenset(self.fixed_nonconference_pairs),
        )
