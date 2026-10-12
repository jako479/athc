# replace-play backup replacements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `replace-play play replacement... [path]` uses, in each game plan, the first replacement that is not already in it and breaks no new league rule.

**Architecture:** Three pure helpers in `src/athc/cli/gameplan/replace_play.py` (`split_args`, `added_violations`, `pick_replacement`) carry the logic; the Click command loads the league's rules and its full play pool the way `check` does and prints through the shared console. `check`'s violation formatter moves to `_common.py` so both commands print a violation the same way.

**Tech Stack:** Python 3.13, Click, pytest, the athc console (`athc.console`).

**Spec:** `docs/superpowers/specs/2026-10-09-replace-play-backups-design.md`

## Global Constraints

- Every existing message stays word for word; new lines: `SKIP <file>: 'NEW' already in the gameplan`, `SKIP <file>: 'NEW' adds a violation: [cat] message`, `<file>: 'OLD' not replaced, no valid replacement`.
- Tally: `'OLD' -> 'NEW1', 'NEW2': replaced <n> instance(s) in <m> gameplan(s), <f> failed, <k> not replaced`.
- Exit: `2 if failed else 1 if nothing replaced or any not replaced else 0`.
- Text files UTF-8, CRLF, final newline. Commits one line, prefix `gameplan:`, no tool names.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` green at the end.

## Review Focus

- The last argument is a folder that shares a play's name: it is the folder (`test_split_folder_named_like_play_is_the_folder`).
- Only the play and a folder given: usage error, not a replacement called like the folder (`test_split_play_and_folder_only_is_usage_error`).
- A plan that already breaks a rule: a replacement adding nothing new still fits (`test_added_violations_same_rule_and_category_is_not_new`, `test_pick_rule_already_broken_does_not_block`).
- The play replaced by itself: not "already in the gameplan" (`test_pick_play_replaced_by_itself`).
- Rule caps on attributes need the play pool's `playpool.toml` (`test_cli_rollout_cap_uses_playpool_rules`).

---

### Task 1: Split the arguments

**Files:**
- Modify: `src/athc/cli/gameplan/replace_play.py`
- Test: `tests/integration/test_gameplan_replace_play.py`

**Interfaces:**
- Produces: `split_args(args: Sequence[str]) -> tuple[str, list[str], str | None]` (play, replacements, path or None); raises `click.UsageError` when no replacement is left.

- [ ] **Step 1: Write the failing tests**

```python
def test_split_one_name_is_usage_error() -> None:
    with pytest.raises(click.UsageError):
        split_args(("OLD",))


def test_split_play_and_replacement(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert split_args(("OLD", "NEW")) == ("OLD", ["NEW"], None)


def test_split_play_and_folder_only_is_usage_error(tmp_path: Path) -> None:
    with pytest.raises(click.UsageError):
        split_args(("OLD", str(tmp_path)))


def test_split_last_existing_folder_is_path(tmp_path: Path) -> None:
    assert split_args(("OLD", "NEW", str(tmp_path))) == ("OLD", ["NEW"], str(tmp_path))


def test_split_last_existing_file_is_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "plans").write_text("", encoding="utf-8")
    assert split_args(("OLD", "NEW", "plans")) == ("OLD", ["NEW"], "plans")


@pytest.mark.parametrize("last", ["plans\\", "plans/", "x.pln", "X.PLN", "plans*"])
def test_split_path_looking_name_is_path(tmp_path: Path, monkeypatch, last: str) -> None:
    monkeypatch.chdir(tmp_path)
    assert split_args(("OLD", "NEW", last)) == ("OLD", ["NEW"], last)


def test_split_plain_names_are_replacements(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert split_args(("OLD", "NEW1", "NEW2")) == ("OLD", ["NEW1", "NEW2"], None)


def test_split_folder_named_like_play_is_the_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "NEW2").mkdir()
    assert split_args(("OLD", "NEW1", "NEW2")) == ("OLD", ["NEW1"], "NEW2")
