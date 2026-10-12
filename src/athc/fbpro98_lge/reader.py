"""Parse FbPro98 .lge league files into LgeFile objects. See specs/lge.md."""

from __future__ import annotations

from itertools import islice
from os import PathLike
from pathlib import Path

from athc.errors import FileFormatError
from athc.fbpro98_lge.model import Conference, Division, LgeFile, Record, Team
from athc.fbpro98_lge.schema import (
    CHUNK_HEADER,
    CONFERENCE_BASE_SIZE,
    CONFERENCE_DIVISIONS_OFFSET,
    CONFERENCE_NAME_OFFSET,
    DIVISION_BASE_SIZE,
    DIVISION_NAME_OFFSET,
    DIVISION_TEAMS_OFFSET,
    GAME,
    GAME_PLAYED,
    ID_C03,
    ID_D03,
    ID_L03,
    ID_R03,
    ID_S03,
    ID_T03,
    LEAGUE_BASE_SIZE,
    LEAGUE_CONFERENCES_OFFSET,
    MASK_FACTOR,
    NAME_SIZE,
    NICKNAME_OFFSET,
    ROSTER_CHUNK_SIZE,
    SCHEDULE_HEADER_SIZE,
    SCHEDULE_PLAYOFF_ROUNDS_OFFSET,
    SCHEDULE_REGULAR_WEEKS_OFFSET,
    TEAM_CHUNK_SIZE,
    TEAM_NAME_OFFSET,
    TEAM_TEXT_SIZE,
)

StrPath = str | PathLike[str]

# A conference's name and its divisions' names and team counts, in file order.
_Heads = list[tuple[str, list[tuple[str, int]]]]


class InvalidLgeError(FileFormatError):
    """Raised when a `.lge` file is structurally invalid."""


def read_lge(league: str, league_dir: StrPath) -> LgeFile:
    """Read and parse a league's .lge file from disk.

    Args:
        league: League name; the file read is `<league>.lge`.
        league_dir: Folder holding the league's files.

    Returns:
        Parsed LgeFile.

    Raises:
        InvalidLgeError: If the file is empty; a chunk is cut short, missing,
            out of order or the wrong size; the schedule is cut short or
            followed by data; or a played game names an unknown team.
        OSError: If the file cannot be opened or read.
    """
    file_path = Path(league_dir) / f"{league}.lge"
    return parse_lge(file_path.read_bytes(), file_path)


def parse_lge(buffer: bytes, path: StrPath = "<buffer>") -> LgeFile:
    """Parse a .lge league file from raw bytes.

    Args:
        buffer: Full contents of a .lge file.
        path: Path used only in error messages. Defaults to "<buffer>" when
            parsing data that did not come from disk.

    Returns:
        Parsed LgeFile.

    Raises:
        InvalidLgeError: If the buffer is empty; a chunk is cut short, missing,
            out of order or the wrong size; the schedule is cut short or
            followed by data; or a played game names an unknown team.
    """
    file_path = Path(path)
    if not buffer:
        raise InvalidLgeError("Empty file.", file_path)
    chunks = _Chunks(buffer, file_path)
    _, conference_count = chunks.take_counted(
        ID_L03, LEAGUE_BASE_SIZE, LEAGUE_CONFERENCES_OFFSET
    )
    walk = _walk_grouped if chunks.grouped() else _walk_nested
    heads, names = walk(chunks, conference_count)
    # Required after the tree, so a tree with more conferences, divisions or
    # teams than its counts say fails here.
    records = _read_schedule(chunks, len(names))
    chunks.finish()
    return LgeFile(conferences=_build(heads, names, records))


def _walk_nested(
    chunks: _Chunks, conference_count: int
) -> tuple[_Heads, list[tuple[str, str]]]:
    # Each conference, then its divisions, each followed by its teams, each
    # followed by its roster.
    heads: _Heads = []
    names: list[tuple[str, str]] = []
    for _ in range(conference_count):
        name, division_count = _take_conference(chunks)
        divisions: list[tuple[str, int]] = []
        for _ in range(division_count):
            division_name, team_count = _take_division(chunks)
            divisions.append((division_name, team_count))
            for _ in range(team_count):
                names.append(_take_team(chunks))
                _take_roster(chunks)
        heads.append((name, divisions))
    return heads, names


