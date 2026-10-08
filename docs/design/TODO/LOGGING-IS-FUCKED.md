# Logging — what is broken and what to do

Status: TODO for 1.0.0. The design is [architecture.md](../architecture.md#output-streams); this file lists where the code does not follow it (audit of 2026-10-08).

## The design in one breath

- stdout (`click.echo`): the command's results and its success/status line — what the user reads, pipes and saves.
- stderr (`logging`): errors, warnings, and library progress.
- One handler setup, in the `cli()` group callback, colored (`RichHandler`); no command calls `basicConfig`.

## What the code does today

Followed:

- No CLI command calls `logger.info` / `logger.warning`; status is echoed.
- No library calls `logger.error`, `print()` or Click; libraries log progress and warnings only.
- Every command reports failures with `logger.error` on stderr.

Not followed:

- `generate-schedule` prints nothing to stdout. The names of the three files it writes appear only in the stderr progress log ("Generated N games -> ..."), so `athc generate-schedule ... > out.txt` captures nothing. The other file-writing commands (`profile copy`, `gameplan set-normals`, `set-specials`, `replace-play`) echo an "Updated ..." line per file plus a summary to stdout.
- `convert-pdb` likewise prints nothing to stdout; its "Conversion complete" line comes from the `pdbtoexcel` library on stderr.
- 15 commands each call `logging.basicConfig(level=INFO, format="%(levelname)s: %(message)s")` instead of one setup in `cli()`: autocontinue, check-ppp, convert-pdb, generate-schedule, gameplan check / find-play / list-normals / list-specials / replace-play / set-normals / set-specials, playpool check, profile check / copy / diff. `cli()` installs no handler; only `main()`'s unexpected-error backstop calls `basicConfig(level=ERROR)`. Output is uncolored and the setup is duplicated 15 times.
- `-q/--quiet` exists only on `gameplan set-normals`.

## The fix

1. `generate-schedule`: echo the three output file names and the seed to stdout as the success line. `convert-pdb`: echo the workbook path.
2. Wire logging once in `cli()`: `RichHandler` on stderr, `click.style` for stdout status; delete the 15 per-command `basicConfig` calls. (Today a 2.0.0 TODO item; pull it into 1.0.0.)
3. Decide whether every file-writing command gets `-q/--quiet`, then add it where chosen.
4. Remove the "Not yet as designed" note from [architecture.md](../architecture.md#output-streams) once done.
