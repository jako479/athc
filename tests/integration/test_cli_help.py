"""The help every command and group shares: argument help lines, Windows
words, and the ranges for the one-line summary (55 characters or fewer), the
description (one to four lines) and the examples (one to six)."""

from __future__ import annotations

import inspect
from collections.abc import Iterator

import click
import pytest
from click.formatting import wrap_text

from athc.cli import cli

SUMMARY_MAX = 55  # fits the command list without Click cutting it off
DESCRIPTION_LINES = range(1, 5)
EXAMPLE_COUNT = range(1, 7)
# Click's help in an 80-column console: 78 wide, the text indented by 2.
TEXT_WIDTH = 76


def summary(help_text: str) -> str:
    """The one-line summary: the help's first paragraph, on one line."""
    first, _, _ = inspect.cleandoc(help_text).partition("\n\n")
    return " ".join(first.split())


def description_lines(help_text: str) -> int:
    """Lines the description takes on the help screen: the text after the
    summary, wrapped as Click wraps it in an 80-column console, blank lines
    left out."""
    _, _, body = inspect.cleandoc(help_text).partition("\n\n")
    wrapped = wrap_text(body, TEXT_WIDTH, preserve_paragraphs=True)
    return sum(1 for line in wrapped.splitlines() if line.strip())


def example_count(epilog: str | None) -> int:
    """The `athc ...` lines under the epilog's `Examples:` heading."""
    _, _, examples = inspect.cleandoc(epilog or "").partition("Examples:")
    return sum(1 for line in examples.splitlines() if line.strip().startswith("athc "))


def summary_fits(help_text: str) -> bool:
    return len(summary(help_text)) <= SUMMARY_MAX


def description_fits(help_text: str) -> bool:
    return description_lines(help_text) in DESCRIPTION_LINES


def examples_fit(epilog: str | None) -> bool:
    return example_count(epilog) in EXAMPLE_COUNT


def _commands(
    group: click.Group, ctx: click.Context, prefix: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], click.Command]]:
    """Every command under `group` with its path, subgroups included."""
    for name in group.list_commands(ctx):
        command = group.get_command(ctx, name)
        assert command is not None
        path = (*prefix, name)
        yield path, command
        if isinstance(command, click.Group):
            sub_ctx = click.Context(command, parent=ctx, info_name=name)
            yield from _commands(command, sub_ctx, path)


COMMANDS = [((), cli), *_commands(cli, click.Context(cli, info_name="athc"))]


def _id(path: tuple[str, ...]) -> str:
    return " ".join(path) or "athc"


# ── the three range checks ────────────────────────────────────────────────────


@pytest.mark.parametrize(("length", "fits"), [(55, True), (56, False)])
def test_summary_limit(length: int, fits: bool) -> None:
    text = "S" * (length - 1) + "."
    assert len(summary(f"{text}\n\nThe description.")) == length
    assert summary_fits(f"{text}\n\nThe description.") is fits


def _help_with(lines: int) -> str:
    """A help text whose description is `lines` short paragraphs."""
    body = "\n\n".join(f"Line {n}." for n in range(1, lines + 1))
    return f"The summary.\n\n{body}"


@pytest.mark.parametrize(
    ("lines", "fits"), [(0, False), (1, True), (4, True), (5, False)]
)
def test_description_range(lines: int, fits: bool) -> None:
    assert description_lines(_help_with(lines)) == lines
    assert description_fits(_help_with(lines)) is fits


def test_description_counts_wrapped_lines() -> None:
    """A paragraph longer than the console counts each line it wraps to."""
    assert description_lines("The summary.\n\n" + "word " * 30) == 2


def _epilog_with(count: int) -> str:
    examples = "\n".join(f"  athc gameplan check plans{n}" for n in range(count))
    return f"Examples:\n\n{examples}"


@pytest.mark.parametrize(
    ("count", "fits"), [(0, False), (1, True), (6, True), (7, False)]
)
def test_examples_range(count: int, fits: bool) -> None:
    assert example_count(_epilog_with(count)) == count
    assert examples_fit(_epilog_with(count)) is fits


def test_no_epilog_has_no_examples() -> None:
    assert example_count(None) == 0


@pytest.mark.parametrize(
    ("path", "command"), COMMANDS, ids=[_id(path) for path, _ in COMMANDS]
)
def test_summary_fits_the_command_list(
    path: tuple[str, ...], command: click.Command
) -> None:
    assert summary_fits(command.help or ""), summary(command.help or "")


# Leaf commands only: a group's agreed screen has no description or examples.
LEAF_COMMANDS = [
    (path, command)
    for path, command in COMMANDS
    if not isinstance(command, click.Group)
]


