# fbpro98-play

Library for parsing Front Page Sports Football Pro '98 play (`.ply`) files.

## Features

- `.ply` parser
- Play / special / user category
- Player offsets and headers
- Game category name resolution

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
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

## Testing

```bash
pytest
```
