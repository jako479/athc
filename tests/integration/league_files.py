"""League files for the scheduler's golden cases.

The divisional case is the PNFL's real 2047 final and 2048 opening files. The
conference case has no game file, so its pair is built here from the
conference test league's tables with the lge test builders: a previous season
whose results give exactly that league's standings, and an upcoming season
with no game. `--snapshot-update` writes the pair into `data/`; a test keeps the
committed files in step with the builder.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from athc.fbpro98_lge.schema import ID_C03, ID_D03, ID_L03, ID_R03, ID_S03, ID_T03
from athc.scheduler.config import load_scheduler_config
from athc.scheduler.domain.league import League
from athc.scheduler.league_files import load_league
from tests.integration.conftest import DATA, EXPECTED
from tests.unit.fbpro98_lge.conftest import (
    build_chunk,
    build_conference_data,
    build_division_data,
    build_game,
    build_league_data,
    build_roster_data,
    build_schedule_data,
    build_team_data,
)
from tests.unit.scheduler.conftest import CONFERENCES_EAST, CONFERENCES_WEST


@dataclass(frozen=True)
class GoldenCase:
    """A test league: committed, test-owned inputs (the previous and upcoming
    league files, a frozen rules file with every output-affecting key set, the
    seed) and its golden set."""

    league: str
    season: int
    previous: str  # file name in data/: the previous season's final .lge
    upcoming: str  # file name in data/: the upcoming season's .lge
    seed: int = 0

    @property
    def rules(self) -> Path:
        return DATA / f"{self.league}.scheduler.toml"

    @property
    def golden_txt(self) -> Path:
        return EXPECTED / f"schedule_{self.season}.txt"

    @property
    def golden_html(self) -> Path:
        return EXPECTED / f"schedule_{self.season}.html"

    @property
    def golden_report(self) -> Path:
        return EXPECTED / f"schedule_{self.season}_report.html"


CASES = (
    GoldenCase(
        "divisions",
        2048,
        "PNFL-2047-after-super-bowl.lge",
        "PNFL-2048-after-week1.lge",
    ),
    GoldenCase(
        "conferences", 2029, "conferences-previous.lge", "conferences-upcoming.lge"
    ),
)
CASE_BY_LEAGUE = {case.league: case for case in CASES}


def write_league_files(case: GoldenCase, root: Path) -> tuple[Path, Path]:
    """Copy the case's two files to `root/previous/<league>.lge` and
    `root/upcoming/<league>.lge`; return the two files."""
    files: list[Path] = []
    for kind, name in (("previous", case.previous), ("upcoming", case.upcoming)):
        folder = root / kind
        folder.mkdir(parents=True, exist_ok=True)
        files.append(Path(shutil.copy(DATA / name, folder / f"{case.league}.lge")))
    return files[0], files[1]


def no_warning(line: str) -> None:
    """A case's previous season is finished, so its League hears no warning."""
    raise AssertionError(f"unexpected warning: {line}")


def case_league(case: GoldenCase, root: Path) -> League:
    """The case's League, built the way `generate-schedule` builds it, with the
    case's seed for the coin toss."""
    previous, upcoming = write_league_files(case, root)
    renames = load_scheduler_config(case.rules).renames.get(case.season, {})
    return load_league(
        previous,
        upcoming,
        renames,
        season=case.season,
        seed=case.seed,
        rules_path=case.rules,
        warn=no_warning,
    )


# --- the built conference league files ----------------------------------------

# Record order, best first. Every pair meets once and the better-placed team
# wins, so the conference finish orders and, with the playoffs below, the
# overall order of CONFERENCES_LEAGUE all follow from it.
RECORD_ORDER = (
    "Texas",
    "Ohio State",
    "Tennessee",
    "Notre Dame",
    "Boston College",
    "Arkansas",
    "LSU",
    "UCLA",
    "Washington",
    "Clemson",
    "Oklahoma",
    "Georgia",
    "Penn State",
    "USC",
    "Colorado",
    "Miami",
    "Oregon",
    "Michigan",
)
# (winner, loser) per round: Texas champion, Tennessee runner-up.
PLAYOFFS = (
    (
        ("Texas", "Ohio State"),
        ("Tennessee", "Boston College"),
        ("Notre Dame", "LSU"),
        ("Arkansas", "UCLA"),
    ),
    (("Texas", "Notre Dame"), ("Tennessee", "Arkansas")),
    (("Texas", "Tennessee"),),
)
WIN, LOSS = 20, 10
# Conference, division and members: team numbers run 1-18 in this order.
STRUCTURE = (
    ("EASTERN", "East", CONFERENCES_EAST),
    ("WESTERN", "West", CONFERENCES_WEST),
)


def conference_league_files() -> tuple[bytes, bytes]:
    """The (previous season, upcoming season) `.lge` bytes."""
    teams = [name for _, _, members in STRUCTURE for name in members]
    number = {name: index for index, name in enumerate(teams, 1)}
    place = {name: index for index, name in enumerate(RECORD_ORDER)}

    def game(first: str, second: str) -> bytes:
        winner, loser = sorted((first, second), key=lambda name: place[name])
        return build_game(number[winner], WIN, number[loser], LOSS)

    regular = [[game(a, b) for a, b in week] for week in _round_robin(teams)]
    playoffs = [
        [
            build_game(number[winner], WIN, number[loser], LOSS)
            for winner, loser in round_
        ]
        for round_ in PLAYOFFS
    ]
    return (
        _lge(number, build_schedule_data(regular, playoffs)),
        _lge(number, build_schedule_data()),
    )


def _round_robin(teams: Sequence[str]) -> list[list[tuple[str, str]]]:
    """Weeks in which every pair meets exactly once (the circle method)."""
    ids = list(teams)
    weeks: list[list[tuple[str, str]]] = []
    for _ in range(len(ids) - 1):
        weeks.append([(ids[i], ids[-1 - i]) for i in range(len(ids) // 2)])
        ids = [ids[0], ids[-1], *ids[1:-1]]
    return weeks


def _lge(number: dict[str, int], schedule: bytes) -> bytes:
    chunks = [build_chunk(ID_L03, build_league_data(len(STRUCTURE)))]
    for conference, division, members in STRUCTURE:
        chunks.append(
            build_chunk(ID_C03, build_conference_data(1, conference.encode()))
        )
        chunks.append(
            build_chunk(ID_D03, build_division_data(len(members), division.encode()))
        )
        for name in members:
            chunks.append(
                build_chunk(ID_T03, build_team_data(number[name], name.encode(), b""))
            )
            chunks.append(build_chunk(ID_R03, build_roster_data(number[name])))
    chunks.append(build_chunk(ID_S03, schedule))
    return b"".join(chunks)


def write_conference_league_files() -> tuple[Path, Path]:
    """Write the built pair into `data/`; returns the two paths."""
    case = CASE_BY_LEAGUE["conferences"]
    paths = (DATA / case.previous, DATA / case.upcoming)
    for path, content in zip(paths, conference_league_files(), strict=True):
        path.write_bytes(content)
    return paths
