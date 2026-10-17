"""Shared fixtures and paths for integration tests."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from athc.fbpro98_gameplan import (
    CustomPlayRef,
    GamePlan,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
)
from athc.fbpro98_lg2.schema import FILENAME_SIZE, FOLDER_SIZE, TEAM_TRAILER_SIZE
from athc.fbpro98_lge.schema import ID_C03, ID_D03, ID_L03, ID_R03, ID_S03, ID_T03
from tests.conftest import CATEGORIES_TOML, LEAGUE, athc_toml
from tests.unit.fbpro98_lge.conftest import (
    build_chunk,
    build_conference_data,
    build_division_data,
    build_league_data,
    build_roster_data,
    build_schedule_data,
    build_team_data,
)

DATA = Path(__file__).resolve().parent / "data"
EXPECTED = Path(__file__).resolve().parent / "expected"
RULES_TOML = DATA / "profile_rules.toml"
OFF1 = DATA / "TST-OFF1.prf"
DEF1 = DATA / "TST-DEF1.prf"

# gameplan check: real gameplans + a curated pool and their rules.
GP_RULES = DATA / "gameplan_rules.toml"
GP_OFFENSE = DATA / "offense.pln"
GP_DEFENSE = DATA / "defense.pln"
PLAYS = DATA / "plays"

# check-ppp: a clean profile that fully matches offense.pln above.
COMPAT_OFF_CLEAN = DATA / "compat_off_clean.prf"

# check-ppp on a tree: the PNFL league file and a copy of its 2049 plans folder
# (Denver's week 6 files, and the same files renamed to Las Vegas's names).
PNFL_LG2 = DATA / "PNFL.lg2"
PPP_TREE = DATA / "ppp"
# The PNFL's .lge, whose 18 teams line up with PNFL.lg2's (Denver is team 5).
PNFL_LGE = DATA.parents[1] / "unit" / "fbpro98_lge" / "data" / "PNFL.lge"

# Real team names, in file order, for a built .lge.
TEAM_NAMES = (
    ("Denver", "Broncos"),
    ("Las Vegas", "Raiders"),
    ("Jacksonville", "Jaguars"),
    ("Buffalo", "Bills"),
    ("Miami", "Dolphins"),
    ("Green Bay", "Packers"),
)

BuildLeague = Callable[..., Path]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ── league folders and league files ──────────────────────────────────────────


@pytest.fixture
def build_league(make_league: Callable[..., Path]) -> BuildLeague:
    """Build a league folder holding the profile and game plan rules; None
    leaves a rules file or setting out. `path`, `team` and `ppp_path` are
    written only when given."""

    def _build(
        name: str = LEAGUE,
        *,
        profile_rules: Path | None = RULES_TOML,
        gameplan_rules: Path | None = GP_RULES,
        play_path: Path | None = PLAYS,
        path: Path | str | None = None,
        team: str | None = None,
        ppp_path: Path | str | None = None,
    ) -> Path:
        settings = [
            ("play_path", play_path),
            ("path", path),
            ("team", team),
            ("ppp_path", ppp_path),
        ]
        lines = [f"{key} = '{value}'\n" for key, value in settings if value is not None]
        body = "[league]\n" + "".join(lines) + CATEGORIES_TOML if lines else None
        folder = make_league(name, body)
        for source, target in (
            (profile_rules, "profile.toml"),
            (gameplan_rules, "gameplan.toml"),
        ):
            if source is not None:
                shutil.copy(source, folder / target)
        return folder

    return _build


def team(
    off1: tuple[str, str] = ("none-o1.prf", "none-o1.pln"),
    def1: tuple[str, str] = ("none-d1.prf", "none-d1.pln"),
    off2: tuple[str, str] = ("none-o2.prf", "none-o2.pln"),
    def2: tuple[str, str] = ("none-d2.prf", "none-d2.pln"),
    folder: str = "PNFL\\2049\\Plans\\Team",
) -> bytes:
    """One .lg2 team record from its (profile, gameplan) name pairs; a pair not
    given names files that are never on disk."""
    names = (*off1, *def1, *off2, *def2)
    entries = b"".join(
        folder.encode("ascii").ljust(FOLDER_SIZE, b"\x00")
        + name.encode("ascii").ljust(FILENAME_SIZE, b"\x00")
        for name in names
    )
    return entries + bytes(TEAM_TRAILER_SIZE)


def lge(*names: tuple[str, str]) -> bytes:
    """A .lge whose teams, in file order, have these (team name, nickname)
    pairs: one conference, one division, no games."""
    chunks = [
        build_chunk(ID_L03, build_league_data(1)),
        build_chunk(ID_C03, build_conference_data(1, b"League")),
        build_chunk(ID_D03, build_division_data(len(names), b"Teams")),
    ]
    for number, (name, nickname) in enumerate(names, 1):
        data = build_team_data(number, name.encode("ascii"), nickname.encode("ascii"))
        chunks.append(build_chunk(ID_T03, data))
        chunks.append(build_chunk(ID_R03, build_roster_data(number)))
    chunks.append(build_chunk(ID_S03, build_schedule_data()))
    return b"".join(chunks)


@pytest.fixture
def lg2_league(
    build_league: BuildLeague,
    write_config: Callable[..., Path],
    tmp_path: Path,
) -> Callable[..., Path]:
    """A league selected in athc.toml whose `path` folder holds its .lg2 and
    .lge (named after the league): the .lg2 built from `teams`, the .lge with
    real team names, `names` or the first of TEAM_NAMES. Keyword arguments go
    to `build_league`. Returns the .lg2 path."""

    def _build(
        *teams: bytes, names: Sequence[tuple[str, str]] | None = None, **kwargs
    ) -> Path:
        lg2_dir = tmp_path / "lg2"
        lg2_dir.mkdir()
        lg2 = lg2_dir / f"{LEAGUE}.lg2"
        lg2.write_bytes(b"".join(teams))
        if names is None:
            names = TEAM_NAMES[: len(teams)]
        (lg2_dir / f"{LEAGUE}.lge").write_bytes(lge(*names))
        build_league(path=lg2_dir, **kwargs)
        write_config(athc_toml())
        return lg2

    return _build


@pytest.fixture
def pnfl_league(
    build_league: BuildLeague, write_config: Callable[..., Path], tmp_path: Path
) -> Path:
    """The test league, with PNFL.lg2 and PNFL.lge copied in as its league
    files and the 2049 plans where the league file puts them (Denver's four
    pairs; Las Vegas's, one game plan per side). Returns the league folder."""
    lg2_dir = tmp_path / "lg2"
    lg2_dir.mkdir()
    shutil.copy2(PNFL_LG2, lg2_dir / f"{LEAGUE}.lg2")
    shutil.copy2(PNFL_LGE, lg2_dir / f"{LEAGUE}.lge")
    shutil.copytree(PPP_TREE, lg2_dir / "PNFL")
    folder = build_league(path=lg2_dir)
    write_config(athc_toml())
    return folder


# ── PNFL.lg2's 2049 plans (`pnfl_league`) ─────────────────────────────────────

# Denver's and Las Vegas's folders in PPP_TREE, named as PNFL.lg2 names them.
DENVER_2049 = PPP_TREE / "2049" / "Plans" / "Denver (Brian)"
LAS_VEGAS_2049 = PPP_TREE / "2049" / "Plans" / "Las Vegas (Neil)"
# Denver's (profile, game plan) pairs in .lg2 order: 1st-half offense and
# defense, then 2nd half; and its game plans alone, in the same order.
DENVER_PAIRS = (
    ("DEN-OFF1.prf", "DEN-OGP1.pln"),
    ("DEN-DEF1.prf", "DEN-DGP1.pln"),
    ("DEN-OFF2.prf", "DEN-OGP2.pln"),
    ("DEN-DEF2.prf", "DEN-DGP2.pln"),
)
DENVER_PLANS = tuple(plan for _, plan in DENVER_PAIRS)


# ── the profile keys' league: Denver and Las Vegas (`build_teams`) ────────────

Lg2League = Callable[..., Path]

# Each team's prefix (`DEN-OFF1.prf`) and its folder in the .lg2, under the
# league's `path`.
DENVER = "DEN"
LAS_VEGAS = "LV"
FOLDERS = {
    DENVER: "PNFL\\2049\\Plans\\Denver",
    LAS_VEGAS: "PNFL\\2049\\Plans\\Las Vegas",
}
# Each key's profile name after the team's prefix (`DEN-OFF1.prf`), and the
# test profile it is a copy of: offense for off1 and off2, defense for def1
# and def2.
KEY_FILES = {
    "off1": ("OFF1.prf", OFF1),
    "def1": ("DEF1.prf", DEF1),
    "off2": ("OFF2.prf", DATA / "TST-OFF2.prf"),
    "def2": ("DEF2.prf", DEF1),
}
# The profile commands' lines for your team's profile missing at its league
# location, and for --team with no profile key.
HINT = "Run 'athc config set ppp_path FOLDER' or pass a .prf file."
TEAM_REQUIRES_KEY = "Error: --team requires a profile key (off1, def1, off2 or def2).\n"


def record(prefix: str) -> bytes:
    """The team's .lg2 record: `<prefix>-OFF1.prf` and the rest, in its folder."""
    pairs = {
        key: (f"{prefix}-{name}", f"{prefix}-{key}.pln")
        for key, (name, _) in KEY_FILES.items()
    }
    return team(**pairs, folder=FOLDERS[prefix])


def location(lg2_dir: Path, prefix: str) -> Path:
    """The team's league location: `path` joined with its .lg2 folder."""
    return lg2_dir.joinpath(*FOLDERS[prefix].split("\\"))


def profile_file(folder: Path, prefix: str, key: str) -> Path:
    """The team's profile for `key` in `folder`."""
    return folder / f"{prefix}-{KEY_FILES[key][0]}"


def put_profiles(folder: Path, prefix: str) -> Path:
    """The team's four profiles, copied into `folder` (created)."""
    folder.mkdir(parents=True, exist_ok=True)
    for key, (_, source) in KEY_FILES.items():
        shutil.copy2(source, profile_file(folder, prefix, key))
    return folder


def build_teams(lg2_league: Lg2League, **settings: str | Path) -> Path:
    """The selected league of Denver, then Las Vegas, each with its four
    profiles at its league location; `settings` (`team`, `ppp_path`) go to
    league.toml. Returns the folder `path` names."""
    lg2_dir = lg2_league(record(DENVER), record(LAS_VEGAS), **settings).parent
    for prefix in FOLDERS:
        put_profiles(location(lg2_dir, prefix), prefix)
    return lg2_dir


def heads(result: Result) -> list[str]:
    """The file each report on stdout is about, in order."""
    return [
        line.removeprefix("OK   ").split(": ")[0]
        for line in result.stdout.splitlines()
        if line and not line.startswith(" ") and "file(s) " not in line
    ]


# ── constructed gameplans ─────────────────────────────────────────────────────


def clock_slot(category: int) -> SpecialSlot:
    """The stock clock play of category 11 or 12; every offense gameplan has both."""
    return SpecialSlot(stock=StockPlayRef(f"CLOCK{category}", 0, 0, 1, category, 0))


def offense_normal(name: str, user_category: int = 0x05) -> CustomPlayRef:
    """Offense normal play; `user_category` 0x05 = Run Left."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=1,
        special_category=0,
        user_category=user_category,
    )


def offense_special(name: str, category: int = 1) -> CustomPlayRef:
    """Offense special-teams play in `category` (1-10)."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=1,
        special_category=category,
        user_category=0,
    )


