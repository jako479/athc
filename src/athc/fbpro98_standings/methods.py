"""The tie-break methods as data.

For division, conference and league standings, each method gives the steps
that sort every team and the tie-breakers for the teams still level. Net
touchdowns, in the game's and the NFL's lists, are not in the league file and
are left out; the coin toss, always last, is the ranking's own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from athc.fbpro98_standings import steps
from athc.fbpro98_standings.steps import Step

Method = Literal["game", "scheduler", "nfl"]
METHODS: tuple[Method, ...] = get_args(Method)


@dataclass(frozen=True, slots=True)
class Rules:
    """How one method orders one kind of standings."""

    sort: tuple[Step, ...]
    """Steps that sort every team, in turn, best first."""

    breakers: tuple[Step, ...]
    """Tie-breakers for the teams level on every sort step."""

    one_advances: bool = False
    """Only the best team of a level group is placed at a time; a step that
    drops some teams sends the rest back to the first tie-breaker (the NFL).
    Otherwise the first tie-breaker that separates a group places its best
    teams, and they and the rest are each ranked again (the game)."""

    by_division_first: bool = False
    """Level teams of one division use the division rules; otherwise only
    each division's best goes on (the NFL's wild-card and draft rules)."""


@dataclass(frozen=True, slots=True)
class MethodRules:
    """One method's rules for each kind of standings."""

    division: Rules

    conference: Rules | None
    """Division winners first, then the rest, each by these rules; None for
    the conference's teams in league order."""

    league: Rules


# The manual's list (page 129).
_GAME_TIES = Rules(
    sort=(steps.win_percentage,),
    breakers=(
        steps.head_to_head,
        steps.division_percentage,
        steps.conference_percentage,
        steps.division_net_points,
        steps.net_points,
        steps.strength_of_schedule(each_opponent_once=True),
    ),
)

GAME = MethodRules(
    division=_GAME_TIES,
    conference=_GAME_TIES,
    # The draft order (page 136), reversed.
    league=Rules(
        sort=(
            steps.champion_then_runner_up,
            steps.win_percentage,
            steps.strength_of_schedule(each_opponent_once=True),
        ),
        breakers=(),
    ),
)

SCHEDULER = MethodRules(
    # The game's own steps.
    division=_GAME_TIES,
    conference=None,
    league=Rules(
        sort=(
            steps.playoff_round,
            steps.win_percentage,
            steps.strength_of_schedule(each_opponent_once=False),
        ),
        breakers=(steps.division_finish, steps.net_points),
    ),
)

# The NFL's tiebreaking procedures and draft order, reversed, for league
# standings.
_NFL_DIVISION = Rules(
    sort=(steps.win_percentage,),
    breakers=(
        steps.head_to_head,
        steps.division_percentage,
        steps.common_games(minimum=0),
        steps.conference_percentage,
        steps.strength_of_victory,
        steps.strength_of_schedule(each_opponent_once=False),
        steps.combined_ranking("conference"),
        steps.combined_ranking("league"),
        steps.common_net_points,
        steps.net_points,
    ),
    one_advances=True,
)

NFL = MethodRules(
    division=_NFL_DIVISION,
    # The wild-card steps.
    conference=Rules(
        sort=(steps.win_percentage,),
        breakers=(
            steps.head_to_head_sweep,
            steps.conference_percentage,
            steps.common_games(minimum=4),
            steps.strength_of_victory,
            steps.strength_of_schedule(each_opponent_once=False),
            steps.combined_ranking("conference"),
            steps.combined_ranking("league"),
            steps.conference_net_points,
            steps.net_points,
        ),
        one_advances=True,
        by_division_first=True,
    ),
    # Teams of different conferences: the interconference steps.
    league=Rules(
        sort=(
            steps.playoff_round,
            steps.win_percentage,
            steps.strength_of_schedule(each_opponent_once=False),
        ),
        breakers=(
            steps.head_to_head,
            steps.common_games(minimum=4),
            steps.strength_of_victory,
            steps.combined_ranking("league"),
            steps.net_points,
        ),
        one_advances=True,
        by_division_first=True,
    ),
)

RULES: dict[Method, MethodRules] = {
    "game": GAME,
    "scheduler": SCHEDULER,
    "nfl": NFL,
}
