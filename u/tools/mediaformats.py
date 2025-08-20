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
import subprocess
from pathlib import Path

import rich_click as click
from rich import print

from ..lib import fslib
from ..lib.clilib import file_conversion_options, target_options

LOGGER = logging.getLogger(__name__)


@click.command
@click.option("--verbose", "-v", is_flag=True, default=False)
@file_conversion_options
@target_options
def jpgize_cmd(
    targets: list[Path],
    *,
    recursive: bool = True,
    pre_scan: bool = True,
    overwrite: bool = False,
    rm: bool = False,
    verbose: bool = False,
):
    """Convert give files to jpg format."""

    supported_mimes = [
        "image/heic",
        "image/webp",
        "image/png",
    ]
    supported_extensions = [
        "heic",
        "webp",
        "png",
    ]

    def supported(file: Path):
        mime = fslib.file_mime(file)
        return (
            mime in supported_mimes
            or file.suffix.lstrip(".").lower() in supported_extensions
        )

    images = fslib.iter_files(*targets, recursive=recursive)
    images = (x for x in images if supported(x))
    if pre_scan:
        images = list(images)  # type: ignore[assignment]

    for v in images:
        temp = jpgize(v)

        dst = fslib.safe_mv(
            temp, fslib.change_file_extension(v, "jpg"), overwrite=overwrite
        )
        print(f"'{v}': converted to '{dst}'")

        if rm:
            if fslib._DRY_RUN:
                print(f"rm -f -- '{v}'")
            else:
                v.unlink()


@click.command
@click.option("--verbose", "-v", is_flag=True, default=False)
@file_conversion_options
@target_options
def mp4ize_cmd(
    targets: list[Path],
    *,
    overwrite: bool = False,
    recursive: bool = True,
    pre_scan: bool = True,
    rm: bool = False,
    verbose: bool = False,
):
    """Convert give files to mp4 format."""

    videos = fslib.iter_files(*targets, recursive=recursive)
    videos = (x for x in videos if fslib.file_matches_mime(x, "video/*"))
    if pre_scan:
        videos = list(videos)  # type: ignore[assignment]

    for v in videos:
        remuxed = mp4ize(v)

        dst = fslib.safe_mv(
            remuxed, fslib.change_file_extension(v, "mp4"), overwrite=overwrite
        )
        print(f"'{v}': remuxed to '{dst}'")

        if rm:
            if fslib._DRY_RUN:
                print(f"rm -f -- '{v}'")
            else:
                v.unlink()


def mp4ize(video: Path, *, fallback_acodec: str = "aac") -> Path:
    dst = Path(fslib.temp_filepath(suffix=".mp4"))

    acodecs = ["copy"]
    if fallback_acodec:
        acodecs.append(fallback_acodec)

    ffmpeg_ok = False
    curr_attempt = 0
    total_attempts = len(acodecs)

    while not ffmpeg_ok and acodecs:
        acodec = acodecs.pop(0)
        cmdl = [
            "ffmpeg",
            "-loglevel",
            "warning",
            "-y",
            "-i",
            video.as_posix(),
            "-c:v",
            "copy",
            "-c:a",
            acodec,
            dst.as_posix(),
        ]

        if fslib._DRY_RUN:
            print(" ".join(cmdl))
            ffmpeg_ok = True

        else:
            try:
                subprocess.run(cmdl, check=True, capture_output=True, text=True)
                ffmpeg_ok = True

            except subprocess.CalledProcessError as e:
                # LOGGER.debug(
                #     f"'{video}': conversion attempt #{curr_attempt+1}/{total_attempts} failed"
                # )
                # LOGGER.debug(f"'{video}': {' '.join(cmdl)}")
                # LOGGER.debug(f"'{video}': {e.stderr}")
                curr_attempt += 1
                continue

    if not ffmpeg_ok:
        raise ValueError("unable to convert video")

    return dst


def jpgize(
    src: Path,
) -> Path:
    dst = Path(fslib.temp_filepath(suffix=".jpg"))

    cmdl = ["convert", "-auto-orient", src.as_posix(), dst.as_posix()]

    if fslib._DRY_RUN:
        print(" ".join(cmdl))
    else:
        subprocess.run(cmdl)

    fslib.clone_exif(src, dst)
    fslib.clone_stat(src, dst)

    return dst
