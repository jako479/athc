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
                           playpool, profile, standings
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
An older version's setup.exe will not install over a newer one; uninstall
first to go back.


FIRST-TIME SETUP
----------------

athc ships configured for PNFL out of the box. The one thing you must
set is your play pool folder: run athc config edit league.toml and set
play_path to your FbPro98 league play pool folder, for example:

   [league]
   play_path = 'D:\SIERRA\FBPRO98\PNFL\plays'

To work on your team's profiles and game plans (check-ppp, gameplan,
profile, convert-pdb), to generate a schedule, or to show the standings,
also set path to the folder that holds the league's files (like PNFL.lg2
and PNFL.lge), and team to your team's name or nickname, for example:

   path = 'D:\SIERRA\FBPRO98'
   team = 'Denver'

athc config set does the same from the command line, for example
athc config set team Denver.

Each league is a folder under leagues\ with its league.toml and rule files
(*.toml). athc ships two: PNFL and PCFL. To switch league, run:

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

   athc.toml            your settings, convert-pdb's category order and
                        deleted plays included (edit to customize; the file
                        documents every setting inline)
   leagues\PNFL\        the PNFL league:
      league.toml          your play pool folder (play_path), league files
                           folder (path), your team (team, for
                           check-ppp, gameplan, profile and
                           convert-pdb), your profiles and game plans
                           folder (ppp_path, optional) and the
                           league's category names; a league that
                           differs can override athc.toml's
                           convert-pdb settings here
      gameplan.toml        league rules, one file per tool
      profile.toml
      scheduler.toml       the scheduler's settings and renamed teams
   leagues\PCFL\        the PCFL league, same layout

To open this folder, run 'athc config reveal' (or paste
%LOCALAPPDATA%\athc into File Explorer's address bar).

Upgrading or reinstalling never overwrites a file in this folder: your
edits to athc.toml, league.toml and the rule files are kept.
It only adds files that are missing, so to get a fresh copy of a shipped
file, delete it and run the setup.exe again.

When a new version adds a tool with new settings:
   The new tool runs with sensible defaults out of the box -- you do
   not have to edit anything. To customize it, add its table to your
   athc.toml.


UNINSTALLING
------------

Uninstall "Assistant to the Head Coach" from Settings > Apps. This
removes the program and the whole %LOCALAPPDATA%\athc\ folder,
including your settings and league rule files. Copy anything you want
to keep first.


TROUBLESHOOTING
---------------

"athc is not recognized":
    Open a new Command Prompt or PowerShell window; one opened before
    the install does not see it. If it still fails, run the setup.exe
    again.

Settings changes aren't picking up:
    Close and reopen the terminal, then re-run the command.

An error with no detail (or filing a bug report):
    The run log holds the full technical detail, every traceback included:
    %LOCALAPPDATA%\athc\Logs\athc.log. Attach it to the report.

convert-pdb says "is not in the play pool" for every play, and
the play sheets are empty:
    play_path in leagues\<NAME>\league.toml is not your play pool folder.
    Run athc config get play_path to see it, and athc config edit
    league.toml to fix it.

convert-pdb says "The system cannot find the file specified." for a game
plan:
    Fix the path after -o / -o2 / -d / -d2, or leave that option out.
    With no -o / -o2 / -d / -d2, the game plans are your team's: fix path,
    team or ppp_path in league.toml.
