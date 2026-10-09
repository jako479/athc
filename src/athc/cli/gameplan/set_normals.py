"""`athc gameplan set-normals` — set the 64 normal slots of a .pln from a play list."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from athc.cli import CONTEXT_SETTINGS, league_option
from athc.cli.gameplan import gameplan
from athc.cli.gameplan._common import build_pool, named_file, parse_play_list
from athc.console import console
from athc.errors import AthcError
from athc.fbpro98_gameplan import GamePlan, read_gameplan, write_gameplan
from athc.gameplan.config import load_config
from athc.gameplan.writer import InvalidPlayInputError, apply_normal_plays

NORMAL_COUNT = GamePlan.NUMBER_NORMAL_PLAYS


@gameplan.command(name="set-normals", context_settings=CONTEXT_SETTINGS)
@click.argument("gameplan_path", metavar="gameplan", type=click.Path(path_type=Path))
@click.argument(
    "input_path",
    metavar="input_file",
    type=click.Path(path_type=Path, allow_dash=True),
)
@click.option("-q", "--quiet", is_flag=True, help="Suppress the success message.")
@league_option
@click.pass_context
def set_normals(
    ctx: click.Context,
    gameplan_path: Path,
    input_path: Path,
    quiet: bool,
    league: str | None,
) -> None:
    """Replace the 64 normal slots of gameplan from the play list in input_file.

    An input_file of `-` reads the list from the console. One play name per line;
    `::` comment lines and ` ::` trailers are ignored. The league's play pool
    resolves names; run `check` to validate the result.
    """
    gameplan_path = named_file(gameplan_path)
    if str(input_path) == "-":
        text = sys.stdin.read()
        source = ""  # a list from the console has no file to name
    else:
        text = named_file(input_path).read_text(encoding="utf-8")
        source = f"{input_path} "
    lines = parse_play_list(text)
    if len(lines) > NORMAL_COUNT:
        raise AthcError(f"input has {len(lines)} play(s), max is {NORMAL_COUNT}")
    config = load_config(league, rule_files=())  # no gameplan rules needed
    pool = build_pool(config.play_path, config.playpool_rules, config.categories)

    specials = [
        f"line {i}: '{name}' is a special teams play; use set-specials"
        for i, name in enumerate(lines, start=1)
        if (r := pool.find_by_name(name)) is not None and r.play_file.is_special_teams
    ]
    if specials:
        for err in specials:
            console.fail(f"{source}{err}")
        ctx.exit(2)

    gp = read_gameplan(gameplan_path)
    try:
        updated = apply_normal_plays(gp, lines, pool)
    except InvalidPlayInputError as error:
        for violation in error.violations:
            console.fail(f"{source}{violation}")
        ctx.exit(2)
    write_gameplan(updated, gameplan_path)
    count = sum(1 for p in updated.normal_plays if p is not None)
    if not quiet:
        console.ok(f"{gameplan_path}: {count} normal play(s)")
