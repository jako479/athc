"""`athc autocontinue` against the real game, in Windows Sandbox: an exhibition
game with 6-minute quarters, through halftime to the end of the game; and a
league game's pre-game screen, driven to Game with drive_league_pregame on and
left alone with it off.

Slow and manual: `uv run pytest -m slow tests/integration/test_autocontinue_game.py`.
It needs Windows Sandbox (with the `wsb` command line), a built installer
(`packaging/release-build.ps1`), and a copy of the game install: the folder
holding `FbPro98`, set by `ATHC_GAME_DIR` or at `SIERRA` in the project root.
The sandbox works on its own copy of the game, so the folder never changes.

The host drives the game's menus by image, through `agent.ps1` in the
sandbox, then waits for autocontinue's lines. In the exhibition game,
`pointer-helper.ps1` in the sandbox lights, moves off or leaves the pointer on
each button as it shows.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import tomllib
import uuid
from collections.abc import Iterator
from pathlib import Path, PureWindowsPath

import cv2
import numpy
import pytest
from cv2.typing import MatLike

from athc.fbpro98_lg2.reader import read_lg2

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).parent / "data" / "autocontinue_game"
# The menus' images: the test's own, then the ones autocontinue ships.
MENU_IMAGES = DATA / "images"
IMAGES = ROOT / "src" / "athc" / "autocontinue" / "images"
DESK = r"C:\Users\WDAGUtilityAccount\Desktop"
SANDBOX_EXE = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "WindowsSandbox.exe"
)

SETUP_TIMEOUT = 20 * 60  # copy the game and install athc
MENU_TIMEOUT = 2 * 60  # one menu screen
MENU_PAUSE = 1.5  # after a click, and between looks for a button
HALF_TIMEOUT = 45 * 60  # one half of 6-minute quarters, with time to spare
PREGAME_TIMEOUT = 2 * 60  # the pre-game screen driven to Game
LEFT_ALONE = 20  # seconds the pre-game screen is watched with it off
GAME_COOLDOWN = 4  # seconds autocontinue waits after clicking Game
MATCH = 0.8  # as autocontinue matches
# A blank spot at the top left of the game window, clear of every button the
# test clicks; the window opens at the same place in every sandbox.
PARK = (455, 195)
# What the pointer helper looks for, as autocontinue ships them.
HELPER_IMAGES = (
    "continue_button",
    "return_button",
    "return_highlight_button",
    "halftime_label",
    "results_label",
)
# What the helper does with the pointer on each button shown, by share. It
# leaves the pointer only on a button it is already on, unlit, at most a
# quarter of them; Continue's box opens where the one before was about that
# often (24 of 84 in a captured game). Only what it does in time counts:
# within the 1 s autocontinue waits after finding Continue before it clicks,
# the scan coming once a second. So the shares come out near these, not on
# them.
MIX = {"light": 0.50, "away": 0.25, "leave": 0.25}
MIX_NEAR = 0.10
IN_TIME_MS = 1000
HELPER_LEAST = 40  # buttons the helper acts on in time in a game, at the least

# Baltimore's test plans and profiles, in the league folder, by half and side:
# (profile, game plan).
TEST_SET = {
    ("first", "offense"): ("PNFL\\BALTOFF1.prf", "PNFL\\RAVENOFF1.pln"),
    ("first", "defense"): ("PNFL\\BALTDEF1.prf", "PNFL\\RAVENDEF1.pln"),
    ("second", "offense"): ("PNFL\\BALTOFF2.prf", "PNFL\\RAVENOFF2.pln"),
    ("second", "defense"): ("PNFL\\BALTDEF2.prf", "PNFL\\RAVENDEF2.pln"),
}


def _game_dir() -> Path:
    """The folder holding FbPro98: ATHC_GAME_DIR, else SIERRA in the project."""
    return Path(os.environ.get("ATHC_GAME_DIR", ROOT / "SIERRA"))


def _setup_exe() -> Path:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    return ROOT / "dist" / f"athc-{version}-setup.exe"


def _needle(name: str) -> MatLike:
    """`name`'s image, in gray: the test's own menu image, else autocontinue's."""
    path = MENU_IMAGES / f"{name}.png"
    if not path.exists():
        path = IMAGES / f"{name}.png"
    needle = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    assert needle is not None, f"{name}.png did not read"
    return needle


