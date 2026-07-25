"""
Basic schedule structure and inventory requirements:
- Each team plays 16 total games, exactly 1 in each week.
- Each team hosts exactly 8 games.
- No pair of teams may play each other in back-to-back weeks.

Home/away sequencing requirements:
- No 4 straight home or away games.
- At most 1 total 3-game home/away streak per team.
- No 3-game home/away streak to start or end the season.
- Every 6-game span must contain between 2 and 4 home games.

Divisional scheduling requirements:
- Each team plays every divisional opponent twice, once at home and once away.
- No 4 straight divisional games.
- At most 4 teams open weeks 1-2 with divisional games in both (at most 1 of
  those a 4-team-division team, at most 2 a 5-team-division team).
- No 3 straight divisional games to start or end the season.
- At most 1 total 3-game divisional streak per team.
- 5-team divisions: max 6 divisional games in any 9-game span (forces <=7 in any 10).
- 4-team divisions: max 4 divisional games in any 7-game span.
- Front-load caps: 4-team divisions max 2 divisional games in weeks 1-4, 3 in
  weeks 1-8, 4 in weeks 1-10; 5-team divisions max 3 in weeks 1-5, 4 in weeks
  1-6, 5 in weeks 1-8, 6 in weeks 1-10.
- At most 2 divisional opponents may be non-interleaved between a team's 2
  meetings with that rival.
- Every team must play at least 1 divisional game in the final 2 weeks.
- Week 16 must contain exactly 8 divisional games.

League-wide caps (a per-team rule shouldn't pile up across all teams at once):
- At most 9 teams with a 3-game home streak; 3 with a 3-game away streak.
- At most 6 teams with a 3-game divisional streak.
- At most 2 teams with 2 non-interleaved rivals.
- At most 3 rematches within a 3-week span.

Soft objective (prefer NFL-typical schedules; caps above stay as backstops):
- Penalize 8 season metrics for landing outside an NFL-typical band [lo, hi],
  weighted by rarity. Zero penalty inside the band; linear per step outside.
  Metrics: teams with a 3-game home / away / divisional streak, 4-team-division
  teams at the front-load cap (3 divisional in the first 8 weeks), 5-team-division
  teams at the front-load ceiling (6 divisional in the first 10 weeks), teams with
  2 non-interleaved rivals, close rematches, and teams opening weeks 1-2 divisional.
  Front-load camping is soft for both division sizes (no hard teams-at-max cap).
  Bands/weights are [phase2] settings; see docs/design/research/cpsat-rule-patterns.md.

Conference scheduling requirements:
- Each team plays every same-conference opponent outside its division exactly once.
- Conference home balance:
  - 5-team division teams host exactly 2 of 4.
  - In each 4-team division, the 5 conference games split 2, 2, 3, 3 across the 4 teams.

Non-conference scheduling requirements:
- After divisional and same-conference games are assigned, the remaining schedule slots
  are
  non-conference games.
- 5-team division teams play 4 non-conference games.
- 4-team division teams play 5 non-conference games.
- Non-conference home balance:
  - 5-team division teams host exactly 2 of 4.
  - In each 4-team division, the 5 non-conference games split 2, 2, 3, 3 across the 4
    teams.

Rule provenance (NFL policy vs. measured NFL schedule patterns):
docs/design/research/nfl-schedules.md.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from ortools.sat.python import cp_model

from athc.scheduler.config import (
    DEFAULT_SOLVER_WORKERS,
    DEFAULT_TIME_LIMIT,
    Phase2Config,
)
from athc.scheduler.domain.league import Team
from athc.scheduler.domain.schedule import (
    HOME_GAMES_PER_TEAM,
    NUM_WEEKS,
    WEEK_16_DIVISIONAL_GAMES,
    Game,
    Schedule,
)
from athc.scheduler.schedulers.types import Matchup, Matchups, make_matchup


class ScheduleBuilder:
    """Shared CP-SAT phase-2 placement model for schedulers with fixed matchups."""

    def __init__(
        self,
        teams: Sequence[Team],
        error_cls: type[RuntimeError],
        amounts: Phase2Config | None = None,
    ) -> None:
        self.model = cp_model.CpModel()
        self.teams = tuple(teams)
        self.error_cls = error_cls
        self.amounts = amounts or Phase2Config()

        self.weeks = range(NUM_WEEKS)
        self.home_games_per_team = HOME_GAMES_PER_TEAM

        self.div_opponents: dict[Team, list[Team]] = {}
        for team in self.teams:
            self.div_opponents[team] = [
                opp
                for opp in self.teams
                if opp.division == team.division and opp != team
            ]

        self.four_team_set: set[Team] = {
            t for t in self.teams if t.division.expected_size == 4
        }
        self.five_team_set: set[Team] = {
            t for t in self.teams if t.division.expected_size == 5
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
                if team_i.division == team_j.division:
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

        self.d: dict[tuple[Team, int], cp_model.IntVar] = {}
        for team_i in self.teams:
            for w in self.weeks:
                self.d[team_i, w] = self.model.new_bool_var(f"d_{team_i.metro}_w{w}")
                self.model.add(
                    self.d[team_i, w]
                    == sum(
                        self.x[team_i, opp, w] + self.x[opp, team_i, w]
                        for opp in self.div_opponents[team_i]
                    )
                )

    def _constraint_one_game_per_week(self) -> None:
        # Require each team to play exactly 1 game in each of the 16 weeks.
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
        # Require each team to host exactly 8 home games.
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

    def _constraint_no_four_straight_home_or_away(self) -> None:
        # Every 4-game window caps home games (and, symmetrically, away games) at
        # the max-consecutive amount, so neither a home nor an away streak exceeds it.
        cap = self.amounts.max_consecutive_home_or_away
        for team_i in self.teams:
            for w in range(NUM_WEEKS - 3):
                self.model.add(
                    self.h[team_i, w]
                    + self.h[team_i, w + 1]
                    + self.h[team_i, w + 2]
                    + self.h[team_i, w + 3]
                    <= cap
                )
            for w in range(NUM_WEEKS - 3):
                self.model.add(
                    self.h[team_i, w]
                    + self.h[team_i, w + 1]
                    + self.h[team_i, w + 2]
                    + self.h[team_i, w + 3]
                    >= 4 - cap
                )

    def _constraint_home_away_balance_in_six_game_windows(self) -> None:
        # Every 6-game window must have between 2 and 4 home games, which also forces 2
        # to 4 away games.
        for team_i in self.teams:
            for w in range(NUM_WEEKS - 5):
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
        # The first and last 3 games must each contain at least 1 home and at least 1
        # away game.
        for team_i in self.teams:
            self.model.add(
                self.h[team_i, 0] + self.h[team_i, 1] + self.h[team_i, 2] <= 2
            )
            self.model.add(
                self.h[team_i, 0] + self.h[team_i, 1] + self.h[team_i, 2] >= 1
            )
            self.model.add(
                self.h[team_i, NUM_WEEKS - 3]
                + self.h[team_i, NUM_WEEKS - 2]
                + self.h[team_i, NUM_WEEKS - 1]
                <= 2
            )
            self.model.add(
                self.h[team_i, NUM_WEEKS - 3]
                + self.h[team_i, NUM_WEEKS - 2]
                + self.h[team_i, NUM_WEEKS - 1]
                >= 1
            )

    def _constraint_max_one_total_three_game_home_or_away_streak(self) -> None:
        # Allow at most one 3-game streak total, counting both home and away streaks
        # together. Streak vars are kept for the league-wide count caps.
        self._streak3h: dict[Team, list[cp_model.IntVar]] = {}
        self._streak3a: dict[Team, list[cp_model.IntVar]] = {}
        for team_i in self.teams:
            streak3h: list[cp_model.IntVar] = []
            for w in range(NUM_WEEKS - 2):
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
            for w in range(NUM_WEEKS - 2):
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
        # Prevent any pair of teams from playing in consecutive weeks.
        for idx, team_i in enumerate(self.teams):
            for team_j in self.teams[idx + 1 :]:
                for w in range(NUM_WEEKS - 1):
                    self.model.add(
                        self.x[team_i, team_j, w]
                        + self.x[team_j, team_i, w]
                        + self.x[team_i, team_j, w + 1]
                        + self.x[team_j, team_i, w + 1]
                        <= 1
                    )

    def _constraint_phase_one_inventory(self, phase_one_inventory: Matchups) -> None:
        # Force phase II to schedule each team pair exactly as many times as phase I
        # selected: 0, 1, or 2 meetings.
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
        # Split each divisional home-and-home into exactly 1 home game and 1 away game
        # for each team.
        for team_i, team_j in self.divisional_pairs:
            self.model.add(sum(self.x[team_i, team_j, w] for w in self.weeks) == 1)
            self.model.add(sum(self.x[team_j, team_i, w] for w in self.weeks) == 1)

    def _constraint_conference_home_balance(self) -> None:
        # Balanced hosting (forced by 8 home games): 5-team division teams host
        # exactly 2 of their 4 cross-division games; 4-team teams 2 or 3 of 5.
        for team_i in self.teams:
            conference_opponents = [
                team_j
                for team_j in self.teams
                if team_j != team_i
                and team_j.conference == team_i.conference
                and team_j.division != team_i.division
            ]
            conf_home_games = sum(
                self.x[team_i, team_j, w]
                for team_j in conference_opponents
                for w in self.weeks
            )

            if team_i in self.five_team_set:
                self.model.add(conf_home_games == 2)
            else:
                self.model.add(conf_home_games >= 2)
                self.model.add(conf_home_games <= 3)

    def _constraint_nonconference_home_balance(self) -> None:
        # Balanced hosting: 5-team division teams host exactly 2 of their 4
        # non-conference games; 4-team teams 2 or 3 of 5.
        for team_i in self.teams:
            non_conference_opponents = [
                team_j
                for team_j in self.teams
                if team_j.conference != team_i.conference
            ]
            non_conf_home_games = sum(
                self.x[team_i, team_j, w]
                for team_j in non_conference_opponents
                for w in self.weeks
            )

            if team_i in self.five_team_set:
                self.model.add(non_conf_home_games == 2)
            else:
                self.model.add(non_conf_home_games >= 2)
                self.model.add(non_conf_home_games <= 3)

    def _constraint_max_consecutive_division(self) -> None:
        # Allow at most 3 straight divisional games but forbid any 4-game divisional
        # streak.
        for team_i in self.teams:
            for w in range(NUM_WEEKS - 3):
                self.model.add(
                    self.d[team_i, w]
                    + self.d[team_i, w + 1]
                    + self.d[team_i, w + 2]
                    + self.d[team_i, w + 3]
                    <= self.amounts.max_consecutive_divisional
                )

    def _constraint_max_teams_divisional_weeks_1_and_2(self) -> None:
        # Cap the teams that open with divisional games in both weeks 1 and 2, both
        # league-wide and (more tightly) per division size.
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
            if team_i in self.four_team_set:
                four_team_openers.append(opens_with_two_div)
            else:
                five_team_openers.append(opens_with_two_div)

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
        # Forbid teams from starting or ending the season with 3 straight divisional
        # games.
        for team_i in self.teams:
            self.model.add(
                self.d[team_i, 0] + self.d[team_i, 1] + self.d[team_i, 2] <= 2
            )
            self.model.add(
                self.d[team_i, NUM_WEEKS - 3]
                + self.d[team_i, NUM_WEEKS - 2]
                + self.d[team_i, NUM_WEEKS - 1]
                <= 2
            )

    def _constraint_max_one_total_three_game_divisional_streak(self) -> None:
        # Allow each team at most 1 total 3-game divisional streak across the season.
        # Streak vars are kept for the league-wide count cap.
        self._streak3d: dict[Team, list[cp_model.IntVar]] = {}
        for team_i in self.teams:
            streak3d: list[cp_model.IntVar] = []
            for w in range(NUM_WEEKS - 2):
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
        # League-wide caps on how many teams have a 3-game home, away, or
        # divisional streak (per-team caps allow every team to have one at once).
        self._streak_team_flags: dict[str, list[cp_model.IntVar]] = {}
        caps = (
            (self._streak3h, "has3h", self.amounts.max_teams_with_home_streak),
            (self._streak3a, "has3a", self.amounts.max_teams_with_away_streak),
            (self._streak3d, "has3d", self.amounts.max_teams_with_divisional_streak),
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
        # Cap divisional clustering at 6 in 9 for 5-team divisions (a 9-window cap
        # forces <=7 in any 10); cap at 4 in 7 for 4-team divisions (forces <=5 in 8).
        for team_i in self.five_team_teams:
            for w in range(NUM_WEEKS - 8):
                self.model.add(
                    sum(self.d[team_i, w + k] for k in range(9))
                    <= self.amounts.five_team_max_divisional_in_9
                )
        for team_i in self.four_team_teams:
            for w in range(NUM_WEEKS - 6):
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
        # Cap early divisional games per team (NFL front-load walls).
        for team_i in self.teams:
            for window, cap in self._front_load_windows(team_i):
                self.model.add(sum(self.d[team_i, w] for w in range(window)) <= cap)

    def _constraint_max_close_rematches(self) -> None:
        # League-wide cap on rematches within a 3-week span (meetings 2 weeks
        # apart; back-to-back is already forbidden).
        close_flags: list[cp_model.IntVar] = []
        for team_i, team_j in self.divisional_pairs:
            wh = sum(w * self.x[team_i, team_j, w] for w in self.weeks)
            wa = sum(w * self.x[team_j, team_i, w] for w in self.weeks)
            gap = self.model.new_int_var(
                0, NUM_WEEKS - 1, f"gap_{team_i.metro}_{team_j.metro}"
            )
            self.model.add_abs_equality(gap, wh - wa)
            flag = self.model.new_bool_var(f"close_{team_i.metro}_{team_j.metro}")
            self.model.add(gap <= 2).only_enforce_if(flag)
            self.model.add(gap >= 3).only_enforce_if(flag.Not())
            close_flags.append(flag)
        self.model.add(sum(close_flags) <= self.amounts.max_close_rematches)
        self._close_rematch_flags = close_flags

    def _constraint_max_two_non_interleaved_divisional_opponents(self) -> None:
        # Count a divisional opponent as interleaved if another rival's first or second
        # meeting
        # falls between the team's first and second meeting with that opponent.
        bunch_flags: list[cp_model.IntVar] = []
        for team_i in self.teams:
            opps = self.div_opponents[team_i]
            first_meet: dict[Team, cp_model.IntVar] = {}
            second_meet: dict[Team, cp_model.IntVar] = {}
            for opp in opps:
                wh = self.model.new_int_var(
                    0, NUM_WEEKS - 1, f"wh_{team_i.metro}_{opp.metro}"
                )
                wa = self.model.new_int_var(
                    0, NUM_WEEKS - 1, f"wa_{team_i.metro}_{opp.metro}"
                )
                self.model.add(
                    wh == sum(w * self.x[team_i, opp, w] for w in self.weeks)
                )
                self.model.add(
                    wa == sum(w * self.x[opp, team_i, w] for w in self.weeks)
                )
                w1 = self.model.new_int_var(
                    0, NUM_WEEKS - 1, f"fm_{team_i.metro}_{opp.metro}"
                )
                w2 = self.model.new_int_var(
                    0, NUM_WEEKS - 1, f"sm_{team_i.metro}_{opp.metro}"
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

            # Cap non-interleaved divisional opponents per team.
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

    def _constraint_week_16_matchups(self) -> None:
        # All-divisional finale: 8 of the final week's 9 games (the max; each
        # 5-team division strands one team).
        if not self.amounts.require_final_week_divisional:
            return
        last_week = NUM_WEEKS - 1
        self.model.add(
            sum(
                self.x[team_i, team_j, last_week] + self.x[team_j, team_i, last_week]
                for team_i, team_j in self.divisional_pairs
            )
            == WEEK_16_DIVISIONAL_GAMES
        )

    def _constraint_late_divisional_presence(self) -> None:
        # Every team plays at least 1 divisional game across the last 2 weeks.
        if not self.amounts.require_divisional_in_final_two_weeks:
            return
        for team_i in self.teams:
            self.model.add(
                self.d[team_i, NUM_WEEKS - 2] + self.d[team_i, NUM_WEEKS - 1] >= 1
            )

    def _add_soft_objective(self) -> None:
        # Prefer NFL-typical schedules: penalize each metric for landing outside
        # its band [lo, hi], weighted by rarity. Zero penalty inside the band; a
        # linear penalty per step outside. The hard caps stay as backstops.
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

        # Teams sitting at the front-load cap. Anti-camping: keep this count near
        # NFL-typical instead of all teams maxed. 4-team = 3 divisional in first 8;
        # 5-team = 6 divisional in first 10 (the front-load ceiling).
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
        self._constraint_no_four_straight_home_or_away()
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
        self._constraint_week_16_matchups()
        self._constraint_late_divisional_presence()
        self._add_soft_objective()

    def _make_solver(
        self, seed: int, time_limit: float, workers: int
    ) -> cp_model.CpSolver:
        # Parallel but reproducible. interleave_search is deterministic for a
        # fixed seed AND a fixed `workers` count -- the schedule changes if the
        # count changes -- so `workers` comes from config (solver_workers), never
        # the machine's core count. It stops on deterministic time, not
        # wall-clock, so the result is machine-speed independent; `time_limit` is
        # that deterministic-time budget.
        solver = cp_model.CpSolver()
        solver.parameters.random_seed = seed
        solver.parameters.randomize_search = True
        solver.parameters.num_search_workers = workers
        solver.parameters.interleave_search = True
        solver.parameters.interleave_batch_size = workers
        solver.parameters.max_deterministic_time = time_limit
        return solver

    def _solve_model(
        self,
        seed: int = 0,
        time_limit: float = DEFAULT_TIME_LIMIT,
        workers: int = DEFAULT_SOLVER_WORKERS,
    ) -> Schedule:
        solver = self._make_solver(seed=seed, time_limit=time_limit, workers=workers)
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
        workers: int = DEFAULT_SOLVER_WORKERS,
    ) -> Schedule:
        self._populate_model(matchups=matchups)
        return self._solve_model(seed=seed, time_limit=time_limit, workers=workers)
