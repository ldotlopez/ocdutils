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

import ffmpeg
import openai

from ..lib import Segment, Transcription, Transcriptor
from ..lib import filesystem as fs

LOGGER = logging.getLogger(__name__)


class OpenAI(Transcriptor):
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

    def describe(
        self,
        contents: bytes,
        *,
        model: str | None = "gpt-4-vision-preview",
        prompt: str | None = "What’s in this image?",
    ) -> str:
        model = model or "gpt-4-vision-preview"
        prompt = prompt or "What’s in this image?"

        with self.custom_api() as client:
            img = base64.b64encode(contents).decode("utf-8")
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

            return response.choices[0].message.content.strip()

    def transcribe(self, file: Path, *, model: str | None = "whisper-1") -> Transcription:  # type: ignore[override]
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


class LocalAI(OpenAI):
    def describe(
        self,
        contents: bytes,
        *,
        model: str | None = "llava",
        prompt: None
        | (
            str
        ) = "What’s in this image? Be brief, it’s for image alt description on a social network. Don’t write in the first person.",
    ) -> str:
        model = model or "llava"
        prompt = (
            prompt
            or "What’s in this image? Be brief, it’s for image alt description on a social network. Don’t write in the first person."
        )

        return super().describe(contents, model=model, prompt=prompt)
