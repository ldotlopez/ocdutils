from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class Transcription:
    text: str
    segments: list[Segment] = dataclasses.field(default_factory=lambda: [])
    language: str | None = None


@dataclasses.dataclass
class Segment:
    start: int
    end: int
    text: str
