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

import itertools
import logging
from collections.abc import Iterable
from itertools import chain
from pathlib import Path

import click

from .lib import filesystem as fs

_LOGGER = logging.getLogger(__name__)


SidecarGroup = list[tuple[str, Path]]
SidecarGroupSet = list[tuple[str, SidecarGroup]]

_ScanItItem = tuple[str, str, Path]


def _scan_it(target: Path, *, recursive: bool = True) -> Iterable[_ScanItItem]:
    if recursive:
        g = fs.iter_files(target)
    else:
        g = target.iterdir()

    for file in g:
        ext = fs.get_file_extension(file)
        yield f"{file.parent}/{file.stem}", ext, file


def scan(
    dir: Path, *_scan_it_args, extensions: list[str] | None = None, **_scan_it_kwargs
) -> SidecarGroupSet:
    # Scan dir and group by common path portion
    g = _scan_it(dir, *_scan_it_args, **_scan_it_kwargs)
    stack = [
        (common, sorted([(key, file) for _, key, file in gr]))
        for common, gr in itertools.groupby(
            sorted(g, key=lambda x: x[0]), lambda x: x[0]
        )
    ]

    # Filter required extensions
    if extensions:
        stack = [
            (common, [(key, file) for key, file in gr if key in extensions])
            for common, gr in stack
        ]

        stack = [(common, gr) for common, gr in stack if len(gr) == len(extensions)]

    # Done
    return stack


def scan_multiple(
    dirs: list[Path], *, extensions: list[str] | None = None
) -> SidecarGroupSet:
    return list(chain.from_iterable(scan(d, extensions=extensions) for d in dirs))


def find_for_file(file: Path, *args, **kwargs) -> SidecarGroup:
    key = f"{file.parent}/{file.stem}"

    return dict(scan(file.parent, *args, **kwargs))[key]


@click.group("sidecars")
def sidecars_cmd():
    pass


@click.command("scan")
@click.option(
    "--extension", "-e", "extensions", help="Filter extension matching", multiple=True
)
@click.argument("dirs", nargs=-1, required=True, type=Path)
def scan_cmd(dirs: list[Path], extensions=None):
    if extensions and len(extensions) < 2:
        raise TypeError("provide at least two extension")

    for _, sidecars in scan_multiple(dirs, extensions=extensions):
        # print(f"{common}")
        for key, file in sidecars:
            print(f"{key}: {file}")


@click.command("find")
@click.option(
    "--extension", "-e", "extensions", help="Filter extension matching", multiple=True
)
@click.argument("file", nargs=1, required=True, type=Path)
def find_cmd(file: Path, extensions=None):
    if not file.is_file():
        return -1

    for key, file in find_for_file(file, extensions=extensions):
        print(f"{key}: {file}")


sidecars_cmd.add_command(find_cmd)
sidecars_cmd.add_command(scan_cmd)


if __name__ == "__main__":
    import sys

    sys.exit(sidecars_cmd())
