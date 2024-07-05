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
from datetime import UTC, datetime
from pathlib import Path

import click

from .backends import BaseBackendFactory, ImageDescriptor, ImageGenerator
from .lib import filesystem as fs
from .lib import spawn

LOGGER = logging.getLogger(__name__)


def ImageGeneratorFactory(backend: str | None = None, **kwargs) -> ImageGenerator:
    env_id = "IMAGE_GENERATOR"
    backends = {"openai": "OpenAI"}
    default = "openai"

    return BaseBackendFactory(
        backend=backend, id=env_id, map=backends, default=default
    )(**kwargs)


def ImageDescriptorFactory(backend: str | None = None, **kwargs) -> ImageDescriptor:
    env_id = "IMAGE_DESCRIPTOR"
    backends = {"openai": "OpenAI"}
    default = "openai"

    return BaseBackendFactory(
        backend=backend, id=env_id, map=backends, default=default
    )(**kwargs)


def generate(prompt: str) -> bytes:
    return ImageGeneratorFactory().generate(prompt)


def describe(file: Path) -> str:
    return ImageDescriptorFactory().describe(file)


def write_comment(file: Path, comment: str):
    with fs.temp_dirpath() as d:
        temp = fs.safe_cp(file, d / file.name)

        cmdl = ["exiftool", f"-Comment={comment}", temp.as_posix()]
        try:
            spawn.run(cmdl)

        except spawn.ProcessFailure as e:
            pass

        fs.clone_exif(file, temp)
        fs.clone_stat(file, temp)

        fs.safe_mv(temp, file, overwrite=True)


@click.command("create-image")
@click.option("--output", "-o", type=Path, default=None, help="Output filename")
@click.argument("prompt", type=str)
def generate_cmd(prompt: str, output: Path | None = None) -> int:
    if output is None:
        ts = datetime.now(tz=UTC).timestamp()
        output = Path(f"{ts}.png")

    buff = generate(prompt)
    output.write_bytes(buff)

    return 0


@click.command("describe-image")
@click.option(
    "--write", "-w", is_flag=True, default=False, help="Write description into file"
)
@click.argument("file", type=Path, nargs=-1)
def describe_cmd(file: tuple[Path], write: bool = False) -> int:
    for f in file:
        desc = describe(f)
        print(f"{f}: {desc}")
        if write:
            write_comment(f, desc)

    return 0
