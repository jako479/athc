<!--
Source: https://docs.pytest.org/en/stable/explanation/goodpractices.html (retrieved 2026-06-10)
Why mimic: the canonical Python answer to "where do tests live and how are they
discovered" — src/ layout, tests/ outside the package, importlib import mode, tox.
Directly applicable to a Python CLI + libraries project. Faithful paraphrase with
headings preserved.
-->

# pytest — Good Integration Practices

## Install package with pip

For development, use a virtual environment (venv) and install your application, its
dependencies, and pytest with pip so "your code and dependencies are isolated from your
system Python installation." Put a `pyproject.toml` in the repo root with build-system
config and project metadata, then install editable with `pip install -e .` — this "lets
you change your source code (both tests and application) and rerun tests at will."

## Conventions for Python test discovery

- Collection starts from configured `testpaths` (or the current directory).
- Directories are recursed into unless they match `norecursedirs`.
- pytest searches for `test_*.py` or `*_test.py` files.
- Collected items: `test`-prefixed functions/methods outside classes, and `test`-prefixed
  functions/methods inside `Test`-prefixed classes (classes must have no `__init__`).
- `unittest.TestCase` subclasses are also discovered.

## Choosing a test layout

### Tests outside application code (recommended default)

```
pyproject.toml
src/
    mypkg/
        __init__.py
        app.py
        view.py
tests/
    test_app.py
    test_view.py
```

Benefits: tests can run against the installed package (`pip install .`) and against a
local editable copy. The **src layout is "strongly suggested"**, especially with the
default `prepend` import mode, because it prevents common pitfalls (the package is only
importable once installed, so tests exercise the real installed package).

For new projects, pytest recommends the **importlib import mode**:

```ini
[pytest]
addopts = ["--import-mode=importlib"]
```

If you do not use editable installs with the src layout, extend the search path via the
`PYTHONPATH` env var or the `pythonpath` config setting.

### Tests as part of application code

```
pyproject.toml
[src/]mypkg/
    __init__.py
    app.py
    view.py
    tests/
        __init__.py
        test_app.py
        test_view.py
```

"Useful if you have direct relation between tests and application modules and want to
distribute them along with your application." Run with `pytest --pyargs mypkg`.

### Choosing an import mode

pytest defaults to `prepend` mode for historical reasons; in that mode "test files must
have unique names" because they are imported as top-level modules. The `importlib` import
mode "does not have any of the drawbacks above, because sys.path is not changed when
importing test modules" — hence the recommendation for new projects.

## tox

When the work is done, tox sets up virtualenvs with predefined dependencies and runs a
preconfigured test command. Crucially, "it will run tests against the installed package
and not against your source code checkout," which helps detect packaging issues.

## Do not run via setuptools

Avoid `python setup.py test` and `pytest-runner` — "not recommended". It depends on
deprecated setuptools features and "relies on features that break security mechanisms in
pip." setuptools intends to remove the `test` command entirely.

---

(Note: this page also implies the role of `conftest.py` — a per-directory file holding
shared fixtures and local plugins that pytest auto-discovers up the directory tree; it is
how test layout and shared setup are wired together without imports.)
