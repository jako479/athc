"""Unit tests for playpool filename-filter rules."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from athc.playpool import (
    FilenameFilter,
    PlaypoolRules,
    RulesFileError,
    build_rules,
    load_rules,
)
from tests.unit.playpool.conftest import RULES_TOML


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "rules.toml"
    p.write_text(text, encoding="utf-8")
    return p


# ── parsing ───────────────────────────────────────────────────────────────────


def test_load_test_rules() -> None:
    rules = load_rules(RULES_TOML)
    assert "GBglpH1R" in rules.timed.include
    assert "TR" in rules.timed.suffix_any
    assert rules.rollout.suffix_none  # populated
    assert len(rules.qb_draw.regex_any) == 2  # compiled


def test_build_from_dict() -> None:
    rules = build_rules({"RolloutPass": {"suffix_any": ["R"]}})
    assert rules.rollout.suffix_any == ("R",)
    assert rules.timed == FilenameFilter()  # absent section → empty


def test_missing_section_is_empty(tmp_path: Path) -> None:
    rules = load_rules(write(tmp_path, "schema_version = 1\n"))
    assert rules == PlaypoolRules()


def test_unknown_section(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="unknown section"):
        load_rules(write(tmp_path, "[Bogus]\nsuffix_any = []\n"))


def test_unknown_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="unknown key"):
        load_rules(write(tmp_path, "[TimedPass]\nbogus = []\n"))


def test_bad_value_type(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="must be a list of strings"):
        load_rules(write(tmp_path, '[TimedPass]\nsuffix_any = "T"\n'))


def test_section_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="must be a table"):
        load_rules(write(tmp_path, "TimedPass = 1\n"))


def test_bad_regex(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="invalid regex"):
        load_rules(write(tmp_path, '[TimedPass]\nregex_any = ["("]\n'))


def test_two_bad_regexes_both_reported(tmp_path: Path) -> None:
    src = write(tmp_path, '[TimedPass]\nregex_any = ["(", "["]\n')
    with pytest.raises(RulesFileError) as ei:
        load_rules(src)
    bad = [e for e in ei.value.errors if "invalid regex" in e]
    assert len(bad) == 2
    assert any("'('" in e for e in bad)
    assert any("'['" in e for e in bad)


def test_collects_multiple_errors(tmp_path: Path) -> None:
    src = write(
        tmp_path,
        "[Bogus]\n"  # unknown section
        "x = []\n"
        "[TimedPass]\n"
        "bogus = []\n"  # unknown key
        'suffix_any = "T"\n'  # bad-type list field
        'regex_any = ["(", "["]\n',  # two invalid regexes
    )
    with pytest.raises(RulesFileError) as ei:
        load_rules(src)
    errors = ei.value.errors
    assert any("unknown section" in e for e in errors)
    assert any("unknown key" in e for e in errors)
    assert any("must be a list of strings" in e for e in errors)
    regex_errors = [e for e in errors if "invalid regex" in e]
    assert len(regex_errors) == 2
    assert any("'('" in e for e in regex_errors)
    assert any("'['" in e for e in regex_errors)
    assert len(errors) == 5


def test_toml_parse_error(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="TOML parse error"):
        load_rules(write(tmp_path, "not = valid = toml"))


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError):
        load_rules(tmp_path / "nope.toml")


def test_pnfl_rules_load() -> None:
    root = Path(__file__).resolve().parents[3]
    rules = load_rules(root / "release" / "rules" / "PNFL.playpool.toml")
    assert "SGZfade" in rules.timed.include
    assert rules.qb_draw.regex_any


# ── FilenameFilter.matches (case-sensitive; vetoes win) ───────────────────────


def test_suffix_any_match() -> None:
    f = FilenameFilter(suffix_any=("T",))
    assert f.matches("PLAYT")
    assert not f.matches("PLAYR")


def test_suffix_none_vetoes() -> None:
    f = FilenameFilter(suffix_any=("T1",), suffix_none=("OUT1",))
    assert not f.matches("FOOOUT1")  # ends in T1 but vetoed by OUT1


def test_include_forces_on() -> None:
    f = FilenameFilter(suffix_any=("T",), include=frozenset({"GBglpH1R"}))
    assert f.matches("GBglpH1R")  # no T suffix, but included


def test_exclude_vetoes() -> None:
    f = FilenameFilter(suffix_any=("R",), exclude=frozenset({"FAKER"}))
    assert not f.matches("FAKER")
    assert f.matches("OTHERR")


def test_regex_any() -> None:
    f = FilenameFilter(regex_any=(re.compile("^.1"),))
    assert f.matches("A1B")  # 2nd char is "1"
    assert not f.matches("AB1")


def test_case_sensitive() -> None:
    f = FilenameFilter(include=frozenset({"GBglpH1R"}), suffix_any=("Top",))
    assert f.matches("GBglpH1R") and not f.matches("gbglph1r")
    assert f.matches("punTop") and not f.matches("punTOP")


# ── the two scenarios called out: timed+rollout, and excluded-timed → rollout ──


def test_rollout_and_timed_both(rules: PlaypoolRules) -> None:
    name = "DEEPTR"  # ends "TR": a timed suffix AND a rollout suffix; not excluded
    assert rules.timed.matches(name)
    assert rules.rollout.matches(name)


def test_timed_excluded_still_rollout(rules: PlaypoolRules) -> None:
    name = "FAKETR"  # ends "TR"; listed in TimedPass.exclude
    assert not rules.timed.matches(name)  # timed vetoed by exclude
    assert rules.rollout.matches(name)  # still a rollout
