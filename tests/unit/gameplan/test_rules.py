"""Unit tests for the gameplan rules loader."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from athc.gameplan import load_rules
from athc.gameplan.rules import RulesFileError

# A minimal valid rule set to append sections onto.
MINIMAL = "schema_version = 1\n"

OFF_SECTION = """
[offense.RM]
required = true
min_count = 10
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "rules.toml"
    p.write_text(text, encoding="utf-8")
    return p


# ── short-name labels ─────────────────────────────────────────────────────────


def test_offense_short_label_maps_to_full_name(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, MINIMAL + OFF_SECTION)])
    assert "Run Middle" in rules.offense_categories
    assert rules.offense_categories["Run Middle"].min_count == 10


def test_defense_short_label_maps_to_full_name(tmp_path: Path) -> None:
    text = MINIMAL + "[defense.RunDazzle]\nrequired = false\nmin_count = 4\n"
    rules = load_rules([write(tmp_path, text)])
    assert "Run Dazzle" in rules.defense_categories


def test_unknown_offense_label(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.ZZZ]\nrequired = true\nmin_count = 1\n"
    with pytest.raises(RulesFileError, match="not an offense category label"):
        load_rules([write(tmp_path, text)])


def test_unknown_defense_label(tmp_path: Path) -> None:
    text = MINIMAL + "[defense.Nonsense]\nrequired = true\nmin_count = 1\n"
    with pytest.raises(RulesFileError, match="not a defense category label"):
        load_rules([write(tmp_path, text)])


# ── min_count / max_count ─────────────────────────────────────────────────────


def test_required_and_min_count_default_when_omitted(tmp_path: Path) -> None:
    """Omitted `required`/`min_count` default to False/0; a cap-only rule is valid."""
    text = MINIMAL + "[offense.RM]\nmax_count = 12\n"
    rules = load_rules([write(tmp_path, text)])
    rule = rules.offense_categories["Run Middle"]
    assert rule.required is False
    assert rule.min_count == 0
    assert rule.max_count == 12


def test_empty_section_rejected(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.RM]\n"
    with pytest.raises(RulesFileError, match="empty rule"):
        load_rules([write(tmp_path, text)])


def test_max_count_optional_offense(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.RM]\nrequired = true\nmin_count = 4\nmax_count = 12\n"
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_categories["Run Middle"].max_count == 12


def test_max_count_optional_defense(tmp_path: Path) -> None:
    text = (
        MINIMAL + "[defense.RunLeft]\nrequired = true\nmin_count = 6\nmax_count = 9\n"
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.defense_categories["Run Left"].max_count == 9


def test_max_count_absent_is_none(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, MINIMAL + OFF_SECTION)])
    assert rules.offense_categories["Run Middle"].max_count is None


def test_max_count_must_be_int(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.RM]\nrequired = true\nmin_count = 4\nmax_count = "x"\n'
    with pytest.raises(RulesFileError, match="must be an integer"):
        load_rules([write(tmp_path, text)])


def test_required_must_be_bool(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.RM]\nrequired = 1\nmin_count = 4\n"
    with pytest.raises(RulesFileError, match="must be a boolean"):
        load_rules([write(tmp_path, text)])


def test_min_count_must_be_int(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.RM]\nmin_count = "x"\n'
    with pytest.raises(RulesFileError, match="must be an integer"):
        load_rules([write(tmp_path, text)])


# ── run/pass cap gating still applies ─────────────────────────────────────────


def test_run_cap_rejected_on_pass(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.PSL]\nrequired = true\nmin_count = 5\nmax_qb_draws = 1\n"
    with pytest.raises(RulesFileError, match="unknown key"):
        load_rules([write(tmp_path, text)])


def test_pass_caps_parse(tmp_path: Path) -> None:
    text = (
        MINIMAL + "[offense.PSL]\nrequired = true\nmin_count = 5\n"
        'max_rollouts = 2\nmax_timed_percent = "1/2"\n'
    )
    rules = load_rules([write(tmp_path, text)])
    rule = rules.offense_categories["Pass Short Left"]
    assert rule.max_rollouts == 2
    assert rule.max_timed_percent == Fraction(1, 2)


# ── count ranges (>= 0, no upper bound) ───────────────────────────────────────

# (section, key) for every integer count setting.
COUNT_SETTINGS = [
    ("[offense.RM]", "min_count"),
    ("[offense.RM]", "max_count"),
    ("[offense.RM]", "max_qb_draws"),
    ("[offense.PSL]", "max_rollouts"),
]


@pytest.mark.parametrize("section,key", COUNT_SETTINGS)
def test_count_zero_ok(tmp_path: Path, section: str, key: str) -> None:
    load_rules(
        [write(tmp_path, MINIMAL + f"{section}\n{key} = 0\n")]
    )  # 0 = lower limit


@pytest.mark.parametrize("section,key", COUNT_SETTINGS)
def test_count_negative_rejected(tmp_path: Path, section: str, key: str) -> None:
    with pytest.raises(RulesFileError, match=">= 0"):  # -1 = one below 0
        load_rules([write(tmp_path, MINIMAL + f"{section}\n{key} = -1\n")])


# ── percent ranges (fraction in [0, 1]) ───────────────────────────────────────

# (section, key, category name) for every fraction setting.
PERCENT_SETTINGS = [
    ("[offense.PSL]", "max_timed_percent", "Pass Short Left"),
    ("[defense.PassShort]", "max_two_dl_percent", "Pass Short"),
]


