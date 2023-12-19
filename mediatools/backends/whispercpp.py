#!/usr/bin/env python3

# Copyright (C) 2022- Luis López <luis@cuarentaydos.com>
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

import io
import logging
import os
from pathlib import Path

import ffmpeg
import pysrt

from ..lib import filesystem as fs
from ..lib import spawn
from . import Segment, Transcription, Transcriptor

LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL = "medium"


def _model_name_to_path(name: str) -> Path:
    # whisperpy saves models in ~/.cache even in macOS
    return Path(os.path.expanduser(f"~/.cache/whisper/{name}.pt"))


class WhisperCpp(Transcriptor):
    def __init__(
        self,
        model_filepath: Path
        | None = _model_name_to_path(os.environ.get("WHISPER_MODEL", DEFAULT_MODEL)),
    ) -> None:
        if model_filepath is None:
            raise ValueError("whisper model not defined")

        elif not model_filepath.exists():
            raise ValueError(f"whisper model '{model_filepath}' not found")

        self.model_filepath = model_filepath

    def transcribe(  # type: ignore[override]
        self,
        file: Path,
        *,
        language: str | None = os.environ.get("WHISPER_LANGUAGE", "auto"),
    ) -> Transcription:
        language = language or "auto"
        with fs.temp_dirpath_ctx() as tmpd:
            base = tmpd / "transcribe"
            wav = tmpd / "transcribe.wav"
            srt = tmpd / "transcribe.srt"

            LOGGER.debug(f"whisper.cpp model: {self.model_filepath}")
            LOGGER.debug(f"whisper.cpp language: {language}")

            (
                ffmpeg.input(file.as_posix())
                .output(
                    wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000
                )
                .overwrite_output()
                .run(quiet=True)
            )

            spawn.run(
                [
                    "whisper.cpp",
                    "-l",
                    language,
                    "--output-srt",
                    "-of",
                    base.as_posix(),
                    "-m",
                    self.model_filepath.as_posix(),
                    wav.as_posix(),
                ]
            )

            return SrtFmt.loads(srt.read_text())


class SrtFmt:
    @staticmethod
    def loads(text) -> Transcription:
        sub = pysrt.from_string(text)
        segments = [
            Segment(start=x.start.ordinal, end=x.end.ordinal, text=x.text) for x in sub
        ]
        text = "".join([x.text for x in sub]).strip()

        return Transcription(text=text, segments=segments)

    @staticmethod
    def dumps(transcription: Transcription) -> str:
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