def _wsb(*args: str) -> str:
    return subprocess.run(
        ["wsb", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _copies(game: Path) -> list[str]:
    """`source|target` for Baltimore's set under every team's .lg2 names, both
    relative to the game folder; exhibition picks its teams at random."""
    lines = []
    for team in read_lg2("PNFL", game).teams:
        for half_name, half in (
            ("first", team.first_half),
            ("second", team.second_half),
        ):
            for side_name, pair in (
                ("offense", half.offense),
                ("defense", half.defense),
            ):
                profile, plan = TEST_SET[(half_name, side_name)]
                lines += [f"{profile}|{pair.profile}", f"{plan}|{pair.gameplan}"]
    return lines


def _mapping(host: Path, name: str, read_only: bool) -> str:
    return (
        "    <MappedFolder>\n"
        f"      <HostFolder>{host}</HostFolder>\n"
        f"      <SandboxFolder>{DESK}\\{name}</SandboxFolder>\n"
        f"      <ReadOnly>{str(read_only).lower()}</ReadOnly>\n"
        "    </MappedFolder>\n"
    )


class Sandbox:
    """The running sandbox, as the host drives it through the agent."""

    def __init__(self, out: Path) -> None:
        self.out = out

    def request(self, *commands: str, timeout: float = 60.0) -> None:
        request = uuid.uuid4().hex[:8]
        staged = self.out / "cmd.tmp"
        staged.write_text("\n".join([request, *commands]) + "\n", encoding="ascii")
        staged.replace(self.out / "cmd.txt")
        done = self.out / "done.txt"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if done.read_text(encoding="utf-8-sig").strip() == request:
                    return
            except OSError:
                pass  # not written yet, or the agent is writing it
            time.sleep(0.3)
        pytest.fail(f"The sandbox agent did not answer within {timeout:.0f} s.")

    def screen(self) -> MatLike:
        """A screenshot, with the mouse parked first: the game draws its own
        pointer, which would cover a button the last click left it on."""
        self.request(f"move {PARK[0]} {PARK[1]}", "wait 300", "shot screen")
        image = cv2.imread(str(self.out / "screen.png"), cv2.IMREAD_GRAYSCALE)
        assert image is not None, "the agent's screenshot did not read"
        return image

    def find(self, *names: str) -> tuple[int, int] | None:
        """The middle of the first of `names`' images on one screenshot, or
        None."""
        screen = self.screen()
        for name in names:
            needle = _needle(name)
            result = cv2.matchTemplate(screen, needle, cv2.TM_CCOEFF_NORMED)
            _, best, _, (left, top) = cv2.minMaxLoc(result)
            if best >= MATCH:
                height, width = needle.shape
                return left + width // 2, top + height // 2
        return None

    def find_all(self, name: str) -> list[tuple[int, int]]:
        """The middle of every spot `name`'s image shows on one screenshot,
        top to bottom, then left to right."""
        needle = _needle(name)
        result = cv2.matchTemplate(self.screen(), needle, cv2.TM_CCOEFF_NORMED)
        height, width = needle.shape
        spots: list[tuple[int, int]] = []
        # Neighboring pixels of one spot all match too: keep the first.
        for top, left in zip(*numpy.where(result >= MATCH), strict=True):
            if all(abs(left - x) >= width or abs(top - y) >= height for x, y in spots):
                spots.append((int(left), int(top)))
        return sorted(
            ((x + width // 2, y + height // 2) for x, y in spots),
            key=lambda spot: (spot[1], spot[0]),
        )

    def click_each(self, name: str, count: int) -> None:
        """Wait for `count` spots of `name`'s image, then click each one."""
        deadline = time.monotonic() + MENU_TIMEOUT
        while time.monotonic() < deadline:
            spots = self.find_all(name)
            if len(spots) == count:
                for x, y in spots:
                    self.request(f"click {x} {y}")
                    time.sleep(MENU_PAUSE)
                return
            time.sleep(MENU_PAUSE)
        self.request("shot failed")
        pytest.fail(f"{count} of {name} were not on screen; see {self.out}.")

    def click_first(self, name: str) -> None:
        """Wait for `name`'s image, then click the top, leftmost spot."""
        deadline = time.monotonic() + MENU_TIMEOUT
        while time.monotonic() < deadline:
            spots = self.find_all(name)
            if spots:
                self.request(f"click {spots[0][0]} {spots[0][1]}")
                time.sleep(MENU_PAUSE)
                return
            time.sleep(MENU_PAUSE)
        self.request("shot failed")
        pytest.fail(f"{name} was not on screen; see {self.out}.")

    def click(self, *names: str, timeout: float = MENU_TIMEOUT) -> None:
        """Wait for one of `names`' images (a button as drawn, or lit up by
        the mouse resting on it), click its middle, then let the screen
        change."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            at = self.find(*names)
            if at is not None:
                self.request(f"click {at[0]} {at[1]}")
                time.sleep(MENU_PAUSE)
                return
            time.sleep(MENU_PAUSE)
        self.request("shot failed")
        pytest.fail(
            f"{names[0]} was not on screen within {timeout:.0f} s; see {self.out}."
        )

    def lines(self) -> list[str]:
        """autocontinue's status lines so far."""
        path = self.out / "ac-err.txt"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def wait_for_line(self, start: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(line.startswith(start) for line in self.lines()):
                return
            time.sleep(10)
        self.request("shot failed")
        pytest.fail(f"No '{start}' line within {timeout:.0f} s; see {self.out}.")


@pytest.fixture
def sandbox(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Sandbox]:
    """The sandbox, set up and running the game and autocontinue. A test's
    parameter, when it gives one, is the athc.ini autocontinue runs with;
    else the installed one."""
    settings: str | None = getattr(request, "param", None)
    game = _game_dir()
    setup = _setup_exe()
    if not SANDBOX_EXE.exists() or shutil.which("wsb") is None:
        pytest.fail("Needs Windows Sandbox and its wsb command line (Windows 11 24H2).")
    if not (game / "FbPro98" / "Hike.exe").exists():
        pytest.fail(
            f"No game at {game}; set ATHC_GAME_DIR to the folder holding FbPro98."
        )
    if not setup.exists():
        pytest.fail(f"No {setup}; run packaging/release-build.ps1 first.")
    if _wsb("list"):
        pytest.fail("A Windows Sandbox is already running; stop it first.")

    assets, out = tmp_path / "assets", tmp_path / "out"
    assets.mkdir()
    out.mkdir()
    for name in ("agent.ps1", "run-autocontinue.cmd", "pointer-helper.ps1"):
        shutil.copy(DATA / name, assets)
    (assets / "images").mkdir()
    for name in HELPER_IMAGES:
        shutil.copy(IMAGES / f"{name}.png", assets / "images")
    if settings is not None:
        (assets / "config").mkdir()
        (assets / "config" / "athc.ini").write_text(settings, encoding="utf-8")
    (assets / "copies.txt").write_text(
        "\n".join(_copies(game / "FbPro98")) + "\n", encoding="utf-8"
    )
    agent = PureWindowsPath(DESK, "assets", "agent.ps1")
    config = tmp_path / "game-test.wsb"
    config.write_text(
        "<Configuration>\n"
        "  <Networking>Disable</Networking>\n"
        "  <MappedFolders>\n"
        + _mapping(game, "SIERRA", True)
        + _mapping(setup.parent, "dist", True)
        + _mapping(assets, "assets", True)
        + _mapping(out, "out", False)
        + "  </MappedFolders>\n"
        "  <LogonCommand>\n"
        "    <Command>powershell.exe -NoProfile -ExecutionPolicy Bypass "
        f"-WindowStyle Hidden -File {agent}</Command>\n"
        "  </LogonCommand>\n"
        "</Configuration>\n",
        encoding="ascii",
    )
    # Kept, and waited for at the end: a launcher dropped while it runs is a
    # ResourceWarning, which the suite turns into an error.
    launcher = subprocess.Popen([str(SANDBOX_EXE), str(config)])
    try:
        deadline = time.monotonic() + SETUP_TIMEOUT
        while not (out / "ready.txt").exists():
            if time.monotonic() > deadline:
                pytest.fail(f"The sandbox was not set up within {SETUP_TIMEOUT} s.")
            time.sleep(5)
        yield Sandbox(out)
    finally:
        for sandbox_id in _wsb("list").split():
            _wsb("stop", "--id", sandbox_id)
        try:
            launcher.wait(timeout=120)
        except subprocess.TimeoutExpired:
            launcher.kill()
            launcher.wait()


ACCEPT = ("accept_button", "accept_highlight_button")
PREGAME_ON = "[autocontinue]\ndrive_league_pregame = true\n"
PREGAME_OFF = "[autocontinue]\ndrive_league_pregame = false\n"


def _both_teams_on_computer(sandbox: Sandbox) -> None:
    """The Controllers screen: Computer for both teams, then Accept. The home
    team starts on Keyboard and would wait for a human at the coin toss. The
    word COMPUTER looks the same selected or not; clicking it again keeps it
    selected."""
    sandbox.click_each("computer_label", 2)
    sandbox.click(*ACCEPT)


def _to_the_league_pregame(sandbox: Sandbox) -> None:
    """Game Type > League > Schedule > every game to Sim > the first game to
    Play > Play > the Controllers screen: the pre-game screen."""
    for names in (
        ("game_type_button",),
        ("league_option",),
        ("schedule_button",),
        ("sim_header",),
    ):
        sandbox.click(*names)
    sandbox.click_first("play_option")
    sandbox.click("play_button")
    _both_teams_on_computer(sandbox)


def test_an_exhibition_game_through_halftime_to_the_end(sandbox: Sandbox) -> None:
    """The pointer lit on, moved off or left on each button as it shows, half,
    a quarter and a quarter: Return clicked at halftime, and the run stopped
    at the end of the game."""
    # Game Type > Exhibition > Accept (teams) > the Controllers screen > Game
    # Controls > 6 Minutes > Game. The mouse stays where the last click left
    # it, so Accept and Game may show lit up.
    for names in (("game_type_button",), ("exhibition_button",), ACCEPT):
        sandbox.click(*names)
    _both_teams_on_computer(sandbox)
    for names in (
        ("game_controls_button",),
        ("6_minutes_option",),
        ("game_button", "game_highlight_button"),
    ):
        sandbox.click(*names)
    sandbox.request("helper")

    sandbox.wait_for_line("Return button clicked.", HALF_TIMEOUT)
    sandbox.wait_for_line("Results label found at", HALF_TIMEOUT)
    deadline = time.monotonic() + 60
    stopped = sandbox.out / "ac-out.txt"
    while "Stopped." not in stopped.read_text(encoding="utf-8"):
        assert time.monotonic() < deadline, "autocontinue did not stop"
        time.sleep(2)

    lines = sandbox.lines()
    assert not [line for line in lines if line.startswith("WARN Unexpected")]
    halftime = lines.index("Waiting 8 seconds.")
    assert lines[halftime - 2].startswith("Halftime label found at ")
    assert lines[halftime - 1].startswith("Return button found at ")
    assert lines[halftime + 1] == "Return button clicked."
    assert lines[-2].startswith("Results label found at ")
    assert lines[-1].startswith("Return button found at ")

    # One line per button the helper acted on: the button, the action, at
    # most how long the button had been up, in ms, and whether the pointer is
    # on it after. A "leave" counts only with the pointer on the button.
    helped = [
        line.split()
        for line in (sandbox.out / "helper.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    in_time = [
        action
        for _, action, late, pointer in helped
        if int(late) <= IN_TIME_MS and (action != "leave" or pointer == "on")
    ]
    assert len(in_time) >= HELPER_LEAST
    for action, share in MIX.items():
        assert abs(in_time.count(action) / len(in_time) - share) <= MIX_NEAR, action
    # Return at halftime and at the end of the game.
    assert len([button for button, *_ in helped if button == "Return"]) >= 2


@pytest.mark.parametrize("sandbox", [PREGAME_ON], indirect=True, ids=["on"])
def test_a_league_pregame_driven_to_the_game(sandbox: Sandbox) -> None:
    """Every pre-game button clicked, in order, then Game, and the game gone
    from the pre-game screen: the run ends there."""
    _to_the_league_pregame(sandbox)
    sandbox.wait_for_line("Game button clicked.", PREGAME_TIMEOUT)
    # The clicks landed: once the 4 s after Game are up, the League play
    # label is gone.
    time.sleep(GAME_COOLDOWN)
    deadline = time.monotonic() + MENU_TIMEOUT
    while sandbox.find("league_play_label") is not None:
        assert time.monotonic() < deadline, "still on the pre-game screen"
        time.sleep(MENU_PAUSE)

    lines = sandbox.lines()
    found = [i for i, line in enumerate(lines) if line.startswith("League play label")]
    assert len(found) == 1 and lines[found[0]].startswith("League play label found at")
    assert lines[found[0] + 1 : found[0] + 6] == [
        "Plans/profiles button clicked.",
        "Visitor button clicked.",
        "Conditions button clicked.",
        "Venues button clicked.",
        "Game button clicked.",
    ]
    assert not [line for line in lines if line.startswith("WARN")]


@pytest.mark.parametrize("sandbox", [PREGAME_OFF], indirect=True, ids=["off"])
def test_a_league_pregame_left_alone_when_off(sandbox: Sandbox) -> None:
    """The pre-game screen stays as it opened, on the home team's plans, with
    nothing said or clicked: the run ends there."""
    _to_the_league_pregame(sandbox)
    deadline = time.monotonic() + MENU_TIMEOUT
    while sandbox.find("league_play_label") is None:
        assert time.monotonic() < deadline, "no pre-game screen"
        time.sleep(MENU_PAUSE)
    time.sleep(LEFT_ALONE)

    assert sandbox.find("visitor_button") is not None  # still the home team's
    lines = sandbox.lines()
    assert not [line for line in lines if "League play" in line or "clicked" in line]
    assert not [line for line in lines if line.startswith("WARN")]
