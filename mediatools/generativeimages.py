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

from .backends import BaseBackendFactory, ImageGenerator

LOGGER = logging.getLogger(__name__)

ENVIRON_KEY = "IMAGE_GENERATOR"
DEFAULT_BACKEND = "openai"
BACKENDS = {"openai": "OpenAI"}


def ImageGeneratorFactory(backend: str | None = None, **kwargs) -> ImageGenerator:
    return BaseBackendFactory(
        backend=backend, id=ENVIRON_KEY, map=BACKENDS, default=DEFAULT_BACKEND
    )(**kwargs)


@click.command("create-image")
@click.option("--output", "-o", type=Path, default=None, help="Output filename")
@click.argument("prompt", type=str)
def create_image_cmd(prompt: str, output: Path | None = None) -> int:
    if output is None:
        ts = datetime.now(tz=UTC).timestamp()
        output = Path(f"{ts}.png")

    backend = ImageGeneratorFactory()

    buff = backend.generate(prompt)
    output.write_bytes(buff)
    return 0


def main(*args) -> int:
    return create_image_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
