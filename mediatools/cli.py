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


import click

from . import (
    audiogrep,
    audiotranscribe,
    contentawareduplicates,
    filesystemfixes,
    formats,
    imgdescribe,
    imgedit,
    motionphotos,
    sidecars,
    texttransform,
)
from .lib import log

# from .similarity import imagehashcmp

log.infect()


@click.group("multitool")
def multitool():
    pass


multitool.add_command(filesystemfixes.fix_extensions_cmd)
multitool.add_command(sidecars.sidecars_cmd)


@click.group("mediatool")
def mediatool():
    pass


mediatool.add_command(audiogrep.audiogrep_cmd)
mediatool.add_command(imgedit.imgedit_cmd)
mediatool.add_command(formats.formats_cmd)
mediatool.add_command(contentawareduplicates.find_duplicates_cmd)
mediatool.add_command(motionphotos.motionphoto_cmd)


@click.group("glados")
def glados():
    pass


glados.add_command(audiotranscribe.transcribe_cmd)
glados.add_command(texttransform.rewrite_cmd)
glados.add_command(imgdescribe.describe_cmd)


@click.group()
def main():
    pass


main.add_command(glados)
main.add_command(mediatool)
main.add_command(multitool)
