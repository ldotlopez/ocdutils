#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Copyright (C) 2018 Luis López <luis@cuarentaydos.com>
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


import pathlib


class InvalidFileTypeError(Exception):
    pass


class RequiredDataNotFoundError(Exception):
    pass


def crc32(p, block_size=1024*1024*4):
    """
    Calculate crc32 for a path object.
    CRC32 is returned as a hexadecimal string
    """

    if not isinstance(p, pathlib.Path):
        p = pathlib.Path(p)

    with p.open('rb') as fh:
        value = 0
        while True:
            buff = fh.read(block_size)
            if not buff:
                break

            value = zlib.crc32(buff, value)

        return hex(value)[2:]
