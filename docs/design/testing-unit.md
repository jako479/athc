# athc — Unit Testing Design

How athc's **unit** tests are structured — components in isolation. Integration tests (CLI → output file): [testing-integration.md](testing-integration.md). Conventions from llm, Flask, Poetry, dbt, CPython, Pillow, mutagen; see [reference-projects.md](reference-projects.md#testing-exemplars).

## Framework

`pytest`. src-layout → `tests/` at the repo root, beside `src/` (runs against the installed/editable package). `--import-mode=importlib` in `addopts` — modern default, and required because mirrored dirs reuse filenames (`test_reader.py` in several libs).

## Config

Unit tests use **no config** — components are called directly with constructed or committed inputs, never reading `athc.ini`. An autouse `config_dir` fixture (root `tests/conftest.py`) still points `ATHC_CONFIG_DIR` at an empty temp dir so nothing leaks to the real machine config; the few tests that load config use the shared `write_config` helper to write `athc.ini` there. A test needing the platformdirs default must `monkeypatch.delenv("ATHC_CONFIG_DIR", raising=False)`.

## Layout

Split by test type; `unit/` **mirrors** `src/athc/` so a file's tests are findable.

```
tests/
  conftest.py                  # shared fixtures: config_dir (autouse) + write_config
  unit/                        # isolated, fast; no IO (or only tmp_path); mirrors src/athc/
    fbpro98_play/
      conftest.py              # make_ply() byte-builder fixture
      data/                    # curated real .ply files
      test_reader.py
      test_model.py
      test_schema.py
      README.md                # this library's test matrix
  integration/                 # CLI end-to-end → output files — see testing-integration.md
```

A unit test exercises one component alone — no IO, or only `tmp_path`. Reading a small committed fixture still counts as unit.

## Fixtures (binary inputs)

Mainstream binary parsers use **both**, split by purpose:

- **Real files** — valid-parse + regression against genuine structure you can't hand-encode. Curated handful (~6–10), not the whole corpus.
- **Constructed bytes** (`make_ply()` / `struct`) — malformed/edge cases (truncation, bad magic, size mismatch) and exhaustive coverage (every category code), where no real file fits and each case pins one defect.

Rule of thumb: real where it validates real-world fidelity; constructed where you need surgical control or full coverage — not "real wherever possible."

### Expected results

Keep expected values **inline** in the test (`@pytest.mark.parametrize` or a small `FixtureExpectation` dataclass) — `data/` holds the inputs, the test holds the answer. Only for genuinely large/opaque output (e.g. gameplan's 64-slot name dump) commit a plain `data/expected/*.txt` instead.

### Fixture data layout

Flat `<lib>/data/` folder, scenario encoded in the filename (`offense-passlong-typical.ply`, `truncated-header.ply`, `empty.ply`). **Do not** mirror the league play-pool category folders — fixtures are organized by parser behavior, not football category (matches mutagen, CPython). Subfolder by parser concern (`valid/`, `malformed/`) only if a suite grows past ~30–40 files.

## Documentation

OSS treats the **test suite as the spec** (well-named tests + CI coverage), not formal traceability matrices. One lightweight addition:

- **Per-library test matrix** at `tests/unit/<lib>/README.md` — each case (normal / error / edge), the test that covers it, and status. Makes edge-case coverage scannable, which a coverage % can't.
- **One test per behavior**; parametrize input variants (e.g. one parametrized test over all category codes) rather than copy-pasting.
- These docs are the strategy/how; the per-library README is the what.

## Coverage

`coverage.py` (`pytest --cov`) measures which lines/branches the tests execute — a measurement *over* whatever suite runs, not a test tier of its own. Run it on the unit suite in CI; treat surprise gaps as missing tests, not a number to chase.
