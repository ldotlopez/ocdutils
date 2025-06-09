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
import shlex
from pathlib import Path

import click

from .backends import BaseBackendFactory, ImageDuplicateFinder
from .lib import filesystem as fs
from .lib import spawn

LOGGER = logging.getLogger(__name__)
DEFAULT_HASH_SIZE = 8


ENVIRON_KEY = "CONTENT_AWARE_DUPLICATES"
DEFAULT_BACKEND = "averagehash"
BACKENDS = {"averagehash": "ImageDuplicateFinder", "cv2histogram": "CV2Matcher"}


def ImageDuplicateFinderFactory(
    backend: str | None = None, **kwargs
) -> ImageDuplicateFinder:
    return BaseBackendFactory(
        backend=backend, id=ENVIRON_KEY, map=BACKENDS, default=DEFAULT_BACKEND
    )(**kwargs)


def find_duplicates(images: list[Path], **kwargs):
    return ImageDuplicateFinderFactory(**kwargs).find(images)


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

    execute_argv = shlex.split(execute)

    files = list(fs.iter_files_in_targets(targets, recursive=recursive))
    images = [x for x in files if fs.file_matches_mime(x, "image/*")]
    click.echo(f"Found {len(images)} images")

    dupes = []

    finder = ImageDuplicateFinderFactory(hash_size=DEFAULT_HASH_SIZE)

    with click.progressbar(length=len(images), label="Calculating image hashes") as bar:

        def update_fn(img, imghash):
            if verbose:
                click.echo(f"{img}: hash={imghash}")
            else:
                bar.update(1, img)

        dupes = finder.find(
            images,
            update_fn=update_fn,
        )

    n_groups = len(dupes)
    for idx, gr in enumerate(dupes):
        pathsstr = " ".join(
            ["'" + img.as_posix().replace("'", "'") + "'" for img in gr]
        )
        click.echo(f"Group {idx+1}/{n_groups}: {pathsstr}")

        print(execute_argv)
        if execute:
            cmdl = execute_argv + [x.as_posix() for x in gr]
            spawn.run(cmdl)


def main(*args) -> int:
    return find_duplicates_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
