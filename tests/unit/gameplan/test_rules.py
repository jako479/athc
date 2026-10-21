"""Unit tests for the gameplan rules loader."""

from __future__ import annotations

import re
from fractions import Fraction
from functools import partial
from pathlib import Path

import pytest

from athc.fbpro98_play import CategoryLabels
from athc.gameplan import DefenseCategoryRule, OffenseCategoryRule, Rules
from athc.gameplan import load_rules as _load_rules
from athc.gameplan.rules import RulesFileError
from tests.conftest import PNFL_LABELS, shipped_files, shipped_id

# Every test loads with the PNFL labels unless it says otherwise.
load_rules = partial(_load_rules, labels=PNFL_LABELS)

# A minimal valid rule set (an empty file) to append sections onto.
MINIMAL = ""

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
    with pytest.raises(RulesFileError, match="Not an offense category label"):
        load_rules([write(tmp_path, text)])


def test_unknown_defense_label(tmp_path: Path) -> None:
    text = MINIMAL + "[defense.Nonsense]\nrequired = true\nmin_count = 1\n"
    with pytest.raises(RulesFileError, match="Not a defense category label"):
        load_rules([write(tmp_path, text)])


def test_side_not_a_table_rejected(tmp_path: Path) -> None:
    text = MINIMAL + 'offense = "RM"\n'
    with pytest.raises(RulesFileError, match=r"\[offense\]: Must be a table"):
        load_rules([write(tmp_path, text)])


def test_section_not_a_table_rejected(tmp_path: Path) -> None:
    text = MINIMAL + "[offense]\nRM = 5\n"
    with pytest.raises(RulesFileError, match=r"\[offense.RM\]: Must be a table"):
        load_rules([write(tmp_path, text)])


