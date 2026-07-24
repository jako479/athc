"""Phase-1 matchup builder for Scheduler C (fixed-place + CP-SAT).

Two non-conference games per team are fixed by division standings: each team
plays the same-place finisher in both other-conference divisions (5th places
play each other, one game). One CP-SAT solve picks the remaining games,
tilting each team's average opponent conference rank (1-9, whole slate) by
`c_spread`: best team hardest, worst easiest, linear between.

Self-contained on purpose: owns its table and difficulty line.

Inventory rules enforced here:
- Each team plays 16 total games.
- Every divisional opponent twice; every same-conference opponent once.
- 5-team divisions play 4 non-conference games; 4-team divisions play 5.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ortools.sat.python import cp_model

from athc.scheduler.config import (
    DEFAULT_DIFFICULTY_C_SPREAD,
    DEFAULT_PHASE1_TIME_LIMIT,
)
from athc.scheduler.domain.league import (
    TEAMS_PER_CONFERENCE,
    Conference,
    ConferenceRankings,
    Division,
    Team,
)
from athc.scheduler.domain.schedule import (
    GAMES_PER_WEEK,
    NUM_WEEKS,
    nonconference_games_for,
)
from athc.scheduler.schedulers.errors import SchedulerError
from athc.scheduler.schedulers.types import Matchup, MatchupPlan, make_matchup

# Fixed non-conference games per (division, place) slot (symmetric): places
# 1-4 play both same-place finishers; the 5th places play each other.
_PlaceSlot = tuple[Division, int]
FIXED_NONCONF_PLACE_OPPONENTS: dict[_PlaceSlot, tuple[_PlaceSlot, ...]] = {
    (Division.AFC_EAST, 1): ((Division.NFC_EAST, 1), (Division.NFC_WEST, 1)),
    (Division.AFC_EAST, 2): ((Division.NFC_EAST, 2), (Division.NFC_WEST, 2)),
    (Division.AFC_EAST, 3): ((Division.NFC_EAST, 3), (Division.NFC_WEST, 3)),
    (Division.AFC_EAST, 4): ((Division.NFC_EAST, 4), (Division.NFC_WEST, 4)),
    (Division.AFC_WEST, 1): ((Division.NFC_EAST, 1), (Division.NFC_WEST, 1)),
    (Division.AFC_WEST, 2): ((Division.NFC_EAST, 2), (Division.NFC_WEST, 2)),
    (Division.AFC_WEST, 3): ((Division.NFC_EAST, 3), (Division.NFC_WEST, 3)),
    (Division.AFC_WEST, 4): ((Division.NFC_EAST, 4), (Division.NFC_WEST, 4)),
    (Division.AFC_WEST, 5): ((Division.NFC_WEST, 5),),
    (Division.NFC_EAST, 1): ((Division.AFC_EAST, 1), (Division.AFC_WEST, 1)),
    (Division.NFC_EAST, 2): ((Division.AFC_EAST, 2), (Division.AFC_WEST, 2)),
    (Division.NFC_EAST, 3): ((Division.AFC_EAST, 3), (Division.AFC_WEST, 3)),
    (Division.NFC_EAST, 4): ((Division.AFC_EAST, 4), (Division.AFC_WEST, 4)),
    (Division.NFC_WEST, 1): ((Division.AFC_EAST, 1), (Division.AFC_WEST, 1)),
    (Division.NFC_WEST, 2): ((Division.AFC_EAST, 2), (Division.AFC_WEST, 2)),
    (Division.NFC_WEST, 3): ((Division.AFC_EAST, 3), (Division.AFC_WEST, 3)),
    (Division.NFC_WEST, 4): ((Division.AFC_EAST, 4), (Division.AFC_WEST, 4)),
    (Division.NFC_WEST, 5): ((Division.AFC_WEST, 5),),
}

TOP_HALF_MAX_RANK = 5
BOTTOM_HALF_MIN_RANK = 5

# Difficulty line: target average opponent conference rank (1-9). c_spread
# tilts it (0 = flat at 5; 2.5 = max useful tilt).
CONF_RANK_CENTER = 5
CONF_RANK_HALF_RANGE = 4

# Deviations are scored in 1/DIFFICULTY_SCALE-rank units. 20 = LCM(4, 5) keeps
# opponent_rank_sum * (DIFFICULTY_SCALE / games) an exact integer for both the
# 4- and 5-non-conference-game teams.
DIFFICULTY_SCALE = 20


def _validate_fixed_place_table() -> None:
    expected_slots = {
        (division, place)
        for division in Division
        for place in range(1, division.expected_size + 1)
    }
    if set(FIXED_NONCONF_PLACE_OPPONENTS) != expected_slots:
        raise SchedulerError(
            "Fixed non-conference place table must define every (division, place)"
        )
    for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items():
        division, place = slot
        label = f"{division.name} place {place}"
        expected = 1 if place == 5 else 2
        if len(opponents) != expected or len(set(opponents)) != expected:
            raise SchedulerError(
                f"{label} must have exactly {expected} distinct fixed opponents"
            )
        for opp in opponents:
            if opp not in FIXED_NONCONF_PLACE_OPPONENTS:
                raise SchedulerError(f"{label} references invalid slot {opp}")
            if opp[0].conference == division.conference:
                raise SchedulerError(f"{label} references a same-conference slot")
            if slot not in FIXED_NONCONF_PLACE_OPPONENTS[opp]:
                raise SchedulerError(
                    f"Fixed non-conference place table is not symmetric: {label} -> "
                    f"{opp[0].name} place {opp[1]} without the reverse edge"
                )


def difficulty_target(
    conf_rank: int, c_spread: float = DEFAULT_DIFFICULTY_C_SPREAD
) -> float:
    """Target average opponent conference rank for a team of `conf_rank` (1-9)."""
    return CONF_RANK_CENTER + c_spread * (conf_rank - CONF_RANK_CENTER) / (
        CONF_RANK_HALF_RANGE
    )


class _FixedCpsatNonConferenceModel:
    """Select every AFC/NFC matchup with the fixed place-table pairs forced in.

    `fixed_pairs` are pinned to 1 before solving, so the line objective only
    chooses the remaining slots around them.
    """

    def __init__(
        self,
        ranked_teams_by_conf: Mapping[Conference, Sequence[Team]],
        conf_rank: dict[Team, int],
        fixed_pairs: frozenset[Matchup],
        c_spread: float = DEFAULT_DIFFICULTY_C_SPREAD,
    ) -> None:
        self.model = cp_model.CpModel()
        self.conf_rank = conf_rank
        self.fixed_pairs = fixed_pairs
        self.c_spread = c_spread
        self.afc_teams = list(ranked_teams_by_conf[Conference.AFC])
        self.nfc_teams = list(ranked_teams_by_conf[Conference.NFC])
        self.teams = tuple(self.afc_teams + self.nfc_teams)
        # Name "x" is OR-Tools convention; key is [AFC team, NFC team].
        self.x: dict[tuple[Team, Team], cp_model.IntVar] = {}
        self.opponent_rank_sum: dict[Team, cp_model.IntVar] = {}

        for afc_team in self.afc_teams:
            for nfc_team in self.nfc_teams:
                self.x[afc_team, nfc_team] = self.model.new_bool_var(
                    f"nc_{afc_team.metro}_{nfc_team.metro}"
                )

    def _var_for_pair(self, team: Team, opponent: Team) -> cp_model.IntVar:
        if team.conference == Conference.AFC:
            return self.x[team, opponent]
        return self.x[opponent, team]

    def _opponents_for(self, team: Team) -> list[Team]:
        return self.nfc_teams if team.conference == Conference.AFC else self.afc_teams

    def _add_fixed_pair_constraints(self) -> None:
        for team_a, team_b in self.fixed_pairs:
            afc, nfc = (
                (team_a, team_b)
                if team_a.conference == Conference.AFC
                else (team_b, team_a)
            )
            self.model.add(self.x[afc, nfc] == 1)

    def _add_degree_constraints(self) -> None:
        for afc_team in self.afc_teams:
            self.model.add(
                sum(self.x[afc_team, nfc_team] for nfc_team in self.nfc_teams)
                == nonconference_games_for(afc_team.division)
            )
        for nfc_team in self.nfc_teams:
            self.model.add(
                sum(self.x[afc_team, nfc_team] for afc_team in self.afc_teams)
                == nonconference_games_for(nfc_team.division)
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
            score = self.model.new_int_var(
                nonconference_games_for(team.division),
                TEAMS_PER_CONFERENCE * nonconference_games_for(team.division),
                f"nc_rank_sum_{team.metro}",
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
        # Score each team's deviation from its line target in
        # 1/DIFFICULTY_SCALE-rank units, then minimize the largest deviation
        # (minimax) and, as a tie-break, the total (minisum). The tie-break
        # weight exceeds any possible total, so the largest is minimized first.
        deviations: list[cp_model.IntVar] = []
        max_dev = DIFFICULTY_SCALE * TEAMS_PER_CONFERENCE
        for team in self.teams:
            games = nonconference_games_for(team.division)
            scaled_sum = self.opponent_rank_sum[team] * (DIFFICULTY_SCALE // games)
            target = round(
                difficulty_target(self.conf_rank[team], self.c_spread)
                * DIFFICULTY_SCALE
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

    def solve(self, seed: int = 0, time_limit: float | None = None) -> set[Matchup]:
        solver = cp_model.CpSolver()
        # Single worker + fixed seed = reproducible; the seed picks among
        # equally-optimal matchup sets.
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = seed
        solver.parameters.randomize_search = True
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = time_limit

        status = solver.solve(self.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulerError(
                f"Fixed-place + CP-SAT non-conference model returned status "
                f"{solver.status_name(status)} - no feasible inventory"
            )

        return {
            make_matchup(afc_team, nfc_team)
            for (afc_team, nfc_team), var in self.x.items()
            if solver.value(var) == 1
        }


class FixedCpsatMatchupBuilder:
    def __init__(
        self,
        teams: Sequence[Team],
        rankings: ConferenceRankings,
        division_standings: Mapping[Division, Sequence[Team]] | None,
        c_spread: float = DEFAULT_DIFFICULTY_C_SPREAD,
        phase1_time_limit: float = DEFAULT_PHASE1_TIME_LIMIT,
        seed: int = 0,
    ) -> None:
        self.teams = teams
        self.rankings = rankings
        self.division_standings = division_standings
        self.c_spread = c_spread
        self.phase1_time_limit = phase1_time_limit
        self.seed = seed

        self.ranked_teams_by_conf: dict[Conference, tuple[Team, ...]] = {
            Conference.AFC: rankings.afc,
            Conference.NFC: rankings.nfc,
        }
        self.conf_rank = {team: rankings.rank_of(team) for team in self.teams}
        self.matchups: list[Matchup] = []
        self.selected_nonconference: set[Matchup] = set()
        self.remaining_nonconference = {
            team: nonconference_games_for(team.division) for team in self.teams
        }
        self.fixed_nonconference_pairs: set[Matchup] = set()

    def _add_divisional_matchups(self) -> None:
        for i, team_i in enumerate(self.teams):
            for team_j in self.teams[i + 1 :]:
                if team_i.division == team_j.division:
                    pair = make_matchup(team_i, team_j)
                    self.matchups.append(pair)
                    self.matchups.append(pair)

    def _add_conference_matchups(self) -> None:
        for i, team_i in enumerate(self.teams):
            for team_j in self.teams[i + 1 :]:
                if (
                    team_i.conference == team_j.conference
                    and team_i.division != team_j.division
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

    def _fixed_place_pairs(self) -> set[Matchup]:
        assert self.division_standings is not None  # checked in build_matchup_plan
        team_at: dict[_PlaceSlot, Team] = {
            (division, index + 1): team
            for division, order in self.division_standings.items()
            for index, team in enumerate(order)
        }
        return {
            make_matchup(team_at[slot], team_at[opp])
            for slot, opponents in FIXED_NONCONF_PLACE_OPPONENTS.items()
            for opp in opponents
        }

    def _solve_nonconference_pairs(self, fixed_pairs: set[Matchup]) -> set[Matchup]:
        model = _FixedCpsatNonConferenceModel(
            ranked_teams_by_conf=self.ranked_teams_by_conf,
            conf_rank=self.conf_rank,
            fixed_pairs=frozenset(fixed_pairs),
            c_spread=self.c_spread,
        )
        model.build()
        return model.solve(seed=self.seed, time_limit=self.phase1_time_limit)

    def build_matchup_plan(self) -> MatchupPlan:
        if self.division_standings is None:
            raise SchedulerError(
                "Scheduler C needs the league file's [DivisionStandings] section"
            )
        _validate_fixed_place_table()
        self._add_divisional_matchups()
        self._add_conference_matchups()

        fixed_pairs = self._fixed_place_pairs()
        self.fixed_nonconference_pairs = set(fixed_pairs)
        nonconference_pairs = self._solve_nonconference_pairs(fixed_pairs)
        if not fixed_pairs <= nonconference_pairs:
            raise SchedulerError(
                "CP-SAT solve dropped a fixed place-table non-conference pair"
            )
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
        if len(self.selected_nonconference) != 40:
            raise SchedulerError(
                f"Expected 40 non-conference games, got "
                f"{len(self.selected_nonconference)}"
            )
        if len(self.matchups) != (NUM_WEEKS * GAMES_PER_WEEK):
            raise SchedulerError(
                f"Expected {NUM_WEEKS * GAMES_PER_WEEK} total matchups in phase-1 "
                f"inventory, got {len(self.matchups)}"
            )

        return MatchupPlan(
            matchups=tuple(self.matchups),
            fixed_nonconference_pairs=frozenset(self.fixed_nonconference_pairs),
        )