@pytest.mark.parametrize(
    ("path", "command"), LEAF_COMMANDS, ids=[_id(path) for path, _ in LEAF_COMMANDS]
)
def test_description_fits_the_range(
    path: tuple[str, ...], command: click.Command
) -> None:
    assert description_fits(command.help or ""), description_lines(command.help or "")


@pytest.mark.parametrize(
    ("path", "command"), LEAF_COMMANDS, ids=[_id(path) for path, _ in LEAF_COMMANDS]
)
def test_examples_fit_the_range(path: tuple[str, ...], command: click.Command) -> None:
    assert examples_fit(command.epilog), example_count(command.epilog)


# ── argument help ─────────────────────────────────────────────────────────────

ARGUMENT_HELP = [
    (("check-ppp",), "PATH", "A .prf, a .pln, or a folder."),
    (
        ("config", "get"),
        "KEY",
        "Setting to print: league, path, play_path, team or ppp_path.",
    ),
    (
        ("config", "set"),
        "KEY",
        "Setting to change: league, path, play_path, team or ppp_path.",
    ),
    (("config", "set"), "VALUE", "New value."),
    (("convert-pdb",), "PDB_FILE", "WinLogStats .pdb file."),
    (
        ("convert-pdb",),
        "OUTPUT",
        ".xlsx, or .xlsm to include sorting macros, or a folder (default: "
        "PDB_FILE with .xlsm, beside it).",
    ),
    (
        ("gameplan", "check"),
        "PATH",
        ".pln files, folders, wildcards or game plan keys (default: current folder).",
    ),
    (("gameplan", "find-play"), "PLAY", "Plays to find (any case)."),
    (
        ("gameplan", "list-normals"),
        "GAME_PLAN",
        "A .pln file or a game plan key.",
    ),
    (
        ("gameplan", "list-normals"),
        "OUTPUT",
        "File or folder for the list (default: GAME_PLAN with .normals.txt, "
        "beside it; - prints it).",
    ),
    (
        ("gameplan", "list-specials"),
        "GAME_PLAN",
        "A .pln file or a game plan key.",
    ),
    (
        ("gameplan", "list-specials"),
        "OUTPUT",
        "File or folder for the list (default: GAME_PLAN with .specials.txt, "
        "beside it; - prints it).",
    ),
    (("gameplan", "replace-play"), "PLAY", "Play to replace (any case)."),
    (
        ("gameplan", "replace-play"),
        "REPLACEMENT",
        "Plays to put in its place, in order; each must be in the play pool.",
    ),
    (
        ("gameplan", "set-normals"),
        "GAME_PLAN",
        "A .pln file or a game plan key.",
    ),
    (
        ("gameplan", "set-normals"),
        "INPUT_FILE",
        "Play list, one name per line (- reads the console).",
    ),
    (
        ("gameplan", "set-specials"),
        "INPUT_FILE",
        "Play list, one name per line (- reads the console).",
    ),
    (
        ("playpool", "check"),
        "FOLDER",
        "Play pool folder (default: the league's play_path).",
    ),
    (
        ("profile", "check"),
        "PATH",
        ".prf files, folders, wildcards or profile keys (default: current folder).",
    ),
    (
        ("profile", "copy"),
        "SOURCE",
        "Profile to copy from: a .prf file or a profile key.",
    ),
    (
        ("profile", "copy"),
        "TARGET",
        "Profiles to copy into: .prf files, folders, wildcards or profile keys.",
    ),
    (("profile", "diff"), "PROFILE1", "A .prf file or a profile key."),
    (
        ("profile", "diff"),
        "PROFILE2",
        "The profile to compare it with, named the same way.",
    ),
]


@pytest.mark.parametrize(
    ("path", "name", "text"),
    ARGUMENT_HELP,
    ids=[f"{_id(path)} {name}" for path, name, _ in ARGUMENT_HELP],
)
def test_argument_help_line(
    runner, path: tuple[str, ...], name: str, text: str
) -> None:
    """Each argument's help is its own line in the Positional arguments section,
    under its bare name."""
    result = runner.invoke(cli, [*path, "--help"])
    assert result.exit_code == 0
    section = result.stdout.split("Positional arguments:\n", 1)[1]
    section = section.split("\n\n", 1)[0]
    assert f"{name} {text}" in " ".join(section.split())  # the help may wrap
    assert any(line.split()[0] == name for line in section.splitlines())


# ── examples ──────────────────────────────────────────────────────────────────

