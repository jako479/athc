# API documentation

Design for the TODO item. Done when every library has its API page and
`docs/design/overview.md` states the rule; then delete this file.

## What mainstream libraries do

- xlsxwriter, openpyxl, pandas, Pillow and requests keep an API reference
  apart from the quickstart and how-to pages and from design pages.
- The reference is one page per class or module, built from the docstrings
  (Sphinx).
- One package with many modules (Pillow, pandas) still has one reference:
  one page per module under one index.
- That split has a name, Diátaxis: tutorial, how-to, reference, explanation.

## Rule to adopt

- One API page per library: `docs/<lib>/README.md` holds the quickstart and
  the reference (public functions, classes and exceptions, one short entry
  each).
- One shared index of those pages in `docs/design/overview.md`.
- A format spec keeps only the byte layout and the rules a reader must
  enforce ("reject X"); nothing about function names or exceptions.

## Work

- Move the Reader Contract sections out of `ply.md`, `pln.md` and `prf.md`
  into each library's README (`lg2.md` is done).
- Give every library README the same shape: quickstart, then reference.
- Add the index to `docs/design/overview.md`, fold the rule in, delete this
  file.