def test_league_label_section_needs_the_league_labels(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Not an offense category label"):
        _load_rules([write(tmp_path, MINIMAL + OFF_SECTION)], labels=CategoryLabels())


def test_game_name_section_loads_without_league_labels(tmp_path: Path) -> None:
    text = MINIMAL + '[offense."Run Middle"]\nrequired = true\n'
    rules = _load_rules([write(tmp_path, text)], labels=CategoryLabels())
    assert "Run Middle" in rules.offense_categories


def test_game_name_section_rejected_when_league_labels_it(tmp_path: Path) -> None:
    text = MINIMAL + '[offense."Run Middle"]\nrequired = true\n'
    with pytest.raises(RulesFileError, match="Not an offense category label") as exc:
        load_rules([write(tmp_path, text)])
    # The message lists the valid labels, plainly: the league's `RM`, not the
    # game name.
    valid = str(exc.value).split("Valid: ", 1)[1]
    assert ", RM, " in valid
    assert "Run Middle" not in valid


def test_unknown_label_message_lists_the_league_labels(tmp_path: Path) -> None:
    text = MINIMAL + "[defense.Nonsense]\nrequired = true\n"
    with pytest.raises(RulesFileError, match=", RunDazzle, "):
        load_rules([write(tmp_path, text)])


@pytest.mark.parametrize(
    "label",
    ["Pass Long Left", "Pass Long Middle", "Razzle Dazzle Run", "User Specific"],
)
def test_offense_game_name_label_loads(tmp_path: Path, label: str) -> None:
    """Categories without a league abbreviation are labeled by their game name."""
    text = MINIMAL + f'[offense."{label}"]\nmax_count = 0\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_categories[label].max_count == 0


def test_user_specific_label_loads_on_each_side(tmp_path: Path) -> None:
    text = (
        MINIMAL
        + '[offense."User Specific"]\nmax_count = 0\n'
        + '[defense."User Specific"]\nmax_count = 1\n'
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_categories["User Specific"].max_count == 0
    assert rules.defense_categories["User Specific"].max_count == 1


def test_game_name_label_on_wrong_side_is_rejected(tmp_path: Path) -> None:
    text = MINIMAL + '[defense."Pass Long Left"]\nmax_count = 0\n'
    with pytest.raises(RulesFileError, match="Not a defense category label"):
        load_rules([write(tmp_path, text)])


def test_unknown_label_message_lists_game_name_labels(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.ZZZ]\nmax_count = 0\n"
    with pytest.raises(RulesFileError, match="Pass Long Left"):
        load_rules([write(tmp_path, text)])


def test_required_special_accepts_clock_categories(tmp_path: Path) -> None:
    text = MINIMAL + 'required_special_categories = ["Run Clock", "Stop Clock"]\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.required_special_categories == frozenset({11, 12})


def test_required_special_rejects_unknown_name(tmp_path: Path) -> None:
    """One past the twelve known names: a name no special category has."""
    text = MINIMAL + 'required_special_categories = ["Spike"]\n'
    with pytest.raises(RulesFileError, match="Unknown name 'Spike'"):
        load_rules([write(tmp_path, text)])


def test_required_special_accepts_all_twelve_names(tmp_path: Path) -> None:
    names = (
        "Field Goal/PAT", "Kickoff", "Punt", "Onside Kick", "Fake FG Run",
        "Fake FG Pass", "Fake Punt Run", "Fake Punt Pass", "Free Kick",
        "Squib Kick", "Run Clock", "Stop Clock",
    )  # fmt: skip
    listed = ", ".join(f'"{name}"' for name in names)
    text = MINIMAL + f"required_special_categories = [{listed}]\n"
    rules = load_rules([write(tmp_path, text)])
    assert rules.required_special_categories == frozenset(range(1, 13))


def test_required_special_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + 'required_special_categories = "Punt"\n'
    with pytest.raises(
        RulesFileError, match="required_special_categories: Must be a list"
    ):
        load_rules([write(tmp_path, text)])


def test_required_special_entries_must_be_strings(tmp_path: Path) -> None:
    text = MINIMAL + "required_special_categories = [3]\n"
    with pytest.raises(
        RulesFileError, match="required_special_categories: Entries must be strings"
    ):
        load_rules([write(tmp_path, text)])


def test_custom_special_play_required_defaults_false(tmp_path: Path) -> None:
    assert load_rules([write(tmp_path, MINIMAL)]).custom_special_play_required is False


def test_custom_special_play_required_parses(tmp_path: Path) -> None:
    text = MINIMAL + "custom_special_play_required = true\n"
    assert load_rules([write(tmp_path, text)]).custom_special_play_required is True


def test_custom_special_play_required_must_be_bool(tmp_path: Path) -> None:
    text = MINIMAL + 'custom_special_play_required = "yes"\n'
    with pytest.raises(
        RulesFileError, match="custom_special_play_required: Must be a boolean"
    ):
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
    with pytest.raises(RulesFileError, match="Empty rule"):
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
    with pytest.raises(RulesFileError, match="Must be an integer"):
        load_rules([write(tmp_path, text)])


def test_required_must_be_bool(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.RM]\nrequired = 1\nmin_count = 4\n"
    with pytest.raises(RulesFileError, match="Must be a boolean"):
        load_rules([write(tmp_path, text)])


def test_min_count_must_be_int(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.RM]\nmin_count = "x"\n'
    with pytest.raises(RulesFileError, match="Must be an integer"):
        load_rules([write(tmp_path, text)])


def test_count_rejects_a_boolean(tmp_path: Path) -> None:
    """TOML's `true` is not a count, though Python counts it as an int."""
    text = MINIMAL + "[offense.RM]\nmin_count = true\n"
    with pytest.raises(RulesFileError, match="min_count: Must be an integer"):
        load_rules([write(tmp_path, text)])


# ── run/pass cap gating still applies ─────────────────────────────────────────


def test_run_cap_rejected_on_pass(tmp_path: Path) -> None:
    text = (
        MINIMAL
        + "[offense.PSL]\nrequired = true\nmin_count = 5\nmax_qb_runs_count = 1\n"
    )
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, text)])


