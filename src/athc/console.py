"""The one console. Every line a command shows goes through here: results on
stdout, status and progress on the stream the design names, the label word
colored and nothing else, and every status line also written to the run log.
"""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.text import Text

from athc.log import log_path, logger

# Never wrap a line, never restyle numbers or paths, never read `[x]` or `:x:`
# in a message as markup or an emoji: `2> err.log` holds whole plain lines.
_OPTIONS: dict[str, Any] = {
    "soft_wrap": True,
    "highlight": False,
    "markup": False,
    "emoji": False,
}
_LABEL_WIDTH = 5  # "OK   ", "SKIP ", "WARN ", "FAIL "


class AthcConsole:
    """One Console for stdout, one for stderr. Rich turns color on for a
    terminal and off when piped; `NO_COLOR` forces it off, `FORCE_COLOR` on."""

    def __init__(
        self, *, force_terminal: bool | None = None, no_color: bool | None = None
    ) -> None:
        self.out = Console(force_terminal=force_terminal, no_color=no_color, **_OPTIONS)
        self.err = Console(
            stderr=True, force_terminal=force_terminal, no_color=no_color, **_OPTIONS
        )

    def print(self, text: str = "") -> None:
        """A result line: the command's product. stdout, never logged."""
        self.out.print(text)

    def ok(self, message: str) -> None:
        """One item done."""
        self._status(self.out, "OK", "green", message, logging.INFO)

    def skip(self, message: str) -> None:
        """One item skipped on purpose."""
        self._status(self.out, "SKIP", "cyan", message, logging.INFO)

    def result(self, message: str) -> None:
        """A tally, or the headline of an item with findings. stdout, logged."""
        self.out.print(message)
        logger.info("%s", message)

    def progress(self, message: str) -> None:
        """Progress of a long run. stderr, logged."""
        self.err.print(message)
        logger.info("%s", message)

    def warn(self, message: str) -> None:
        """Noted, nothing failed."""
        self._status(self.err, "WARN", "yellow", message, logging.WARNING)

    def fail(self, message: str) -> None:
        """One item, or the run, failed."""
        self._status(self.err, "FAIL", "red", message, logging.ERROR)

    def unexpected(self, what: str | None = None) -> None:
        """A bug. Call it inside the `except`, so the traceback reaches the log."""
        subject = f"{what}: " if what else ""
        message = f"{subject}unexpected error (see log: {log_path()})"
        self._status(self.err, "FAIL", "red", message, logging.ERROR, exc_info=True)

    def _status(
        self,
        target: Console,
        label: str,
        color: str,
        message: str,
        level: int,
        *,
        exc_info: bool = False,
    ) -> None:
        padded = label.ljust(_LABEL_WIDTH)
        target.print(Text.assemble((label, color), padded[len(label) :], message))
        logger.log(level, "%s%s", padded, message, exc_info=exc_info)


console = AthcConsole()
