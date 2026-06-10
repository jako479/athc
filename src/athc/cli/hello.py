from __future__ import annotations

import click

from athc.hello.core import greet


@click.command(
    help="Read a greeting from the [hello] section of athc.ini and print it."
)
def hello() -> None:
    click.echo(greet())