def test_pass_cap_rejected_on_run(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.RM]\nmax_rollouts_count = 1\n"
    with pytest.raises(
        RulesFileError,
        match=re.escape("[offense.RM]: Unknown key(s): max_rollouts_count."),
    ):
        load_rules([write(tmp_path, text)])


def test_offense_cap_rejected_on_defense(tmp_path: Path) -> None:
    text = MINIMAL + "[defense.PassShort]\nmax_qb_runs_count = 1\n"
    with pytest.raises(
        RulesFileError,
        match=re.escape("[defense.PassShort]: Unknown key(s): max_qb_runs_count."),
    ):
        load_rules([write(tmp_path, text)])


def test_pass_caps_parse(tmp_path: Path) -> None:
    text = (
        MINIMAL + "[offense.PSL]\nrequired = true\nmin_count = 5\n"
        'max_rollouts_count = 2\nmax_timed_ratio = "1/2"\n'
    )
    rules = load_rules([write(tmp_path, text)])
    rule = rules.offense_categories["Pass Short Left"]
    assert rule.max_rollouts_count == 2
    assert rule.max_timed_ratio == Fraction(1, 2)


# ── one form per attribute ────────────────────────────────────────────────────

# (section, attribute) for every capped attribute.
ATTRIBUTES = [
    ("[offense.RM]", "max_qb_runs"),
    ("[offense.PSL]", "max_rollouts"),
    ("[offense.PSL]", "max_timed"),
    ("[defense.PassShort]", "max_two_dl"),
]

# Each section the tables here use: its side and the game name its rule is
# filed under.
SECTIONS = {
    "[offense.RM]": ("offense", "Run Middle"),
    "[offense.PSL]": ("offense", "Pass Short Left"),
    "[defense.PassShort]": ("defense", "Pass Short"),
}


def rule_of(rules: Rules, section: str) -> OffenseCategoryRule | DefenseCategoryRule:
    side, name = SECTIONS[section]
    if side == "offense":
        return rules.offense_categories[name]
    return rules.defense_categories[name]


@pytest.mark.parametrize("section,attr", ATTRIBUTES)
def test_two_forms_of_one_attribute_rejected(
    tmp_path: Path, section: str, attr: str
) -> None:
    text = MINIMAL + f'{section}\n{attr}_count = 2\n{attr}_ratio = "1/2"\n'
    with pytest.raises(RulesFileError, match="Set at most one of"):
        load_rules([write(tmp_path, text)])


@pytest.mark.parametrize("section,attr", ATTRIBUTES)
@pytest.mark.parametrize(
    "form,value,parsed",
    [("count", "2", 2), ("ratio", '"1/2"', Fraction(1, 2)), ("percent", "50", 50)],
)
def test_one_form_of_one_attribute_accepted(
    tmp_path: Path, section: str, attr: str, form: str, value: str, parsed: object
) -> None:
    text = MINIMAL + f"{section}\n{attr}_{form} = {value}\n"
    rule = rule_of(load_rules([write(tmp_path, text)]), section)
    assert getattr(rule, f"{attr}_{form}") == parsed
    others = [f for f in ("count", "ratio", "percent") if f != form]
    assert all(getattr(rule, f"{attr}_{f}") is None for f in others)


# ── count ranges (>= 0, no upper bound) ───────────────────────────────────────

# (section, key) for every integer count setting.
COUNT_SETTINGS = [
    ("[offense.RM]", "min_count"),
    ("[offense.RM]", "max_count"),
    ("[offense.RM]", "max_qb_runs_count"),
    ("[offense.PSL]", "max_rollouts_count"),
]


@pytest.mark.parametrize("section,key", COUNT_SETTINGS)
def test_count_zero_ok(tmp_path: Path, section: str, key: str) -> None:
    text = MINIMAL + f"{section}\n{key} = 0\n"  # 0 = lower limit
    assert getattr(rule_of(load_rules([write(tmp_path, text)]), section), key) == 0


