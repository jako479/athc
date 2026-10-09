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

64-bit Windows. Nothing else: athc carries its own Python, and installing
needs no internet and no admin rights.

   Windows 8.1 or newer:   check-ppp, config, convert-pdb, gameplan,
                           playpool, profile
   Windows 10 or newer:    autocontinue, generate-schedule


INSTALLATION
------------

1. Run athc-<version>-setup.exe.
2. Open a new Command Prompt or PowerShell window and run 'athc'.

The program installs to:

   %LOCALAPPDATA%\Programs\Assistant to the Head Coach\

with this README, COMMANDS.txt, SCHEDULER-COMMANDS.txt, CHANGELOG.txt and
LICENSE.txt beside it. The Start menu has a shortcut to this README.

To upgrade, run the new version's setup.exe. Your settings are kept.


FIRST-TIME SETUP
----------------

athc ships configured for PNFL out of the box. The one thing you must
set is your plays folder: open leagues\PNFL\league.toml in your settings
folder (see below) and set play_path to your FbPro98 league plays
folder, for example:

   [league]
   play_path = 'D:\SIERRA\FBPRO98\PNFL\plays'

To check every profile and game plan in a folder with check-ppp, also set
path to the folder that holds the league's files (like PNFL.lg2), for
example:

   path = 'D:\SIERRA\FBPRO98'

Each league is a folder under leagues\ with its league.toml, rule files
(*.toml) and standings\. athc ships two: PNFL and PCFL. To switch league, run:

   athc config set league PCFL

To add another league, copy a league folder and rename it.


USING THE TOOLS
---------------

Once installed, the 'athc' command is available from any terminal
(Command Prompt or PowerShell):

   athc --help                      list top-level commands
   athc <command> --help            show help for one command

For what each tool does, with examples, see COMMANDS.txt in the
install folder (see INSTALLATION above).


SETTINGS FOLDER
---------------

After install, your settings live at:

   %LOCALAPPDATA%\athc\

That folder will contain:

   athc.ini             your settings (edit to customize; the file
                        documents every setting inline)
   leagues\PNFL\        the PNFL league:
      league.toml          your plays folder (play_path), league files
                           folder (path) and the league's category names
      gameplan.toml        league rules, one file per tool
      profile.toml
      playpool.toml
      pdbtoexcel.toml      convert-pdb's category order and deleted plays
      scheduler.toml
      standings\           <season>.league.ini for the scheduler
   leagues\PCFL\        the PCFL league, same layout

To open this folder, run 'athc config reveal' (or paste
%LOCALAPPDATA%\athc into File Explorer's address bar).

Upgrading or reinstalling never overwrites a file in this folder: your
edits to athc.ini, league.toml, the rule files and the standings are kept.
It only adds files that are missing, so to get a fresh copy of a shipped
file, delete it and run the setup.exe again.

When a new version adds a tool with new settings:
   The new tool runs with sensible defaults out of the box -- you do
   not have to edit anything. To customize it, add its section to your
   athc.ini.


UNINSTALLING
------------

Uninstall "Assistant to the Head Coach" from Settings > Apps. This
removes the program and the whole %LOCALAPPDATA%\athc\ folder,
including your settings, league files and standings. Copy anything you
want to keep first.


TROUBLESHOOTING
---------------

"athc is not recognized":
    Open a new Command Prompt or PowerShell window; one opened before
    the install does not see it. If it still fails, run the setup.exe
    again.

Settings changes aren't picking up:
    Close and reopen the terminal, then re-run the command.

An error with no detail (or filing a bug report):
    Run  set ATHC_DEBUG=1  first, then re-run the command to see the
    full technical traceback.

convert-pdb says "Play file not found" for every play, and the play
sheets are empty:
    play_path in leagues\<NAME>\league.toml is not your plays folder.

convert-pdb says "pdbtoexcel.toml: not found":
    The league folder has no pdbtoexcel.toml. For PNFL or PCFL, run the
    setup.exe again to add it back; for another league, copy the one from
    leagues\PNFL\ and edit it.

convert-pdb says a game plan was not found:
    Fix the path after -o / -o2 / -d / -d2, or leave that option out.
