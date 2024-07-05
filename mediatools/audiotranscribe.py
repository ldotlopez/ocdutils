#!/usr/bin/env python3

# Copyright (C) 2022 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


from __future__ import annotations

import dataclasses
import io
import json
import logging
from pathlib import Path

import click
import pysrt

from .backends import (
    AudioSegment,
    AudioTranscription,
    AudioTranscriptor,
    BaseBackendFactory,
)
from .lib import filesystem as fs

LOGGER = logging.getLogger(__name__)


ENVIRON_KEY = "AUDIO_TRANSCRIPTOR"
DEFAULT_BACKEND = "openai"
BACKENDS = {
    "openai": "OpenAI",
    "whisper": "WhisperPy",
    "whispercpp": "WhisperCpp",
}


class SrtTimeFmt:
    @staticmethod
    def str_to_int(text: str) -> int:
        return pysrt.SubRipTime.from_string(text).ordinal

    @staticmethod
    def int_to_str(ms: int) -> str:
        return str(pysrt.SubRipTime.from_ordinal(ms))


class JSONFmt:
    @staticmethod
    def loads(text: str) -> AudioTranscription:
        data = json.loads(text)
        return AudioTranscription(
            text=data["text"],
            segments=[
                AudioSegment(start=s["start"], end=s["end"], text=s["text"])
                for s in data.get("segments", [])
            ],
            language=data.get("language", None),
        )

    @staticmethod
    def dumps(transcription: AudioTranscription) -> str:
        if transcription.segments is None:
            segments = None
        else:
            segments = [dataclasses.asdict(x) for x in transcription.segments]

        return json.dumps(
            dict(
                text=transcription.text,
                segments=segments,
                language=transcription.language,
            )
        )


class SrtFmt:
    @staticmethod
    def loads(text) -> AudioTranscription:
        sub = pysrt.from_string(text)
        segments = [
            AudioSegment(start=x.start.ordinal, end=x.end.ordinal, text=x.text)
            for x in sub
        ]
        text = "".join([x.text for x in sub]).strip()

        return AudioTranscription(text=text, segments=segments)

    @staticmethod
    def dumps(transcription: AudioTranscription) -> str:
        srt = pysrt.SubRipFile(
            items=[
                pysrt.SubRipItem(
                    index=idx + 1,
                    start=pysrt.SubRipTime.from_ordinal(s.start * 1000),
                    end=pysrt.SubRipTime.from_ordinal(s.end * 1000),
                    text=s.text,
                )
                for idx, s in enumerate(transcription.segments)
            ]
        )

        buff = io.StringIO()
        srt.write_into(buff)
        ret = buff.getvalue()
        buff.close()

        return ret


def AudioTranscriptorFactory(backend: str | None = None, **kwargs) -> AudioTranscriptor:
    return BaseBackendFactory(
        backend=backend, id=ENVIRON_KEY, map=BACKENDS, default=DEFAULT_BACKEND
    )(**kwargs)


def transcribe(
    file: Path, *, backend: str | None = DEFAULT_BACKEND, **kwargs
) -> AudioTranscription:
    return AudioTranscriptorFactory(backend=backend).transcribe(file, **kwargs)


@click.command("transcribe")
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--overwrite", "-f", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def transcribe_cmd(
    targets: list[Path],
    overwrite: bool = False,
    recursive: bool = False,
):
    tr = AudioTranscriptorFactory()

    for file in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        mime = fs.file_mime(file)
        if not mime.startswith("video/") and not mime.startswith("audio/"):
            click.echo(f"{file}: not a media file", err=True)
            continue

        dest = fs.change_file_extension(file, "srt")
        if dest.exists() and not overwrite:
            click.echo(f"{dest}: already exists")
            continue

        transcription = tr.transcribe(file)
        tr_srt = SrtFmt.dumps(transcription)

        dest.write_text(tr_srt)


def main(*args) -> int:
    return transcribe_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
