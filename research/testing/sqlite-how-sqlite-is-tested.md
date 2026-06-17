<!--
Source: https://www.sqlite.org/testing.html (retrieved 2026-06-10)
Why mimic: the gold-standard "how we test" strategy doc — names every test TYPE, the
rationale for each, and the coverage metrics (branch / MC/DC / mutation). Copy the
section structure, not the scale. Verbatim excerpt with headings preserved; long
prose trimmed only where noted.
-->

# How SQLite Is Tested

## 1. Introduction

The reliability and robustness of SQLite is achieved in part by thorough and careful testing.

As of version 3.42.0 (2023-05-16), the SQLite library consists of approximately 155.8 KSLOC of C code. By comparison, the project has 590 times as much test code and test scripts — 92053.1 KSLOC.

### 1.1. Executive Summary

- Four independently developed test harnesses
- 100% branch test coverage in an as-deployed configuration
- Millions and millions of test cases
- Out-of-memory tests
- I/O error tests
- Crash and power loss tests
- Fuzz tests
- Boundary value tests
- Disabled optimization tests
- Regression tests
- Malformed database tests
- Extensive use of assert() and run-time checks
- Valgrind analysis
- Undefined behavior checks
- Checklists

## 2. Test Harnesses

There are four independent test harnesses used for testing the core SQLite library. Each test harness is designed, maintained, and managed separately from the others.

1. **The TCL Tests** are the original tests for SQLite, in the same source tree as the core and in the public domain. They are the primary tests used during development. 51445 distinct test cases, many parameterized and run multiple times, so a full run performs millions of separate tests.

2. **The TH3** test harness is a set of proprietary tests, written in C, that provide 100% branch test coverage (and 100% MC/DC test coverage) to the core SQLite library. Designed to run on embedded/specialized platforms. Uses only published SQLite interfaces. 50362 distinct test cases, heavily parameterized — a full-coverage test runs about 2.4 million different test instances; a pre-release soak test does about 248.5 million tests.

3. **The SQL Logic Test (SLT)** harness runs huge numbers of SQL statements against both SQLite and several other SQL database engines (PostgreSQL, MySQL, SQL Server, Oracle 10g) and verifies they all get the same answers. Runs 7.2 million queries comprising 1.12GB of test data.

4. **The dbsqlfuzz** engine is a proprietary fuzz tester that mutates both the SQL and the database file at the same time, reaching new error states. Built on LLVM libFuzzer with a custom mutator. Runs about one billion test mutations per day.

Additional specialized programs: speedtest1.c (performance), mptester.c (multi-process stress), threadtest3.c (multi-thread stress), fuzzershell.c and jfuzz (fuzzing).

All tests must run successfully, on multiple platforms and under multiple compile-time configurations, before each release. Prior to each check-in, developers typically run a "veryquick" subset of ~304.7 thousand Tcl test cases — enough to catch most errors but running in minutes, not hours.

## 3. Anomaly Testing

Anomaly tests verify correct behavior when something goes wrong. It is relatively easy to build an engine that behaves correctly on well-formed inputs on a fully functional computer; it is harder to respond sanely to invalid inputs and continue functioning after system malfunctions.

### 3.1. Out-Of-Memory Testing

OOM testing simulates malloc() failures via a rigged allocator that fails after a set number of allocations. Tests run in a loop: fail on the 1st allocation, verify correct handling, increment the failure counter, repeat until the operation completes without a simulated failure. Run twice — fail-once and fail-continuously modes.

### 3.2. I/O Error Testing

Similar to OOM testing, but simulates failed I/O via an instrumented Virtual File System. After the failure mechanism is disabled, `PRAGMA integrity_check` confirms no corruption was introduced.

### 3.3. Crash Testing

Demonstrates the database will not corrupt if the application/OS crashes or power fails mid-update. Done in simulation via an alternative VFS that reorders and corrupts unsynchronized writes; after the simulated crash the database is reopened and verified to have either completed or completely rolled back the transaction.

### 3.4. Compound failure tests

Stacking multiple failures — e.g. an I/O error or OOM fault occurring while recovering from a prior crash.

## 4. Fuzz Testing

Fuzz testing establishes that SQLite responds correctly to invalid, out-of-range, or malformed inputs.

### 4.1. SQL Fuzz

Creating syntactically correct yet nonsensical SQL and feeding it to SQLite. History: American Fuzzy Lop (AFL, profile-guided, 2015–2019), Google OSS Fuzz (guided fuzzer on Google infra), and the current proprietary dbsqlfuzz + jfuzz. Historical fuzz-found cases are collected as database files and rerun by the "fuzzcheck" utility on every `make test`.

#### 4.1.6. Tension Between Fuzz Testing And 100% MC/DC Testing

Fuzz testing and 100% MC/DC testing are in tension: MC/DC discourages defensive code with unreachable branches, but without defensive code a fuzzer is more likely to find a problematic path. MC/DC builds code robust in normal use; fuzzing builds code robust against malicious attack. SQLite maintains 100% MC/DC of the core but now devotes most testing CPU to fuzzing.

### 4.2. Malformed Database Files

Build a well-formed database, corrupt one or more bytes by some means other than SQLite, then read it. Verifies SQLite reports format errors via SQLITE_CORRUPT without overflowing buffers, dereferencing NULL, or other unwholesome actions.

