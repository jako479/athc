"""Atomic file writes: the whole file or nothing.

`atomic_write` writes to a temp file beside the target, then swaps it in with
`os.replace`, so a reader (the game, another athc command) never sees a
half-written file and a failure leaves the old one as it was. Every library
writer and the config writers go through it.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import time
from os import fspath
from pathlib import Path

from athc.errors import StrPath

# A scanner may hold a just-written file for a moment on Windows, so the swap
# is retried for about a second before its error is raised (pip does the same).
_REPLACE_TRIES = 5
_REPLACE_WAIT = 0.25


def atomic_write(path: StrPath, data: bytes | str, *, encoding: str = "utf-8") -> None:
    """Write `data` to `path` by way of a temp file in the same folder.

    `bytes` is written as is; `str` is written as `Path.write_text` would,
    UTF-8 with the platform newline. The folder must exist: nothing is
    created but the file. Any OSError is re-raised naming `path`, never the
    temp file, which is removed; the target then still holds what it held.
    """
    target = Path(path)
    temp = target.with_name(f"{target.name}.{secrets.token_hex(4)}.tmp")
    try:
        # One open with O_EXCL, never tempfile: on Windows tempfile retries a
        # folder that refuses new files until it has tried billions of names.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        fd = os.open(temp, flags, 0o666)
        if isinstance(data, bytes):
            with os.fdopen(fd, "wb") as binary:
                binary.write(data)
                binary.flush()
                os.fsync(binary.fileno())
        else:
            with os.fdopen(fd, "w", encoding=encoding) as text:
                text.write(data)
                text.flush()
                os.fsync(text.fileno())
        _replace(temp, target)
    except BaseException as error:
        # Never written, or already gone: the real error is being raised.
        with contextlib.suppress(OSError):
            temp.unlink()
        if isinstance(error, OSError):
            error.filename = fspath(path)
            error.filename2 = None
        raise


def _replace(temp: Path, target: Path) -> None:
    for attempt in range(1, _REPLACE_TRIES + 1):
        try:
            temp.replace(target)
            return
        except PermissionError:
            if attempt == _REPLACE_TRIES:
                raise
            time.sleep(_REPLACE_WAIT)