def _walk_grouped(
    chunks: _Chunks, conference_count: int
) -> tuple[_Heads, list[tuple[str, str]]]:
    # Every conference, then every division, team and roster, in the same order
    # as a nested file; the counts nest them.
    conferences = [_take_conference(chunks) for _ in range(conference_count)]
    division_count = sum(count for _, count in conferences)
    divisions = iter([_take_division(chunks) for _ in range(division_count)])
    heads = [(name, list(islice(divisions, count))) for name, count in conferences]
    team_count = sum(count for _, division in heads for _, count in division)
    names = [_take_team(chunks) for _ in range(team_count)]
    for _ in range(team_count):
        _take_roster(chunks)
    return heads, names


def _read_schedule(chunks: _Chunks, team_count: int) -> list[Record]:
    offset = chunks.offset
    data = chunks.take(ID_S03)
    label = f"S03 chunk at {offset:#x}"
    if len(data) < SCHEDULE_HEADER_SIZE:
        raise chunks.error(
            f"{label} is {len(data)} bytes, expected at least {SCHEDULE_HEADER_SIZE}."
        )
    regular_weeks = data[SCHEDULE_REGULAR_WEEKS_OFFSET]
    weeks = regular_weeks + data[SCHEDULE_PLAYOFF_ROUNDS_OFFSET]
    # One (scored, allowed) pair per played game, by team number - 1.
    scores: list[list[tuple[int, int]]] = [[] for _ in range(team_count)]
    position = SCHEDULE_HEADER_SIZE
    for week in range(1, weeks + 1):
        if position == len(data):
            raise chunks.error(f"{label} is cut short in week {week}.")
        end = position + 1 + data[position] * GAME.size
        if end > len(data):
            raise chunks.error(f"{label} is cut short in week {week}.")
        # Playoff games never count; unplayed ones may not name their teams yet.
        if week <= regular_weeks:
            games = GAME.iter_unpack(data[position + 1 : end])
            for home, home_score, away, away_score, _, status in games:
                if status != GAME_PLAYED:
                    continue
                for number in (home, away):
                    if not 1 <= number <= team_count:
                        raise chunks.error(
                            f"{label}, week {week}: No team {number} "
                            f"(teams are 1-{team_count})."
                        )
                scores[home - 1].append((home_score, away_score))
                scores[away - 1].append((away_score, home_score))
        position = end
    if position != len(data):
        raise chunks.error(f"{label} has data after the last week.")
    return [_record(team_scores) for team_scores in scores]


def _record(scores: list[tuple[int, int]]) -> Record:
    return Record(
        wins=sum(scored > allowed for scored, allowed in scores),
        losses=sum(scored < allowed for scored, allowed in scores),
        ties=sum(scored == allowed for scored, allowed in scores),
        points_for=sum(scored for scored, _ in scores),
        points_against=sum(allowed for _, allowed in scores),
    )


def _build(
    heads: _Heads, names: list[tuple[str, str]], records: list[Record]
) -> tuple[Conference, ...]:
    # Teams are numbered 1..N in file order, the numbers the schedule uses.
    teams = iter(
        Team(name=name, nickname=nickname, record=record)
        for (name, nickname), record in zip(names, records, strict=True)
    )
    return tuple(
        Conference(
            name=name,
            divisions=tuple(
                Division(name=division_name, teams=tuple(islice(teams, count)))
                for division_name, count in divisions
            ),
        )
        for name, divisions in heads
    )


def _take_conference(chunks: _Chunks) -> tuple[str, int]:
    data, division_count = chunks.take_counted(
        ID_C03, CONFERENCE_BASE_SIZE, CONFERENCE_DIVISIONS_OFFSET
    )
    return _read_text(data, CONFERENCE_NAME_OFFSET, NAME_SIZE), division_count


def _take_division(chunks: _Chunks) -> tuple[str, int]:
    data, team_count = chunks.take_counted(
        ID_D03, DIVISION_BASE_SIZE, DIVISION_TEAMS_OFFSET
    )
    return _read_text(data, DIVISION_NAME_OFFSET, NAME_SIZE), team_count


def _take_team(chunks: _Chunks) -> tuple[str, str]:
    # The team name and nickname.
    data = chunks.take(ID_T03, TEAM_CHUNK_SIZE)
    # Byte 0 is the team number, in clear; it keys the mask on the rest.
    fields = _unmask(data[0], data[1:])
    return (
        _read_text(fields, TEAM_NAME_OFFSET, TEAM_TEXT_SIZE),
        _read_text(fields, NICKNAME_OFFSET, TEAM_TEXT_SIZE),
    )


