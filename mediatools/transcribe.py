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
import importlib
import json
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

import click
import ffmpeg

from .lib import filesystem as fs
from .lib import spawn

DEFAULT_BACKEND = "openai"

_LOGGER = logging.getLogger(__name__)

_BACKENDS = {}


@dataclasses.dataclass
class Transcription:
    text: str
    segments: list[Segment] | None = None
    language: str | None = None

    @classmethod
    def fromjson(cls, text) -> Transcription:
        raise NotImplementedError()

    def __str__(self) -> str:
        return self.text

    def json(self) -> str:
        if self.segments is None:
            segments = None
        else:
            segments = [dataclasses.asdict(x) for x in self.segments]

        return json.dumps(
            dict(text=self.text, segments=segments, language=self.language)
        )

    def srt(self) -> str:
        def fmt(ts):
            hh = int(ts // 3600)
            mm = int((ts - (hh * 3600)) // 60)
            ss = int(ts // 1 % 60)
            xx = int(ts % 1 * 1000 // 1)

            return f"{hh:02}:{mm:02}:{ss:02},{xx:03}"

        lines = []
        for idx, s in enumerate(self.segments or []):
            start = fmt(s.start)
            end = fmt(s.end)

            lines.extend([str(idx + 1), f"{start} --> {end}", s.text, "", ""])

        return "\n".join(lines)


@dataclasses.dataclass
class Segment:
    start: float
    end: float
    text: str


def _transcribe_with_openai(file: Path, *, model: str = "medium") -> Transcription:
    import openai  # Already loaded, but fixes linter warnings

    if api_base := os.environ.get("OPENAI_API_BASE", ""):
        openai.api_base = api_base

    if api_key := os.environ.get("OPENAI_API_KEY", ""):
        openai.api_key = api_key

    with fs.temp_dirpath() as tmpd:
        wav = tmpd / "transcribe.m4a"

        (
            ffmpeg.input(file.as_posix())
            .audio.output(wav.as_posix(), format="mp4")
            .overwrite_output()
            .run()
        )

        with open(wav, "rb") as fh:
            resp = openai.Audio.transcribe("whisper-1", fh)

        return Transcription(
            text=resp["text"].strip(),
            segments=[
                Segment(start=x["start"], end=x["end"], text=x["text"].strip())
                for x in resp["segments"]
            ],
            language=resp.get("language"),
        )


def _transcribe_with_whisper_py(
    file: Path,
    *,
    model_name: str | None = os.environ.get("WHISPER_MODEL"),
    language: str | None = os.environ.get("WHISPER_LANGUAGE", None),
) -> Transcription:
    import whisper  # Already loaded, but fixes linter warnings

    if not model_name:
        raise ValueError("model not defined")

    _LOGGER.debug(f"whisper model: {model_name}")
    _LOGGER.debug(f"whisper language: {language or 'auto'}")
    m = whisper.load_model(model_name)

    with fs.temp_dirpath() as tmpd:
        wav = tmpd / "audio.wav"
        (
            ffmpeg.input(file.as_posix())
            .output(wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000)
            .overwrite_output()
            .run(quiet=True)
        )
        res = m.transcribe(file.as_posix(), language=language)

        return Transcription(
            text=res["text"].strip(),
            segments=[
                Segment(start=x["start"], end=x["end"], text=x["text"].strip())
                for x in res["segments"]
            ],
            language=res.get("language"),
        )


def _transcribe_with_whisper_cpp(
    file: Path,
    *,
    model_filepath: str | Path | None = os.environ.get("WHISPER_MODEL"),
    language: str | None = os.environ.get("WHISPER_LANGUAGE", "auto"),
) -> str:
    if isinstance(model_filepath, Path):
        model_filepath = model_filepath.as_posix()

    if not model_filepath:
        raise ValueError("model not defined")

    _LOGGER.debug(f"whisper.cpp model: {model_filepath}")
    _LOGGER.debug(f"whisper.cpp language: {language}")

    with fs.temp_dirpath() as tmpd:
        base = tmpd / "transcribe"
        wav = tmpd / "transcribe.wav"
        srt = tmpd / "transcribe.srt"

        (
            ffmpeg.input(file.as_posix())
            .output(wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000)
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
                model_filepath,
                wav.as_posix(),
            ]
        )

        return srt.read_text()


def _try_load_backend(module_name: str, backend_name: str, fn: Callable) -> bool:
    global _BACKENDS

    try:
        importlib.import_module(module_name)
    except ImportError:
        _LOGGER.warning(
            f"{module_name} not installed, backend '{backend_name}' not available"
        )
        return False

    _BACKENDS[backend_name] = fn
    return True


def transcribe(
    file: Path, *, backend: str | None = DEFAULT_BACKEND, **kwargs
) -> Transcription:
    backend = backend or DEFAULT_BACKEND
    return _BACKENDS[backend](file, **kwargs)


@click.command("transcribe")
@click.option("--backend", type=str)
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def transcribe_cmd(
    targets: list[Path],
    backend: str,
    overwrite: bool = False,
    recursive: bool = False,
):
    for file in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        mime = fs.file_mime(file)
        if not mime.startswith("video/") and not mime.startswith("audio/"):
            click.echo(f"{file}: not a media file", err=True)
            continue

        transcription = transcribe(file, backend=backend)
        dest = fs.change_file_extension(file, "srt")
        if dest.exists() and not overwrite:
            click.echo(f"{dest}: already exists")
            continue

        dest.write_text(transcription.srt())


_try_load_backend("openai", "openai", _transcribe_with_openai)
_try_load_backend("whisper", "whisper", _transcribe_with_whisper_py)


if __name__ == "__main__":
    sys.exit(transcribe_cmd())
