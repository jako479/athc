"""Writer protocol and registry, keyed by output-format extension."""

from __future__ import annotations

from collections.abc import Callable
from os import PathLike
from typing import Protocol

from athc.scheduler.domain.schedule import Schedule
from athc.scheduler.writers.html_writer import HtmlScheduleWriter
from athc.scheduler.writers.txt_writer import TxtScheduleWriter

StrPath = str | PathLike[str]


class ScheduleWriter(Protocol):
    """Output boundary for persisting or exporting a generated schedule."""

    def write(self, schedule: Schedule) -> None: ...


# A factory takes the output path and the league name (the text writer has no
# use for the name).
WriterFactory = Callable[[StrPath, str], ScheduleWriter]


def _html(output: StrPath, league_name: str) -> ScheduleWriter:
    return HtmlScheduleWriter(output, league_name=league_name)


def _txt(output: StrPath, league_name: str) -> ScheduleWriter:
    return TxtScheduleWriter(output)


WRITERS: dict[str, WriterFactory] = {
    "html": _html,
    "htm": _html,
    "txt": _txt,
}


def available_writer_formats() -> tuple[str, ...]:
    """Return the file-extension tokens callers may pass to `get_writer`."""
    return tuple(sorted(set(WRITERS)))


def get_writer(fmt: str, output: StrPath, league_name: str) -> ScheduleWriter:
    """Return a writer for `fmt` bound to `output`. Raises ValueError if unsupported."""
    try:
        factory = WRITERS[fmt.lower()]
    except KeyError as exc:
        choices = ", ".join(available_writer_formats())
        raise ValueError(
            f"Unsupported output format {fmt!r}. Available: {choices}"
        ) from exc
    return factory(output, league_name)
