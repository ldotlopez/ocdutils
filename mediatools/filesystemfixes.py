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
from collections.abc import Callable
from pathlib import Path

import click

from .lib import filesystem as fs


def lowercase_extension_tr(filepath: Path) -> Path:
    return filepath.parent / (filepath.stem + filepath.suffix.lower())


def replace_extension_tr(filepath: Path, haystack: list[str], repl: str):
    if fs.get_file_extension(filepath) in haystack:
        return filepath.parent / (filepath.stem + "." + repl)

    return filepath


@click.command("fix-extensions")
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def fix_extensions_cmd(targets, *, recursive: bool = False, verbose: bool = False):
    trs: list[Callable[[Path], Path]] = [
        lowercase_extension_tr,
        functools.partial(replace_extension_tr, haystack=["jpeg"], repl="jpg"),
        functools.partial(replace_extension_tr, haystack=["mpeg"], repl="mpg"),
        functools.partial(replace_extension_tr, haystack=["tif"], repl="tiff"),
    ]

    for file in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        dst = file
        for fn in trs:
            dst = fn(dst)

        if dst == file:
            if verbose:
                click.echo(f"{click.format_filename(file)}: already OK")
            continue

        try:
            dst = fs.safe_mv(file, dst, overwrite=False)
        except FileExistsError:
            click.echo(f"{click.format_filename(file)}: file already exists", err=True)
            continue

        if verbose:
            click.echo(f"{click.format_filename(file)} → {click.format_filename(dst)}")


@click.group("filesystem-fixes")
def filesystem_fixes_cmd():
    pass


def iter_over(*paths: Path, recursive: bool, include_roots: bool):
    for root in paths:
        pass


filesystem_fixes_cmd.add_command(fix_extensions_cmd)


def main(*args) -> int:
    return filesystem_fixes_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
