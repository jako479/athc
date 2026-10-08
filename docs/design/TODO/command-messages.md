# Command messages

Design for the TODO item. Done when every command in the release docs lists
its messages; then delete this file.

## Need

- The release docs don't say what each command prints, or what a warning or
  error means and what to do about it.
- Only the general rule is written down ([architecture.md](../architecture.md#output-streams)); nothing
  per command.

## What to document, per command

In `config/release/docs/COMMANDS.txt`, a short "Messages" part for each command:

- What it prints: report lines, the summary, status lines.
- Each error or warning it can show: what it means, what to do.
- Problems shown as report lines instead (like a file that can't be read).
- What it skips without a message.
- Its exit codes.

## Work

- Collect each command's messages from its code.
- Add the "Messages" part to each command in `COMMANDS.txt`.
- Delete this file.
