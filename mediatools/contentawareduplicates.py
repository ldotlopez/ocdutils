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
from collections.abc import Iterable
from pathlib import Path

import click
import imagehash
import PIL

from .backends import ImageDuplicateFinder, get_backend_from_map
from .lib import filesystem as fs
from .lib import spawn

LOGGER = logging.getLogger(__name__)
DEFAULT_HASH_SIZE = 8

BACKEND_MAP = {"imagehash": "ImageDuplicateFinder"}
DEFAULT_BACKEND = os.environ.get(
    "MEDIATOOLS_CONTENT_AWARE_DUPLICATES_BACKEND", "imagehash"
)


def ImageDuplicateFinderFactory(
    backend: str | None = DEFAULT_BACKEND, **kwargs
) -> ImageDuplicateFinder:
    Cls = get_backend_from_map(backend or DEFAULT_BACKEND, BACKEND_MAP)

    return Cls()


def find_duplicates(
    images: list[Path], *, backend: str | None = DEFAULT_BACKEND, **kwargs
):
    return ImageDuplicateFinderFactory(backend=backend, **kwargs).find(images)


def unroll_target_files(
    targets: list[Path], *, recursive: bool = False
) -> Iterable[Path]:
    for t in targets:
        if t.is_file():
            yield t
            continue

        if recursive:
            yield from fs.iter_files(t)
            continue

        click.echo(f"{click.format_filename(t)}: not a file", err=True)
        continue


@click.command("find-duplicates")
@click.option("--execute", "-x", type=str)
@click.option("--recursive", "-r", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option(
    "--hash-size",
    type=int,
    default=DEFAULT_HASH_SIZE,
    help="powers of 2, lower values more false positives",
)
@click.argument("targets", nargs=-1, required=True, type=Path)
def find_duplicates_cmd(
    targets: list[Path],
    hash_size: int,
    recursive: bool = False,
    verbose: bool = False,
    execute: str | None = None,
):
    if not targets:
        return

    files = list(fs.iter_files_in_targets(targets, recursive=recursive))
    images = [x for x in files if fs.file_matches_mime(x, "image/*")]
    click.echo(f"Found {len(images)} images")

    with click.progressbar(length=len(images), label="Calculating image hashes") as bar:

        def update_fn(img, imghash):
            if verbose:
                click.echo(f"{img}: hash={imghash}")
            else:
                bar.update(1, img)

        dupes = find_duplicates(
            images,
            hash_size=hash_size,
            update_fn=update_fn,
        )

    for idx, (imghash, gr) in enumerate(dupes):
        pathsstr = " ".join(
            ["'" + img.as_posix().replace("'", "'") + "'" for img in gr]
        )
        click.echo(f"Group {idx+1}  ({imghash}): {pathsstr}")

        if execute:
            cmdl = [execute] + [x.as_posix() for x in gr]
            spawn.run(cmdl)


def main(*args) -> int:
    return find_duplicates_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
