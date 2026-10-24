"""Unit tests for the profile rules loader."""

from __future__ import annotations

import re
from functools import partial
from pathlib import Path

import pytest

from athc.fbpro98_play import CategoryLabels
from athc.fbpro98_profile import Down, FieldPosition, MinutesRemaining, YardsToGo
from athc.profile import (
    PercentBound,
    ProfileRules,
    RulesFileError,
    SituationRule,
    SubstitutionRule,
)
from athc.profile import load_rules as _load_rules
from athc.profile.rules import (
    DEFENSE_LIST_SCOPE,
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    OFFENSE_LIST_SCOPE,
    PASS_LONG_ANY,
    PASS_LONG_LEFT,
    PASS_LONG_MIDDLE,
    PASS_LONG_RANDOM,
    PASS_LONG_RIGHT,
    PASS_MEDIUM_ANY,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_MIDDLE,
    PASS_MEDIUM_RANDOM,
    PASS_MEDIUM_RIGHT,
    PASS_SHORT_ANY,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RANDOM,
    PASS_SHORT_RIGHT,
    RAZZLE_DAZZLE_PASS,
    RAZZLE_DAZZLE_RUN,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RANDOM,
    RUN_RIGHT,
)
from tests.conftest import (
    PNFL_DEFENSE,
    PNFL_LABELS,
    PNFL_OFFENSE,
    league_labels,
    shipped_files,
    shipped_id,
)
from tests.unit.profile.conftest import (
    DATA,
    DEFENSE_CODES_BY_NAME,
    OFFENSE_CODES_BY_NAME,
    exact_substitution,
)

# Every test loads with the PNFL labels unless it says otherwise.
load_rules = partial(_load_rules, labels=PNFL_LABELS)

MINIMAL = "audibles_allowed = false\nmin_categories = 2\n"

