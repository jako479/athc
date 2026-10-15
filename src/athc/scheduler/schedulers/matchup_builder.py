"""Phase-1 matchup builder for the scheduler (two-phase CP-SAT).

Structure fixes the same-conference games: every divisional rival twice (a
league with divisions) and every other conference team once. The rest of each
team's `weeks` are non-conference games. Some are fixed -- the same-place pairs
(each division place plays the same place in every other-conference division
that has that place) and any cross-conference rivalry -- and one CP-SAT solve
picks the remainder along the difficulty line: each team's opponent conference
ranks (1-9) add up close to a target tilted by `difficulty_slope`, best team
hardest, worst easiest, linear between. With `random_nonconference` the
remainder is random from the run's seed instead.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

from ortools.sat.python import cp_model

from athc.scheduler.config import (
    DEFAULT_DIFFICULTY_SLOPE,
    DEFAULT_PHASE1_TIME_LIMIT,
    DEFAULT_SOLVER_WORKERS,
    DEFAULT_WEEKS,
    SolverWorkers,
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
from athc.scheduler.schedulers.utils import make_solver, run_solver

# Difficulty line: a team's target sum of opponent conference ranks (1-9). The
# slope tilts the per-game target (0 = flat at 5) over the league's smallest
# non-conference count; each game past that adds a neutral 5, so a team with
# an extra game gets no extra tilt.
CONF_RANK_CENTER = 5
CONF_RANK_HALF_RANGE = 4

# Misses are scored in 1/DIFFICULTY_SCALE-rank units, the target rounded to
# the unit.
DIFFICULTY_SCALE = 20

# Random non-conference games: each pairing's weight is drawn from the seed in
# 0..RANDOM_WEIGHT_RANGE-1, and the solve keeps the heaviest set.
RANDOM_WEIGHT_RANGE = 1_000_000


def difficulty_target(
    conf_rank: int,
    games: int,
    tilted_games: int,
    slope: float = DEFAULT_DIFFICULTY_SLOPE,
) -> float:
    """Target sum of opponent conference ranks for a team of `conf_rank` (1-9)
    with `games` non-conference games: `tilted_games` of them (the league's
    smallest non-conference count) tilted by `slope`, the rest a neutral 5."""
    tilt = slope * (conf_rank - CONF_RANK_CENTER) / CONF_RANK_HALF_RANGE
    return CONF_RANK_CENTER * games + tilted_games * tilt


class _NonConferenceModel:
    """Select every cross-conference matchup with the fixed pairs forced in.

    `rows` are the first conference's teams and `columns` the second's, both in
    conference-rank order (the grid order is part of the pinned models).
    `fixed_pairs` are pinned to 1; `build_line` or `build_random` then sets the
    objective that chooses the remaining slots around them.
    """

    def __init__(
        self,
        rows: Sequence[Team],
        columns: Sequence[Team],
        conf_rank: Mapping[Team, int],
        nonconference_games: Mapping[Team, int],
        fixed_pairs: frozenset[Matchup],
    ) -> None:
        self.model = cp_model.CpModel()
        self.conf_rank = conf_rank
        self.nonconference_games = nonconference_games
        self.fixed_pairs = fixed_pairs
        self.rows = list(rows)
        self.columns = list(columns)
        self.row_conference = self.rows[0].conference
        self.teams = tuple(self.rows + self.columns)
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

    def _set_line_objective(self, slope: float) -> None:
        # Score each team's miss (its opponent rank sum minus its target) in
        # 1/DIFFICULTY_SCALE-rank units, then minimize the largest miss
        # (minimax) and, as a tie-break, the total (minisum). The tie-break
        # weight exceeds any possible total, so the largest is minimized first.
        tilted_games = min(self.nonconference_games.values())
        misses: list[cp_model.IntVar] = []
        bounds: list[int] = []
        for team in self.teams:
            games = self.nonconference_games[team]
            target = round(
                difficulty_target(self.conf_rank[team], games, tilted_games, slope)
                * DIFFICULTY_SCALE
            )
            # The rank sum spans games..9 x games, so this bounds the miss
            # whatever the slope.
            bound = max(
                abs(DIFFICULTY_SCALE * games - target),
                abs(DIFFICULTY_SCALE * TEAMS_PER_CONFERENCE * games - target),
            )
            scaled_sum = self.opponent_rank_sum[team] * DIFFICULTY_SCALE
            miss = self.model.new_int_var(0, bound, f"nc_miss_{team.metro}")
            self.model.add(miss >= scaled_sum - target)
            self.model.add(miss >= target - scaled_sum)
            misses.append(miss)
            bounds.append(bound)
        worst = self.model.new_int_var(0, max(bounds), "nc_worst_miss")
        for miss in misses:
            self.model.add(worst >= miss)
        tie_break = sum(bounds) + 1
        self.model.minimize(tie_break * worst + sum(misses))

    def build_line(self, slope: float) -> None:
        """The difficulty line: each team's opponent rank sum near its target."""
        self._add_fixed_pair_constraints()
        self._add_degree_constraints()
        self._add_opponent_rank_sum_constraints()
        self._set_line_objective(slope)

    def _set_random_objective(self, seed: int) -> None:
        # Seeded weights make a seed repeat its games on any machine; their own
        # stream keeps them apart from the standings coin toss, which shuffles
        # with random.Random(seed).
        rng = random.Random(f"random_nonconference {seed}")
        self.model.maximize(
            sum(rng.randrange(RANDOM_WEIGHT_RANGE) * var for var in self.x.values())
        )

    def build_random(self, seed: int) -> None:
        """Random games: the heaviest set under seeded random pair weights."""
        self._add_fixed_pair_constraints()
        self._add_degree_constraints()
        self._set_random_objective(seed)

    def solve(
        self,
        seed: int = 0,
        time_limit: float = DEFAULT_PHASE1_TIME_LIMIT,
        workers: SolverWorkers = DEFAULT_SOLVER_WORKERS,
    ) -> set[Matchup]:
        # The seed picks among equally-optimal matchup sets.
        solver = make_solver(seed=seed, time_limit=time_limit, workers=workers)
        status = run_solver(solver, self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulerError(
                f"Two-phase CP-SAT non-conference model returned status "
                f"{solver.status_name(status)} - no feasible inventory."
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
        difficulty_slope: float = DEFAULT_DIFFICULTY_SLOPE,
        random_nonconference: bool = False,
        phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT,
        workers: SolverWorkers = DEFAULT_SOLVER_WORKERS,
        seed: int = 0,
    ) -> None:
        self.league = league
        self.teams = league.teams
        self.rankings = league.rankings
        self.weeks = weeks
        self.rivalries = tuple(rivalries)
        self.difficulty_slope = difficulty_slope
        self.random_nonconference = random_nonconference
        self.phase1_time_limit = phase1_time_limit
        self.workers: SolverWorkers = workers
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
                    "Duplicate non-conference pair in phase-1 inventory: "
                    f"{i.metro} vs {j.metro}."
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
                    "Non-conference slot count went negative after reserving "
                    f"{i.metro} vs {j.metro}."
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
        )
        if self.random_nonconference:
            model.build_random(self.seed)
        else:
            model.build_line(self.difficulty_slope)
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
            raise SchedulerError("CP-SAT solve dropped a fixed non-conference pair.")
        self._add_nonconference_pairs(nonconference_pairs)

        if any(slots != 0 for slots in self.remaining_nonconference.values()):
            unresolved = {
                team.metro: slots
                for team, slots in self.remaining_nonconference.items()
                if slots != 0
            }
            raise SchedulerError(
                "Non-conference inventory left unresolved slots: "
                + ", ".join(f"{metro} {slots}" for metro, slots in unresolved.items())
                + "."
            )
        expected_nonconference = sum(self.nonconference_games.values()) // 2
        if len(self.selected_nonconference) != expected_nonconference:
            raise SchedulerError(
                f"Expected {expected_nonconference} non-conference games, got "
                f"{len(self.selected_nonconference)}."
            )
        expected_total = self.weeks * GAMES_PER_WEEK
        if len(self.matchups) != expected_total:
            raise SchedulerError(
                f"Expected {expected_total} total matchups in phase-1 inventory, got "
                f"{len(self.matchups)}."
            )

        return MatchupPlan(
            matchups=tuple(self.matchups),
            fixed_nonconference_pairs=frozenset(self.fixed_nonconference_pairs),
        )
