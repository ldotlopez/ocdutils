#! /bin/env python3

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


import base64
import contextlib
import logging
import os
from pathlib import Path
from typing import cast

import ffmpeg
import openai

from ..lib import filesystem as fs
from . import ImageDescriptor, Segment, Transcription, Transcriptor

LOGGER = logging.getLogger(__name__)


OPENAI_VISION_MODEL = os.environ.get("OPENAI_VISION_MODEL", "gpt-4-vision-preview")
OPENAI_VISION_PROMPT = os.environ.get("OPENAI_VISION_PROMPT", "What’s in this image?")
OPENAI_TRANSCRIPTION_MODEL = os.environ.get("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")


class OpenAI(ImageDescriptor, Transcriptor):
    @contextlib.contextmanager
    def custom_api(self):
        api_base = os.environ.get("OPENAI_API_BASE", "")
        api_key = os.environ.get("OPENAI_API_KEY", "")

        kwargs = {}
        if api_base:
            kwargs["base_url"] = api_base
        if api_key:
            kwargs["api_key"] = api_key

        yield openai.OpenAI(**kwargs)

    def describe(  # type: ignore[override]
        self,
        file: Path,
        *,
        model: str | None = OPENAI_VISION_MODEL,
        prompt: str | None = OPENAI_VISION_PROMPT,
    ) -> str:
        model = cast(str, model or OPENAI_VISION_MODEL)
        prompt = cast(str, prompt or OPENAI_VISION_PROMPT)

        with self.custom_api() as client:
            img = base64.b64encode(file.read_bytes()).decode("utf-8")
            LOGGER.warning(f"Asking '{model}' to describe image with '{prompt}'")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            return cast(str, response.choices[0].message.content or "").strip()

    def transcribe(self, file: Path, *, model: str | None = OPENAI_TRANSCRIPTION_MODEL) -> Transcription:  # type: ignore[override]
        model = model or OPENAI_TRANSCRIPTION_MODEL

        with fs.temp_dirpath() as tmpd:
            audio = tmpd / "transcribe.m4a"

            (
                ffmpeg.input(file.as_posix())
                .audio.output(audio.as_posix(), format="mp4")
                .overwrite_output()
                .run()
            )

            with self.custom_api() as client:
                resp = client.audio.transcriptions.create(
                    model=model, file=audio, response_format="verbose_json"
                )

            return Transcription(
                text=resp.text.strip(),
                segments=[
                    Segment(
                        start=x["start"] // 1_000_000_000,
                        end=x["end"] // 1_000_000_000,
                        text=x["text"].strip(),
                    )
                    for x in resp.segments or []
                ],
            )
