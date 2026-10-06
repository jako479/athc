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

uv (Python package manager).
Install by opening Command Prompt or PowerShell and running:

   winget install --id=astral-sh.uv -e

winget ships with Windows 10/11. If you see "winget is not
recognized", install "App Installer" from the Microsoft Store first.

You do not need to install Python. uv downloads it automatically
if it is not already on your computer.


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

athc ships configured for PNFL out of the box. The one thing you must
set is your plays folder: open leagues\PNFL\league.ini in your settings
folder (see below) and set play_path to your FbPro98 league plays
folder, for example:

   [league]
   play_path = D:\SIERRA\FBPRO98\PNFL\plays

To check every profile and game plan in a folder with check-ppp, also set
path to the folder that holds the league's files (like PNFL.lg2), for
example:

   path = D:\SIERRA\FBPRO98

Each league is a folder under leagues\ with its league.ini, rules\ and
standings\. athc ships two: PNFL and PCFL. To switch league, run:

   athc config set league PCFL

To add another league, copy a league folder and rename it.


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
   docs\               this README plus per-command references
   leagues\PNFL\        the PNFL league:
      league.ini           your plays folder (play_path) and league
                           files folder (path)
      rules\               gameplan.toml, profile.toml, playpool.toml,
                           scheduler.toml
      standings\           <season>.league.ini for the scheduler
   leagues\PCFL\        the PCFL league, same layout

To open this folder, run 'athc config reveal' (or paste
%LOCALAPPDATA%\athc into File Explorer's address bar).

What survives reinstalls:
   athc.ini             YES -- your edits are preserved on every reinstall.
                        Delete it to have install.bat seed a fresh PNFL
                        starter copy on the next run.
   leagues\*\league.ini YES -- preserved
   leagues\*\standings\ YES -- preserved (files are only added, never replaced)
   docs\                overwritten every install
   leagues\*\rules\     overwritten every install (copy a file before editing
                        your own league's rules)

When a new version adds a tool with new settings:
   The new tool runs with sensible defaults out of the box -- you do
   not have to edit anything.

   To customize it, see the freshly-extracted athc.ini in this zip (it
   lists every current setting), copy the new section into your athc.ini,
   and edit the values.


TROUBLESHOOTING
---------------

"uv is not recognized":
    uv is not installed, or was installed without being added to PATH.
    Follow the REQUIREMENTS section above.

"athc is not recognized":
    The installer hasn't been run yet, or it failed partway. Re-run
    install.bat and watch the window for errors.

Settings changes aren't picking up:
    Close and reopen the terminal, then re-run the command.

An error with no detail (or filing a bug report):
    Run  set ATHC_DEBUG=1  first, then re-run the command to see the
    full technical traceback.
