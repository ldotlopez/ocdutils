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


import functools
import hashlib
import zlib
from pathlib import Path
from typing import IO, Callable

import click

from .lib import filesystem as fs


def _generic_digest(fh, *, algorithms: str) -> str:
    x = hashlib.file_digest(fh, algorithms)
    return x.hexdigest()


DIGESTERS: dict[str, Callable] = {}
for x in hashlib.algorithms_available:
    fn = functools.partial(_generic_digest, algorithms=x)
    DIGESTERS[x] = fn


def crc32_digest(fh: IO) -> str:
    ret = 0

    while True:
        chunk = fh.read(4096)  # Read 4KB chunks
        if not chunk:
            break

        ret = zlib.crc32(chunk, ret)

    return f"{ret:08x}"


DIGESTERS["crc32"] = crc32_digest


@click.command("hash-rename")
@click.option("--algo", type=click.Choice(DIGESTERS.keys()), default="crc32")
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--force", "-f", is_flag=True, default=False)
@click.option("--dry-run", "-n", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def crc32_rename_cmd(
    targets,
    *,
    algo: str,
    recursive: bool = False,
    verbose: bool = False,
    force: bool = False,
    dry_run: bool = False,
):
    for src in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        with src.open("rb") as fh:
            fhhash = DIGESTERS[algo](fh)
            dst = src.parent / (fhhash + src.suffix)

        if dst.exists() and not force:
            click.echo(f"{src}: Destination {dst} exists", err=True)
            continue

        if dry_run or verbose:
            click.echo(f"mv '{src!s}' '{dst!s}'")

        if dry_run:
            return

        fs.safe_mv(src, dst, overwrite=force)
