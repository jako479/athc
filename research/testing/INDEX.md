# Test-documentation research — examples & findings

Curated reference set for designing athc's test docs. Each file has a 2-line header
(source URL + why it's worth mimicking). Retrieved 2026-06-10.

## Saved examples

| File | Source | What to mimic |
|------|--------|---------------|
| [sqlite-how-sqlite-is-tested.md](sqlite-how-sqlite-is-tested.md) | sqlite.org/testing.html | The gold-standard **testing-strategy / "how we test" doc**. One section per test *type* (anomaly, fuzz, regression, boundary, coverage) with the rationale for each. Copy the section structure; ignore the scale. |
| [curl-test-suite-readme.md](curl-test-suite-readme.md) | github.com/curl/curl `docs/tests/TEST-SUITE.md` | In-repo **tests/README** for a CLI+library project. Names the three test *kinds* (cli tool / library / unit), test numbering, memory & coverage runs, and "how to write a test". |
| [curl-test-case-fileformat.md](curl-test-case-fileformat.md) | github.com/curl/curl `docs/tests/FILEFORMAT.md` | A **declarative one-file-per-test-case** format. Mimic the `<testcase>` skeleton: `<info>/<keywords>` (what it covers) + `<client>/<command>` (setup) + `<verify>` (expected output). Tags themselves are curl-only. |
| [pytest-good-integration-practices.md](pytest-good-integration-practices.md) | docs.pytest.org `explanation/goodpractices.html` | **Where Python tests live & how they're discovered**: `src/` layout, `tests/` outside the package, `importlib` import mode, tox, conftest.py. Most directly applicable to athc. |
| [python-docx-feature-file-example.feature](python-docx-feature-file-example.feature) | github.com/python-openxml/python-docx `features/doc-add-table.feature` | A real **BDD Gherkin feature→scenario map**. Each `Scenario` = one behavior/edge case in Given/When/Then. Filename prefixes group features by component. Living docs that double as a feature→test list. |
| [django-writing-code-unit-tests.md](django-writing-code-unit-tests.md) | docs.djangoproject.com `internals/contributing/.../unit-tests/` | How a **large project organizes & documents its suite**: one dir per test area under `tests/`, one runner, how to run a subset, contributor conventions ("all tests must pass"). |

### Considered but not saved
- **Requirements-traceability-matrix (RTM) repos** (shtracer, RallyTechServices, spm2020spring/RequirementTraceabilityMatrix, burdiuz/traceability-matrices): these are *tooling/templates/demos*, not test docs of a mainstream product. No reputable mainstream OSS project was found maintaining a hand-written requirements→tests grid worth copying — see Finding 1.
- **curl `tests/README.md`**: no longer exists at that path (404); curl moved test docs to `docs/tests/` — the two curl files above are the current authoritative versions.

---

## Findings (Q1–Q5)

### Q1 — Do mainstream OSS projects keep a coverage matrix / test plan / traceability doc?
**Mostly no.** A formal requirements→test traceability matrix is rare in mainstream OSS and is primarily an **enterprise / QA / regulated-industry** practice (IEEE 829 test plans, ISO/IEC/IEEE 29119, ISTQB, DO-178C/IEC 62304 safety-critical). Typical reputable OSS projects instead rely on: (a) the test suite itself as the source of truth, (b) per-PR "add a regression test for every bug" policies (SQLite, Django), and (c) CI coverage reports (Codecov/Coveralls) for the *numeric* coverage signal — not a maintained enumerated matrix. The RTM-style artifacts that exist on GitHub are almost all generators/templates, not living docs inside a shipping project. A genuine "test plan" prose doc is more common than a matrix, but still the exception, not the norm.

### Q2 — When a tracking doc exists, what format?
Ranked by how often you actually see it in OSS:
- **(a) feature→test, as executable specs** — most common and most useful. Realized as **Gherkin `.feature` files** (python-docx) or just well-named `test_<behavior>` functions whose names *are* the spec. The mapping is implicit in code, not a separate table.
- **(b) test→feature list** — second; shows up as a `tests/README` describing what each test directory/module covers (Django's per-dir layout, curl's numbered cases).
- **(c) an actual grid/matrix with checkboxes** (rows = cases, cols = status) — **rare** in OSS; mainly enterprise/safety-critical QA deliverables. When OSS does it, it's usually a one-off release checklist (SQLite's ~200-item release checklist is the closest mainstream example, and it's a checklist, not a requirements grid).

Recommendation for a small project: lean on (a) — name one test per behavior — and add a short (b)-style `tests/README` index. Skip (c) unless a regulator asks.

### Q3 — What does a good testing *strategy / design* doc look like?
SQLite's "How SQLite Is Tested" is the template: a prose document, **organized by test *type* / risk**, that for each type states *what it checks, why, and how* — e.g. anomaly tests (OOM, I/O error, crash), fuzzing, regression, boundary-value, plus the **coverage standard** it holds itself to (statement vs branch vs MC/DC vs mutation) and the dynamic/static analysis used. It is explicitly distinct from a coverage *list*: it explains the philosophy and the categories, not which test hits which line. For a small project, a one-page version (test levels, what each covers, tools, coverage target, how to run) is the right scope.

### Q4 — Where do projects put test docs?
Two stable conventions, often combined:
- A **`tests/README`** (or `docs/tests/…`, as curl now does) sitting next to the tests, describing layout, how to run, and how to add a test.
- A **contributor doc** (`CONTRIBUTING`, or `docs/internals/.../unit-tests` like Django) covering test policy and running a subset.
The high-level *strategy* doc, when it exists, lives on the project site or in `docs/` (SQLite's testing.html). **Per-component test plans generally sit next to the component** (Gherkin `features/*.feature` named per component; test files mirroring the module tree) rather than in one centralized matrix. Root `TESTING.md` exists but is less common than a `tests/README` + CONTRIBUTING split.

### Q5 — Is the norm one test per behavior/edge-case, with parametrization for variants?
**Yes — confirmed.** The mainstream pattern is one focused test per behavior or edge case (one assert-worthy idea each), with **parametrization** for input variants of the same behavior (pytest `@pytest.mark.parametrize`; SQLite reuses parameterized cases to turn ~50k cases into millions of instances; Gherkin `Scenario Outline`/`Examples` does the same for BDD). Boundary values get explicit both-sides cases (SQLite's `testcase()` macros). So: separate tests for *distinct behaviors*, parametrized rows for *variants of one behavior* — don't fold unrelated behaviors into one mega-test.
