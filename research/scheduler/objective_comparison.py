"""Compare phase-1 objectives: minisum vs minimax (worst-case opponent-rank miss).

NOTE: this one-off study drove the minimax decision against the original 1-9
conference-rank model; it is not maintained for the later overall 1-18 switch
(its model construction would need updating to run again).

Phase-1 only (the non-conference solve), so it is fast. For each standing we
solve the rank-only model under both objectives and measure every team's
"miss" = average opponent rank - its curve target. We report the worst-case
miss (the largest single-team miss) and supporting stats so we can pick which
objective to keep.

Run:  .venv\\Scripts\\python.exe research\\scheduler\\objective_comparison.py
      [--trials 200] [--seed 0]

Standings are random permutations of the current league's two 9-team
conferences (paired: each seed feeds both objectives). The real league and a
few hand-built extremes are also reported.
"""

from __future__ import annotations

import argparse
import random
import statistics
import time
from collections.abc import Sequence
from pathlib import Path

from ortools.sat.python import cp_model

from athc.scheduler.config import load_league
from athc.scheduler.domain.league import (
    TEAMS_PER_CONFERENCE,
    Conference,
    ConferenceRankings,
    League,
    Team,
    build_league,
)
from athc.scheduler.domain.schedule import nonconference_games_for
from athc.scheduler.schedulers.matchup_builder import (
    _RankBasedNonConferenceModel,
    difficulty_target,
)
from athc.scheduler.schedulers.types import make_matchup

WORKERS = 8

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAGUE_PATH = REPO_ROOT / "release" / "2048.league.ini"
OBJECTIVES = ("minisum", "minimax")
BAND_LOW, BAND_HIGH = 3.5, 6.5

# Deviations are scored in units of 1/SCALE of a rank, against the curve target
# (rounded to that resolution - 0.05 rank, far finer than the 1/games = 0.2-0.25
# granularity of achievable averages, so effectively un-rounded). SCALE must be a
# multiple of both game counts (4 and 5) so opponent_rank_sum * (SCALE / games)
# stays an exact integer; 20 = LCM(4, 5) keeps the coefficients small and fast.
SCALE = 20


def _divisions(teams: Sequence[Team]) -> dict[str, list[str]]:
    by_div: dict[str, list[str]] = {}
    for team in teams:
        by_div.setdefault(team.division.name, []).append(team.metro)
    return by_div


def _rankings_from_order(
    teams: Sequence[Team], afc: Sequence[str], nfc: Sequence[str]
) -> League:
    # Interleave the two 9-team orders into one overall 1-18 list so the derived
    # conference ranks match afc/nfc (1st AFC, 1st NFC, 2nd AFC, ...).
    overall = [team for pair in zip(afc, nfc, strict=True) for team in pair]
    return build_league(_divisions(teams), overall)


def _ranks(rankings: ConferenceRankings) -> dict[Team, int]:
    ranks: dict[Team, int] = {}
    for seq in (rankings.afc, rankings.nfc):
        for i, team in enumerate(seq, start=1):
            ranks[team] = i
    return ranks


