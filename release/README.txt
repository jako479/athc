athc
====

Assistant to the Head Coach -- umbrella CLI for Front Page
Sports Football Pro '98 league management.

No tools are wired up yet. Real subcommands (gameplan, profile,
generate-schedule, etc.) are being added as the project is ported
in.


WHAT'S NEW IN v0.1.0
--------------------

- Initial release. Install/build pipeline in place; subcommands
  land as the project is ported in.


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

You only need to run install.bat once. Re-running it later picks up
new versions without touching your settings.


USING THE TOOLS
---------------

Once installed, the 'athc' command is available from any terminal
(Command Prompt or PowerShell):

   athc --help                      list top-level commands
   athc <command> --help            show help for one command

For what each tool does, with examples, see COMMANDS.txt in your
settings folder (see below).


SETTINGS AND DOCS FOLDER
------------------------

After install, settings and documentation live together at:

   %LOCALAPPDATA%\athc\

That folder will contain:

   athc.ini             your settings (edit to customize)
   athc.ini.example     always-current reference -- shows every section
                        and key supported by the installed version
   README.txt           this file
   COMMANDS.txt         per-command reference

To open the folder, paste this into File Explorer's address bar:

   %LOCALAPPDATA%\athc

What survives reinstalls:
   athc.ini             YES -- your edits are preserved on every reinstall.
                        Delete it to have install.bat seed a fresh copy
                        from athc.ini.example on the next run.
   athc.ini.example     overwritten every install (always shows the latest)
   README.txt           overwritten every install
   COMMANDS.txt         overwritten every install

When a new version adds a tool with new settings:
   The new tool runs with sensible defaults out of the box -- you do
   not have to edit anything.

   To customize the new tool's settings, open athc.ini.example, copy
   the new section into your athc.ini, and edit the values.


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
