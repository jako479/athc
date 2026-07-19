"""Unit tests for the profile rules loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_profile import Down, MinutesRemaining, SubstitutionPair, YardsToGo
from athc.profile import RulesFileError, SituationRule, load_rules
from athc.profile.rules import (
    PASS_LONG_RIGHT,
    RAZZLE_DAZZLE_PASS,
    RAZZLE_DAZZLE_RUN,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RANDOM,
)
from tests.unit.profile.conftest import DATA

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


# ── normal ────────────────────────────────────────────────────────────────────


def test_load_valid_full() -> None:
    rules = load_rules([DATA / "profile_rules.toml"])
    assert rules.audibles_allowed is False
    assert rules.min_categories == 2
    assert rules.substitutions["QB"] == SubstitutionPair(75, 80)
    assert rules.offense_situations and rules.defense_situations


def test_disallowed_expands_to_complement() -> None:
    rules = load_rules([DATA / "profile_rules.toml"])
    rule = find(rules.offense_situations, down=Down.THIRD, yards=YardsToGo.ZERO_TO_ONE)
    assert rule.allowed_categories is not None
    assert RAZZLE_DAZZLE_PASS not in rule.allowed_categories


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


def test_disallowed_categories_parse(tmp_path: Path) -> None:
    text = (
        MINIMAL
        + 'disallowed_offensive_categories = ["Razzle Dazzle Run", "Run Random"]\n'
        "disallowed_defensive_categories = []\n"
    )
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_disallowed_categories == frozenset(
        {RAZZLE_DAZZLE_RUN, RUN_RANDOM}
    )
    assert rules.defense_disallowed_categories == frozenset()


def test_audibles_allowed_defaults_when_omitted(tmp_path: Path) -> None:
    """Omitted `audibles_allowed` defaults to True (no audibles check)."""
    rules = load_rules([write(tmp_path, "min_categories = 2\n")])
    assert rules.audibles_allowed is True


def test_min_categories_defaults_when_omitted(tmp_path: Path) -> None:
    """Omitted `min_categories` defaults to 0 (no baseline minimum)."""
    rules = load_rules([write(tmp_path, "audibles_allowed = false\n")])
    assert rules.min_categories == 0


def test_layering_overrides_scalar(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text(MINIMAL, encoding="utf-8")
    b = tmp_path / "b.toml"
    b.write_text("min_categories = 9\n", encoding="utf-8")
    rules = load_rules([a, b])
    assert rules.min_categories == 9
    assert rules.audibles_allowed is False  # untouched by the overlay


def test_layering_overrides_audibles(tmp_path: Path) -> None:
    a = tmp_path / "a.toml"
    a.write_text("audibles_allowed = false\n", encoding="utf-8")
    b = tmp_path / "b.toml"
    b.write_text("audibles_allowed = true\n", encoding="utf-8")
    rules = load_rules([a, b])
    assert rules.audibles_allowed is True


def test_all_time_buckets_match_distinctly(tmp_path: Path) -> None:
    """Each of the five time buckets gets its own rule."""
    buckets = [">5:00", ">2:00-5:00", ">1:00-2:00", ">0:15-1:00", "0:00-0:15"]
    sections = "".join(
        f'\n[offense.bucket_{i}]\ntime = "{t}"\nmin_categories = 3\n'
        for i, t in enumerate(buckets)
    )
    rules = load_rules([write(tmp_path, MINIMAL + sections)])
    assert {r.time for r in rules.offense_situations} == set(MinutesRemaining)


# ── errors ────────────────────────────────────────────────────────────────────


def test_empty_paths() -> None:
    with pytest.raises(RulesFileError, match="at least one"):
        load_rules([])


def test_toml_parse_error(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="TOML parse error"):
        load_rules([write(tmp_path, "not = valid = toml")])


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
        ">= 0" in joined and "unknown category" in joined and "unknown value" in joined
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
    with pytest.raises(RulesFileError, match="unknown key"):
        load_rules([write(tmp_path, MINIMAL + "bogus = 1\n")])


def test_unknown_situation_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="unknown key"):
        load_rules([write(tmp_path, MINIMAL + SECTION + "bogus = 1\n")])


def test_situation_needs_constraint(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.empty]\ntime = ">5:00"\ndown = "first"\n'
    with pytest.raises(RulesFileError, match="needs one of"):
        load_rules([write(tmp_path, text)])


def test_bad_time(tmp_path: Path) -> None:
    text = MINIMAL + SECTION.replace('">5:00"', '"halftime"')
    with pytest.raises(RulesFileError, match="unknown value"):
        load_rules([write(tmp_path, text)])


def test_allowed_and_disallowed_exclusive(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'allowed = ["RL"]\ndisallowed = ["RM"]\n'
    with pytest.raises(RulesFileError, match="mutually exclusive"):
        load_rules([write(tmp_path, text)])


def test_unknown_category(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'allowed = ["NOPE"]\n'
    with pytest.raises(RulesFileError, match="unknown category"):
        load_rules([write(tmp_path, text)])


def test_mandatory_must_be_list(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'mandatory = "RL"\n'
    with pytest.raises(RulesFileError, match="must be a list"):
        load_rules([write(tmp_path, text)])


def test_mandatory_unknown_category(tmp_path: Path) -> None:
    text = MINIMAL + SECTION + 'mandatory = ["NOPE"]\n'
    with pytest.raises(RulesFileError, match="unknown category"):
        load_rules([write(tmp_path, text)])


def test_disallowed_categories_unknown_name(tmp_path: Path) -> None:
    text = MINIMAL + 'disallowed_offensive_categories = ["bogus"]\n'
    with pytest.raises(RulesFileError, match="unknown name"):
        load_rules([write(tmp_path, text)])


def test_unknown_field_name(tmp_path: Path) -> None:
    text = MINIMAL + SECTION.replace('"inside_def_5"', '"midfield"')
    with pytest.raises(RulesFileError, match="unknown value"):
        load_rules([write(tmp_path, text)])


# ── substitutions ───────────────────────────────────────────────────────────────

ALL_POSITIONS = ["OL", "QB", "RB", "WR", "K", "DL", "LB", "DB"]


def _subs(body: str) -> str:
    return MINIMAL + "[substitutions]\n" + body


def test_substitutions_single_group(tmp_path: Path) -> None:
    text = _subs("QB = { out_percent = 75, in_percent = 80 }\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions == {"QB": SubstitutionPair(75, 80)}


def test_substitutions_all_groups(tmp_path: Path) -> None:
    body = "".join(
        f"{p} = {{ out_percent = 70, in_percent = 80 }}\n" for p in ALL_POSITIONS
    )
    rules = load_rules([write(tmp_path, _subs(body))])
    assert set(rules.substitutions) == set(ALL_POSITIONS)
    assert all(s == SubstitutionPair(70, 80) for s in rules.substitutions.values())


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
        "[substitutions]\nQB = { out_percent = 70, in_percent = 90 }\n"
        "DL = { out_percent = 60, in_percent = 70 }\n",
        encoding="utf-8",
    )
    rules = load_rules([a, b])
    assert rules.substitutions["QB"] == SubstitutionPair(70, 90)  # later file wins
    assert rules.substitutions["DL"] == SubstitutionPair(60, 70)  # accumulated


# Percent limits (min 0, max 100, out == in) accepted for every group.
@pytest.mark.parametrize("position", ALL_POSITIONS)
@pytest.mark.parametrize("out,in_", [(0, 0), (0, 100), (100, 100)])
def test_substitutions_percent_limits_ok(
    tmp_path: Path, position: str, out: int, in_: int
) -> None:
    text = _subs(f"{position} = {{ out_percent = {out}, in_percent = {in_} }}\n")
    rules = load_rules([write(tmp_path, text)])
    assert rules.substitutions[position] == SubstitutionPair(out, in_)


# One below min / one above max / out > in rejected for every group.
@pytest.mark.parametrize("position", ALL_POSITIONS)
@pytest.mark.parametrize(
    "out,in_,msg",
    [
        (-1, 50, r"\[0, 100\]"),  # one below 0
        (50, 101, r"\[0, 100\]"),  # one above 100
        (90, 80, "must be <="),  # out > in
    ],
)
def test_substitutions_percent_invalid(
    tmp_path: Path, position: str, out: int, in_: int, msg: str
) -> None:
    text = _subs(f"{position} = {{ out_percent = {out}, in_percent = {in_} }}\n")
    with pytest.raises(RulesFileError, match=msg):
        load_rules([write(tmp_path, text)])


def test_substitutions_missing_key(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="requires"):
        load_rules([write(tmp_path, _subs("QB = { out_percent = 75 }\n"))])


def test_substitutions_unknown_position(tmp_path: Path) -> None:
    text = _subs("zz = { out_percent = 75, in_percent = 80 }\n")
    with pytest.raises(RulesFileError, match="unknown key"):
        load_rules([write(tmp_path, text)])


def test_substitutions_unknown_pair_key(tmp_path: Path) -> None:
    text = _subs("QB = { out_percent = 75, in_percent = 80, foo = 1 }\n")
    with pytest.raises(RulesFileError, match="unknown key"):
        load_rules([write(tmp_path, text)])


def test_substitutions_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="must be a table"):
        load_rules([write(tmp_path, MINIMAL + "substitutions = 5\n")])


def test_substitutions_position_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(RulesFileError, match="must be a table"):
        load_rules([write(tmp_path, _subs("QB = 5\n"))])


def test_substitutions_non_integer(tmp_path: Path) -> None:
    text = _subs('QB = { out_percent = "x", in_percent = 80 }\n')
    with pytest.raises(RulesFileError, match="must be an integer"):
        load_rules([write(tmp_path, text)])


def test_min_categories_zero_ok(tmp_path: Path) -> None:
    rules = load_rules([write(tmp_path, "min_categories = 0\n")])
    assert rules.min_categories == 0


def test_rule_min_categories_zero_ok(tmp_path: Path) -> None:
    text = MINIMAL + '[offense.x]\ntime = ">5:00"\nmin_categories = 0\n'
    rules = load_rules([write(tmp_path, text)])
    assert rules.offense_situations[0].min_categories == 0


# ── shipped rules ─────────────────────────────────────────────────────────────


def test_pnfl_rules_load() -> None:
    root = Path(__file__).resolve().parents[3]
    rules = load_rules([str(root / "release" / "rules" / "PNFL.profile.toml")])
    assert rules.min_categories == 2
    assert RUN_RANDOM in rules.offense_disallowed_categories
    assert rules.defense_disallowed_categories == frozenset()
    assert rules.offense_situations and rules.defense_situations
