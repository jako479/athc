# fbpro98-play

Library for parsing Front Page Sports Football Pro '98 play (`.ply`) files.

## Features

- `.ply` parser
- Play / special / user category
- Player offsets and headers
- Game category name resolution

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_play import read_play

play_file = read_play("some_play.ply")
print(play_file.play_category)
print(play_file.special_category)
print(play_file.user_category)
print(play_file.player_offsets[0])
print(play_file.player_headers[0].position)
```

## API

- `read_play(path)` reads a `.ply` and returns a `PlayFile`; `parse_play(buffer, path)` parses raw bytes, `path` only naming the source in errors.
- `PlayFile`: `file_path`, `stream_length`, `player_offsets`, `player_headers`, `play_category`, `special_category`, `user_category`; `is_offensive` / `is_defensive` / `is_special_teams`; `category` (a category enum member, `UNKNOWN_CATEGORY` when unrecognized) and `category_name`.
- `PlayerHeader`: `offset`, `rank`, `player_type`, `position`.
- Categories: `OffensiveCategory`, `DefensiveCategory`, `SpecialOffensiveCategory`, `SpecialDefensiveCategory`; each member has `code`, `short`, `long`, `is_run`, `is_pass`. `resolve_category(play_category, special_category, user_category)` names one from raw bytes; `category_by_short(short)` looks one up by league label.
- `InvalidPlayFileError`: a bad block ID, a size field that doesn't match the file length, or a file too short for the category bytes or a player header. `read_play` also raises it for an unrecognized category, where `parse_play` returns a file whose `category` is `UNKNOWN_CATEGORY`.

## Testing

```bash
pytest
```
