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

import contextlib
import logging
import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import click

from . import sidecars
from .lib import filesystem as fs

_LOGGER = logging.getLogger(__name__)

_MOTIONPHOTO_MARKER = b"MotionPhoto_Data"


class MotionPhotoBytes:
    @classmethod
    def fromfile(cls, filepath: str, *args, **kwargs) -> MotionPhotoBytes:
        with open(filepath, "rb") as fh:
            return cls(fh.read(), *args, **kwargs)

    def __init__(self, buff: bytes, marker: bytes = _MOTIONPHOTO_MARKER):
        self.marker = marker
        idx = buff.find(self.marker)

        self.image: memoryview
        self.video: memoryview | None

        if idx >= 0:
            self.image = memoryview(buff[0:idx])
            self.video = memoryview(buff[idx + len(self.marker) :])
        else:
            self.image = memoryview(buff[:])
            self.video = None

    @property
    def has_video(self) -> bool:
        return self.video is not None

    def insert_video(self, buff: bytes) -> None:
        self.video = memoryview(buff)

    def drop_video(self) -> None:
        self.video = None

    @property
    def data(self) -> bytes:
        if self.has_video:
            return bytes(self.image) + self.marker + bytes(self.video)  # type: ignore[arg-type]
        else:
            return bytes(self.image)


class MotionPhoto(MotionPhotoBytes):
    def __init__(self, filepath: str | Path):
        if isinstance(filepath, str):
            filepath = Path(filepath)

        return super().__init__(filepath.read_bytes())

    def insert_video(self, filepath: str | Path):  # type: ignore[override]
        if isinstance(filepath, str):
            filepath = Path(filepath)

        super().insert_video(filepath.read_bytes())

    def save(self, filepath: str | Path):
        if isinstance(filepath, str):
            filepath = Path(filepath)

        filepath.write_bytes(self.data)


def join(image: Path, video: Path, motionphoto: Path):
    mp = MotionPhoto(image)
    mp.insert_video(video)
    mp.save(motionphoto)


def split(motionphoto: Path, image: Path, video: Path):
    mp = MotionPhoto(motionphoto)

    image.write_bytes(mp.image)

    if mp.has_video:
        video.write_bytes(mp.video)  # type: ignore[arg-type]
    else:
        print("Error")


def _create_stat_holder(source: Path) -> Path:
    _, t = tempfile.mkstemp()
    holder = Path(t)
    fs.clone_stat(source, holder)

    return holder


@contextlib.contextmanager
def _stat_holder(source: Path) -> Iterator:
    _, t = tempfile.mkstemp()
    holder = Path(t)
    fs.clone_stat(source, holder)

    yield holder

    holder.unlink()


@click.group("motionphotos")
def motionphoto_cmd():
    pass


@click.command()
@click.option("--motionphoto", "--mp", required=True)
def test_cmd(motionphoto):
    mp = MotionPhoto(motionphoto)
    sys.exit(0 if mp.has_video else 1)


@click.command("split")
@click.option("--motionphoto", "--mp", required=True, type=Path)
@click.option("--image", "-i", required=True, type=Path)
@click.option("--video", "-v", required=True, type=Path)
def split_cmd(motionphoto, image, video):
    with _stat_holder(motionphoto) as statholder:
        ret = split(motionphoto=motionphoto, image=image, video=video)

        fs.clone_stat(statholder, image)
        fs.clone_stat(statholder, video)

        return ret


@click.command("join")
@click.option("--image", "-i", required=True)
@click.option("--video", "-v", required=True)
@click.option("--mp", "motionphoto", required=True)
def join_cmd(image, video, motionphoto):
    with _stat_holder(image) as statholder:
        fs.clone_stat(statholder, image)

        ret = join(
            image=image,
            video=video,
            motionphoto=motionphoto,
        )

        fs.clone_stat(statholder, motionphoto)

        return ret


@click.command("scan")
@click.argument("targets", nargs=-1, required=True, type=Path)
def scan_cmd(targets: list[Path]):
    for filepath in fs.iter_files_in_targets(targets):
        if MotionPhoto(fs.as_posix(filepath)).has_video:
            print(f"+ {filepath}")
        else:
            print(f"- {filepath}")


@click.command("scan-and-merge")
@click.argument("dirs", nargs=-1, required=True, type=Path)
def scan_and_merge(dirs: list[Path]):
    for _, gr in sidecars.scan_multiple(dirs, extensions=["jpg", "mp4"]):
        m = dict(gr)
        join(m["jpg"], m["mp4"], m["jpg"])
        if fs._DRY_RUN:
            print(f"rm -f -- {m['mp4']}")
        else:
            os.unlink(m["mp4"])


@click.command("insert")
@click.option("--video", "-v", required=True, type=Path)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--rm", "-d", "delete_video", is_flag=True, default=False)
@click.argument("image", type=Path)
def insert_cmd(
    image: Path, video: Path, overwrite: bool = False, delete_video: bool = False
):
    with _stat_holder(image) as statholder:
        if image == video:
            click.echo(
                f"{click.format_filename(video)}: image and video are the same file"
            )
            return 255

        if not video.exists():
            click.echo(f"{click.format_filename(video)}: not such file", err=True)
            return 255

        mp = MotionPhoto(image)
        if mp.has_video and not overwrite:
            click.echo(f"{click.format_filename(image)}: already has video", err=True)
            return 255

        mp.insert_video(video)
        mp.save(image)

        fs.clone_stat(statholder, image)

    if delete_video:
        video.unlink()


@click.command("extract")
@click.option("--video", "-v", required=True, type=Path)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--rm", "-d", "delete_video", is_flag=True, default=False)
@click.argument("image", type=Path)
def extract_cmd(
    image: Path, video: Path, overwrite: bool = False, delete_video: bool = False
):
    with _stat_holder(image) as statholder:
        if image == video:
            raise ValueError(video)

        mp = MotionPhoto(image)
        if not mp.has_video:
            raise ValueError("hash video")

        if video.exists() and not overwrite:
            raise ValueError("hash video")

        video.write_bytes(mp.video)  # type: ignore[arg-type]
        fs.clone_stat(statholder, video)

        if delete_video:
            mp.drop_video()
            mp.save(image)
            fs.clone_stat(statholder, image)


motionphoto_cmd.add_command(test_cmd)
motionphoto_cmd.add_command(scan_cmd)
motionphoto_cmd.add_command(join_cmd)
motionphoto_cmd.add_command(split_cmd)
motionphoto_cmd.add_command(scan_and_merge)
motionphoto_cmd.add_command(insert_cmd)
motionphoto_cmd.add_command(extract_cmd)


def main(*args) -> int:
    return motionphoto_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))


if __name__ == "__main__":
    main()
