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

import hashlib
import os
import pickle
from pathlib import Path
from typing import Any


class CacheDir:
    def __init__(self, basepath: Path):
        self.basepath = basepath

    def _hash(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _get_filepath(self, key: str) -> Path:
        hd = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.basepath / f"{hd[0]}/{hd[0:2]}/{hd}.bin"

    def get(self, key: str) -> Any:
        fp = self._get_filepath(key)

        try:
            with open(fp, "rb") as fh:
                data = pickle.loads(fh.read())
            return data[self._hash(key)]

        except (KeyError, FileNotFoundError) as e:
            raise MissError(key) from e

    def set(self, key: str, value: Any) -> None:
        fp = self._get_filepath(key)
        os.makedirs(os.path.dirname(fp), exist_ok=True)

        try:
            with open(fp, "rb") as fh:
                data = pickle.loads(fh.read())
        except FileNotFoundError:
            data = {}

        data[self._hash(key)] = value
        with open(fp, "wb") as fh:
            fh.write(pickle.dumps(data))


class MissError(Exception):
    pass
