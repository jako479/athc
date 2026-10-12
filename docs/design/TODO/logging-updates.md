# Proposal — logging updates

Status: idea for later; nothing implemented.

## Why

Some messages read like config-file syntax instead of plain words, unlike the messages next to them.

## How

Name the file and line number, then say the problem in plain words.

## Example

Old:

```text
WARN playpool.toml: [RolloutPass] exclude 'LA6XFL1R' is not in the play pool
```

New:

```text
WARN playpool.toml, line 14: the play LA6XFL1R excluded from Rollout Pass was not found in the play folder
```
