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


from pathlib import Path

import click
import PIL.Image

from .lib import filesystem as fs

_REMBG_IMPORTED = False
_CLIP_IMPORTED = False


@click.command("autocrop")
@click.argument("file", type=click.File(mode="rb"))
def autocrop_cmd(file: click.File):
    path = Path(file.name)
    with PIL.Image.open(file) as img:
        output_path = Path(f"{path.parent / path.stem}.cropped.png")
        out = autocrop(img)
        out.save(output_path)
        fs.clone_exif(path, output_path)
        fs.clone_stat(path, output_path)


@click.command("describe")
@click.argument("file", type=click.File(mode="rb"))
def describe_cmd(file: click.File):
    with PIL.Image.open(file) as img:
        return describe(img)


@click.command("removebg")
@click.argument("file", type=click.File(mode="rb"))
def removebg_cmd(file: click.File):
    path = Path(file.name)

    with PIL.Image.open(file) as img:
        output_path = Path(f"{path.parent / path.stem}.removebg.png")
        out = autocrop(remove_background(img))
        out.save(output_path)
        fs.clone_exif(path, output_path)
        fs.clone_stat(path, output_path)


def remove_background(img: PIL.Image) -> PIL.Image:
    global _REMBG_IMPORTED
    if not _REMBG_IMPORTED:
        import rembg

        _REMBG_IMPORTED = True

    return rembg.remove(img)


def autocrop(img: PIL.Image) -> PIL.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    ret = img.crop(bbox)

    return ret


@click.group("imgedit")
def imgedit_cmd():
    pass


imgedit_cmd.add_command(autocrop_cmd)
imgedit_cmd.add_command(removebg_cmd)


def main(*args) -> int:
    return imgedit_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
