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
from . import (
    AudioSegment,
    AudioTranscription,
    AudioTranscriptor,
    EmbeddingsHandler,
    ImageDescriptor,
    ImageGenerator,
    TextCompletion,
)

if shutil.which("ffmpeg") is None:
    raise SystemError("ffmpeg not in PATH")


LOGGER = logging.getLogger(__name__)

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", None)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")
OPENAI_EMBEDDINGS_MODEL = os.environ.get(
    "OPENAI_EMBEDDINGS_MODEL", "mxbai-embed-large"  # "text-embedding-ada-002"
)
OPENAI_TRANSCRIPTION_LANGUAGE: str = os.environ.get("OPENAI_TRANSCRIPTION_LANGUAGE", "")
OPENAI_TRANSCRIPTION_MODEL: str = os.environ.get(
    "OPENAI_TRANSCRIPTION_MODEL", "whisper-1"
)
OPENAI_VISION_MODEL: str = os.environ.get("OPENAI_VISION_MODEL", "gpt-4-vision-preview")
OPENAI_VISION_PROMPT: str = os.environ.get(
    "OPENAI_VISION_PROMPT", "What is in the image?"
)

MAX_IMAGE_SIZE: int = int(os.environ.get("MEDIATOOLS_DESCRIBE_IMAGE_MAX_SIZE", "1024"))


class OpenAI(
    TextCompletion,
    ImageDescriptor,
    ImageGenerator,
    AudioTranscriptor,
    EmbeddingsHandler,
):
    @contextlib.contextmanager
    def custom_api(self):
        kwargs = {}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        if OPENAI_API_KEY:
            kwargs["api_key"] = OPENAI_API_KEY

        yield openai.OpenAI(**kwargs)

    def complete_chat(
        self, text: str, *, system: str | None, model: str = OPENAI_CHAT_MODEL
    ) -> str:
        system_msg = [{"role": "system", "content": system}] if system else []
        user_msg = [{"role": "user", "content": text}]

        with self.custom_api() as client:
            resp = client.chat.completions.create(
                model=model, messages=system_msg + user_msg
            )

        return resp.choices[0].message.content.strip()

    def get_embeddings_as_response(
        self, text: str
    ) -> openai.types.create_embedding_response.CreateEmbeddingResponse:
        with self.custom_api() as client:
            return client.embeddings.create(input=text, model=OPENAI_EMBEDDINGS_MODEL)

    def get_embeddings(self, text: str) -> list[float]:
        resp = self.get_embeddings_as_response(text)
        return resp.data[0].embedding

    def generate_image(self, prompt: str) -> bytes:
        with self.custom_api() as client:
            response = client.images.generate(
                prompt=prompt,
                response_format="b64_json",
                n=1,
            )

            return base64.b64decode(response.data[0].base64_json)

    def describe_image(  # type: ignore[override]
        self,
        file: Path,
        *,
        model: str | None = OPENAI_VISION_MODEL,
        prompt: str | None = OPENAI_VISION_PROMPT,
    ) -> str:
        model = model or OPENAI_VISION_MODEL
        prompt = prompt or OPENAI_VISION_PROMPT

        rawimg = file.read_bytes()

        with Image.open(io.BytesIO(rawimg)) as img:
            if max(img.size) > MAX_IMAGE_SIZE:
                ratio = MAX_IMAGE_SIZE / max(img.size)
                new_size = (round(img.size[0] * ratio), round(img.size[1] * ratio))

                img = img.resize(new_size)
                bs = io.BytesIO()
                img.save(bs, format="PNG")
                rawimg = bs.getvalue()

                LOGGER.debug(f"{file}: image resized to {new_size!r}")

        with self.custom_api() as client:
            b64img = base64.b64encode(rawimg).decode("utf-8")
            LOGGER.info(f"{file} model='{model}', prompt='{prompt}'")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64img}"},
                        },
                    ],
                }
            ]

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,  # temperature": 0.9
            )

            return cast(str, response.choices[0].message.content or "").strip()

    def transcribe_audio(  # type: ignore[override]
        self,
        file: Path,
        *,
        model: str = OPENAI_TRANSCRIPTION_MODEL,
        language: str = OPENAI_TRANSCRIPTION_LANGUAGE,
    ) -> AudioTranscription:
        with fs.temp_dirpath() as tmpd:
            audio = tmpd / "transcribe.m4a"
            (
                ffmpeg.input(file.as_posix())
                .audio.output(audio.as_posix(), format="mp4")
                .overwrite_output()
                .global_args("-hide_banner", "-loglevel", "warning")
                .run()
            )

            with self.custom_api() as client:
                resp = client.audio.transcriptions.create(
                    model=model,
                    file=audio,
                    language=language or "",
                    response_format="verbose_json",
                )

            return AudioTranscription(
                text=resp.text.strip(),
                segments=[
                    AudioSegment(
                        start=x["start"] // 1_000_000_000,
                        end=x["end"] // 1_000_000_000,
                        text=x["text"].strip(),
                    )
                    for x in resp.segments or []
                ],
            )
