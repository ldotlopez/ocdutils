#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

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

from typing import Optional, Type

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
        self.video: Optional[memoryview]

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
        super().fromfile(filepath)

    def insert_video(self, filepath: str):  # type: ignore[override]
        with open(filepath, "rb") as fh:
            super().insert_video(fh.read())

    def save(self, dest: str):
        with open(dest, "wb") as fh:
            fh.write(self.data)