def solve(league: League, objective: str) -> set[tuple[Team, Team]]:
    """Solve phase-1 with the chosen objective scored against exact targets.

    Reuses the production constraints (degree, top/bottom floor, opponent-rank
    sum) but replaces the rounded objective with an exact one: each team's
    deviation is opponent_rank_sum * (SCALE / games) - round(target * SCALE),
    in 1/SCALE-rank units. minisum minimizes the total; minimax the largest.
    """
    ranked = {
        Conference.AFC: list(league.rankings.afc),
        Conference.NFC: list(league.rankings.nfc),
    }
    ranks = _ranks(league.rankings)
    model = _RankBasedNonConferenceModel(ranked, ranks)
    model._add_degree_constraints()
    model._add_top_bottom_constraints()
    model._add_opponent_rank_sum_constraints()

    cp = model.model
    big = SCALE * TEAMS_PER_CONFERENCE
    deviations = []
    for team in model.teams:
        games = nonconference_games_for(team.division)
        scaled_sum = model.opponent_rank_sum[team] * (SCALE // games)
        target = round(difficulty_target(ranks[team]) * SCALE)
        dev = cp.new_int_var(0, big, f"dev_{team.metro}")
        cp.add(dev >= scaled_sum - target)
        cp.add(dev >= target - scaled_sum)
        deviations.append(dev)
    if objective == "minimax":
        worst = cp.new_int_var(0, big, "worst")
        for dev in deviations:
            cp.add(worst >= dev)
        cp.minimize(worst)
    else:
        cp.minimize(sum(deviations))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = WORKERS
    status = solver.solve(cp)
    if status != cp_model.OPTIMAL:
        raise RuntimeError(f"{objective}: solver returned {solver.status_name(status)}")
    return {
        make_matchup(a, b) for (a, b), var in model.x.items() if solver.value(var) == 1
    }


def team_misses(league: League, pairs: set[tuple[Team, Team]]) -> list[float]:
    """Each team's signed miss = avg opponent rank - curve target."""
    ranks = _ranks(league.rankings)
    opp_sum: dict[Team, int] = {t: 0 for t in league.teams}
    for a, b in pairs:
        opp_sum[a] += ranks[b]
        opp_sum[b] += ranks[a]
    misses: list[float] = []
    for team in league.teams:
        games = nonconference_games_for(team.division)
        avg = opp_sum[team] / games
        misses.append(avg - difficulty_target(ranks[team]))
    return misses


def avgs_out_of_band(league: League, pairs: set[tuple[Team, Team]]) -> int:
    ranks = _ranks(league.rankings)
    opp_sum: dict[Team, int] = {t: 0 for t in league.teams}
    for a, b in pairs:
        opp_sum[a] += ranks[b]
        opp_sum[b] += ranks[a]
    out = 0
    for team in league.teams:
        avg = opp_sum[team] / nonconference_games_for(team.division)
        if not (BAND_LOW <= avg <= BAND_HIGH):
            out += 1
    return out


class Stats:
    def __init__(self) -> None:
        self.worst: list[float] = []  # largest abs miss per standing
        self.total: list[float] = []  # sum of abs miss per standing
        self.out: list[int] = []  # teams with avg outside the 3.5-6.5 band

    def add(self, league: League, pairs: set[tuple[Team, Team]]) -> float:
        misses = [abs(m) for m in team_misses(league, pairs)]
        worst = max(misses)
        self.worst.append(worst)
        self.total.append(sum(misses))
        self.out.append(avgs_out_of_band(league, pairs))
        return worst


def _pct(values: list[float], q: float) -> float:
    s = sorted(values)
    idx = min(len(s) - 1, int(q * len(s)))
    return s[idx]


def _hist(values: list[float], edges: Sequence[float]) -> str:
    counts = [0] * (len(edges) + 1)
    for v in values:
        placed = False
        for i, e in enumerate(edges):
            if v <= e:
                counts[i] += 1
                placed = True
                break
        if not placed:
            counts[-1] += 1
    labels = [f"<={edges[0]:.2f}"]
    labels += [f"{edges[i - 1]:.2f}-{edges[i]:.2f}" for i in range(1, len(edges))]
    labels += [f">{edges[-1]:.2f}"]
    return "\n".join(
        f"    {lab:>12}: {c}" for lab, c in zip(labels, counts, strict=True)
    )


def report_random(trials: int, base_seed: int, teams: Sequence[Team]) -> None:
    afc = [t.metro for t in teams if t.conference == Conference.AFC]
    nfc = [t.metro for t in teams if t.conference == Conference.NFC]
    stats = {obj: Stats() for obj in OBJECTIVES}
    worst_by_obj: dict[str, list[float]] = {obj: [] for obj in OBJECTIVES}
    started = time.perf_counter()
    for i in range(trials):
        rng = random.Random(base_seed + i)
        a = afc[:]
        n = nfc[:]
        rng.shuffle(a)
        rng.shuffle(n)
        league = _rankings_from_order(teams, a, n)
        for obj in OBJECTIVES:
            worst_by_obj[obj].append(stats[obj].add(league, solve(league, obj)))
    elapsed = time.perf_counter() - started

    last_seed = base_seed + trials - 1
    print(f"\n=== {trials} random standings (seeds {base_seed}..{last_seed}) ===")
    print(
        f"solved {trials * 2} models in {elapsed:.1f}s "
        f"({elapsed / (trials * 2) * 1000:.0f} ms/solve)\n"
    )
    print(
        f"{'objective':<10} {'worst-miss: mean':>16} {'p50':>6} {'p90':>6} "
        f"{'p95':>6} {'max':>6} {'totmiss':>9} {'out:mean':>9} {'out:max':>8}"
    )
    for obj in OBJECTIVES:
        s = stats[obj]
        p50, p90, p95 = _pct(s.worst, 0.50), _pct(s.worst, 0.90), _pct(s.worst, 0.95)
        print(
            f"{obj:<10} {statistics.mean(s.worst):>16.3f} {p50:>6.2f} "
            f"{p90:>6.2f} {p95:>6.2f} {max(s.worst):>6.2f} "
            f"{statistics.mean(s.total):>9.2f} {statistics.mean(s.out):>9.2f} "
            f"{max(s.out):>8d}"
        )

    print("\nworst-miss distribution (count of standings):")
    edges = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    for obj in OBJECTIVES:
        print(f"  {obj}:")
        print(_hist(stats[obj].worst, edges))

    mm = worst_by_obj["minimax"]
    ms = worst_by_obj["minisum"]
    pairs = list(zip(ms, mm, strict=True))
    wins = sum(1 for a, b in pairs if b < a - 1e-9)
    ties = sum(1 for a, b in pairs if abs(a - b) <= 1e-9)
    losses = trials - wins - ties
    mean_gap = statistics.mean(a - b for a, b in pairs)
    penalty = statistics.mean(stats["minimax"].total) - statistics.mean(
        stats["minisum"].total
    )
    print("\nminimax vs minisum on worst-case miss (paired, same standing):")
    print(f"  minimax strictly better: {wins}  tie: {ties}  minimax worse: {losses}")
    print(f"  mean(worst_minisum - worst_minimax) = {mean_gap:.3f}")
    print(f"  mean total-miss penalty of minimax = {penalty:.3f}")


def report_cases(cases: list[tuple[str, League]]) -> None:
    print("\n=== named standings (real league + extremes) ===")
    print(
        f"{'case':<16} {'minisum worst':>14} {'total':>7} {'out':>4}   "
        f"{'minimax worst':>14} {'total':>7} {'out':>4}"
    )
    for name, league in cases:
        row = [f"{name:<16}"]
        for obj in OBJECTIVES:
            pairs = solve(league, obj)
            misses = [abs(m) for m in team_misses(league, pairs)]
            out = avgs_out_of_band(league, pairs)
            row.append(f"{max(misses):>14.3f} {sum(misses):>7.2f} {out:>4d}  ")
        print(" ".join(row))


def build_cases(real: League, teams: Sequence[Team]) -> list[tuple[str, League]]:
    afc = [t.metro for t in teams if t.conference == Conference.AFC]
    nfc = [t.metro for t in teams if t.conference == Conference.NFC]

    def split(metros: list[str]) -> tuple[list[str], list[str]]:
        small = sorted(m for m in metros if _team(teams, m).division.expected_size == 4)
        big = sorted(m for m in metros if _team(teams, m).division.expected_size == 5)
        return small, big

    afc_small, afc_big = split(afc)
    nfc_small, nfc_big = split(nfc)

    cases: list[tuple[str, League]] = [("real", real)]
    cases.append(
        (
            "reversed",
            _rankings_from_order(
                teams,
                [t.metro for t in reversed(real.rankings.afc)],
                [t.metro for t in reversed(real.rankings.nfc)],
            ),
        )
    )
    cases.append(
        (
            "east-top",
            _rankings_from_order(teams, afc_small + afc_big, nfc_small + nfc_big),
        )
    )
    cases.append(
        (
            "west-top",
            _rankings_from_order(teams, afc_big + afc_small, nfc_big + nfc_small),
        )
    )
    cases.append(
        (
            "interleave",
            _rankings_from_order(
                teams, _interleave(afc_small, afc_big), _interleave(nfc_small, nfc_big)
            ),
        )
    )
    for name, afc_order, nfc_order in _FREE_SLOT_LEAGUES:
        cases.append((name, _rankings_from_order(teams, afc_order, nfc_order)))
    return cases


def _team(teams: Sequence[Team], metro: str) -> Team:
    return next(t for t in teams if t.metro == metro)


def _interleave(a: list[str], b: list[str]) -> list[str]:
    out: list[str] = []
    for i in range(max(len(a), len(b))):
        if i < len(a):
            out.append(a[i])
        if i < len(b):
            out.append(b[i])
    return out


# The three playoff-split stress leagues from the unit-test conftest.
_FREE_SLOT_LEAGUES = [
    (
        "5-free-slots",
        [
            "New England",
            "Cincinnati",
            "Pittsburgh",
            "Denver",
            "Miami",
            "Buffalo",
            "Jacksonville",
            "Los Angeles",
            "Las Vegas",
        ],
        [
            "Washington",
            "Chicago",
            "Minnesota",
            "San Francisco",
            "Atlanta",
            "New York",
            "Philadelphia",
            "Green Bay",
            "Seattle",
        ],
    ),
    (
        "6-free-slots",
        [
            "New England",
            "Cincinnati",
            "Miami",
            "Pittsburgh",
            "Buffalo",
            "Jacksonville",
            "Denver",
            "Los Angeles",
            "Las Vegas",
        ],
        [
            "Washington",
            "Chicago",
            "Atlanta",
            "Minnesota",
            "New York",
            "Philadelphia",
            "San Francisco",
            "Green Bay",
            "Seattle",
        ],
    ),
    (
        "7-free-slots",
        [
            "New England",
            "Cincinnati",
            "Miami",
            "Buffalo",
            "Jacksonville",
            "Pittsburgh",
            "Denver",
            "Los Angeles",
            "Las Vegas",
        ],
        [
            "Washington",
            "Chicago",
            "Atlanta",
            "New York",
            "Philadelphia",
            "Minnesota",
            "San Francisco",
            "Green Bay",
            "Seattle",
        ],
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    real = load_league(LEAGUE_PATH)
    teams = real.teams
    report_random(args.trials, args.seed, teams)
    report_cases(build_cases(real, teams))


if __name__ == "__main__":
    main()
