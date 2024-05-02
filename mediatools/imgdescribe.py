#! /bin/env python3

# Copyright (C) 2022- Luis López <luis@cuarentaydos.com>
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
from pathlib import Path

import click

from .backends import ImageDescriptor, get_backend_from_map
from .lib import filesystem as fs
from .lib import spawn

LOGGER = logging.getLogger(__name__)
DEFAULT_BACKEND = "openai"
BACKEND_MAP = {"openai": "OpenAI", "lavis": "LAVIS"}


def ImageDescriptorFactory(backend: str = DEFAULT_BACKEND, **kwargs) -> ImageDescriptor:
    Descriptor = get_backend_from_map(
        os.environ.get("MEDIATOOLS_DESCRIBE_BACKEND", backend or DEFAULT_BACKEND),
        BACKEND_MAP,
    )

    return Descriptor()


def describe(file: Path, *, backend: str = DEFAULT_BACKEND, **kwargs) -> str:
    return ImageDescriptorFactory(backend=backend).describe(file, **kwargs)


def write_comnent(file: Path, comment: str):
    with fs.temp_dirpath() as d:
        temp = fs.safe_cp(file, d / file.name)

        cmdl = ["exiftool", "-Comment={comment}", temp.as_posix()]
        try:
            spawn.run(cmdl)
        except spawn.ProcessFailure as e:
            pass

        fs.clone_exif(file, temp)
        fs.clone_stat(file, temp)

        fs.safe_mv(temp, file, overwrite=True)


@click.command("img-describe")
@click.option(
    "--write", "-w", is_flag=True, default=False, help="Write description into file"
)
@click.argument("file", type=Path, nargs=-1)
def describe_cmd(file: tuple[Path], write: bool = False):
    for f in file:
        desc = describe(f)
        print(f"{f}: {desc}")
        if write:
            write_comnent(f, desc)


def main(*args) -> int:
    return describe_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
