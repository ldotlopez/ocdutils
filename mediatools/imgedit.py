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
from pathlib import Path

import click
from PIL import Image

from .lib import filesystem as fs

LOGGER = logging.getLogger(__name__)

_REMBG_IMPORTED = False
_CLIP_IMPORTED = False


def remove_background(img: Image.Image) -> Image.Image:
    global _REMBG_IMPORTED
    if not _REMBG_IMPORTED:
        LOGGER.warning(
            "loading rembg and downloading some models, this can take a while"
        )
        import rembg

        _REMBG_IMPORTED = True

    return rembg.remove(img)


def autocrop(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        aimg = img.convert("RGBA")
    else:
        aimg = img

    alpha = aimg.split()[-1]
    bbox = alpha.getbbox()
    ret = img.crop(bbox)

    return ret


def remove_transparency(img: Image.Image, bg_color=(255, 255, 255)) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg = Image.new("RGBA", img.size, bg_color + (255,))
        alpha = img.convert("RGBA").split()[-1]
        bg.paste(img, mask=alpha)
        return bg.convert("RGB")

    return img.convert("RGB")

    # # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    # if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
    #     # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
    #     alpha = img.convert("RGBA").split()[-1]

    #     # Create a new background image of our matt color.
    #     # Must be RGBA because paste requires both images have the same format
    #     # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
    #     bg = Image.new("RGBA", img.size, bg_color + (255,))
    #     bg.paste(img, mask=alpha)
    #     return bg

    # else:
    #     return img


@click.command("autocrop")
@click.argument("file", type=click.File(mode="rb"))
def autocrop_cmd(file: click.File):
    path = Path(file.name)
    with Image.open(file) as img:
        output_path = Path(f"{path.parent / path.stem}.cropped.png")
        out = autocrop(img)
        out.save(output_path)
        fs.clone_exif(path, output_path)
        fs.clone_stat(path, output_path)


@click.command("removebg")
@click.argument("file", type=click.File(mode="rb"))
def removebg_cmd(file: click.File):
    path = Path(file.name)

    with Image.open(file) as img:
        output_path = Path(f"{path.parent / path.stem}.removebg{path.suffix}")
        out = autocrop(remove_background(img))

        if output_path.suffix.lower() not in (".png", ".tiff", ".tif"):
            out = remove_transparency(out)

        out.save(output_path)
        fs.clone_exif(path, output_path)
        fs.clone_stat(path, output_path)


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
