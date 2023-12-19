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


import os
import shutil
from pathlib import Path

import ffmpeg
import whisper

from ..lib import filesystem as fs
from . import Segment, Transcription, Transcriptor

if shutil.which("ffmpeg") is None:
    raise SystemError("ffmpeg not in PATH")


DEFAULT_MODEL = "medium"


class WhisperPy(Transcriptor):
    def __init__(
        self, *, model_name: str | None = os.environ.get("WHISPER_MODEL", DEFAULT_MODEL)
    ) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = whisper.load_model(self.model_name)

        return self._model

    def transcribe(  # type: ignore[override]
        self,
        file: Path,
        *,
        language: str | None = os.environ.get("WHISPER_LANGUAGE", None),
    ) -> Transcription:
        with fs.temp_dirpath_ctx() as tmpd:
            wav = tmpd / "audio.wav"
            (
                ffmpeg.input(file.as_posix())
                .output(
                    wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000
                )
                .overwrite_output()
                .run(quiet=True)
            )
            res = self.model.transcribe(file.as_posix(), language=language)

            return Transcription(
                text=res["text"].strip(),
                segments=[
                    Segment(start=x["start"], end=x["end"], text=x["text"].strip())
                    for x in res["segments"]
                ],
                language=res.get("language"),
            )
