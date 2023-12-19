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
import io
import logging
import os
from pathlib import Path
from typing import cast

import ffmpeg
import openai
from PIL import Image

from ..lib import filesystem as fs
from . import ImageDescriptor, Segment, TextCompletion, Transcription, Transcriptor

LOGGER = logging.getLogger(__name__)

OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")


OPENAI_VISION_MODEL: str = os.environ.get("OPENAI_VISION_MODEL", "gpt-4-vision-preview")
OPENAI_VISION_PROMPT: str = os.environ.get(
    "OPENAI_VISION_PROMPT", "What’s in this image?"
)
OPENAI_TRANSCRIPTION_MODEL: str = os.environ.get(
    "OPENAI_TRANSCRIPTION_MODEL", "whisper-1"
)


MAX_IMAGE_SIZE: int = int(os.environ.get("MEDIATOOLS_DESCRIBE_IMAGE_MAX_SIZE", "1024"))


class OpenAI(TextCompletion, ImageDescriptor, Transcriptor):
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

    def complete(
        self, system: str, text: str, *, model: str | None = OPENAI_CHAT_MODEL
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ]

        with self.custom_api() as client:
            resp = client.chat.completions.create(model=model, messages=messages)

        return resp.choices[0].message.content.strip()

    def describe(  # type: ignore[override]
        self,
        file: Path,
        *,
        model: str | None = OPENAI_VISION_MODEL,
        prompt: str | None = OPENAI_VISION_PROMPT,
    ) -> str:
        model = cast(str, model or OPENAI_VISION_MODEL)
        prompt = cast(str, prompt or OPENAI_VISION_PROMPT)

        contents = file.read_bytes()
        with Image.open(io.BytesIO(contents)) as img:
            if max(img.size) > MAX_IMAGE_SIZE:
                ratio = MAX_IMAGE_SIZE / max(img.size)
                new_size = (round(img.size[0] * ratio), round(img.size[1] * ratio))

                img = img.resize(new_size)
                bs = io.BytesIO()
                img.save(bs, format="PNG")
                contents = bs.getvalue()

                LOGGER.info(f"image resizeed to {new_size!r}")

        with self.custom_api() as client:
            img = base64.b64encode(contents).decode("utf-8")
            LOGGER.debug(f"Asking '{model}' to describe image with '{prompt}'")

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