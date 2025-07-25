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


import zlib
from pathlib import Path

import click

from .lib import filesystem as fs


@click.command("crc32-rename")
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--force", "-f", is_flag=True, default=False)
@click.option("--dry-run", "-n", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def crc32_rename_cmd(
    targets,
    *,
    recursive: bool = False,
    verbose: bool = False,
    force: bool = False,
    dry_run: bool = False,
):
    for src in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        dst = get_crc32_filepath(src)
        if dst.exists() and not force:
            click.echo(f"{src}: Destination {dst} exists", err=True)
            continue

        if dry_run or verbose:
            click.echo(f"mv '{src!s}' '{dst!s}'")

        if dry_run:
            return

        fs.safe_mv(src, dst, overwrite=force)


def get_crc32_filepath(filepath: Path) -> Path:
    """
    Renames a file based on its CRC32 checksum, preserving the original extension.

    Args:
        filepath (str): The path to the file to be renamed.
    """

    crc_value = get_crc32(filepath)

    # Convert CRC32 to an 8-character hexadecimal string (e.g., 'AABBCCDD')
    crc_hex = f"{crc_value:08x}"

    # Construct the new filename
    return filepath.parent / (crc_hex + filepath.suffix)


def get_crc32(filepath: Path) -> int:
    """
    Calculates the CRC32 checksum of a given file.

    Args:
        filepath (str): The path to the file.

    Returns:
        int: The CRC32 checksum as an integer.
    """
    # Initialize CRC to 0
    ret = 0

    # Open the file in binary read mode
    with filepath.open("rb") as fh:
        while True:
            # Read file in chunks to handle large files efficiently
            chunk = fh.read(4096)  # Read 4KB chunks
            if not chunk:
                break
            # Update CRC32 value with the current chunk
            ret = zlib.crc32(chunk, ret)

    return ret


# @click.group("filesystem-fixes")
# def filesystem_fixes_cmd():
#     pass


# def iter_over(*paths: Path, recursive: bool, include_roots: bool):
#     for root in paths:
#         pass


# filesystem_fixes_cmd.add_command(fix_extensions_cmd)


# def main(*args) -> int:
#     return filesystem_fixes_cmd(*args) or 0


# if __name__ == "__main__":
#     import sys

#     sys.exit(main(*sys.argv))
