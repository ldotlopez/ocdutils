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


class MotionPhoto:
    @classmethod
    def fromfile(cls, filepath: str, *args, **kwargs) -> MotionPhoto:
        with open(filepath, "rb") as fh:
            return cls(fh.read(), *args, **kwargs)

    def __init__(self, buff: bytes, marker: bytes = _MARKER):
        self.data = memoryview(buff)
        self.marker = marker
        self.idx = buff.find(self.marker)

    @property
    def image(self) -> bytes:
        if self.has_video:
            return bytes(self.data[0 : self.idx])
        else:
            return bytes(self.data)

    @property
    def video(self) -> Optional[bytes]:
        if not self.has_video:
            return None

        return bytes(self.data[self.idx + len(self.marker) :])

    @property
    def has_video(self) -> bool:
        return self.idx >= 0

    def insert_video(self, buff: bytes) -> None:
        # Update index before add
        self.idx = len(self.image)
        self.data = memoryview(bytes(self.image) + self.marker + buff)

    def drop_video(self) -> None:
        self.data = memoryview(bytes(self.image))
        # Update index after drop
        self.idx = -1