@pytest.mark.parametrize("section,key,name", PERCENT_SETTINGS)
@pytest.mark.parametrize("val", ["0", "1", "1/2"])  # 0 and 1 = the limits
def test_percent_in_range_ok(
    tmp_path: Path, section: str, key: str, name: str, val: str
) -> None:
    rules = load_rules([write(tmp_path, MINIMAL + f'{section}\n{key} = "{val}"\n')])
    cats = (
        rules.offense_categories
        if section.startswith("[offense")
        else rules.defense_categories
    )
    assert getattr(cats[name], key) == Fraction(val)


@pytest.mark.parametrize("section,key", [(s, k) for s, k, _ in PERCENT_SETTINGS])
@pytest.mark.parametrize("val", ["-1/100", "101/100"])  # just below 0 / just above 1
def test_percent_out_of_range_rejected(
    tmp_path: Path, section: str, key: str, val: str
) -> None:
    with pytest.raises(RulesFileError, match=r"\[0, 1\]"):
        load_rules([write(tmp_path, MINIMAL + f'{section}\n{key} = "{val}"\n')])


# ── disallowed categories ─────────────────────────────────────────────────────


def test_disallowed_categories_parse(tmp_path: Path) -> None:
    text = (
        MINIMAL + "disallowed_offensive_categories = "
        '["Pass Long Left", "Razzle Dazzle Run", "User Specific"]\n'
        'disallowed_defensive_categories = ["User Specific"]\n'
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.disallowed_offensive_categories == frozenset(
        {"Pass Long Left", "Razzle Dazzle Run", "User Specific"}
    )
    assert rules.disallowed_defensive_categories == frozenset({"User Specific"})


def test_disallowed_unknown_category(tmp_path: Path) -> None:
    text = MINIMAL + 'disallowed_offensive_categories = ["Bogus Category"]\n'
    with pytest.raises(RulesFileError, match="unknown category"):
        load_rules([write(tmp_path, text)])


def test_disallowed_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + 'disallowed_offensive_categories = "Pass Long Left"\n'
    with pytest.raises(RulesFileError, match="must be a list"):
        load_rules([write(tmp_path, text)])


def test_disallowed_absent_is_empty(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, MINIMAL + OFF_SECTION)])
    assert rules.disallowed_offensive_categories == frozenset()
    assert rules.disallowed_defensive_categories == frozenset()


# ── layering / paths ──────────────────────────────────────────────────────────


def test_empty_paths_rejected() -> None:
    with pytest.raises(RulesFileError, match="at least one"):
        load_rules([])


def test_layering_replaces_category_rule(tmp_path: Path) -> None:
    """A later file's same-labelled section replaces the earlier one wholesale."""
    a = tmp_path / "a.toml"
    a.write_text(MINIMAL + "[offense.RM]\nrequired = true\nmin_count = 10\n", "utf-8")
    b = tmp_path / "b.toml"
    b.write_text("[offense.RM]\nmin_count = 4\n", "utf-8")
    rule = load_rules([a, b]).offense_categories["Run Middle"]
    assert rule.min_count == 4
    assert rule.required is False  # replaced, not merged with a's required=true


# ── the shipped PNFL rule set loads ───────────────────────────────────────────


def test_pnfl_rules_load() -> None:
    root = Path(__file__).resolve().parents[3]
    rules = load_rules([str(root / "release" / "rules" / "PNFL.gameplan.toml")])
    assert rules.offense_categories["Run Middle"].min_count == 10
    assert "User Specific" in rules.disallowed_offensive_categories
    assert "Pass Long Left" in rules.disallowed_offensive_categories
    assert rules.disallowed_defensive_categories == frozenset({"User Specific"})


def test_pnfl_required_special_categories() -> None:
    """The shipped PNFL set requires the six real kicks; fakes stay optional."""
    root = Path(__file__).resolve().parents[3]
    rules = load_rules([str(root / "release" / "rules" / "PNFL.gameplan.toml")])
    # Field Goal/PAT(1), Kickoff(2), Punt(3), Onside Kick(4), Free Kick(9), Squib(10).
    assert rules.required_special_categories == frozenset({1, 2, 3, 4, 9, 10})
    # The four fake-kick categories (5-8) are not required.
    assert rules.required_special_categories.isdisjoint({5, 6, 7, 8})


# ── collect-all-errors ────────────────────────────────────────────────────────


def test_collects_multiple_errors(tmp_path: Path) -> None:
    """One file with several independent problems reports them all at once."""
    text = (
        MINIMAL + "bogus_top_key = 1\n"
        "[offense.RM]\nmin_count = -1\n"
        "[offense.ZZZ]\nrequired = true\n"
    )
    with pytest.raises(RulesFileError) as exc:
        load_rules([write(tmp_path, text)])
    assert len(exc.value.errors) == 3
    joined = "\n".join(exc.value.errors)
    assert "unknown key" in joined
    assert ">= 0" in joined
    assert "not an offense category label" in joined


def test_collects_errors_across_files(tmp_path: Path) -> None:
    """Each file's problem is collected; loading reports both together."""
    a = tmp_path / "a.toml"
    a.write_text(MINIMAL + "[offense.RM]\nmin_count = -1\n", "utf-8")
    b = tmp_path / "b.toml"
    b.write_text(MINIMAL + "[defense.Nonsense]\nrequired = true\n", "utf-8")
    with pytest.raises(RulesFileError) as exc:
        load_rules([a, b])
    assert len(exc.value.errors) == 2
