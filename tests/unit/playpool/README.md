# playpool — Test Matrix

Cases covered for the play-pool library. Convention in [../../../docs/design/testing-unit.md](../../../docs/design/testing-unit.md).

One row per behavior. `[P]` = parametrized. Input: `make` = constructed `PlayFile`/record; `tree` = the curated plays in `data/plays/` in the league folder layout, plus the same files copied into a flat tree and a tree of arbitrary folder names (conftest fixtures `league_pool` / `flat_pool` / `arbitrary_pool`); `built` = a `.ply` built byte by byte (`build_ply` / `build_record` from the fbpro98_play tests); `rel` = a play's path relative to the pool root; `tmp` = constructed input. Status: ☐ planned · ☑ done. **Implemented** — `pytest tests/unit/playpool` passes.

## model.py — record classes and `PlayPool`

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `category` (enum member) from the file | make | `OffensiveCategory.RUN_MIDDLE` | `test_category` | ☑ |
| Offensive `to_dict` | make; pass play, run play | the whole dict; a run play's `pass_logic` is None | `test_offensive_to_dict` `[P]` | ☑ |
| Defensive `to_dict` | make; `2-DL`, no front | the whole dict; no front is None | `test_defensive_to_dict` `[P]` | ☑ |
| Special `to_dict` (no extra fields) | make | the whole dict, base keys only | `test_special_to_dict` | ☑ |
| `to_dict` `file_path`, `relative_to` | make; none, `Offense` | `Offense/p.ply`; `p.ply` | `test_to_dict_file_path` `[P]` | ☑ |
| `find_by_name` case-insensitive | make | hit; miss → None | `test_find_by_name` | ☑ |
| `add` files a play under its side | make | one list each | `test_add_files_by_side` | ☑ |
| `add` rejects a bare `Play` | make | `TypeError` | `test_add_rejects_a_bare_play` | ☑ |
| Duplicate name → last added wins | make | last record | `test_duplicate_name_last_wins` | ☑ |

## reader.py — file-driven classification (identical across league layout / arbitrary / flat)

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Offensive: category + rollout/qb_run/pass_logic from the file | tree | same in all 3 layouts | `test_offensive_file_driven` `[P]` | ☑ |
| `screen` only from a `Screens/` folder | tree | only `AF6Zscrn`, only in the league layout | `test_screen_only_from_screens_folder` `[P]` | ☑ |
| Defensive: category + `defensive_front` from the file | tree | same in all 3 layouts | `test_defensive_file_driven` `[P]` | ☑ |
| Rollout margin | built; QB 100 / 101 units outside the line | not / rollout | `test_rollout_is_beyond_100_units_outside_the_line` `[P]` | ☑ |
| Category gates the attributes | built; pass play whose QB runs, run play whose QB moves out and throws | no `qb_run`; no `rollout`, no `pass_logic` | `test_category_still_gates_the_attributes` | ☑ |
| Run play in a `Screens/` folder | tmp | no `screen` | `test_run_play_in_screens_folder_is_no_screen` | ☑ |
| Special play filed | tree | `SpecialPlay` | `test_special_file_driven` `[P]` | ☑ |
| Consistent trees → no issues | tree | `[]` | `test_no_issues_on_consistent_trees` `[P]` | ☑ |

## reader.py — `issues` (every warning kept on the pool, word for word)

`glob` = `Path.glob` patched to list in reverse path order, so only the reader's sort puts the plays in path order.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Duplicate name → last in sorted path order wins | tmp, glob | later folder's play; the warning text | `test_duplicate_winner_is_last_in_path_order` | ☑ |
| Unreadable file (a folder named `.ply`) | tmp | "<path>: Access is denied. Skipped."; rest loads | `test_unreadable_file_is_an_issue` | ☑ |
| Invalid file | tmp | "<path>: <reason> Skipped."; rest loads | `test_invalid_file_is_an_issue` | ☑ |
| Issues in path order | tmp, glob | duplicate (`a/`, `b/`) before the `Offense/PML` mismatch | `test_issues_keep_path_order` | ☑ |
| The reader never logs | tmp | no log records; both problems are issues | `test_reader_never_logs` | ☑ |

## reader.py — `folder_warnings` (recognized league folder vs the play file)

Warning = `<path-from-pool-root>: <reason>`. Wrong side reported alone; category checked only when the side matches; unrecognized folders never warn. Category folders are the league's labels (`CategoryLabels`); the play's own side is looked up first.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Wrong side, file wins (end-to-end) | tmp | defensive record + side warning | `test_wrong_side_folder_file_wins_and_warns` | ☑ |
| Wrong category, file wins (end-to-end) | tmp | file category + category warning | `test_wrong_category_folder_warns` | ☑ |
| No labels: side and `Screens` folders still count (end-to-end) | tmp | `screen`; side warning; `PMR` ignored | `test_side_and_screens_folders_apply_without_labels` | ☑ |
| `Screens` / `R&SDefs` alone name their side | rel | side warning | `test_screens_and_rns_folders_name_their_side` `[P]` | ☑ |
| Deeper category folder wins | rel; `PML/PSM`, `PSM/PML` | no warning; `PML` warning | `test_deeper_category_folder_wins` `[P]` | ☑ |
| Defensive play in offense tree | rel | side warning | `test_warn_defensive_play_in_offense_tree` | ☑ |
| Offensive play in defense (3-4) tree | rel | side warning | `test_warn_offensive_play_in_defense_tree` | ☑ |
| Special play in a side tree | rel | side warning | `test_warn_special_play_in_side_tree` | ☑ |
| Offense category mismatch (PSL in PML) | rel | category warning | `test_warn_offense_category_mismatch` | ☑ |
| Defense category mismatch | rel | category warning | `test_warn_defense_category_mismatch` | ☑ |
| `User Specific` in a category folder | rel | category warning | `test_warn_user_specific_in_category_folder` | ☑ |
| Wrong side suppresses category warning | rel | side warning only | `test_wrong_side_reported_alone` | ☑ |
| Consistent folder | rel | no warning | `test_no_warn_when_consistent` | ☑ |
| Loose / side-root / unrecognized (incl. User Specific) | rel | no warning | `test_no_warn_loose_or_unrecognized` `[P]` | ☑ |
| No league labels | `CategoryLabels()`, `Offense/PML` | no warning (folder unrecognized) | `test_no_labels_means_no_category_folders` | ☑ |
| Label shared by both sides | `RR` offense + defense | each side's Run Right quiet; other category warns | `test_shared_label_resolves_to_the_plays_side` | ☑ |
| Other side's label | defense play in `PML/` | side warning | `test_other_sides_label_still_warns_wrong_side` | ☑ |
| `34`/`43` prefix uses defense labels | defensive play in `34RunLeft` / `43RunLeft`, `34PML` / `43PML` | category warning; no warning | `test_front_prefix_uses_defense_labels` `[P]` | ☑ |
| `34`/`43` prefix without a defense label is unrecognized | offensive play in `34PML` / `43PML`, and in `34RunLeft` / `43RunLeft` with no labels | no warning | `test_front_prefix_needs_a_defense_label` `[P]` | ☑ |
