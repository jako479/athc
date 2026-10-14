"""The one place errors become a line, a log entry and an exit code: the `main`
of every athc command and group, which the `athc` script and `python -m athc`
reach through `athc.cli.main()`."""

from __future__ import annotations

import runpy
import sys
from collections.abc import Callable
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from athc.cli import CONTEXT_SETTINGS, AthcCommand, cli
from athc.errors import ALREADY_EXISTS, FILE_NOT_FOUND, AthcError


def _command(raiser: Callable[[], None]) -> click.Command:
    @click.command(cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
    def cmd() -> None:
        raiser()

    return cmd


def _log(log_dir: Path) -> str:
    return (log_dir / "athc.log").read_text(encoding="utf-8")


def test_athc_error_is_a_fail_line_exit_2(log_dir: Path) -> None:
    def _raise() -> None:
        raise AthcError("league 'NOPE' not found")

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 2
    assert result.stderr == "FAIL league 'NOPE' not found\n" and result.stdout == ""
    assert "ERROR league 'NOPE' not found" in _log(log_dir)
    assert _log(log_dir).rstrip().endswith("INFO exit 2")


def test_os_error_is_a_fail_line_exit_2() -> None:
    def _raise() -> None:
        raise FileNotFoundError(2, "No such file or directory", "x.pln")

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL x.pln: {FILE_NOT_FOUND}\n"


def test_unwritable_log_folder_is_a_fail_line_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "logs"
    blocker.write_text("not a folder", encoding="utf-8")
    monkeypatch.setenv("ATHC_LOG_DIR", str(blocker))
    result = CliRunner().invoke(_command(lambda: None), [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {blocker}: {ALREADY_EXISTS}\n"
    assert result.stdout == ""


def test_bug_is_unexpected_with_traceback_in_the_log(log_dir: Path) -> None:
    def _raise() -> None:
        raise RuntimeError("kaboom")

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL Unexpected error. See {log_dir / 'athc.log'} for details.\n"
    )
    assert "RuntimeError: kaboom" in _log(log_dir)


def test_ctrl_c_is_interrupted_130(log_dir: Path) -> None:
    def _raise() -> None:
        raise KeyboardInterrupt

    result = CliRunner().invoke(_command(_raise), [])
    assert result.exit_code == 130
    assert result.stderr.endswith("FAIL Interrupted.\n")
    assert "INFO exit 130" in _log(log_dir)


def test_usage_error_keeps_clicks_text(log_dir: Path) -> None:
    result = CliRunner().invoke(cli, ["gameplan", "check", "--nope"])
    assert result.exit_code == 2
    assert "Usage:" in result.stderr and "No such option" in result.stderr
    assert "ERROR No such option" in _log(log_dir)


def test_usage_error_gets_its_period(log_dir: Path) -> None:
    """Click leaves the period off this one; the one place adds it."""
    result = CliRunner().invoke(cli, ["gameplan", "list-normals", "a", "b", "c"])
    assert result.exit_code == 2
    assert result.stderr.startswith("Usage: ")
    assert result.stderr.endswith("Error: Got unexpected extra argument (c).\n")
    assert "ERROR Got unexpected extra argument (c).\n" in _log(log_dir)


@pytest.mark.parametrize(
    ("args", "ending"),
    [
        (["gameplan", "check", "--nope"], "Error: No such option '--nope'.\n"),
        (
            ["gameplan", "check", "--recursiv"],
            "Error: No such option '--recursiv'. Did you mean '--recursive'?\n",
        ),
    ],
    ids=["period", "question"],
)
def test_usage_error_that_ends_a_sentence_is_kept(args: list[str], ending: str) -> None:
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 2
    assert result.stderr.endswith(ending)


def test_click_wildcard_expansion_is_off(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """On Windows Click would turn `GP*.pln` into GP1.pln and GP2.pln before
    the command saw it, and list-normals would write the play list over
    GP2.pln. athc gets the word as typed, and list-normals takes one file."""
    for name in ("GP1.pln", "GP2.pln"):
        (tmp_path / name).write_bytes(b"a game plan")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["athc", "gameplan", "list-normals", "GP*.pln"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert capsys.readouterr().err == f"FAIL GP*.pln: {FILE_NOT_FOUND}\n"
    assert (tmp_path / "GP2.pln").read_bytes() == b"a game plan"


def test_positional_arguments_show_bare_names() -> None:
    """An optional argument and a repeating one are listed as `OUTPUT_FILE`
    and `PLAY`; the usage line and Click's error hint keep `[OUTPUT_FILE]`
    and `PLAY...`."""

    @click.command(cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
    @click.argument("play", nargs=-1, required=True, help="Plays to find.")
    @click.argument("output_file", required=False, help="Where to write them.")
    def cmd(play: tuple[str, ...], output_file: str | None) -> None:
        pass

    help_text = CliRunner().invoke(cmd, ["--help"], prog_name="cmd").stdout
    assert "Usage: cmd [OPTIONS] PLAY... [OUTPUT_FILE]\n" in help_text
    section = help_text.split("Positional arguments:\n", 1)[1].split("\n\n", 1)[0]
    assert section.splitlines() == [
        "  PLAY         Plays to find.",
        "  OUTPUT_FILE  Where to write them.",
    ]
    missing = CliRunner().invoke(cmd, [])
    assert missing.stderr.endswith("Error: Missing argument 'PLAY...'.\n")


def test_bare_athc_shows_help_without_logging_it(log_dir: Path) -> None:
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 2
    assert result.stderr.startswith("Usage: ") and result.stdout == ""
    log = _log(log_dir)
    assert "Usage:" not in log
    assert "ERROR no command given; help shown" in log
    assert not log.splitlines()[0].endswith(" ")  # no args, no trailing space


def test_bare_group_shows_help_without_logging_it(log_dir: Path) -> None:
    result = CliRunner().invoke(cli, ["gameplan"])
    assert result.exit_code == 2
    assert result.stderr.startswith("Usage: ")
    assert "Usage:" not in _log(log_dir)


def test_findings_code_passes_through(log_dir: Path) -> None:
    @click.command(cls=AthcCommand, context_settings=CONTEXT_SETTINGS)
    @click.pass_context
    def cmd(ctx: click.Context) -> None:
        ctx.exit(1)

    assert CliRunner().invoke(cmd, []).exit_code == 1
    assert "INFO exit 1" in _log(log_dir)


def test_normal_return_is_exit_0(log_dir: Path) -> None:
    result = CliRunner().invoke(_command(lambda: None), [])
    assert result.exit_code == 0
    assert "INFO exit 0" in _log(log_dir)


def test_start_line_names_the_version_and_args(log_dir: Path) -> None:
    CliRunner().invoke(cli, ["--version"])
    first = _log(log_dir).splitlines()[0]
    assert " INFO athc " in first and first.endswith(" --version")


def test_athc_debug_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATHC_DEBUG", "1")

    def _raise() -> None:
        raise RuntimeError("kaboom")

    assert CliRunner().invoke(_command(_raise), []).exit_code == 2


def test_python_m_athc_goes_through_main(
    log_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["athc"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("athc", run_name="__main__", alter_sys=True)
    assert exc.value.code == 2  # bare `athc`: Click's no-args help is a usage error
    assert "Usage:" in capsys.readouterr().err
    assert "INFO exit 2" in _log(log_dir)
