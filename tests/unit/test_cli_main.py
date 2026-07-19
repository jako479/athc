"""Tests for the umbrella entry point's top-level error guard (`athc.cli.main`)."""

from __future__ import annotations

import pytest

import athc.cli as cli_pkg


def _boom() -> None:
    raise RuntimeError("kaboom")


def test_main_converts_unexpected_error_to_message(monkeypatch, caplog) -> None:
    # Unexpected exceptions become a one-line message + exit 2, not a traceback.
    monkeypatch.setattr(cli_pkg, "cli", _boom)
    with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
        cli_pkg.main()
    assert exc.value.code == 2
    assert any("kaboom" in r.getMessage() for r in caplog.records)


def test_main_debug_reraises(monkeypatch) -> None:
    # ATHC_DEBUG=1 re-raises so developers get the full traceback.
    monkeypatch.setenv("ATHC_DEBUG", "1")
    monkeypatch.setattr(cli_pkg, "cli", _boom)
    with pytest.raises(RuntimeError, match="kaboom"):
        cli_pkg.main()
