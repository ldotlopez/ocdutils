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
from collections.abc import Callable, Iterable
from concurrent import futures
from pathlib import Path

import click
import imagehash
import PIL

from ..lib import filesystem as fs
from ..lib import spawn

_LOGGER = logging.getLogger(__name__)
_DEFAULT_HASH_SIZE = 8


try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    _LOGGER.warning("HEIF support not enabled, install pillow-heif")


UpdateFn = Callable[[Path, str | None], None]


def imagehash_frompath(path: Path, *, hash_size=_DEFAULT_HASH_SIZE) -> str:
    # User average_hash or phash?
    with imagehash.Image.open(fs.as_posix(path)) as img:
        return str(imagehash.average_hash(img, hash_size))


def imagehash_frombytes(data: bytes, *, hash_size=_DEFAULT_HASH_SIZE) -> str:
    with imagehash.Image.open(io.BytesIO(data)) as img:
        # FIXME: use average_hash or phash ?
        return str(imagehash.average_hash(img, hash_size))


def find_duplicates(
    images: list[Path],
    hash_size: int | None = _DEFAULT_HASH_SIZE,
    update_fn: UpdateFn | None = None,
):
    hash_size = hash_size or _DEFAULT_HASH_SIZE

    def _g(it):
        return it
        # return [x for x in it]

    def map_and_update(item):
        try:
            ret = imagehash_frompath(item, hash_size=hash_size)
        except PIL.UnidentifiedImageError:
            _LOGGER.warning(f"{item}: unidentified image")
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

    return list(groups_g)


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
    default=_DEFAULT_HASH_SIZE,
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


def main():
    return find_duplicates_cmd()


if __name__ == "__main__":
    import sys

    sys.exit(main())
