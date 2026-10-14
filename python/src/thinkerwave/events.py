from __future__ import annotations  # lazy annotations

from typing import Iterable, Iterator, Optional


def parse_sse(lines: Iterable[str]) -> Iterator[tuple[Optional[str], str, str]]:
    """Yield (id, event, data) per SSE message; comments (": …") are ignored."""
    eid: Optional[str] = None
    name = "message"
    data: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r")
        if line == "":
            if data:
                yield eid, name, "\n".join(data)
            eid, name, data = None, "message", []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if field == "id":
            eid = value
        elif field == "event":
            name = value
        elif field == "data":
            data.append(value)
    if data:
        yield eid, name, "\n".join(data)
