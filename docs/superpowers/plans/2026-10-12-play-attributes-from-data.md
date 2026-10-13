# Play Attributes From Play Data — Implementation Plan

Status: built 2026-10-13 on `worktree-play-attributes`. Superseded on two points: the rules live in the playpool README ("How athc reads a play"), not ply.md section 5, and `qb_draw` became `qb_run`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `fbpro98_play` tells from a play's own bytes whether an offensive play is a QB run, rollout pass and/or timed pass, and a defensive play's front (3-4, 4-3, 2-DL); `playpool` uses that instead of file names and folders, and `playpool.toml` goes away.

**Architecture:** The reader decodes every player's two logic-box lists (`ply.md` section 2); `PlayFile` derives the attributes per `ply.md` section 5. `playpool` reads them from the `PlayFile` (folders only add `screen`). Every consumer drops the playpool rules file.

**Tech Stack:** Python 3.13, `struct`, dataclasses, Click, pytest, ruff, pyright.

**Spec:** the user's request (2026-10-12) and `docs/fbpro98_play/specs/ply.md` sections 2 and 5.

## Global Constraints

- Messages and behavior stay the same except where the swap forces a change; each changed test states why.
- Same architecture, naming, styling and error handling as the sibling libraries: on-disk codes in `schema.py`, frozen slots dataclasses, and a record too short for its logic raises `InvalidPlayFileError` ("Truncated player record at 0x…."), like the gameplan reader's truncated records.
- Rollout margin is the caller's choice (`ply.md` 5); `playpool` uses 100 units (90 units = 1 yard).
- Offense attributes keep their category gates in `playpool`: `qb_draw` only on run plays, `rollout` / `pass_logic` only on pass plays.
- Special-teams plays carry none of the attributes.
- Text files: UTF-8, CRLF, final newline. Commits: one line, `<tool>:` prefix, no AI mention.

## Review Focus

- A record too short for its box lists (header only, a list cut short, a count too high) is rejected with the record's offset; bytes after the lists are ignored.
- Two tackles on one side, or no tackle: no rollout from a bogus edge; no tackle means no rollout.
- A play with no QB, or a QB that never passes: not timed, not a rollout.
- Margin boundary: exactly `margin` outside counts, one unit less does not, on both sides.
- DL counts 1 and 5 have no front; 2, 3, 4 map to 2-DL, 3-4, 4-3.

---

### Task 1: fbpro98_play decodes player logic

**Files:**
- Modify: `src/athc/fbpro98_play/schema.py`, `src/athc/fbpro98_play/model.py`, `src/athc/fbpro98_play/reader.py`, `src/athc/fbpro98_play/__init__.py`
- Test: `tests/unit/fbpro98_play/test_reader.py`, `tests/unit/fbpro98_play/test_schema.py`, `tests/unit/fbpro98_play/README.md`

**Interfaces:**
- Produces: `Command(code: int, arguments: tuple[int, ...])`, `LogicBox(x: int, y: int, commands: tuple[Command, ...])`, `PlayerLogic(pre_snap: tuple[LogicBox, ...] = (), after_snap: tuple[LogicBox, ...] = ())`; `PlayFile.player_logic: tuple[PlayerLogic, ...] = ()` (last field, one per slot); schema `PLY_BOX_COUNT`, `PLY_BOX`, `PLY_COMMAND`, `PLY_ARGUMENT`, `COMMAND_*` and `POSITION_*` codes.