EXAMPLES = [
    (("check-ppp",), ["athc check-ppp", "athc check-ppp handed-in"]),
    (
        ("gameplan", "find-play"),
        [
            "athc gameplan find-play OR45RL01",
            "athc gameplan find-play OR45RL01 BCFGPAT --path plans -r",
        ],
    ),
    (
        ("gameplan", "list-normals"),
        [
            "athc gameplan list-normals off1",
            "athc gameplan list-normals DEN-OGP1.pln plays.txt --sort category",
        ],
    ),
    (
        ("gameplan", "list-specials"),
        [
            "athc gameplan list-specials def1 -",
            "athc gameplan list-specials DEN-DGP1.pln spec.txt",
        ],
    ),
    (
        ("gameplan", "replace-play"),
        [
            "athc gameplan replace-play OLDRUN NEWRUN",
            "athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r",
        ],
    ),
    (
        ("gameplan", "set-normals"),
        [
            "athc gameplan set-normals off1 plays.txt",
            "athc gameplan set-normals DEN-OGP1.pln -",
        ],
    ),
    (
        ("gameplan", "set-specials"),
        [
            "athc gameplan set-specials spec.txt",
            "athc gameplan set-specials spec.txt --path plans -r",
        ],
    ),
]


@pytest.mark.parametrize(
    ("path", "examples"), EXAMPLES, ids=[_id(path) for path, _ in EXAMPLES]
)
def test_examples_close_the_help(
    runner, path: tuple[str, ...], examples: list[str]
) -> None:
    """The examples end the help, under `Examples:`, one per line, and their
    count is in range."""
    result = runner.invoke(cli, [*path, "--help"])
    assert result.exit_code == 0
    block = "".join(f"    {example}\n" for example in examples)
    assert result.stdout.endswith(f"\n  Examples:\n\n{block}")
    assert examples_fit(dict(COMMANDS)[path].epilog)


# ── whole screens ─────────────────────────────────────────────────────────────

GAME_PLAN_KEYS = """\
  Game plan keys, for your team's league game plans:
    off1  1st-half offense    def1  1st-half defense
    off2  2nd-half offense    def2  2nd-half defense
"""
TEAM_OPTION = """\
  --team NAME      Team the game plan keys refer to (default: team in
                   league.toml).
  --league NAME    League to use (default: the one set with athc config set
                   league).
  -h, --help       Show this message and exit.
"""

