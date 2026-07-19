athc
====

Assistant to the Head Coach -- umbrella CLI for Front Page
Sports Football Pro '98 league management.

Provides the 'athc' command and its tools. Run 'athc --help'
to list them.


WHAT'S NEW IN v0.1.0
--------------------

- Initial release: install/build pipeline plus the core athc
  commands (run 'athc --help').


REQUIREMENTS
------------

Windows 10 or newer.

Python 3.12 or later.
Download from: https://www.python.org/downloads/

IMPORTANT: During Python installation, check the box that says
"Add Python to PATH". Without this, the install script will not work.

uv (Python package manager).
Install by opening Command Prompt or PowerShell and running:

   winget install --id=astral-sh.uv -e

winget ships with Windows 10/11. If you see "winget is not
recognized", install "App Installer" from the Microsoft Store first.


INSTALLATION
------------

1. Extract this zip to a folder on your computer.
2. Double-click install.bat and wait for it to finish.

install.bat downloads athc's dependencies, so you need an internet
connection the first time you install.

You only need to run install.bat once. Re-running it later picks up
new versions without touching your settings.


FIRST-TIME SETUP
----------------

athc ships configured for PNFL out of the box -- the bundled rule sets
in rules\ are already wired up. The one thing you must set is your
plays folder. Run 'athc config edit' (or open athc.ini, see below) and
set PlayPath under [league.PNFL] to your FbPro98 league plays folder,
for example:

   [league.PNFL]
   PlayPath = D:\SIERRA\FBPRO98\PNFL\plays


USING THE TOOLS
---------------

Once installed, the 'athc' command is available from any terminal
(Command Prompt or PowerShell):

   athc --help                      list top-level commands
   athc <command> --help            show help for one command

For what each tool does, with examples, see docs\COMMANDS.txt in
your settings folder (see below).


SETTINGS AND DOCS FOLDER
------------------------

After install, settings and documentation live together at:

   %LOCALAPPDATA%\athc\

That folder will contain:

   athc.ini             your settings (edit to customize; the file
                        documents every setting inline)
   docs\                this README plus per-command references
   rules\               PNFL rule sets (PNFL.*.toml) for
                        gameplan/profile/playpool

To open this folder, run 'athc config reveal' (or paste
%LOCALAPPDATA%\athc into File Explorer's address bar).

What survives reinstalls:
   athc.ini             YES -- your edits are preserved on every reinstall.
                        Delete it to have install.bat seed a fresh PNFL
                        starter copy on the next run.
   docs\                overwritten every install
   rules\               overwritten every install (copy a file before editing
                        your own league's rules)

When a new version adds a tool with new settings:
   The new tool runs with sensible defaults out of the box -- you do
   not have to edit anything.

   To customize it, see the freshly-extracted athc.ini in this zip (it
   lists every current setting), copy the new section into your athc.ini,
   and edit the values.


TROUBLESHOOTING
---------------

"python is not recognized" or "uv is not recognized":
    These were installed without adding to PATH (or not installed at
    all). Follow the REQUIREMENTS section above, making sure to check
    the PATH option during Python install.

"athc is not recognized":
    The installer hasn't been run yet, or it failed partway. Re-run
    install.bat and watch the window for errors.

Settings changes aren't picking up:
    Close and reopen the terminal, then re-run the command.

An error with no detail (or filing a bug report):
    Run  set ATHC_DEBUG=1  first, then re-run the command to see the
    full technical traceback.
