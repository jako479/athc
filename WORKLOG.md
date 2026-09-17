# Worklog

History of what changed and why. Where things stand now: [STATUS.md](STATUS.md).

- 2026-09-17 — project tooling reworked to match how a modern Python project is
  normally set up. No tool behaves differently; 1153 tests pass at 93.5%
  coverage, ruff and pyright are clean.
  - **Setup is `uv sync`, commands run through `uv run`.** Dev tools moved out
    of `[project.optional-dependencies]` into a `dev` dependency group, which
    is the current standard — extras ship to anyone who installs athc, groups
    stay local. `uv.lock` is committed now, so every machine installs the exact
    same versions.
  - **Coverage runs with every test run and fails below 92%.** It was measured
    nowhere before. The floor sits two points under the real number so a genuine
    drop fails and normal churn does not. There is no CI, so the check has to
    live in the test command.
  - **Ruff gained the pathlib, simplify, comprehension and pycodestyle-warning
    rule groups.** It flagged eight things. Two were real and fixed — a file
    opened without pathlib in `pdbtoexcel` and in a test helper. Three were a
    false "Yoda condition" reading of `assert CONSTANT == frozenset(...)`, now
    ignored in tests. Two are the glob calls behind `--glob` arguments, kept
    with a comment: the user types a whole pattern like `plays\**\*.ply`, and
    only `glob.glob` accepts one — `Path.glob` matches within a folder you
    already have.
  - **Pytest turns warnings into errors**, so a deprecation notice cannot sit
    in the output unread.
  - **Agent instructions live in [AGENTS.md](AGENTS.md)** at the repo root, the
    format ~60k projects use, with `.claude/CLAUDE.md` reduced to a pointer at
    it. The old file named a skill that does not exist and carried another
    project's test commands.
  - **`.vscode/` is no longer tracked.** Of 15 major Python projects checked,
    14 ignore it outright: the project pins the tool in pyproject.toml, and
    each developer wires up their own editor.
  - **Binary game files are marked binary in `.gitattributes`.** `.ply`, `.pln`,
    `.prf`, `.pdb` and `.bin` were left to git's guesswork, which risks line-ending
    damage to a file it misreads as text.
  - **The `.pdb` test data is in the repo.** The stock Python `.gitignore` line
    for MSVC debug symbols was silently excluding both convert-pdb fixtures, so
    a fresh clone had no test data.
