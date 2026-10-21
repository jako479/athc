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

with this README, one file per command (autocontinue.txt, check-ppp.txt,
config.txt, convert-pdb.txt, gameplan.txt, generate-schedule.txt,
playpool.txt, profile.txt, standings.txt), USAGE_ORIGINAL.txt, CHANGELOG.txt
and LICENSE.txt beside it. The Start menu has a shortcut to this README.

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

   athc --help                        list top-level commands
   athc <group> --help                list subcommands in a group
   athc <group> <subcommand> --help   show help for one subcommand

For what each tool does, with examples, see its file in the install folder
(see INSTALLATION above): autocontinue.txt, check-ppp.txt, config.txt,
convert-pdb.txt, gameplan.txt, generate-schedule.txt (Commissioner only),
playpool.txt, profile.txt and standings.txt. USAGE_ORIGINAL.txt keeps each
command's help as it was before 1.0, for reference; run --help for the
current help.

Settings live in athc.toml (the file documents every option inline). Each
league is a folder under leagues\ next to it: league.toml (path, play_path,
team, ppp_path, category names, and any convert-pdb settings that differ
from athc.toml's) and rule files (gameplan.toml, profile.toml,
scheduler.toml). League-aware tools use the league named by [athc] league
unless the command is given --league NAME.

Game plan and profile keys: off1, def1, off2 and def2 name your team's
1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense
file, found in ppp_path in league.toml, else where the league file puts
them. team in league.toml is your team; --team NAME picks another team for
one run. A file or folder that exists by that name wins over the key.


EXIT CODES
----------

   The same numbers in every command, so a script can treat 2 as "athc
   could not do it" everywhere:
      0    done -- clean, or with warnings only
      1    findings -- ran fine and reported problems in valid input
           (violations, play pool issues, differences, a play found
           nowhere, nothing replaced, no valid replacement); only gameplan
           check, find-play, replace-play, profile check, profile diff,
           check-ppp and playpool check use it
      2    error -- could not do the job: bad arguments, a config, league
           or rules problem, a missing or bad file, a file that failed
           inside a batch, a missing dependency, or a bug
      130  stopped with Ctrl-C (autocontinue stops that way on purpose, so
           there it is 0)

   A batch (a folder or a list of files) processes every file, then exits
   with the worst outcome: error beats findings beats clean. Warnings never
   change the code.

   A status line starts with a label: OK (done), SKIP (left alone on
   purpose), WARN (noted, nothing failed), FAIL (that item, or the run,
   failed). Results, OK and SKIP go to standard output; progress, WARN and
   FAIL to standard error, so  > out.txt  keeps the results and  2> err.txt
   the problems. Every status line is also in the run log,
   %LOCALAPPDATA%\athc\Logs\athc.log.


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