@pytest.mark.parametrize("section,key", COUNT_SETTINGS)
def test_count_negative_rejected(tmp_path: Path, section: str, key: str) -> None:
    with pytest.raises(RulesFileError, match=">= 0"):  # -1 = one below 0
        load_rules([write(tmp_path, MINIMAL + f"{section}\n{key} = -1\n")])


# ── ratio ranges (fraction in [0, 1]) ─────────────────────────────────────────

# (section, key, category name) for every fraction setting.
RATIO_SETTINGS = [
    ("[offense.PSL]", "max_timed_ratio", "Pass Short Left"),
    ("[defense.PassShort]", "max_two_dl_ratio", "Pass Short"),
]


@pytest.mark.parametrize("section,key,name", RATIO_SETTINGS)
@pytest.mark.parametrize("val", ["0", "1", "1/2"])  # 0 and 1 = the limits
def test_ratio_in_range_ok(
    tmp_path: Path, section: str, key: str, name: str, val: str
) -> None:
    rules = load_rules([write(tmp_path, MINIMAL + f'{section}\n{key} = "{val}"\n')])
    cats = (
        rules.offense_categories
        if section.startswith("[offense")
        else rules.defense_categories
    )
    assert getattr(cats[name], key) == Fraction(val)


@pytest.mark.parametrize("section,key", [(s, k) for s, k, _ in RATIO_SETTINGS])
@pytest.mark.parametrize("val", ["-1/100", "101/100"])  # just below 0 / just above 1
def test_ratio_out_of_range_rejected(
    tmp_path: Path, section: str, key: str, val: str
) -> None:
    with pytest.raises(RulesFileError, match=r"\[0, 1\]"):
        load_rules([write(tmp_path, MINIMAL + f'{section}\n{key} = "{val}"\n')])


def test_ratio_must_be_string(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.PSL]\nmax_timed_ratio = 0.5\n"
    with pytest.raises(RulesFileError, match='Must be a string like "1/2"'):
        load_rules([write(tmp_path, text)])


@pytest.mark.parametrize(
    "val", ["half", "1/0"], ids=["not a number", "zero denominator"]
)
def test_ratio_not_a_fraction_rejected(tmp_path: Path, val: str) -> None:
    text = MINIMAL + f'[offense.PSL]\nmax_timed_ratio = "{val}"\n'
    with pytest.raises(
        RulesFileError,
        match=re.escape(f"[offense.PSL].max_timed_ratio: Invalid fraction '{val}': "),
    ):
        load_rules([write(tmp_path, text)])


# ── percent ranges (whole number 0-100) ───────────────────────────────────────
# One shared validator, so one key exercises it.


@pytest.mark.parametrize("val", [0, 100, 50])  # 0 and 100 = the limits
def test_percent_in_range_ok(tmp_path: Path, val: int) -> None:
    text = MINIMAL + f"[offense.PSL]\nmax_timed_percent = {val}\n"
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_categories["Pass Short Left"].max_timed_percent == val


@pytest.mark.parametrize("val", [-1, 101])  # just below 0 / just above 100
def test_percent_out_of_range_rejected(tmp_path: Path, val: int) -> None:
    text = MINIMAL + f"[offense.PSL]\nmax_timed_percent = {val}\n"
    with pytest.raises(RulesFileError, match=r"\[0, 100\]"):
        load_rules([write(tmp_path, text)])


def test_percent_must_be_int(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.PSL]\nmax_timed_percent = "50"\n'
    with pytest.raises(RulesFileError, match="Must be an integer"):
        load_rules([write(tmp_path, text)])


# ── allowed categories ────────────────────────────────────────────────────────