```

- [ ] **Step 2: Run them; they fail** (`uv run pytest tests/integration/test_gameplan_replace_play.py -k split`): `split_args` is not defined.

- [ ] **Step 3: Implement**

```python
def _is_path(arg: str) -> bool:
    """Whether the last argument names the files, not a play: an existing file
    or folder (first, so a folder named like a play is the folder), a name
    with a folder separator, a `.pln` name, or a wildcard. Play names are
    plain file stems with none of these."""
    return (
        Path(arg).exists()
        or "/" in arg
        or "\\" in arg
        or arg.casefold().endswith(".pln")
        or is_glob(arg)
    )


def split_args(args: Sequence[str]) -> tuple[str, list[str], str | None]:
    """`play replacement... [path]` -> `(play, replacements, path)`, path None
    when the last argument is a play. UsageError without a replacement."""
    if not args:
        raise click.UsageError("Missing argument 'play'.")
    play, *rest = args
    path = rest.pop() if rest and _is_path(rest[-1]) else None
    if not rest:
        raise click.UsageError("Missing argument 'replacement'.")
    return play, rest, path
```

- [ ] **Step 4: Run them; they pass.**

- [ ] **Step 5: Commit** `gameplan: replace-play splits play, replacements and an optional path`

### Task 2: Pick the first replacement that fits

**Files:**
- Modify: `src/athc/cli/gameplan/_common.py` (add `format_violation`), `src/athc/cli/gameplan/check.py` (use it), `src/athc/cli/gameplan/replace_play.py`
- Test: `tests/integration/test_gameplan_replace_play.py`

**Interfaces:**
- Consumes: `replace_in_gameplan`, `find_in_gameplan`, `validate_gameplan(gp, rules, pool)`.
- Produces: `format_violation(v: Violation) -> str` (`[cat] message`); `added_violations(before, after) -> list[Violation]`; `Skipped(name: str, reasons: tuple[str, ...])`; `Picked(updated: GamePlan | None, entry: CustomPlayRef | None, normal_hits: Hits, special_hits: Hits, skipped: tuple[Skipped, ...])`; `pick_replacement(gp, target, entries, rules, pool, path=None) -> Picked`.

- [ ] **Step 1: Write the failing tests** (pool: `read_play_pool(PLAYS, labels=PNFL_LABELS)` in a module fixture; entries from `build_custom_play(pool.find_by_name(name), pool.root_dir)`; rules `Rules(offense_categories={"Run Middle": OffenseCategoryRule(max_count=0)})`):

```python
def test_added_violations_new_rule_is_new() -> None:
    v = Violation(RuleName.CATEGORY_MAX_COUNT, "m", "Run Middle")
    assert added_violations((), (v,)) == [v]


def test_added_violations_same_rule_and_category_is_not_new() -> None:
    before = Violation(RuleName.CATEGORY_MAX_COUNT, "has 2 plays", "Run Middle")
    after = Violation(RuleName.CATEGORY_MAX_COUNT, "has 3 plays", "Run Middle")
    assert added_violations((before,), (after,)) == []


def test_pick_skips_play_already_in_gameplan(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)})
    picked = pick_replacement(gp, "OLDRUN", _entries(pool, NORMAL_REPL, NORMAL_TARGET), Rules(), pool)
    assert picked.skipped == (Skipped(NORMAL_REPL, ("already in the gameplan",)),)
    assert picked.entry is not None and picked.entry.name == NORMAL_TARGET


def test_pick_skips_play_breaking_a_rule(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    picked = pick_replacement(gp, "OLDRUN", _entries(pool, NORMAL_REPL, NORMAL_TARGET), RM_MAX_0, pool)
    assert picked.skipped == (Skipped(NORMAL_REPL, ("adds a violation: [Run Middle] Offensive category 'Run Middle' has 1 plays; allows at most 0.",)),)
    assert picked.entry is not None and picked.entry.name == NORMAL_TARGET


def test_pick_none_fits(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_TARGET)})
    picked = pick_replacement(gp, "OLDRUN", _entries(pool, NORMAL_REPL, NORMAL_TARGET), RM_MAX_0, pool)
    assert picked.updated is None and picked.entry is None
    assert [i for i, _ in picked.normal_hits] == [0] and len(picked.skipped) == 2


