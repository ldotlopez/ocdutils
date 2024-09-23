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


import os
from collections.abc import Callable
from pathlib import Path

import click

from .lib import filesystem as fs
from .lib import spawn


def _generic_converter(
    filepath: Path,
    destination: Path,
    convert_fn: Callable[[Path, Path], None],
    *,
    overwrite: bool,
) -> Path:
    temp = fs.temp_filename(destination)

    convert_fn(filepath, temp)

    return fs.safe_mv(temp, destination, overwrite=overwrite)


def _with_convert_cmdl(
    file: Path, *, output_format: str = "jpg", overwrite: bool
) -> Path:
    def convert(src: Path, dst: Path):
        cmdl = ["convert", "-auto-orient", src.as_posix(), dst.as_posix()]
        if fs._DRY_RUN:
            print(" ".join(cmdl))
        else:
            spawn.run(cmdl)

        fs.clone_exif(src, dst)
        fs.clone_stat(src, dst)

    return _generic_converter(
        file,
        fs.change_file_extension(file, output_format),
        convert,
        overwrite=overwrite,
    )


def mp4ize(video: Path, *, fallback_acodec: str | None = None, overwrite: bool) -> Path:
    def convert(src: Path, dst: Path):
        acodecs = ["copy"]
        if fallback_acodec:
            acodecs.append(fallback_acodec)

        ffmpeg_ok = False
        for idx, ca in enumerate(acodecs):
            try:
                cmdl = [
                    "ffmpeg",
                    "-loglevel",
                    "warning",
                    "-y",
                    "-i",
                    src.as_posix(),
                    "-c:v",
                    "copy",
                    "-c:a",
                    ca,
                    dst.as_posix(),
                ]
                if fs._DRY_RUN:
                    print(" ".join(cmdl))
                else:
                    spawn.run(cmdl)

                ffmpeg_ok = True
                break

            except spawn.ProcessFailure:
                if dst.exists():
                    dst.unlink()

                if idx + 1 == len(acodecs):
                    raise

        if not ffmpeg_ok:
            raise SystemError()

        fs.clone_stat(src, dst)
        fs.clone_exif(src, dst)

    return _generic_converter(
        video, fs.change_file_extension(video, "mp4"), convert, overwrite=overwrite
    )


@click.group("formats")
def formats_cmd():
    pass


@click.command("mp4ize")
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--rm", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("videos", nargs=-1, required=True, type=Path)
def mp4ize_cmd(
    videos: list[Path],
    *,
    format: str = "mp4",
    overwrite: bool = False,
    recursive: bool = True,
    rm: bool = False,
    verbose: bool = False,
):
    g = fs.iter_files_in_targets(videos, recursive=recursive)
    g = (x for x in g if fs.matches_mime(x, "video/*"))

    for v in g:
        remuxed = mp4ize(v, fallback_acodec="aac", overwrite=overwrite)
        if verbose:
            print(f"'{v}' -> '{remuxed}'")

        if rm:
            if fs._DRY_RUN:
                print(f"rm -f -- '{v}'")
            else:
                os.unlink(v)


@click.command("jpgize")
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--rm", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("images", nargs=-1, required=True, type=Path)
def jpgize_cmd(
    images: list[Path],
    *,
    overwrite: bool = False,
    recursive: bool = True,
    rm: bool = False,
    verbose: bool = False,
):
    supported_mimes = {
        "image/heic": _with_convert_cmdl,
        "image/webp": _with_convert_cmdl,
    }
    supported_extensions = {"heic": _with_convert_cmdl, "webp": _with_convert_cmdl}

    g = fs.iter_files_in_targets(images, recursive=recursive)

    for img in g:
        mime = fs.file_mime(img)
        convert_fn = supported_mimes.get(mime, None) or supported_extensions.get(
            img.suffix.lstrip(".").lower(), None
        )

        if convert_fn is None:
            click.echo(f"{click.format_filename(img)}: unsupported", err=True)
            continue

        convert_fn(img, overwrite=overwrite)

        if rm and not fs._DRY_RUN:
            img.unlink()
        else:
            print(f"rm -- {img}")


formats_cmd.add_command(mp4ize_cmd)
formats_cmd.add_command(jpgize_cmd)


def run_command_and_return_stdout_else_raise_exception(cmdl: list[str]) -> str:
    pass


def main(*args) -> int:
    return formats_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