def test_allowed_categories_parse(tmp_path: Path) -> None:
    """Entries are the league's names; the rules hold the game names."""
    text = (
        MINIMAL + 'allowed_offensive_categories = ["RM", "PSL"]\n'
        'allowed_defensive_categories = ["RunDazzle"]\n'
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.allowed_offensive_categories == frozenset(
        {"Run Middle", "Pass Short Left"}
    )
    assert rules.allowed_defensive_categories == frozenset({"Run Dazzle"})


def test_allowed_game_name_rejected(tmp_path: Path) -> None:
    """Only league names count, even for a category the league has no name for."""
    text = MINIMAL + 'allowed_offensive_categories = ["Pass Long Left"]\n'
    with pytest.raises(RulesFileError, match="is not an offense category label"):
        load_rules([write(tmp_path, text)])


def test_allowed_needs_the_league_names(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_offensive_categories = ["RM"]\n'
    with pytest.raises(RulesFileError, match="is not an offense category label"):
        _load_rules([write(tmp_path, text)], labels=CategoryLabels())


def test_allowed_unknown_offense_label(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_offensive_categories = ["Bogus"]\n'
    with pytest.raises(RulesFileError) as exc:
        load_rules([write(tmp_path, text)])
    assert str(exc.value).startswith(
        f"{tmp_path / 'rules.toml'}: allowed_offensive_categories: "
        "'Bogus' is not an offense category label. Valid: "
    )
    assert str(exc.value).endswith(".")


def test_allowed_unknown_defense_label(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_defensive_categories = ["Bogus"]\n'
    with pytest.raises(RulesFileError, match="is not a defense category label"):
        load_rules([write(tmp_path, text)])


def test_allowed_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_offensive_categories = "RM"\n'
    with pytest.raises(RulesFileError, match="Must be a list"):
        load_rules([write(tmp_path, text)])


def test_allowed_entries_must_be_strings(tmp_path: Path) -> None:
    text = MINIMAL + "allowed_offensive_categories = [1]\n"
    with pytest.raises(RulesFileError, match="Entries must be strings"):
        load_rules([write(tmp_path, text)])


def test_allowed_absent_is_empty(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, MINIMAL + OFF_SECTION)])
    assert rules.allowed_offensive_categories == frozenset()
    assert rules.allowed_defensive_categories == frozenset()


def test_allowed_empty_list_loads_empty(tmp_path: Path) -> None:
    """An explicit `[]` is the same as omitting the key: nothing enforced."""
    text = MINIMAL + "allowed_offensive_categories = []\n"
    rules = load_rules([write(tmp_path, text)])
    assert rules.allowed_offensive_categories == frozenset()


# ── [profile_compatibility] ───────────────────────────────────────────────────


def test_profile_compatibility_defaults_when_omitted(tmp_path: Path) -> None:
    """Omitted section leaves the compatibility check off."""
    rules = load_rules([write(tmp_path, MINIMAL)])
    assert rules.require_all_gameplan_categories_in_profile is False


def test_profile_compatibility_parses(tmp_path: Path) -> None:
    text = (
        MINIMAL + "[profile_compatibility]\n"
        "require_all_gameplan_categories_in_profile = true\n"
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.require_all_gameplan_categories_in_profile is True


def test_profile_compatibility_unknown_key(tmp_path: Path) -> None:
    text = MINIMAL + "[profile_compatibility]\nbogus = true\n"
    message = (
        "[profile_compatibility]: Unknown key(s): bogus. "
        "Valid: require_all_gameplan_categories_in_profile."
    )
    with pytest.raises(RulesFileError, match=re.escape(message)):
        load_rules([write(tmp_path, text)])


def test_profile_compatibility_must_be_bool(tmp_path: Path) -> None:
    text = (
        MINIMAL
        + '[profile_compatibility]\nrequire_all_gameplan_categories_in_profile = "x"\n'
    )
    with pytest.raises(RulesFileError, match="Must be a boolean"):
        load_rules([write(tmp_path, text)])


def test_profile_compatibility_must_be_table(tmp_path: Path) -> None:
    text = MINIMAL + "profile_compatibility = true\n"
    with pytest.raises(RulesFileError, match="Must be a table"):
        load_rules([write(tmp_path, text)])


def test_layering_overrides_profile_compatibility(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(
        "[profile_compatibility]\nrequire_all_gameplan_categories_in_profile = true\n",
        encoding="utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text(
        "[profile_compatibility]\nrequire_all_gameplan_categories_in_profile = false\n",
        encoding="utf-8",
    )
    assert load_rules([a, b]).require_all_gameplan_categories_in_profile is False
    assert load_rules([a, b]) == Rules()


# ── top-level keys ────────────────────────────────────────────────────────────


def test_schema_version_is_an_unknown_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match=r"\(top\): Unknown key"):
        load_rules([write(tmp_path, "schema_version = 1\n")])


# ── layering / paths ──────────────────────────────────────────────────────────


def test_empty_paths_rejected() -> None:
    with pytest.raises(RulesFileError, match="At least one"):
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
    assert load_rules([a, b]) == Rules(
        offense_categories={"Run Middle": OffenseCategoryRule(min_count=4)}
    )


def test_layering_replaces_allowed_list(tmp_path: Path) -> None:
    """A later file's allowed list replaces the earlier one; an omitted key
    keeps the earlier list."""
    a = tmp_path / "a.toml"
    a.write_text(
        MINIMAL + 'allowed_offensive_categories = ["RM", "RL"]\n'
        'allowed_defensive_categories = ["RunLeft"]\n',
        "utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text('allowed_offensive_categories = ["PSL"]\n', "utf-8")
    rules = load_rules([a, b])
    assert rules.allowed_offensive_categories == frozenset({"Pass Short Left"})
    assert rules.allowed_defensive_categories == frozenset({"Run Left"})
    assert rules == Rules(
        allowed_offensive_categories=frozenset({"Pass Short Left"}),
        allowed_defensive_categories=frozenset({"Run Left"}),
    )


def test_layering_replaces_special_keys(tmp_path: Path) -> None:
    """A later file's special keys replace the earlier ones; an omitted key
    keeps the earlier value."""
    a = tmp_path / "a.toml"
    a.write_text(
        'required_special_categories = ["Punt", "Kickoff"]\n'
        "custom_special_play_required = true\n",
        "utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text('required_special_categories = ["Field Goal/PAT"]\n', "utf-8")
    rules = load_rules([a, b])
    assert rules == Rules(
        required_special_categories=frozenset({1}),
        custom_special_play_required=True,
    )
    c = tmp_path / "c.toml"
    c.write_text("custom_special_play_required = false\n", "utf-8")
    assert load_rules([a, c]).custom_special_play_required is False


def test_bom_is_skipped(tmp_path: Path) -> None:
    """A UTF-8 byte-order mark (Notepad, Excel) is dropped, not a parse error."""
    p = tmp_path / "rules.toml"
    p.write_text(MINIMAL + OFF_SECTION, encoding="utf-8-sig")
    assert load_rules([p]).offense_categories["Run Middle"].min_count == 10


# ── every shipped league's rules load ─────────────────────────────────────────


@pytest.mark.parametrize("path", shipped_files("*/gameplan.toml"), ids=shipped_id)
def test_shipped_rules_load(path: Path) -> None:
    load_rules([path])


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
    assert "Unknown key" in joined
    assert ">= 0" in joined
    assert "Not an offense category label" in joined


def test_collects_errors_across_files(tmp_path: Path) -> None:
    """Each file's problem is collected; loading reports both together."""
    a = tmp_path / "a.toml"
    a.write_text(MINIMAL + "[offense.RM]\nmin_count = -1\n", "utf-8")
    b = tmp_path / "b.toml"
    b.write_text(MINIMAL + "[defense.Nonsense]\nrequired = true\n", "utf-8")
    with pytest.raises(RulesFileError) as exc:
        load_rules([a, b])
    assert len(exc.value.errors) == 2