SCREENS = {
    ("autocontinue",): """\
Usage: athc autocontinue [OPTIONS]

  Click the game's Continue button between plays.

  Watches the primary monitor while the game is the active window and clicks
  Continue each time it appears, after a short delay. Runs until you press
  Ctrl+C or move the mouse to the top-left corner of the screen.

Options:
  --delay SECONDS                 Seconds to wait before each click. Overrides
                                  delay_before_continue in athc.ini (1.0 by
                                  default).
  -n, --dry-run                   Report the button each time it is found;
                                  never move the mouse or click.
  --hot-corner / --no-hot-corner  Stop when the mouse hits the top-left
                                  corner. Overrides hot_corner in athc.ini (on
                                  by default).
  -h, --help                      Show this message and exit.

  Examples:

    athc autocontinue
    athc autocontinue --delay 3
    athc autocontinue --dry-run
""",
    ("gameplan",): """\
Usage: athc gameplan [OPTIONS] COMMAND [ARGS]...

  Check and edit game plans (.pln).

Options:
  -h, --help  Show this message and exit.

Commands:
  check          Check game plans against the league's rules.
  find-play      Find plays by name in game plans.
  list-normals   List the 64 normal plays in a game plan.
  list-specials  List the special-teams plays in a game plan.
  replace-play   Replace one play with another in game plans.
  set-normals    Set the 64 normal plays from a play list.
  set-specials   Set the special-teams plays from a play list.
""",
    ("gameplan", "check"): f"""\
Usage: athc gameplan check [OPTIONS] [PATH]...

  Check game plans against the league's rules.

  To check game plans with their profiles, run athc check-ppp.

Positional arguments:
  PATH  .pln files, folders, wildcards or game plan keys (default: current
        folder).

Options:
  -r, --recursive  Include subfolders.
{TEAM_OPTION}
{GAME_PLAN_KEYS}
  Examples:

    athc gameplan check
    athc gameplan check off1
    athc gameplan check plans -r
""",
    ("gameplan", "find-play"): f"""\
Usage: athc gameplan find-play [OPTIONS] PLAY...

  Find plays by name in game plans.

  Lists each play's normal and special-teams slots in each game plan.

Positional arguments:
  PLAY  Plays to find (any case).

Options:
  --path PATH      Game plans to search: a .pln file, a folder, a wildcard or
                   a game plan key (default: your team's game plans).
  -r, --recursive  Include subfolders.
{TEAM_OPTION}
{GAME_PLAN_KEYS}
  Examples:

    athc gameplan find-play OR45RL01
    athc gameplan find-play OR45RL01 BCFGPAT --path plans -r
""",
    ("gameplan", "replace-play"): f"""\
Usage: athc gameplan replace-play [OPTIONS] PLAY REPLACEMENT...

  Replace one play with another in game plans.

  Each game plan gets the first REPLACEMENT not already in it with which it
  still passes athc gameplan check; the others are backups, tried in order.

Positional arguments:
  PLAY         Play to replace (any case).
  REPLACEMENT  Plays to put in its place, in order; each must be in the play
               pool.

Options:
  --path PATH      Game plans to edit: a .pln file, a folder, a wildcard or a
                   game plan key (default: your team's game plans).
  -r, --recursive  Include subfolders.
{TEAM_OPTION}
{GAME_PLAN_KEYS}
  Examples:

    athc gameplan replace-play OLDRUN NEWRUN
    athc gameplan replace-play OLDRUN NEWRUN BACKUP --path plans -r
""",
    ("gameplan", "set-specials"): f"""\
Usage: athc gameplan set-specials [OPTIONS] INPUT_FILE

  Set the special-teams plays from a play list.

  Other-side game plans are skipped; unlisted categories keep their plays.

Positional arguments:
  INPUT_FILE  Play list, one name per line (- reads the console).

Options:
  --path PATH      Game plans to edit: a .pln file, a folder, a wildcard or a
                   game plan key (default: your team's game plans).
  -r, --recursive  Include subfolders.
{TEAM_OPTION}
{GAME_PLAN_KEYS}
  Examples:

    athc gameplan set-specials spec.txt
    athc gameplan set-specials spec.txt --path plans -r
""",
    ("gameplan", "list-normals"): f"""\
Usage: athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT]

  List the 64 normal plays in a game plan.

  An existing output file is replaced.

Positional arguments:
  GAME_PLAN  A .pln file or a game plan key.
  OUTPUT     File or folder for the list (default: GAME_PLAN with
             .normals.txt, beside it; - prints it).

Options:
  --sort [slot|name|category]  slot keeps slot order (empty slots blank); name
                               sorts by name; category groups by category
                               under :: headers with the league's names.
                               [default: slot]
  --team NAME                  Team the game plan keys refer to (default: team
                               in league.toml).
  --league NAME                League to use (default: the one set with athc
                               config set league).
  -h, --help                   Show this message and exit.

{GAME_PLAN_KEYS}
  Examples:

    athc gameplan list-normals off1
    athc gameplan list-normals DEN-OGP1.pln plays.txt --sort category
""",
    ("gameplan", "list-specials"): f"""\
Usage: athc gameplan list-specials [OPTIONS] GAME_PLAN [OUTPUT]

  List the special-teams plays in a game plan.

  Lists them in game plan order; an existing output file is replaced.

Positional arguments:
  GAME_PLAN  A .pln file or a game plan key.
  OUTPUT     File or folder for the list (default: GAME_PLAN with
             .specials.txt, beside it; - prints it).

Options:
  --team NAME    Team the game plan keys refer to (default: team in
                 league.toml).
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

{GAME_PLAN_KEYS}
  Examples:

    athc gameplan list-specials def1 -
    athc gameplan list-specials DEN-DGP1.pln spec.txt
""",
    ("gameplan", "set-normals"): f"""\
Usage: athc gameplan set-normals [OPTIONS] GAME_PLAN INPUT_FILE

  Set the 64 normal plays from a play list.

  Lines starting with :: are comments; run athc gameplan check afterward.

Positional arguments:
  GAME_PLAN   A .pln file or a game plan key.
  INPUT_FILE  Play list, one name per line (- reads the console).

Options:
  --team NAME    Team the game plan keys refer to (default: team in
                 league.toml).
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

{GAME_PLAN_KEYS}
  Examples:

    athc gameplan set-normals off1 plays.txt
    athc gameplan set-normals DEN-OGP1.pln -
""",
}


@pytest.mark.parametrize("path", list(SCREENS), ids=_id)
def test_help_screen(runner, path: tuple[str, ...]) -> None:
    """The whole help, as an 80-column console shows it."""
    result = runner.invoke(cli, [*path, "--help"], prog_name="athc", terminal_width=78)
    assert result.exit_code == 0
    assert result.stdout == SCREENS[path]


# ── Windows words ─────────────────────────────────────────────────────────────

NOT_WINDOWS_WORDS = (
    "directory",
    "directories",
    "stdout",
    "glob",
    "config dir",
    "ctrl-c",
    "file manager",
)


@pytest.mark.parametrize("path", [path for path, _ in COMMANDS], ids=_id)
def test_help_uses_windows_words(runner, path: tuple[str, ...]) -> None:
    """Folder, console, wildcard, File Explorer and Ctrl+C, as Windows says them."""
    result = runner.invoke(cli, [*path, "--help"])
    assert result.exit_code == 0
    text = result.stdout.lower()
    for word in NOT_WINDOWS_WORDS:
        assert word not in text
