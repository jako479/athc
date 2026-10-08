# Output folders

Status: TODO for 1.0.0. Done when every row below matches and the "Not yet as
designed" note under [Output files](../architecture.md#output-files) is gone;
then delete this file.

## The rule

A produced file's missing folders are created in full (pandoc, 7-Zip and yt-dlp
do the same; precedents in [reference-projects.md](../reference-projects.md#missing-output-folders-created-in-full)).
A command that edits a file in place never creates its target. Whatever writes
the file makes the call, CLI or library.

## Commands

Behavior when the folder of the path the command writes does not exist, as of
2026-10-08.

| Command | Does | Should |
|---|---|---|
| `convert-pdb pdb_file output_file` | Error "output folder not found", exit 1 (`pdbtoexcel/main.py`) | Create the whole folder chain |
| `gameplan list-normals gameplan [output_file]` | Error, exit 1 (`cli/gameplan/_common.py`, `emit_play_list`) | Create the whole folder chain |
| `gameplan list-specials gameplan [output_file]` | Error, exit 1 (same helper) | Create the whole folder chain |
| `profile diff -o file` | Error, exit 2 (`cli/profile/diff.py`) | Create the whole folder chain |
| `generate-schedule` | Writes to the current directory, which always exists | Same |
| `config edit` / `config set` / `config reveal` | Create the whole config-folder chain | Same |
| `gameplan set-normals` / `set-specials` / `replace-play`, `profile copy` | Edit an existing file; a missing path is an error | Same |

Read-only commands (`check-ppp`, the `check` commands, `find-play`,
`autocontinue`, `config path`) write nothing.

## Changes

- `convert-pdb`: drop the folder check in `pdbtoexcel/main.py`; create the
  output file's folders before the workbook opens.
- `list-normals` / `list-specials`: `emit_play_list` creates the folders before
  writing.
- `profile diff`: create the folders before writing `-o`.
- Tests, both sides for each writer: folder exists (unchanged), one level
  missing, several levels missing; an editor with a missing target still
  errors. `test_missing_output_folder_exit_1` and its row in
  `tests/integration/README.md` flip to the new behavior.
- CHANGELOG: the convert-pdb line "the output folder must exist; a missing one
  is a one-line error instead of being created" becomes the new behavior.
- Docs: remove the "Not yet as designed" note under Output files; the tool
  READMEs for `convert-pdb`, `gameplan` and `profile` say missing folders are
  created.
