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


import logging
import os
import sys
from collections.abc import Iterable
from pathlib import Path

import click
import imagehash
import PIL

from .backends import ImageDuplicateFinder, get_backend_from_map, get_backend_name
from .backends.averagehash import ImageDuplicateFinder
from .lib import filesystem as fs
from .lib import spawn

LOGGER = logging.getLogger(__name__)
DEFAULT_HASH_SIZE = 8


@click.command("img-hash")
@click.option("--recursive", "-r", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option(
    "--hash-size",
    type=int,
    default=DEFAULT_HASH_SIZE,
    help="powers of 2, lower values more false positives",
)
@click.argument("targets", nargs=-1, required=True, type=Path)
def media_hash_cmd(
    targets: list[Path], hash_size: int, recursive: bool = False, verbose: bool = False
):
    if not targets:
        return

    g = fs.iter_files_in_targets(targets, recursive=recursive)
    g = (x for x in g if fs.file_matches_mime(x, "image/*"))

    hasher = ImageDuplicateFinder(hash_size=hash_size)
    for f in g:
        try:
            signature = hasher.hash(f)
        except OSError as exc:
            print(f"{f}: error ({exc})", file=sys.stderr)
            continue

        print(f"{signature}\t{f}")
        # def update_fn(img, imghash):
        #     if verbose:
        #         click.echo(f"{img}: hash={imghash}")
        #     else:
        #         bar.update(1, img)

        # dupes = finder.find(
        #     images,
        #     update_fn=update_fn,
        # )


def main(*args) -> int:
    return media_hash_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
