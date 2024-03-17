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
import shutil
from pathlib import Path
from typing import cast

import ffmpeg
import openai
from PIL import Image

from ..lib import filesystem as fs
from . import ImageDescriptor, Segment, TextCompletion, Transcription, Transcriptor

if shutil.which("ffmpeg") is None:
    raise SystemError("ffmpeg not in PATH")


LOGGER = logging.getLogger(__name__)

OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")


OPENAI_VISION_MODEL: str = os.environ.get("OPENAI_VISION_MODEL", "gpt-4-vision-preview")
OPENAI_VISION_PROMPT: str = os.environ.get(
    "OPENAI_VISION_PROMPT", "What’s in this image?"
)
OPENAI_TRANSCRIPTION_MODEL: str = os.environ.get(
    "OPENAI_TRANSCRIPTION_MODEL", "whisper-1"
)
OPENAI_TRANSCRIPTION_LANGUAGE: str = os.environ.get("OPENAI_TRANSCRIPTION_LANGUAGE", "")


MAX_IMAGE_SIZE: int = int(os.environ.get("MEDIATOOLS_DESCRIBE_IMAGE_MAX_SIZE", "1024"))

API_BASE = os.environ.get("OPENAI_API_BASE", "")
API_KEY = os.environ.get("OPENAI_API_KEY", "")


class OpenAI(TextCompletion, ImageDescriptor, Transcriptor):
    @contextlib.contextmanager
    def custom_api(self):
        kwargs = {}
        if API_BASE:
            kwargs["base_url"] = API_BASE
        if API_KEY:
            kwargs["api_key"] = API_KEY

        yield openai.OpenAI(**kwargs)

    def complete(
        self, system: str, text: str, *, model: str = OPENAI_CHAT_MODEL
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
        model: str = OPENAI_VISION_MODEL,
        prompt: str = OPENAI_VISION_PROMPT,
    ) -> str:
        rawimg = file.read_bytes()

        with Image.open(io.BytesIO(rawimg)) as img:
            if max(img.size) > MAX_IMAGE_SIZE:
                ratio = MAX_IMAGE_SIZE / max(img.size)
                new_size = (round(img.size[0] * ratio), round(img.size[1] * ratio))

                img = img.resize(new_size)
                bs = io.BytesIO()
                img.save(bs, format="PNG")
                rawimg = bs.getvalue()

                LOGGER.info(f"image resized to {new_size!r}")

        with self.custom_api() as client:
            b64img = base64.b64encode(rawimg).decode("utf-8")
            LOGGER.info(f"Asking '{model}' to describe image with '{prompt}'")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64img}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            return cast(str, response.choices[0].message.content or "").strip()

    def transcribe(self, file: Path, *, model: str = OPENAI_TRANSCRIPTION_MODEL, language: str = OPENAI_TRANSCRIPTION_LANGUAGE) -> Transcription:  # type: ignore[override]
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
                    model=model,
                    file=audio,
                    language=language or "",
                    response_format="verbose_json",
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
