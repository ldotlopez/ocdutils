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

from typing import Optional

_MARKER = b"MotionPhoto_Data"


class MotionPhotoBytes:
    @classmethod
    def fromfile(cls, filepath: str, *args, **kwargs) -> MotionPhotoBytes:
        with open(filepath, "rb") as fh:
            return cls(fh.read(), *args, **kwargs)

    def __init__(self, buff: bytes, marker: bytes = _MARKER):
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
    def __init__(self, filepath: str):
        with open(filepath, "rb") as fh:
            return super().__init__(fh.read())

    def insert_video(self, filepath: str):  # type: ignore[override]
        with open(filepath, "rb") as fh:
            super().insert_video(fh.read())

    def save(self, dest: str):
        with open(dest, "wb") as fh:
            fh.write(self.data)


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="command")

    test = command.add_parser("test")
    test.add_argument("--mp", dest="motionphoto", required=True)

    join = command.add_parser("join")
    join.add_argument("-i", dest="image", required=True)
    join.add_argument("-v", dest="video", required=True)
    join.add_argument("--mp", dest="motionphoto", required=True)

    split = command.add_parser("split")
    split.add_argument("-i", dest="image", required=True)
    split.add_argument("-v", dest="video", required=True)
    split.add_argument("--mp", dest="motionphoto", required=True)

    args = parser.parse_args()

    if args.command == "test":
        mp = MotionPhoto(args.motionphoto)
        sys.exit(0 if mp.has_video else 1)

    elif args.command == "join":
        mp = MotionPhoto(args.image)
        mp.insert_video(args.video)
        mp.save(args.motionphoto)

    elif args.command == "split":
        mp = MotionPhoto(args.motionphoto)

        with open(args.image, "wb") as fh:
            fh.write(mp.image)

        with open(args.video, "wb") as fh:
            fh.write(mp.video)


if __name__ == "__main__":
    main()