def _take_roster(chunks: _Chunks) -> None:
    # Every team has a roster; it is not read.
    chunks.take(ID_R03, ROSTER_CHUNK_SIZE)


def _unmask(team: int, data: bytes) -> bytes:
    return bytes(
        byte ^ ((MASK_FACTOR * team + index) & 0xFF) for index, byte in enumerate(data)
    )


def _read_text(data: bytes, offset: int, size: int) -> str:
    # Text after the NUL is left over from an earlier, longer value; a name
    # that fills its field has no NUL.
    field = data[offset : offset + size]
    end = field.find(b"\x00")
    return field[: size if end == -1 else end].decode("ASCII", errors="replace")


def _tag_name(tag: bytes) -> str:
    # Printable ASCII shows as text, without a trailing colon; anything else,
    # from a file that is not a .lge, shows as hex.
    text = tag.decode("latin-1")
    if tag.isascii() and text.isprintable():
        return text.removesuffix(":")
    return tag.hex(" ")


class _Chunks:
    """Hands out the file's chunks in order, checking each tag and size."""

    def __init__(self, buffer: bytes, path: Path) -> None:
        self._buffer = buffer
        self._path = path
        self._offset = 0

    @property
    def offset(self) -> int:
        """Where the next chunk starts."""
        return self._offset

    def take(self, tag: bytes, size: int | None = None) -> bytes:
        """The next chunk's data. The chunk must carry `tag` and, when `size`
        is given, hold exactly that many bytes."""
        offset = self._offset
        data = self._next(tag)
        if size is not None:
            self._check_size(tag, offset, data, size)
        return data

    def take_counted(
        self, tag: bytes, base_size: int, count_offset: int
    ) -> tuple[bytes, int]:
        """The next chunk's data and child count: a fixed part of `base_size`
        bytes, holding the count at `count_offset`, then one id byte per
        child."""
        offset = self._offset
        data = self._next(tag)
        if len(data) < base_size:
            raise self.error(
                f"{_tag_name(tag)} chunk at {offset:#x} is {len(data)} bytes, "
                f"expected at least {base_size}."
            )
        count = data[count_offset]
        self._check_size(tag, offset, data, base_size + count)
        return data, count

    def grouped(self) -> bool:
        """Whether the chunks ahead are grouped by kind (every T03, then every
        R03) rather than nested (each T03 followed by its R03): the first T03
        is followed by another T03. The scan stops at a chunk cut short; the
        walk reports it."""
        offset = self._offset
        previous = b""
        while offset + CHUNK_HEADER.size <= len(self._buffer):
            tag, size = CHUNK_HEADER.unpack_from(self._buffer, offset)
            if previous == ID_T03:
                return tag == ID_T03
            previous = tag
            offset += CHUNK_HEADER.size + size
        return False

    def finish(self) -> None:
        """Fail if anything follows the last chunk taken."""
        if self._offset != len(self._buffer):
            raise self.error(
                f"Unexpected data at {self._offset:#x} after the S03 chunk."
            )

    def _next(self, tag: bytes) -> bytes:
        offset = self._offset
        buffer = self._buffer
        if offset == len(buffer):
            raise self.error(
                f"Expected {_tag_name(tag)} chunk at {offset:#x}, "
                "found the end of the file."
            )
        if offset + CHUNK_HEADER.size > len(buffer):
            raise self.error(f"Chunk header at {offset:#x} is cut short.")
        found, size = CHUNK_HEADER.unpack_from(buffer, offset)
        if found != tag:
            raise self.error(
                f"Expected {_tag_name(tag)} chunk at {offset:#x}, "
                f"found {_tag_name(found)}."
            )
        start = offset + CHUNK_HEADER.size
        end = start + size
        if end > len(buffer):
            raise self.error(
                f"{_tag_name(tag)} chunk at {offset:#x} runs past the end of the file."
            )
        self._offset = end
        return buffer[start:end]

    def _check_size(self, tag: bytes, offset: int, data: bytes, size: int) -> None:
        if len(data) != size:
            raise self.error(
                f"{_tag_name(tag)} chunk at {offset:#x} is {len(data)} bytes, "
                f"expected {size}."
            )

    def error(self, reason: str) -> InvalidLgeError:
        """The error to raise for `reason`, naming the file."""
        return InvalidLgeError(reason, self._path)