def defense_normal(name: str, user_category: int = 0x04) -> CustomPlayRef:
    """Defense normal play; `user_category` 0x04 = Run Left."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=0,
        special_category=0,
        user_category=user_category,
    )


def defense_special(name: str, category: int) -> CustomPlayRef:
    """Defense special-teams play in `category` (1-10)."""
    return CustomPlayRef(
        filename=f"plays\\{name}.PLY",
        play_category=0,
        special_category=category,
        user_category=0,
    )


def build_gameplan(
    profile_type: ProfileType,
    normals: Mapping[int, CustomPlayRef] | None = None,
    specials: Mapping[int, CustomPlayRef] | None = None,
) -> GamePlan:
    """A gameplan with the given normal slots (0-based) and custom special slots
    (1-based category) filled; an offense gameplan gets its two stock clock plays."""
    normal_slots: list[CustomPlayRef | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    for index, play in (normals or {}).items():
        normal_slots[index] = play
    special_slots = [SpecialSlot() for _ in range(GamePlan.NUMBER_SPECIAL_CATEGORIES)]
    for category, play in (specials or {}).items():
        special_slots[category - 1] = SpecialSlot(custom=play)
    if profile_type is ProfileType.OFFENSE:
        for category in (11, 12):
            special_slots[category - 1] = clock_slot(category)
    return GamePlan(
        profile_type=profile_type,
        normal_plays=tuple(normal_slots),
        special_plays=tuple(special_slots),
    )
