# Worklog

History of what changed and why. Where things stand now: [STATUS.md](STATUS.md).

- 2026-09-21 — **gameplan**: attribute caps were one fixed form per attribute
  (a count for QB draws and rollouts, a fraction for timed and 2-DL), so a
  league could not say what its own rule said. Each attribute now takes one of
  `max_<attr>_count`, `max_<attr>_ratio` or `max_<attr>_percent`, and naming two
  forms for one attribute is a rules-file error. Ratio and percent compare the
  exact play ratio, so nothing rounds. The PNFL 2-DL caps moved to the new
  percent form at their current league values: 50% Pass Short and Medium, 75%
  Pass Long, 100% Pass Dazzle.
- 2026-09-21 — **profile**: the league rule that a gameplan's play categories
  must all appear in the profile was only an informational warning, so a profile
  breaking it still passed. It is a violation now, like every other rule, and
  `CompatWarning` is gone — both directions are `CompatIssue`. The two
  compatibility checks also moved out of the code and into the rules file, under
  `[gameplan_compatibility]`, so a league enables each one itself. Substitution
  rules gained the league's non-QB bounds: every group but QB and K is capped at
  95 out and 96-100 in.
- 2026-09-21 — **docs**: `RULES_PNFL.md` was deleted for both gameplan and
  profile. Each restated every league value in prose tables, so it went stale
  the moment a number changed; the rules TOML and its comments are the reference
  now. Both rules files lost their `schema_version` and their explanatory
  preamble. Exit codes and the error-vs-finding distinction moved from
  ARCHITECTURE into each tool's README, where a coach will actually look.
- 2026-09-18 — the shipped `release/athc.ini` is checked by one test per
  section loader in `test_config.py`, with `ATHC_CONFIG_DIR` pointed at
  `release/` so the bundled rule files must exist. The old autocontinue-only
  check is gone; it proved only that its own section parsed.
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
