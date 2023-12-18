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

import click
import openai

from .backends import openai

LOGGER = logging.getLogger(__name__)


@click.command("img-describe")
# @click.option(
#     "-d", "--device", type=click.Choice(["cpu", "cuda"]), required=False, default=None
# )
@click.option("-m", "--model", type=str, required=False, default=None)
@click.argument("file", type=click.File(mode="rb"))
def describe_cmd(
    file: click.File,
    # device: Literal["cuda"] | Literal["cpu"] | None = None,
    model: str | None = None,
):
    envbackend = os.environ.get("IMG2TXT_BACEND", "open-ai").lower()
    Backend = {"local-ai": openai.LocalAI, "open-ai": openai.OpenAI}.get(envbackend)

    ret = Backend().describe(file.read(), model=model)  # type: ignore[attr-defined]
    print(ret)


def main(*args) -> int:
    return describe_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
