<!--
Source: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/ (retrieved 2026-06-10)
Why mimic: shows how a large project ORGANIZES and DOCUMENTS its test suite in-repo —
one directory per test area under tests/, a single runner (runtests.py), how to run a
subset, and contributor-facing conventions ("all tests must pass at all times").
Faithful paraphrase with headings preserved.
-->

# Django — Unit tests (contributing guide)

Django ships with its own test suite in the `tests/` directory of the code base. The
policy is that **all tests must pass at all times**. Django's tests all use the testing
infrastructure that ships with Django; see "Writing and running tests" for how to write
new tests.

## Test suite organization

- Tests live in the top-level `tests/` directory.
- **One directory per test area.** Each subdirectory name in `tests/` is the name of a
  test (e.g. `generic_relations`, `i18n`).
- **Contrib app tests** live under `tests/<app>_tests` (e.g. `tests/auth_tests` for
  `django.contrib.auth`).

## Running the unit tests

```bash
git clone https://github.com/YourGitHubName/django.git django-repo
cd django-repo/tests
python -m pip install -e ..
python -m pip install -r requirements/py3.txt
./runtests.py
```

Run a subset by appending module/class/method paths:

```bash
./runtests.py generic_relations i18n                       # whole modules
./runtests.py i18n.tests.TranslationTests                  # one test class
./runtests.py i18n.tests.TranslationTests.test_lazy_objects # one test method
```

Useful options: `--tox` (run across Python versions/envs), `--selenium=<BROWSERS>`,
`--screenshots`, `--debug-sql`, `--parallel=1` (sequential, full tracebacks),
`--bisect` / `--pair` (find tests that fail only in combination).

## Settings & databases

- The default test settings use SQLite (`tests/test_sqlite.py`).
- Custom databases require `default` and `other` aliases in the `DATABASES` setting; the
  runner prepends `test_` to database names.
- Test databases must use a UTF-8 character set. Some tests (e.g. `contrib.postgres`) are
  skipped on incompatible backends.

## Tips for writing tests

Use `@isolate_apps()` to define models inside a test without polluting the global `apps`
registry:

```python
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

class TestModelDefinition(SimpleTestCase):
    @isolate_apps("app_label")
    def test_model_definition(self):
        class TestModel(models.Model):
            pass
        ...
```

The page also covers troubleshooting (Unicode errors, hanging tests) and links out to the
general "Writing and running tests" topic and code-coverage reporting.