- [ ] **Step 1: Failing tests** — `test_reader.py`: `test_decodes_player_logic` (`SF1YemTy` QB, hex-checked by hand), `test_every_fixture_player_has_logic` `[P]`, `test_decodes_built_logic`, `test_bytes_after_the_logic_are_ignored`, `test_rejects_truncated_player_record` `[P]` (one byte short / no after-snap list / header only), `test_rejects_box_count_past_the_record`; `test_parses_minimal_valid_buffer` grows to 8-byte records (a header plus two empty lists is now the smallest valid record); `test_zero_offset_parses` becomes `test_zero_offset_is_rejected` (the record overlaps the offsets table, so its logic cannot be read); `test_schema.py` sizes and codes. `build_ply` emits valid 8-byte records; `build_record` encodes logic.
- [ ] **Step 2:** `uv run pytest tests/unit/fbpro98_play -q` — fails (`ImportError`).
- [ ] **Step 3: Implement** — `_parse_player_logic(buffer, start, end, path)` reads both box lists from `buffer[start + 4 : end]` (record end = next record's start, the last ends at the end of the file) and turns `struct.error` into `InvalidPlayFileError(f"Truncated player record at 0x{start:02X}.", path)`; headers are all read first so their errors keep priority.
- [ ] **Step 4:** `uv run pytest tests/unit/fbpro98_play -q` — all pass.
- [ ] **Step 5: Commit** — `fbpro98_play: decode each player's logic boxes`

### Task 2: fbpro98_play play attributes

**Files:**
- Modify: `src/athc/fbpro98_play/model.py`, `src/athc/fbpro98_play/__init__.py`, `docs/fbpro98_play/README.md`, `docs/fbpro98_play/ARCHITECTURE.md`
- Test: `tests/unit/fbpro98_play/test_attributes.py` (new), `tests/unit/fbpro98_play/README.md`

**Interfaces:**
- Produces: `DefensiveFront` enum (`THREE_FOUR = "3-4"`, `FOUR_THREE = "4-3"`, `TWO_DL = "2-DL"`) moved here from `playpool`; `PlayFile.is_timed_pass: bool`, `PlayFile.is_qb_run: bool`, `PlayFile.is_rollout(margin: int) -> bool`, `PlayFile.defensive_front: DefensiveFront | None`.

- [ ] **Step 1: Failing tests** (`test_attributes.py`, `PlayFile`s built from headers + logic, plus real fixtures):
  - timed: QB with `0x06` → True; QB with `0x08` only → False; no QB → False; defensive play → False; special-teams play → False.
  - QB run: QB with `0x0C` → True; another player's `0x0C` → False.
  - rollout: QB reaching exactly `margin` right of the rightmost tackle → True, `margin - 1` → False; same on the left; spot reached by a Move to counts; spot after the pass does not; QB that never passes → False; no tackles → False.
  - front: DL count 1 → None, 2 → `TWO_DL`, 3 → `THREE_FOUR`, 4 → `FOUR_THREE`, 5 → None; offensive play → None; special-teams defense → None.
  - real fixtures: `SF1YemTy` timed, not rollout; `JJ7XWagR` rollout at 100; `JJ10drw3` QB run; `JJ43rlZB` 4-3; `KCC33rmA` 3-4; `MN22PLz` 2-DL.
- [ ] **Step 2:** run — fail.
- [ ] **Step 3: Implement** in `model.py`:

```python
_MOVE_TO, _TIMED_PASS, _CHECK_RECEIVERS, _RUN = 0x02, 0x06, 0x08, 0x0C
_QB, _TACKLE = 0x0020, 0x0011
_DOWN_LINEMEN = frozenset({0x0101, 0x0102})  # DT, DE
_FRONTS = {2: DefensiveFront.TWO_DL, 3: DefensiveFront.THREE_FOUR,
           4: DefensiveFront.FOUR_THREE}

    def is_rollout(self, margin: int) -> bool:
        tackles = [l.after_snap[0].x for l in self._logic_of(_TACKLE) if l.after_snap]
        if not self._is_normal_offense or not tackles:
            return False
        left, right = min(tackles), max(tackles)
        for qb in self._logic_of(_QB):
            spots = _spots_before_pass(qb)
            if spots and (min(spots) <= left - margin or max(spots) >= right + margin):
                return True
        return False
```

  `_spots_before_pass(logic)` walks pre-snap then after-snap boxes: each box's x, then each Move to's x, stopping at the first Timed pass / Check receivers; `None` when the QB never passes.
- [ ] **Step 4:** run — pass; docs updated (README API list, ARCHITECTURE "what this package does").
- [ ] **Step 5: Commit** — `fbpro98_play: QB run, timed pass, rollout and defensive front from play data`

### Task 3: playpool takes the attributes from the play file

**Files:**
- Modify: `src/athc/playpool/model.py`, `src/athc/playpool/reader.py`, `src/athc/playpool/__init__.py`
- Delete: `src/athc/playpool/rules.py`, `tests/unit/playpool/test_rules.py`, `tests/unit/playpool/test_rule_warnings.py`, `tests/unit/playpool/data/rules.toml`
- Test: `tests/unit/playpool/conftest.py`, `tests/unit/playpool/test_reader.py`, `tests/unit/playpool/test_model.py`, `tests/unit/playpool/README.md`
- Docs: `docs/playpool/README.md`, `docs/playpool/ARCHITECTURE.md`

**Interfaces:**
- Consumes: Task 2's `PlayFile` attributes and `DefensiveFront`.
- Produces: `read_play_pool(root_dir, *, labels=None)` (no `rules`); `ROLLOUT_MARGIN = 100` in `playpool.reader`; `athc.playpool` no longer exports `DefensiveFront`, `FilenameFilter`, `PlaypoolRules`, `RulesFileError`, `build_rules`, `load_rules`, `rule_warnings`.

- [ ] **Step 1: Tests first** — `test_reader.py`: OFFENSE table from the play data (`GBglpH1R` and `JJ9ZXOTR` not rollouts: their QBs stay inside the tackles, -131 and -60 units; the old `R` suffix was the only reason), DEFENSE fronts in every layout (`AF32gp02` gains `THREE_FOUR`: 3 DL), new `test_rollout_margin_is_100_units` (100 → rollout, 99 → not, through `read_play_pool` on a constructed play is not possible, so through `_offensive` with a constructed `PlayFile`), `test_category_gates_stay` (a run play's QB pass logic gives no `pass_logic`; a pass play's QB run gives no `qb_draw`).
- [ ] **Step 2:** run — fail.
- [ ] **Step 3: Implement** — `_offensive(name, play_file, *, screen)` reads `is_qb_run` / `is_rollout(ROLLOUT_MARGIN)` / `is_timed_pass`; `DefensivePlay(defensive_front=play_file.defensive_front)`; `_FolderInfo` loses `front` (`R&SDefs` and `34…`/`43…` still mark the defense tree and category for the mismatch warnings); `StrPath` moves to `model.py`.
- [ ] **Step 4:** `uv run pytest tests/unit/playpool -q` — pass; docs updated.
- [ ] **Step 5: Commit** — `playpool: play attributes from the play file; playpool.toml retired`

### Task 4: consumers drop the playpool rules file

**Files:**
- Modify: `src/athc/cli/gameplan/_common.py` (`build_pool(play_path, labels, league_file)`), `src/athc/cli/gameplan/check.py`, `replace_play.py`, `set_normals.py`, `set_specials.py`, `src/athc/cli/check_ppp.py`, `src/athc/gameplan/config.py` (no `playpool_rules`), `src/athc/gameplan/validators.py` (`DefensiveFront` from `fbpro98_play`), `src/athc/pdbtoexcel/config.py` (no `playpool_rules`), `src/athc/pdbtoexcel/workbook_creator.py`
- Delete: `config/dev/leagues/{PNFL,PCFL}/playpool.toml`, `config/release/leagues/{PNFL,PCFL}/playpool.toml`, `tests/integration/data/playpool_rules.toml`
- Modify: `packaging/sandbox-steps.ps1`, `config/*/athc.ini` and `league.toml` comments
- Test: integration tests that copy `POOL_RULES` or test a bad `playpool.toml`; `tests/unit/test_errors.py`; pdbtoexcel and gameplan unit tests importing `DefensiveFront` from `playpool`
- Docs: `docs/gameplan/*`, `docs/pdbtoexcel/*`, `docs/check_ppp/README.md`, `docs/design/architecture.md`, `config/release/docs/README.txt`, `COMMANDS.txt`, test READMEs

- [ ] **Step 1:** update tests: delete the bad-`playpool.toml` tests (the file no longer exists, so nothing reads it); `test_cli_rollout_cap_uses_playpool_rules` → the rollout comes from the play file (no rules copied); `test_cli_league_playpool_rules_apply` → attribute caps apply with no playpool file; `test_rules_file_error_is_shared` drops playpool; config tests stop asserting `playpool_rules`.
- [ ] **Step 2:** run — fail where the code still takes the rules.
- [ ] **Step 3:** implement the removals.
- [ ] **Step 4:** `uv run pytest` — investigate every golden diff: a change is accepted only when the play data explains it (e.g. `GP5Xtop1` is a timed pass, `AT8ZRolD` a rollout, pass defenses outside the front folders now show their front).
- [ ] **Step 5: Commit** — `athc: commands use play attributes from the play file`

### Task 5: project meta and verification

- [ ] CHANGELOG / STATUS / release README entries at the top of their sections.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` — all green.
- [ ] CRLF check on every touched text file.
- [ ] One whole-branch review; fix findings.
- [ ] Commit — `athc: play attributes docs and meta`
