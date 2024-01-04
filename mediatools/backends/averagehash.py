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


import io
import itertools
import logging
from collections.abc import Callable
from concurrent import futures
from pathlib import Path

import imagehash
import PIL

from ..lib import filesystem as fs

LOGGER = logging.getLogger(__name__)
DEFAULT_HASH_SIZE = 8


try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    LOGGER.warning("HEIF support not enabled, install pillow-heif")


UpdateFn = Callable[[Path, str | None], None]


class ImageDuplicateFinder:
    def __init__(
        self,
        hash_size: int | None = DEFAULT_HASH_SIZE,
    ):
        self.hash_size = hash_size or DEFAULT_HASH_SIZE

    def find(
        self,
        images: list[Path],
        update_fn: UpdateFn | None = None,
    ):
        def _g(it):
            return it
            # return [x for x in it]

        def map_and_update(item):
            try:
                ret = imagehash_frompath(item, hash_size=self.hash_size)
            except PIL.UnidentifiedImageError:
                LOGGER.warning(f"{item}: unidentified image")
                ret = None

            except OSError as e:
                LOGGER.warning(f"{item}: {e}")
                ret = None

            if update_fn:
                update_fn(item, ret)

            return ret

        with futures.ThreadPoolExecutor() as executor:
            hashes = executor.map(map_and_update, images)

        # zip without None's
        zip_g = _g(
            (imghash, image)
            for (imghash, image) in zip(hashes, images)
            if imghash is not None
        )

        # Sort by hash
        sorted_g = _g(sorted(zip_g, key=lambda x: x[0]))

        # group by hash and strip imghashes
        grouped_g = _g(
            (imghash, [img for _, img in gr])
            for imghash, gr in itertools.groupby(sorted_g, lambda x: x[0])
        )

        # Strip unique items
        groups_g = _g(((imghash, gr) for imghash, gr in grouped_g if len(gr) > 1))

        # FIXME: Strip imghash because upstream consumer (command line tool) doesn't support data format
        groups_g = (gr for (_, gr) in groups_g)

        return list(groups_g)


def imagehash_frompath(path: Path, *, hash_size=DEFAULT_HASH_SIZE) -> str:
    # User average_hash or phash?
    with imagehash.Image.open(fs.as_posix(path)) as img:
        return str(imagehash.average_hash(img, hash_size))


def imagehash_frombytes(data: bytes, *, hash_size=DEFAULT_HASH_SIZE) -> str:
    with imagehash.Image.open(io.BytesIO(data)) as img:
        # FIXME: use average_hash or phash ?
        return str(imagehash.average_hash(img, hash_size))
