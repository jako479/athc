"""Shared fixtures for the whole suite.

`config_dir` isolates config lookup (env `ATHC_CONFIG_DIR`) for every test; `write_config`
writes raw INI into that dir. Tests that exercise the platformdirs default must
`monkeypatch.delenv("ATHC_CONFIG_DIR", raising=False)` themselves.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate config lookup to a temp dir so tests never read the real machine config."""
    d = tmp_path / "athc-config"
    d.mkdir()
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(d))
    return d


@pytest.fixture
def write_config(config_dir: Path) -> Callable[..., Path]:
    """Write raw INI (dedented, leading newline stripped) to `config_dir/name`."""

    def _write(body: str, name: str = "athc.ini") -> Path:
        path = config_dir / name
        path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
        return path

    return _write


@pytest.fixture
def make_league(config_dir: Path) -> Callable[..., Path]:
    """Create `leagues/<name>/` (with `rules/` and `standings/`) under the temp
    config dir, write `league.ini` from `body` when given, and return the folder."""

    def _make(name: str = "PNFL", body: str | None = None) -> Path:
        folder = config_dir / "leagues" / name
        (folder / "rules").mkdir(parents=True)
        (folder / "standings").mkdir()
        if body is not None:
            (folder / "league.ini").write_text(
                textwrap.dedent(body).lstrip("\n"), encoding="utf-8"
            )
        return folder

    return _make
