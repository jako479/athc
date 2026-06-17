# Schedule file format

The text format the game's schedule-import tool reads, and what `generate-schedule`'s
`txt` writer emits. [2048 Schedule.txt](2048%20Schedule.txt) is a full example.

```
Week 1
Los Angeles#Buffalo
Denver#Minnesota
...
Seattle#Chicago
Week 2
New England#Buffalo
...
```

- A `Week <n>` line starts each week; the lines under it are that week's games. Weeks
  ascend, no blank lines between them.
- Each game is `away#home` — visitor left, host right, one `#`. Team names are exact and
  may contain spaces.
- Game order within a week doesn't matter.
- UTF-8, LF line endings, one trailing newline.

Games per week isn't fixed: each team plays at most once a week, so it's `teams / 2`
(fewer in a week where a team has a bye). The importer reads however many lines a week
has.
