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

import json
import logging
import os
import sys
from math import log
from pathlib import Path

import click
import ffmpeg

from .lib import filesystem as fs
from .lib import spawn

_LOGGER = logging.getLogger(__name__)

DEFAULT_BACKEND = "whisper.cpp"


def _transcribe_with_openai(file: Path, *, model: str = "medium") -> str:
    with fs.temp_dirpath() as tmpd:
        base = tmpd / "transcribe"
        wav = tmpd / "transcribe.m4a"

        (
            ffmpeg.input(file.as_posix())
            .audio.output(wav.as_posix(), format="mp4")
            .overwrite_output()
            .run()
        )
        with open(wav, "rb") as fh:
            buff = openai.Audio.transcribe("whisper-1", fh)

        data = json.loads(buff)
        return data["text"]


def _transcribe_with_openai_cpp(file: Path, *, modelpath: Path | None = None) -> str:
    model = modelpath.as_posix() if modelpath else os.environ.get("WHISPER_MODEL_FILE")
    if not model:
        raise ValueError("model not defined")

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
                os.environ.get("WHISPER_LANGUAGE", "auto"),
                "--output-srt",
                "-of",
                base.as_posix(),
                "-m",
                model,
                wav.as_posix(),
            ]
        )

        return srt.read_text()


_BACKENDS = {}

try:
    import openai

    _BACKENDS["openai"] = _transcribe_with_openai
except ImportError:
    _LOGGER.warning("openai not installed, backend not available")


def transcribe(file: Path, *, backend: str | None = DEFAULT_BACKEND, **kwargs) -> str:
    backends = {
        "whisper.cpp": _transcribe_with_openai_cpp,
        "openai": _transcribe_with_openai,
    }

    return _BACKENDS[backend](file, **kwargs)


@click.command("transcribe")
@click.option("--backend", type=str, default=DEFAULT_BACKEND)
@click.option("--model", type=Path)
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def transcribe_cmd(
    targets: list[Path],
    model: Path,
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

        transcription = transcribe(file, backend=backend, model=model)
        dest = fs.change_file_extension(file, "srt")
        if dest.exists() and not overwrite:
            click.echo(f"{dest}: already exists")
            continue

        dest.write_text(transcription)


if __name__ == "__main__":
    sys.exit(transcribe_cmd())