### 4.3. Boundary Value Tests

Tests push SQLite right to the edge of its defined limits (max columns, max statement length, max integer) and verify correct behavior, plus tests just beyond the limits that verify errors are returned. testcase() macros verify both sides of each boundary are tested.

## 5. Regression Testing

A reported bug is not considered fixed until new test cases that would exhibit the bug are added to the TCL or TH3 suites. Over the years this has produced thousands of regression tests that ensure fixed bugs are not reintroduced.

## 6. Automatic Resource Leak Detection

Both the TCL and TH3 harnesses automatically track system resources and report leaks (memory, file descriptors, threads, mutexes) on every test run. SQLite is designed to never leak memory, even after an OOM or disk I/O error.

## 7. Test Coverage

The SQLite core (including the unix VFS) has 100% branch test coverage under TH3 in its default configuration as measured by gcov.

### 7.1. Statement versus branch coverage

Statement coverage measures what percentage of lines execute at least once. Branch coverage is more rigorous — it measures whether each machine-code branch is evaluated in both directions. For `if( a>b && c!=25 ){ d++; }`, 100% branch coverage requires at least three cases: `a<=b`, `a>b && c==25`, `a>b && c!=25`. Any one gives 100% statement coverage; all three are needed for branch coverage.

### 7.2. Coverage testing of defensive code

SQLite keeps defensive conditionals (always-true/always-false) rather than deleting them to reach 100% branch coverage. Macros `ALWAYS(X)` and `NEVER(X)` mark them. In release builds they are pass-throughs; during testing they assert if the expected truth value is wrong; during coverage measurement they become constant truth values so they generate no branch instructions.

### 7.3. Forcing coverage of boundary values and boolean vector tests

The `testcase(X)` macro marks a condition for which both true and false cases must exist. A no-op in release builds; in coverage builds it generates code that is checked to evaluate both ways. Used for boundary values, multi-case switch fall-through, and verifying every bit of a bitmask affects the outcome. SQLite contains 1184 uses of `testcase()`.

### 7.4. Branch coverage versus MC/DC

MC/DC (Modified Condition/Decision Coverage): each decision tries every outcome, each condition takes every outcome, each entry/exit is invoked, and each condition is shown to independently affect the decision. In C with short-circuit `&&`/`||`, MC/DC and branch coverage are nearly identical except for boolean vector tests; testcase() macros close that gap, so SQLite achieves 100% MC/DC in addition to 100% branch coverage.

### 7.6. Mutation testing

Beyond "every branch is taken both ways," mutation testing shows every branch *makes a difference* in output. A script rewrites each branch instruction (to an unconditional jump or a no-op), recompiles, and verifies the test suite catches the mutation. Branches that are pure optimizations are exempted with `/*OPTIMIZATION-IF-TRUE*/` / `/*OPTIMIZATION-IF-FALSE*/` comments.

### 7.7. Experience with full test coverage

Full-coverage testing is extremely effective at locating and preventing bugs and gives confidence that a change in one area has no unintended consequences elsewhere. But maintaining 100% MC/DC is laborious and "probably not cost effective for a typical application" — it is justified for a very widely deployed infrastructure library like SQLite.

## 8. Dynamic Analysis

Internal/external checks while the code is live and running.

- **8.1. Assert** — 6754 assert() statements verify preconditions, postconditions, and loop invariants; enabled only under SQLITE_DEBUG (production disables them as they make the engine ~3x slower).
- **8.2. Valgrind** — finds array overruns, uninitialized reads, stack overflows, memory leaks. Too slow for the full suite, but the veryquick tests and TH3 coverage are run through Valgrind before every release.
- **8.3. Memsys2** — an optional allocation wrapper (SQLITE_MEMDEBUG) that catches leaks, buffer overruns, uninitialized use, and use-after-free, faster than Valgrind.
- **8.4. Mutex Asserts** — sqlite3_mutex_held()/notheld() used inside asserts to verify correct multi-threaded mutex discipline.
- **8.5. Journal Tests** — a "journal-test VFS" verifies nothing is written to the database file that was not first written and synced to the rollback journal.
- **8.6. Undefined Behavior Checks** — suites are rerun with -ftrapv (GCC), -fsanitize=undefined (Clang), /RTC1 (MSVC), and with -funsigned-char/-fsigned-char, on 32- and 64-bit and big/little-endian systems, plus tests deliberately designed to provoke UB.

## 9. Disabled Optimization Tests

The whole suite is run twice — optimizations on and off — and must produce identical output, proving optimizations do not introduce errors. (A minority of tests that count disk accesses/sorts/scan steps are excepted.)

## 10. Checklists

An online release checklist of ~200 items is individually verified for each release. The checklist is run manually — "it is important to keep a human in the loop" reviewing output and asking "Is this really right?" — and continuously evolves as new potential problems are discovered.

## 11. Static Analysis

SQLite compiles warning-free under GCC/Clang (-Wall -Wextra) and MSVC, and the Clang Static Analyzer. Notably, "static analysis has not been helpful in finding bugs in SQLite … More bugs have been introduced into SQLite while trying to get it to compile without warnings than have been found by static analysis."

## 12. Summary

Open source does not mean poorly tested. SQLite's quality comes from careful design plus extensive testing; this document summarizes the procedures every release undergoes, intended to inspire confidence that SQLite is suitable for mission-critical use.
