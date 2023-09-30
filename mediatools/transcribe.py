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

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

import click

from .lib import filesystem as fs
from .lib import spawn

_LOGGER = logging.getLogger(__name__)


def _transcribe_with_whisper_cpp(file: Path, *, model: Path):
    tmpd = Path(tempfile.mkdtemp())
    base = tmpd / "transcribe"
    wav = tmpd / "transcribe.wav"
    srt = tmpd / "transcribe.srt"

    spawn.run(
        [
            "ffmpeg",
            "-loglevel",
            "warning",
            "-y",
            "-i",
            file.as_posix(),
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            wav.as_posix(),
        ]
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
            model.as_posix(),
            wav.as_posix(),
        ]
    )

    buff = srt.read_text()
    shutil.rmtree(tmpd)

    return buff


@click.command("transcribe")
@click.option("--method", default="whisper.cpp")
@click.option("--model", type=Path)
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def transcribe_cmd(
    targets: list[Path],
    model: Path,
    method: str,
    overwrite: bool = False,
    recursive: bool = False,
):
    backends = {"whisper.cpp": _transcribe_with_whisper_cpp}

    for file in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        mime = fs.file_mime(file)
        if not mime.startswith("video/") and not mime.startswith("audio/"):
            click.echo(f"{file}: not a media file", err=True)
            continue

        transcription = backends[method](file, model=model)
        dest = fs.change_file_extension(file, "srt")
        if dest.exists() and not overwrite:
            click.echo(f"{dest}: already exists")
            continue

        dest.write_text(transcription)


if __name__ == "__main__":
    sys.exit(transcribe_cmd())