# A valid situation section to append to MINIMAL, then mutate. `min_categories`
# is its constraint, so appending allowed/disallowed/mandatory stays valid.
SECTION = """
[offense.x]
time = ">5:00"
down = "first"
yards = "0-1"
fields = ["inside_def_5"]
min_categories = 2
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "rules.toml"
    p.write_text(text, encoding="utf-8")
    return p


def find(rules: tuple[SituationRule, ...], **filters: object) -> SituationRule:
    for r in rules:
        if all(getattr(r, k) == v for k, v in filters.items()):
            return r
    raise KeyError(filters)


def min_rule(n: int, *, time: MinutesRemaining | None = None) -> SituationRule:
    """The rule a section holding only `min_categories = n` (and `time`) gives."""
    return SituationRule(
        time=time,
        down=None,
        yards=None,
        fields=None,
        allowed_categories=None,
        disallowed_categories=frozenset(),
        mandatory_alternatives=(),
        min_categories=n,
    )


# ── normal ────────────────────────────────────────────────────────────────────


def test_load_valid_full() -> None:
    """Every top-level part of the full rule set loads as written."""
    rules = load_rules([DATA / "profile_rules.toml"])
    ranged = SubstitutionRule(
        out_percent=PercentBound(maximum=95),
        in_percent=PercentBound(minimum=96, maximum=100),
    )
    assert rules.audibles_allowed is False
    assert rules.min_categories == 2
    assert rules.require_all_profile_categories_in_gameplan is True
    assert rules.substitutions == {
        "QB": exact_substitution(75, 80),
        "OL": ranged,
        "RB": ranged,
        "WR": ranged,
        "DL": ranged,
        "LB": ranged,
        "DB": ranged,
    }
    assert rules.offense_allowed_categories == frozenset(range(0x00, 0x10)) - {
        RAZZLE_DAZZLE_RUN,
        PASS_LONG_LEFT,
        PASS_LONG_MIDDLE,
    }
    assert rules.defense_allowed_categories == frozenset(range(0x00, 0x10))
    assert (len(rules.offense_situations), len(rules.defense_situations)) == (15, 4)


def test_disallowed_parsed() -> None:
    rules = load_rules([DATA / "profile_rules.toml"])
    rule = find(rules.offense_situations, down=Down.THIRD, yards=YardsToGo.ZERO_TO_ONE)
    assert rule.disallowed_categories == frozenset({RAZZLE_DAZZLE_PASS})
    assert rule.allowed_categories is None


def test_mandatory_parsed() -> None:
    rules = load_rules([DATA / "profile_rules.toml"])
    rule = find(rules.offense_situations, down=Down.THIRD, yards=YardsToGo.OVER_TEN)
    assert rule.mandatory_alternatives == (frozenset({PASS_LONG_RIGHT}),)


def test_mandatory_multiple_categories(tmp_path: Path) -> None:
    """A flat list makes every listed category its own requirement (AND)."""
    text = MINIMAL + SECTION + 'mandatory = ["RL", "RM"]\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_situations[0].mandatory_alternatives == (
        frozenset({RUN_LEFT}),
        frozenset({RUN_MIDDLE}),
    )


def test_min_categories_on_rule(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.late]\ntime = ">5:00"\nmin_categories = 3\n'
    rules = load_rules([write(tmp_path, text)])
    rule = rules.offense_situations[0]
    assert rule.min_categories == 3
    assert rule.time == MinutesRemaining.OVER_FIVE


def test_omitted_buckets_are_none(tmp_path: Path) -> None:
    """Any omitted bucket filter is None (matches all)."""
    text = MINIMAL + '[offense.any]\nallowed = ["RM"]\n'
    rules = load_rules([write(tmp_path, text)])
    rule = rules.offense_situations[0]
    assert (rule.time, rule.down, rule.yards, rule.fields) == (None, None, None, None)


# Every filter value -> the game bucket it selects.
@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("time", '">5:00"', MinutesRemaining.OVER_FIVE),
        ("time", '">2:00-5:00"', MinutesRemaining.TWO_TO_FIVE),
        ("time", '">1:00-2:00"', MinutesRemaining.ONE_TO_TWO),
        ("time", '">0:15-1:00"', MinutesRemaining.FIFTEEN_SEC_TO_ONE),
        ("time", '"0:00-0:15"', MinutesRemaining.ZERO_TO_FIFTEEN_SEC),
        ("down", '"first"', Down.FIRST),
        ("down", '"second"', Down.SECOND),
        ("down", '"third"', Down.THIRD),
        ("down", '"fourth"', Down.FOURTH),
        ("yards", '"0-1"', YardsToGo.ZERO_TO_ONE),
        ("yards", '"2-5"', YardsToGo.TWO_TO_FIVE),
        ("yards", '"6-10"', YardsToGo.SIX_TO_TEN),
        ("yards", '">10"', YardsToGo.OVER_TEN),
        ("fields", '["inside_def_5"]', {FieldPosition.INSIDE_DEF_5}),
        ("fields", '["def_5_to_def_35"]', {FieldPosition.DEF_5_TO_DEF_35}),
        ("fields", '["def_35_to_off_35"]', {FieldPosition.DEF_35_TO_OFF_35}),
        ("fields", '["off_35_to_off_5"]', {FieldPosition.OFF_35_TO_OFF_5}),
        ("fields", '["inside_off_5"]', {FieldPosition.INSIDE_OFF_5}),
    ],
)
def test_filter_value_selects_its_bucket(
    tmp_path: Path, key: str, value: str, expected: object
) -> None:
    text = MINIMAL + f"[offense.x]\n{key} = {value}\nmin_categories = 2\n"
    rule = load_rules([write(tmp_path, text)]).offense_situations[0]
    assert getattr(rule, key) == expected


# Every category name a situation rule takes -> its codes; a defense pass name
# covers all three directions.
@pytest.mark.parametrize(
    ("side", "name", "expected"),
    [
        ("offense", "GLR", {GOAL_LINE_RUN}),
        ("offense", "RL", {RUN_LEFT}),
        ("offense", "RM", {RUN_MIDDLE}),
        ("offense", "RR", {RUN_RIGHT}),
        ("offense", "GLP", {GOAL_LINE_PASS}),
        ("offense", "PRD", {RAZZLE_DAZZLE_PASS}),
        ("offense", "PLR", {PASS_LONG_RIGHT}),
        ("offense", "PML", {PASS_MEDIUM_LEFT}),
        ("offense", "PMM", {PASS_MEDIUM_MIDDLE}),
        ("offense", "PMR", {PASS_MEDIUM_RIGHT}),
        ("offense", "PSL", {PASS_SHORT_LEFT}),
        ("offense", "PSM", {PASS_SHORT_MIDDLE}),
        ("offense", "PSR", {PASS_SHORT_RIGHT}),
        ("defense", "GLrun", {GOAL_LINE_RUN}),
        ("defense", "RunDazzle", {RAZZLE_DAZZLE_RUN}),
        ("defense", "RunLeft", {RUN_LEFT}),
        ("defense", "RunMiddle", {RUN_MIDDLE}),
        ("defense", "RunRight", {RUN_RIGHT}),
        ("defense", "GLpass", {GOAL_LINE_PASS}),
        ("defense", "PassDazzle", {RAZZLE_DAZZLE_PASS}),
        ("defense", "PassLong", PASS_LONG_ANY),
        ("defense", "PassMedium", PASS_MEDIUM_ANY),
        ("defense", "PassShort", PASS_SHORT_ANY),
    ],
)
def test_situation_category_name_selects_its_codes(
    tmp_path: Path, side: str, name: str, expected: set[int]
) -> None:
    text = MINIMAL + f'[{side}.x]\nallowed = ["{name}"]\n'
    rules = load_rules([write(tmp_path, text)])
    situations = (
        rules.offense_situations if side == "offense" else rules.defense_situations
    )
    assert situations[0].allowed_categories == expected


def test_situation_allowed_empty_list_is_an_empty_set(tmp_path: Path) -> None:
    """`allowed = []` in a section is an empty set, not "no limit"."""
    text = MINIMAL + "[offense.x]\nallowed = []\n"
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_situations[0].allowed_categories == frozenset()


def test_audibles_allowed_defaults_when_omitted(tmp_path: Path) -> None:
    """Omitted `audibles_allowed` defaults to True (no audibles check)."""
    rules = load_rules([write(tmp_path, "min_categories = 2\n")])
    assert rules.audibles_allowed is True


def test_min_categories_defaults_when_omitted(tmp_path: Path) -> None:
    """Omitted `min_categories` defaults to 0 (no baseline minimum)."""
    rules = load_rules([write(tmp_path, "audibles_allowed = false\n")])
    assert rules.min_categories == 0


# ── allowed category lists ────────────────────────────────────────────────────

VALID_OFFENSE = "GLP, GLR, PLR, PML, PMM, PMR, PRD, PSL, PSM, PSR, RL, RM, RR."
VALID_DEFENSE = (
    "GLpass, GLrun, PassDazzle, PassLong, PassMedium, PassShort, "
    "RunDazzle, RunLeft, RunMiddle, RunRight."
)


def load_error(tmp_path: Path, text: str, labels: CategoryLabels = PNFL_LABELS) -> str:
    """The whole message loading `text` with `labels` raises."""
    with pytest.raises(RulesFileError) as exc:
        _load_rules([write(tmp_path, text)], labels=labels)
    return str(exc.value)


def test_allowed_categories_parse(tmp_path: Path) -> None:
    """Labels resolve to codes; a defense label covers each of its codes."""
    text = (
        MINIMAL + 'allowed_offensive_categories = ["RL", "PSR"]\n'
        'allowed_defensive_categories = ["PassShort"]\n'
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_allowed_categories == frozenset({RUN_LEFT, PASS_SHORT_RIGHT})
    assert rules.defense_allowed_categories == PASS_SHORT_ANY


@pytest.mark.parametrize(
    ("side", "name"),
    [("offense", name) for name in OFFENSE_CODES_BY_NAME]
    + [("defense", name) for name in DEFENSE_CODES_BY_NAME],
)
def test_allowed_list_label_stands_for_its_category_codes(
    tmp_path: Path, side: str, name: str
) -> None:
    """Whatever a league calls a category, its label in the list stands for
    exactly that category's codes."""
    if side == "offense":
        labels = CategoryLabels.from_tables({name: "X"}, {})
        text = 'allowed_offensive_categories = ["X"]\n'
    else:
        labels = CategoryLabels.from_tables({}, {name: "X"})
        text = 'allowed_defensive_categories = ["X"]\n'
    rules = _load_rules([write(tmp_path, text)], labels=labels)
    assert (rules.offense_allowed_categories, rules.defense_allowed_categories) == (
        (OFFENSE_CODES_BY_NAME[name], frozenset())
        if side == "offense"
        else (frozenset(), DEFENSE_CODES_BY_NAME[name])
    )


