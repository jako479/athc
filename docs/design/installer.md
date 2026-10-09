# athc installer

How the athc and athc-admin setup.exe files are built, what they put on disk,
and how they are tested. This one doc covers both; athc-admin's installer.md
only points here.

The build follows the Tamarack Habilitations `pdf-converter` tool
(`C:\Users\Brian\Projects\Customer Projects\Tamarack Habilitations\pdf-converter`).

## End-user flow

1. Download `athc-<ver>-setup.exe`.
2. Run it. No admin rights, no Python, no internet needed.
3. Open a new terminal and run `athc`.

## The pattern

Two tools, two steps:

1. PyInstaller freezes athc into a one-folder bundle: a small `athc.exe`
   launcher, a bundled Python interpreter, and every dependency.
2. Inno Setup compiles that folder, the release docs and the seed config into
   `athc-<ver>-setup.exe`: a per-user install, the install folder on the
   user's PATH, config seeded once, and an uninstaller.

Why a frozen bundle and not an installer that installs Python: the users are
not developers. The bundle needs no Python and no internet, and cannot collide
with a Python they already have.

## Build

The build files live in a top-level `packaging/` folder, the most common home
for them in Python apps that ship a Windows installer (Thonny, Rare, Cura,
Gaphor). `config/release/` holds only the files that get installed:
`athc.ini`, `docs\` and `leagues\`.

| File | What it does |
|---|---|
| `packaging/release-build.ps1` | Installs the locked versions into a throwaway Python 3.13 build venv, freezes athc, then compiles `dist/athc-<ver>-setup.exe`, showing Inno Setup's messages. |
| `packaging/entry.py` | The script PyInstaller freezes; calls athc's `main()`. |
| `packaging/athc.iss` | The Inno Setup script. |
| `packaging/release-test.ps1` | Runs the setup.exe life cycle in Windows Sandbox. |
| `packaging/sandbox-steps.ps1` | The steps that run inside the sandbox. |

The build installs the exact versions in `uv.lock`, the ones the tests ran
against, and stops if `uv.lock` is out of date; this is the mainstream way
(Electrum, qutebrowser, Picard, Gaphor). PyInstaller is locked too, in a
`build` dependency group, and goes into the build venv only.

What the freeze needs beyond PyInstaller's defaults:

| Concern | Why | What the build does |
|---|---|---|
| Subcommands | athc finds its subcommands through `importlib.metadata` entry points, which load the modules by name from dist-info metadata. | Copies athc's metadata and every athc module into the bundle. |
| Package data | The autocontinue PNGs and the pdbtoexcel `.bin` resources are not found by import scanning. | Collects athc's data files. |
| ortools | ortools keeps its native DLLs in `ortools\.libs`, which PyInstaller cannot resolve and has no hook for. | Collects ortools' binaries. |

Build tooling, one time: uv, Inno Setup 6
(`winget install JRSoftware.InnoSetup`), and the Windows Sandbox optional
feature with its `wsb` command line for the test.

## What the setup.exe does

- Shows as "Assistant to the Head Coach" (Apps & features, Start menu) and
  installs per user into `%LOCALAPPDATA%\Programs\Assistant to the Head Coach`.
  The command is `athc.exe`.
- Installs on 64-bit Windows only, since the bundled Python is 64-bit.
- Wipes the old bundle's `_internal` folder before copying, because
  PyInstaller renames internals between builds.
- Adds the install folder to the user's PATH.
- Installs the release docs into the install folder, refreshed on every
  install: `README.txt`, `COMMANDS.txt`, `SCHEDULER-COMMANDS.txt`,
  `CHANGELOG.txt` and `LICENSE.txt`. Adds a Start-menu shortcut to the README
  and opens it after install.
- Seeds every file in `%LOCALAPPDATA%\athc` only if it is missing: `athc.ini`,
  and each league's `league.toml`, standings and rule TOMLs.
- Uninstall removes the program, its PATH entry, the Start-menu shortcut and
  the whole `%LOCALAPPDATA%\athc` folder, user edits included.

The seeded `athc.ini` selects PNFL; the only value a user must edit is
`play_path` in `leagues\PNFL\league.toml`, plus `path` to run `check-ppp` on a
folder. Layout: [architecture.md](architecture.md#config).

## Install, upgrade, reinstall, uninstall

Upgrade and reinstall both mean running a setup.exe over an existing install;
the uninstaller does not run.

| | Program and docs (install folder) | `%LOCALAPPDATA%\athc` files | PATH entry |
|---|---|---|---|
| First install | installed | all seeded | added |
| Upgrade or reinstall | replaced | kept as they are; only missing files are added | kept |
| Uninstall | removed | whole folder removed, edits included | removed |
| Uninstall, then install | installed fresh | all seeded fresh | added |

When a release must replace a specific seeded file, its setup.exe gives that
one file its own overwrite entry.

## Config evolution

In-code defaults are authoritative. Every section and key in `athc.ini` is
optional; a missing one uses the tool's default.

A release that adds a tool's section:

1. The tool runs on its defaults; the user does nothing.
2. To customize, the user adds the section to their own `athc.ini`.

No migration step, no merge prompts, no clobber risk. Pattern follows
pgcli/mycli: a single self-documenting config, seeded once and left alone.

## Deprecation

When a tool sees a deprecated key: log a one-line startup warning, keep reading
it for 2-3 releases, then drop. Pattern follows VS Code's `deprecationMessage`.

## Testing

`packaging/release-test.ps1` runs the setup.exe in Windows Sandbox with no
network, which also proves it installs offline:

1. Silent install: program, docs, seeded config, shortcut and PATH entry.
2. Every command and subcommand runs on the integration-test fixtures; reports,
   lists, diffs and schedules match the goldens.
3. Upgrade over the install: a stale `_internal` file is gone, the docs are
   refreshed, an edited `athc.ini` and rule TOML are kept, a deleted seeded
   file comes back.
4. Silent uninstall: the program, `%LOCALAPPDATA%\athc`, the shortcut and the
   PATH entry are gone.

It prints PASS/FAIL lines, exits non-zero on any failure, and closes the
sandbox when done.

## Admin build

athc-admin builds `athc-admin-<ver>-setup.exe`, which freezes athc and
athc-admin together into one `athc.exe`. athc-admin's commands then show up
the same way athc's do, with no code changes.

- athc-admin follows the same layout: scripts in its own `packaging/`, admin
  docs in its own `config/release/docs/`.
- Its `release-build.ps1` reuses athc's `packaging/entry.py` and `athc.iss`
  from the athc checkout beside it (or `-AthcRoot`). It installs the exact
  versions in athc's `uv.lock`, so both bundles carry the same libraries, and
  also bundles athc-admin's metadata, modules and `sql\*.sql`.
- It installs athc's docs plus `README-admin.txt` and `COMMANDS-admin.txt`.
- It has the same app identity and install folder as the public setup.exe, so
  it installs over a public install in place: one `athc.exe` on PATH, one
  uninstall entry.
- The public setup.exe refuses to install over the admin edition, which would
  drop the admin commands and leave their docs behind. The admin install
  leaves a registry marker for this; its uninstall removes it.
- Its `release-test.ps1` runs athc's sandbox test on the admin setup.exe, plus
  its own `sandbox-steps.ps1` for the logparser commands and for the public
  setup.exe refusing to install over it.
- athc and athc-admin versions stay in lockstep (athc-admin's release.md).