def test_pick_no_hits(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    picked = pick_replacement(gp, MISSING, _entries(pool, NORMAL_REPL), Rules(), pool)
    assert picked == Picked(None, None, [], [], ())


def test_pick_rule_already_broken_does_not_block(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN"), 1: offense_normal(NORMAL_REPL, 0x09)})
    picked = pick_replacement(gp, "OLDRUN", _entries(pool, "DN28RMX3"), RM_MAX_0, pool)
    assert picked.entry is not None and picked.skipped == ()


def test_pick_play_replaced_by_itself(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal(NORMAL_TARGET)})
    picked = pick_replacement(gp, NORMAL_TARGET, _entries(pool, NORMAL_TARGET), Rules(), pool)
    assert picked.entry is not None and picked.skipped == ()


def test_pick_model_refusal_raises(pool) -> None:
    gp = _offense_gameplan(normals={0: offense_normal("OLDRUN")})
    with pytest.raises(AthcError):
        pick_replacement(gp, "OLDRUN", _entries(pool, SPECIAL_REPL), Rules(), pool)
```

- [ ] **Step 2: Run them; they fail** (names not defined).

- [ ] **Step 3: Implement** — move `check._format_violation` to `_common.format_violation` and import it in `check.py`; then in `replace_play.py`:

```python
@dataclass(frozen=True, slots=True)
class Skipped:
    """A replacement passed over in one game plan, with each reason as the rest
    of its `SKIP` line: `already in the gameplan`, or `adds a violation: ...`
    once per violation it would add."""

    name: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Picked:
    """What `pick_replacement` chose for one game plan. `updated` and `entry`
    are None when the play is not in it (no hits) or no replacement fits."""

    updated: GamePlan | None
    entry: CustomPlayRef | None
    normal_hits: Hits
    special_hits: Hits
    skipped: tuple[Skipped, ...]


def _rule_key(v: Violation) -> tuple[RuleName, str | None]:
    return v.rule_name, v.category


def added_violations(
    before: Sequence[Violation], after: Sequence[Violation]
) -> list[Violation]:
    """The violations in `after` beyond `before`, counted per rule and
    category: a rule already broken in a category does not count again, so a
    plan that already fails `check` can still be edited."""
    surplus = Counter(map(_rule_key, after)) - Counter(map(_rule_key, before))
    known = {v.message for v in before}
    return [v for v in after if surplus[_rule_key(v)] and v.message not in known]


def _already_in(gp: GamePlan, name: str, target: str) -> bool:
    """Whether `name` fills a slot of `gp` other than the play being replaced."""
    if name.casefold() == target.casefold():
        return False
    normal, special = find_in_gameplan(gp, name)
    return bool(normal or special)


def pick_replacement(
    gp: GamePlan,
    target: str,
    entries: Sequence[CustomPlayRef],
    rules: Rules,
    pool: PlayPool,
    path: Path | None = None,
) -> Picked:
    """Swap `target` for the first of `entries` that fits `gp`: not already in
    it and adding no rule violation (see `added_violations`). AthcError, as in
    `replace_in_gameplan`, when the model refuses an entry for a slot."""
    normal_hits, special_hits = find_in_gameplan(gp, target)
    if not normal_hits and not special_hits:
        return Picked(None, None, normal_hits, special_hits, ())
    before = validate_gameplan(gp, rules, pool)
    skipped: list[Skipped] = []
    for entry in entries:
        if _already_in(gp, entry.name, target):
            skipped.append(Skipped(entry.name, ("already in the gameplan",)))
            continue
        updated, normal_hits, special_hits = replace_in_gameplan(
            gp, target, entry, path
        )
        added = added_violations(before, validate_gameplan(updated, rules, pool))
        if added:
            reasons = tuple(f"adds a violation: {format_violation(v)}" for v in added)
            skipped.append(Skipped(entry.name, reasons))
            continue
        return Picked(updated, entry, normal_hits, special_hits, tuple(skipped))
    return Picked(None, None, normal_hits, special_hits, tuple(skipped))
```

- [ ] **Step 4: Run them; they pass.** Run the `check` tests too (`uv run pytest tests/integration/test_gameplan_check.py`).

- [ ] **Step 5: Commit** `gameplan: replace-play picks the first replacement that fits`

### Task 3: The command

**Files:**
- Modify: `src/athc/cli/gameplan/replace_play.py`
- Test: `tests/integration/test_gameplan_replace_play.py`, `tests/integration/test_cli_root.py:144-147`

**Interfaces:**
- Consumes: `split_args`, `pick_replacement`, `Picked`, `Skipped`.

- [ ] **Step 1: Write the failing tests**
  - `test_cli_path_left_out_uses_current_folder` (replaces `test_cli_requires_path`): chdir into a tmp folder holding `offense.pln`; `[NORMAL_TARGET, NORMAL_REPL]` → exit 0, tally `replaced 1 instance(s) in 1 gameplan(s), 0 failed, 0 not replaced`.
  - `test_cli_one_name_is_usage_error`: `[NORMAL_TARGET]` → exit 2.
  - `test_cli_every_replacement_must_be_in_pool` (replaces `test_cli_rejects_multiple_plays`): `[NORMAL_TARGET, NORMAL_REPL, MISSING, path]` → exit 2, `FAIL replacement play 'NOSUCHPLAYXX' not found in the play pool`.
  - `test_cli_backup_used_when_first_already_in_plan`: stdout exactly the `SKIP ... already in the gameplan` line then the `OK` line; exit 0.
  - `test_cli_backup_used_when_first_breaks_rule`: league `gameplan.toml` `[offense.RM]` `max_count = 0`; stdout the `SKIP ... adds a violation: ...` line then `OK`; exit 0.
  - `test_cli_rollout_cap_uses_playpool_rules`: league `playpool.toml` (the test rules) and `[offense.PSL]` `max_rollouts_count = 0`; replacements `AF1AwagR` (a rollout) then `JJ1AarrX`; the first is skipped, the second used.
  - `test_cli_no_valid_replacement_single_file`: exit 1; stdout the `SKIP` lines then `<file>: 'OLDRUN' not replaced, no valid replacement`; file unchanged.
  - `test_cli_directory_counts_not_replaced`: one plan fits, one does not; exit 1; tally `..., 0 failed, 1 not replaced`; header `'OLDRUN' -> 'DN28RM01', 'OR45RL01'`.
  - `test_cli_root.py`: replace-play usage shows `play replacement... [path]`.

- [ ] **Step 2: Run them; they fail.**

- [ ] **Step 3: Implement** — `args` (`nargs=-1, required=True, metavar="play replacement... [path]"`) through `split_args`; `load_config(league)`; rules from `load_rules(config.rule_files, labels=config.categories)` when any are configured, else `Rules()`; `build_pool(config.play_path, config.playpool_rules, config.categories)`; each replacement resolved through the pool (the existing `FAIL` text); per file `pick_replacement`, then `SKIP` lines, the not-found / not-replaced / `OK` lines; the tally and exit code from the Global Constraints. Docstring and the module comment about "no playpool rules" updated.

- [ ] **Step 4: Run the whole file and `test_cli_root.py`; they pass.**

- [ ] **Step 5: Commit** `gameplan: replace-play takes backup replacements and checks league rules`

### Task 4: Docs

**Files:**
- Modify: `docs/gameplan/README.md`, `docs/gameplan/ARCHITECTURE.md`, `docs/design/architecture.md` (exit-code line), `config/release/docs/COMMANDS.txt` (section 7), `tests/integration/README.md` (replace-play tables), `CHANGELOG.md`, `STATUS.md`.

- [ ] **Step 1:** Describe the new command line, the skip rule, the new lines, tally and exit codes; read each design doc end to end for anything else the change touches.
- [ ] **Step 2:** CRLF check on every changed text file.
- [ ] **Step 3:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright`.
- [ ] **Step 4: Commit** `gameplan: replace-play docs for backup replacements`