def test_allowed_categories_omitted_is_empty(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, MINIMAL)])
    assert rules.offense_allowed_categories == frozenset()
    assert rules.defense_allowed_categories == frozenset()


def test_allowed_categories_empty_list_is_empty(tmp_path: Path) -> None:
    text = (
        MINIMAL + "allowed_offensive_categories = []\n"
        "allowed_defensive_categories = []\n"
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_allowed_categories == frozenset()
    assert rules.defense_allowed_categories == frozenset()


def test_allowed_categories_reject_game_name(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_offensive_categories = ["Razzle Dazzle Run"]\n'
    assert load_error(tmp_path, text) == (
        f"{tmp_path / 'rules.toml'}: allowed_offensive_categories: "
        f"'Razzle Dazzle Run' is not an offense category label. Valid: {VALID_OFFENSE}"
    )


def test_allowed_categories_reject_unknown_defense_label(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_defensive_categories = ["RL"]\n'
    assert load_error(tmp_path, text) == (
        f"{tmp_path / 'rules.toml'}: allowed_defensive_categories: "
        f"'RL' is not a defense category label. Valid: {VALID_DEFENSE}"
    )


def test_allowed_categories_reject_user_specific_label(tmp_path: Path) -> None:
    """Profiles have no User Specific category, so its league label is not one
    of the list's labels."""
    labels = CategoryLabels.from_tables(
        {**PNFL_OFFENSE, "User Specific": "US"}, PNFL_DEFENSE
    )
    text = MINIMAL + 'allowed_offensive_categories = ["US"]\n'
    assert load_error(tmp_path, text, labels=labels) == (
        f"{tmp_path / 'rules.toml'}: allowed_offensive_categories: "
        f"'US' is not an offense category label. Valid: {VALID_OFFENSE}"
    )


def test_allowed_categories_without_league_labels(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_offensive_categories = ["RL"]\n'
    assert load_error(tmp_path, text, labels=CategoryLabels()) == (
        f"{tmp_path / 'rules.toml'}: allowed_offensive_categories: "
        "'RL' is not an offense category label. Valid: ."
    )


def test_allowed_categories_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + 'allowed_offensive_categories = "RL"\n'
    assert load_error(tmp_path, text) == (
        f"{tmp_path / 'rules.toml'}: allowed_offensive_categories: Must be a list."
    )


def test_allowed_categories_entries_must_be_strings(tmp_path: Path) -> None:
    text = MINIMAL + "allowed_offensive_categories = [1]\n"
    assert load_error(tmp_path, text) == (
        f"{tmp_path / 'rules.toml'}: allowed_offensive_categories: "
        "Entries must be strings."
    )


def test_layering_replaces_allowed_list(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text('allowed_offensive_categories = ["RL", "RM"]\n', encoding="utf-8")
    b = tmp_path / "b.toml"
    b.write_text('allowed_offensive_categories = ["PSL"]\n', encoding="utf-8")
    assert load_rules([a, b]) == ProfileRules(
        offense_allowed_categories=frozenset({PASS_SHORT_LEFT})
    )


def test_layering_empty_list_clears_allowed(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(
        'allowed_offensive_categories = ["RL"]\n'
        'allowed_defensive_categories = ["PassShort"]\n',
        encoding="utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text(
        "allowed_offensive_categories = []\nallowed_defensive_categories = []\n",
        encoding="utf-8",
    )
    assert load_rules([a, b]) == ProfileRules()


def test_layering_omitted_keeps_allowed(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(
        'allowed_offensive_categories = ["RL"]\n'
        'allowed_defensive_categories = ["PassShort"]\n',
        encoding="utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text("min_categories = 2\n", encoding="utf-8")
    assert load_rules([a, b]) == ProfileRules(
        min_categories=2,
        offense_allowed_categories=frozenset({RUN_LEFT}),
        defense_allowed_categories=PASS_SHORT_ANY,
    )


# ── [gameplan_compatibility] ──────────────────────────────────────────────────


def test_gameplan_compatibility_defaults_when_omitted(tmp_path: Path) -> None:
    """Omitted section leaves the compatibility check off."""
    rules = load_rules([write(tmp_path, MINIMAL)])
    assert rules.require_all_profile_categories_in_gameplan is False


def test_gameplan_compatibility_parses(tmp_path: Path) -> None:
    text = (
        MINIMAL + "[gameplan_compatibility]\n"
        "require_all_profile_categories_in_gameplan = true\n"
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.require_all_profile_categories_in_gameplan is True


def test_gameplan_compatibility_unknown_key(tmp_path: Path) -> None:
    text = MINIMAL + "[gameplan_compatibility]\nbogus = true\n"
    message = (
        "[gameplan_compatibility]: Unknown key(s): bogus. "
        "Valid: require_all_profile_categories_in_gameplan."
    )
    with pytest.raises(RulesFileError, match=re.escape(message)):
        load_rules([write(tmp_path, text)])


def test_gameplan_compatibility_rejects_the_gameplan_rules_flag(tmp_path: Path) -> None:
    """`require_all_gameplan_categories_in_profile` belongs to the gameplan
    rules' `[profile_compatibility]`, so here it is an unknown key."""
    text = (
        MINIMAL + "[gameplan_compatibility]\n"
        "require_all_gameplan_categories_in_profile = true\n"
    )
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, text)])


def test_gameplan_compatibility_must_be_bool(tmp_path: Path) -> None:
    text = (
        MINIMAL
        + '[gameplan_compatibility]\nrequire_all_profile_categories_in_gameplan = "x"\n'
    )
    with pytest.raises(RulesFileError, match="Must be a boolean"):
        load_rules([write(tmp_path, text)])


def test_gameplan_compatibility_must_be_table(tmp_path: Path) -> None:
    text = MINIMAL + "gameplan_compatibility = true\n"
    with pytest.raises(RulesFileError, match="Must be a table"):
        load_rules([write(tmp_path, text)])


def test_layering_overrides_gameplan_compatibility(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(
        "[gameplan_compatibility]\nrequire_all_profile_categories_in_gameplan = true\n",
        encoding="utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text(
        "[gameplan_compatibility]\nrequire_all_profile_categories_in_gameplan = false\n",
        encoding="utf-8",
    )
    assert load_rules([a, b]).require_all_profile_categories_in_gameplan is False
    assert load_rules([a, b]) == ProfileRules()


def test_layering_overrides_scalar(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(MINIMAL, encoding="utf-8")
    b = tmp_path / "b.toml"
    b.write_text("min_categories = 9\n", encoding="utf-8")
    rules = load_rules([a, b])
    assert rules.min_categories == 9
    assert rules.audibles_allowed is False  # untouched by the overlay
    assert rules == ProfileRules(audibles_allowed=False, min_categories=9)


def test_layering_overrides_audibles(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text("audibles_allowed = false\n", encoding="utf-8")
    b = tmp_path / "b.toml"
    b.write_text("audibles_allowed = true\n", encoding="utf-8")
    rules = load_rules([a, b])
    assert rules.audibles_allowed is True
    assert rules == ProfileRules()


def test_layering_replaces_situation_rule_by_label(tmp_path: Path) -> None:
    """A later file's section of the same side and name replaces the earlier
    rule in its place; other names accumulate, and the same name on offense and
    defense is two rules."""
    a = tmp_path / "a.toml"
    a.write_text(
        "[offense.x]\nmin_categories = 3\n"
        "[offense.y]\nmin_categories = 4\n"
        "[defense.x]\nmin_categories = 5\n",
        encoding="utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text(
        '[offense.x]\ntime = ">5:00"\nmin_categories = 6\n'
        "[offense.z]\nmin_categories = 7\n",
        encoding="utf-8",
    )
    assert load_rules([a, b]) == ProfileRules(
        offense_situations=(
            min_rule(6, time=MinutesRemaining.OVER_FIVE),
            min_rule(4),
            min_rule(7),
        ),
        defense_situations=(min_rule(5),),
    )


# ── errors ────────────────────────────────────────────────────────────────────


def test_empty_paths() -> None:
    with pytest.raises(RulesFileError, match="At least one"):
        load_rules([])


def test_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with pytest.raises(RulesFileError) as exc:
        load_rules([missing])
    assert str(exc.value) == f"{missing}: The system cannot find the file specified."


def test_toml_parse_error(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Not valid TOML: "):
        load_rules([write(tmp_path, "not = valid = toml")])


def test_bom_is_skipped(tmp_path: Path) -> None:
    """A UTF-8 byte-order mark (Notepad, Excel) is dropped, not a parse error."""
    p = tmp_path / "rules.toml"
    p.write_text(MINIMAL, encoding="utf-8-sig")
    assert load_rules([p]).min_categories == 2


def test_negative_min_categories_rejected(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match=">= 0"):
        load_rules([write(tmp_path, "min_categories = -1\n")])


def test_collects_multiple_errors(tmp_path: Path) -> None:
    """Every problem in a file is reported together, not just the first."""
    text = (
        "min_categories = -1\n"
        '[offense.a]\nallowed = ["NOPE"]\n'
        '[defense.b]\ntime = "halftime"\nmin_categories = 2\n'
    )
    with pytest.raises(RulesFileError) as exc:
        load_rules([write(tmp_path, text)])
    assert len(exc.value.errors) == 3
    joined = "\n".join(exc.value.errors)
    assert (
        ">= 0" in joined and "Unknown category" in joined and "Unknown value" in joined
    )


def test_collects_errors_across_files(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text("min_categories = -1\n", encoding="utf-8")
    b = tmp_path / "b.toml"
    b.write_text('[offense.x]\nallowed = ["NOPE"]\n', encoding="utf-8")
    with pytest.raises(RulesFileError) as exc:
        load_rules([a, b])
    assert len(exc.value.errors) == 2


def test_negative_rule_min_categories_rejected(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.x]\ntime = ">5:00"\nmin_categories = -1\n'
    with pytest.raises(RulesFileError, match=">= 0"):
        load_rules([write(tmp_path, text)])


def test_unknown_top_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, MINIMAL + "bogus = 1\n")])


def test_schema_version_is_an_unknown_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, MINIMAL + "schema_version = 1\n")])


def test_unknown_situation_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, MINIMAL + SECTION + "bogus = 1\n")])


def test_situation_needs_constraint(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.empty]\ntime = ">5:00"\ndown = "first"\n'
    with pytest.raises(RulesFileError, match="Needs one of"):
        load_rules([write(tmp_path, text)])


def test_bad_time(tmp_path: Path) -> None:
    text = MINIMAL + SECTION.replace('">5:00"', '"halftime"')
    with pytest.raises(RulesFileError, match="Unknown value"):
        load_rules([write(tmp_path, text)])


def test_filter_must_be_a_string(tmp_path: Path) -> None:
    text = MINIMAL + SECTION.replace('">5:00"', "5")
    with pytest.raises(
        RulesFileError, match=re.escape("[offense.x].time: Must be a string.")
    ):
        load_rules([write(tmp_path, text)])


def test_allowed_and_disallowed_exclusive(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'allowed = ["RL"]\ndisallowed = ["RM"]\n'
    with pytest.raises(
        RulesFileError,
        match=r"\[offense\.x\]: Set at most one of allowed, disallowed\.",
    ):
        load_rules([write(tmp_path, text)])


def test_unknown_category(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'allowed = ["NOPE"]\n'
    with pytest.raises(RulesFileError, match="Unknown category"):
        load_rules([write(tmp_path, text)])


def test_category_entries_must_be_strings(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + "allowed = [1]\n"
    with pytest.raises(
        RulesFileError,
        match=re.escape("[offense.x].allowed: Entries must be strings (got int)."),
    ):
        load_rules([write(tmp_path, text)])


def test_mandatory_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'mandatory = "RL"\n'
    with pytest.raises(
        RulesFileError, match=r"\[offense\.x\]\.mandatory: Must be a list\."
    ):
        load_rules([write(tmp_path, text)])


def test_disallowed_empty_list_forbids_nothing(tmp_path: Path) -> None:
    text = MINIMAL + "[offense.x]\ndisallowed = []\n"
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_situations[0].disallowed_categories == frozenset()
    assert rules.offense_situations[0].allowed_categories is None


def test_disallowed_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.x]\ndisallowed = "PRD"\n'
    with pytest.raises(
        RulesFileError, match=re.escape("[offense.x].disallowed: Must be a list.")
    ):
        load_rules([write(tmp_path, text)])


def test_fields_must_be_a_non_empty_list(tmp_path: Path) -> None:
    text = MINIMAL + SECTION.replace('["inside_def_5"]', "[]")
    with pytest.raises(
        RulesFileError, match=r"\[offense\.x\]\.fields: Must be a non-empty list\."
    ):
        load_rules([write(tmp_path, text)])


def test_mandatory_unknown_category(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'mandatory = ["NOPE"]\n'
    with pytest.raises(RulesFileError, match="Unknown category"):
        load_rules([write(tmp_path, text)])


def test_unknown_field_name(tmp_path: Path) -> None:
    text = MINIMAL + SECTION.replace('"inside_def_5"', '"midfield"')
    with pytest.raises(RulesFileError, match="Unknown value"):
        load_rules([write(tmp_path, text)])


def test_field_entries_must_be_strings(tmp_path: Path) -> None:
    path = write(tmp_path, MINIMAL + SECTION.replace('"inside_def_5"', "[1]"))
    with pytest.raises(RulesFileError) as exc:
        load_rules([path])
    assert exc.value.errors == [f"{path}: [offense.x].fields: Entries must be strings."]


@pytest.mark.parametrize("value", ["5", "[1]"])
def test_side_must_be_a_table(tmp_path: Path, value: str) -> None:
    """Both sides' problems are collected, not just the first."""
    path = write(tmp_path, MINIMAL + f"offense = {value}\ndefense = {value}\n")
    with pytest.raises(RulesFileError) as exc:
        load_rules([path])
    assert exc.value.errors == [
        f"{path}: [offense]: Must be a table.",
        f"{path}: [defense]: Must be a table.",
    ]


@pytest.mark.parametrize("value", ["5", '"abc"'])
def test_situation_must_be_a_table(tmp_path: Path, value: str) -> None:
    path = write(tmp_path, MINIMAL + f"[offense]\nx = {value}\n")
    with pytest.raises(RulesFileError) as exc:
        load_rules([path])
    assert exc.value.errors == [f"{path}: [offense.x]: Must be a table."]


# ── substitutions ───────────────────────────────────────────────────────────────

ALL_POSITIONS = ["OL", "QB", "RB", "WR", "K", "DL", "LB", "DB"]
SUB_KEYS = [
    "out_percent",
    "min_out_percent",
    "max_out_percent",
    "in_percent",
    "min_in_percent",
    "max_in_percent",
]


def _subs(body: str) -> str:
    return MINIMAL + "[substitutions]\n" + body


def _single_key_rule(key: str, value: int) -> SubstitutionRule:
    """The rule one `key = value` produces (every other bound unchecked)."""
    side = "out_percent" if key.endswith("out_percent") else "in_percent"
    field = {"": "exact", "min_": "minimum", "max_": "maximum"}[key.removesuffix(side)]
    return SubstitutionRule(**{side: PercentBound(**{field: value})})


def test_substitutions_single_group(tmp_path: Path) -> None:
    text = _subs("QB = { out_percent = 75, in_percent = 80 }\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions == {"QB": exact_substitution(75, 80)}


def test_substitutions_all_groups(tmp_path: Path) -> None:
    body = "".join(
        f"{p} = {{ out_percent = 70, in_percent = 80 }}\n" for p in ALL_POSITIONS
    )
    rules = load_rules([write(tmp_path, _subs(body))])
    assert set(rules.substitutions) == set(ALL_POSITIONS)
    assert all(s == exact_substitution(70, 80) for s in rules.substitutions.values())


def test_substitutions_min_max_both_sides(tmp_path: Path) -> None:
    text = _subs(
        "QB = { min_out_percent = 70, max_out_percent = 80, "
        "min_in_percent = 75, max_in_percent = 90 }\n"
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions["QB"] == SubstitutionRule(
        out_percent=PercentBound(minimum=70, maximum=80),
        in_percent=PercentBound(minimum=75, maximum=90),
    )


# Any one key alone is a valid group (limits 0 and 100 included); everything
# else in the group stays unchecked.
@pytest.mark.parametrize("key", SUB_KEYS)
@pytest.mark.parametrize("value", [0, 100])
def test_substitutions_single_key_leaves_rest_unchecked(
    tmp_path: Path, key: str, value: int
) -> None:
    rules = load_rules([write(tmp_path, _subs(f"QB = {{ {key} = {value} }}\n"))])
    assert rules.substitutions["QB"] == _single_key_rule(key, value)


def test_substitutions_exact_one_side_range_other(tmp_path: Path) -> None:
    text = _subs("QB = { out_percent = 75, min_in_percent = 80 }\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions["QB"] == SubstitutionRule(
        out_percent=PercentBound(exact=75), in_percent=PercentBound(minimum=80)
    )


def test_substitutions_min_equals_max_ok(tmp_path: Path) -> None:
    text = _subs("QB = { min_out_percent = 75, max_out_percent = 75 }\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions["QB"].out_percent == PercentBound(minimum=75, maximum=75)


def test_substitutions_omitted_is_empty(tmp_path: Path) -> None:
    assert load_rules([write(tmp_path, MINIMAL)]).substitutions == {}


def test_substitutions_layering_override_and_accumulate(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(
        "[substitutions]\nQB = { out_percent = 75, in_percent = 80 }\n",
        encoding="utf-8",
    )
    b = tmp_path / "b.toml"
    b.write_text(
        "[substitutions]\nQB = { min_out_percent = 70 }\n"
        "DL = { out_percent = 60, in_percent = 70 }\n",
        encoding="utf-8",
    )
    rules = load_rules([a, b])
    # The later file replaces the whole group — the exact pair is gone.
    assert rules.substitutions["QB"] == SubstitutionRule(
        out_percent=PercentBound(minimum=70)
    )
    assert rules.substitutions["DL"] == exact_substitution(60, 70)  # accumulated
    assert rules == ProfileRules(
        substitutions={
            "QB": SubstitutionRule(out_percent=PercentBound(minimum=70)),
            "DL": exact_substitution(60, 70),
        }
    )


# Percent limits (min 0, max 100, out == in) accepted; every group shares the
# one parser.
@pytest.mark.parametrize("out,in_", [(0, 0), (0, 100), (100, 100)])
def test_substitutions_percent_limits_ok(tmp_path: Path, out: int, in_: int) -> None:
    text = _subs(f"QB = {{ out_percent = {out}, in_percent = {in_} }}\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions["QB"] == exact_substitution(out, in_)


# One below 0 / one above 100 rejected for every key; the message names the key.
@pytest.mark.parametrize("key", SUB_KEYS)
@pytest.mark.parametrize("value", [-1, 101])
def test_substitutions_percent_out_of_range(
    tmp_path: Path, key: str, value: int
) -> None:
    text = _subs(f"QB = {{ {key} = {value} }}\n")
    with pytest.raises(RulesFileError, match=rf"{key}: Must be in \[0, 100\]"):
        load_rules([write(tmp_path, text)])


@pytest.mark.parametrize(
    "body",
    [
        "out_percent = 75, min_out_percent = 70",
        "out_percent = 75, max_out_percent = 80",
        "in_percent = 80, min_in_percent = 75",
        "in_percent = 80, max_in_percent = 90",
    ],
)
def test_substitutions_exact_with_bound_same_side_rejected(
    tmp_path: Path, body: str
) -> None:
    side = body.split("_", 1)[0]
    msg = (
        rf"\[substitutions\]\.QB: Set at most one of {side}_percent, "
        rf"min_{side}_percent/max_{side}_percent\."
    )
    with pytest.raises(RulesFileError, match=msg):
        load_rules([write(tmp_path, _subs(f"QB = {{ {body} }}\n"))])


@pytest.mark.parametrize("side", ["out", "in"])
def test_substitutions_min_above_max_rejected(tmp_path: Path, side: str) -> None:
    body = f"min_{side}_percent = 71, max_{side}_percent = 70"  # one past equal
    msg = rf"\[substitutions\]\.QB\.min_{side}_percent: Must be <= max_{side}_percent\."
    with pytest.raises(RulesFileError, match=msg):
        load_rules([write(tmp_path, _subs(f"QB = {{ {body} }}\n"))])


# Exact out one above exact in rejected (out == in is accepted by
# test_substitutions_percent_limits_ok).
def test_substitutions_out_above_in_rejected(tmp_path: Path) -> None:
    text = _subs("QB = { out_percent = 81, in_percent = 80 }\n")
    msg = re.escape(
        "[substitutions].QB.out_percent: Must be <= in_percent (80), got 81."
    )
    with pytest.raises(RulesFileError, match=msg):
        load_rules([write(tmp_path, text)])


def test_substitutions_out_vs_in_not_checked_for_ranges(tmp_path: Path) -> None:
    """Only the two exact keys are compared; bounds never are."""
    text = _subs("QB = { min_out_percent = 90, max_in_percent = 80 }\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions["QB"] == SubstitutionRule(
        out_percent=PercentBound(minimum=90), in_percent=PercentBound(maximum=80)
    )


def test_substitutions_empty_group_rejected(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Needs one of"):
        load_rules([write(tmp_path, _subs("QB = {}\n"))])


def test_substitutions_unknown_position(tmp_path: Path) -> None:
    text = _subs("zz = { out_percent = 75, in_percent = 80 }\n")
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, text)])


def test_substitutions_unknown_group_key(tmp_path: Path) -> None:
    text = _subs("QB = { out_percent = 75, in_percent = 80, foo = 1 }\n")
    with pytest.raises(RulesFileError, match="Unknown key"):
        load_rules([write(tmp_path, text)])


def test_substitutions_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Must be a table"):
        load_rules([write(tmp_path, MINIMAL + "substitutions = 5\n")])


def test_substitutions_position_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="Must be a table"):
        load_rules([write(tmp_path, _subs("QB = 5\n"))])


@pytest.mark.parametrize("key", SUB_KEYS)
def test_substitutions_non_integer(tmp_path: Path, key: str) -> None:
    text = _subs(f'QB = {{ {key} = "x" }}\n')
    with pytest.raises(RulesFileError, match=rf"{key}: Must be an integer"):
        load_rules([write(tmp_path, text)])


@pytest.mark.parametrize("value", ["70.0", "true"])
def test_substitutions_float_or_bool_rejected(tmp_path: Path, value: str) -> None:
    """Whole numbers only — a float or boolean is not an integer."""
    text = _subs(f"QB = {{ min_out_percent = {value} }}\n")
    with pytest.raises(RulesFileError, match="Must be an integer"):
        load_rules([write(tmp_path, text)])


def test_min_categories_zero_ok(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, "min_categories = 0\n")])
    assert rules.min_categories == 0


def test_rule_min_categories_zero_ok(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.x]\ntime = ">5:00"\nmin_categories = 0\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_situations[0].min_categories == 0


# ── every shipped league's rules load ─────────────────────────────────────────


@pytest.mark.parametrize("path", shipped_files("*/profile.toml"), ids=shipped_id)
def test_shipped_rules_load(path: Path) -> None:
    _load_rules([path], labels=league_labels(path))


@pytest.mark.parametrize("path", shipped_files("*/profile.toml"), ids=shipped_id)
def test_shipped_rules_ban_the_old_categories(path: Path) -> None:
    """With its league's labels, each file's allowed lists ban exactly what the
    old disallowed lists did."""
    rules = _load_rules([path], labels=league_labels(path))
    assert OFFENSE_LIST_SCOPE - rules.offense_allowed_categories == frozenset(
        {
            RAZZLE_DAZZLE_RUN,
            PASS_LONG_LEFT,
            PASS_LONG_MIDDLE,
            RUN_RANDOM,
            PASS_LONG_RANDOM,
            PASS_MEDIUM_RANDOM,
            PASS_SHORT_RANDOM,
        }
    )
    assert DEFENSE_LIST_SCOPE - rules.defense_allowed_categories == frozenset()
