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
    embeddings,
    filesystemfixes,
    formats,
    generativeimages,
    imgedit,
    mediahash,
    motionphotos,
    sidecars,
    texttransform,
)
from .lib import log

log.infect(config={"mediatools": "INFO"})


def logging_options(fn):
    fn = click.option("-v", "verbose", count=True, help="Increase log level")(fn)
    fn = click.option("-q", "quiet", count=True, help="Decrease log level")(fn)

    return fn


@click.group("multitool")
@logging_options
def multitool(verbose: int = 0, quiet: int = 0):
    log.setup_log_level(verbose=verbose, quiet=quiet)
    pass


multitool.add_command(filesystemfixes.fix_extensions_cmd)
multitool.add_command(sidecars.sidecars_cmd)


@click.group("mediatool")
@logging_options
def mediatool(verbose: int = 0, quiet: int = 0):
    log.setup_log_level(verbose=verbose, quiet=quiet)
    pass


mediatool.add_command(audiogrep.audiogrep_cmd)
mediatool.add_command(imgedit.imgedit_cmd)
mediatool.add_command(formats.formats_cmd)
mediatool.add_command(contentawareduplicates.find_duplicates_cmd)
mediatool.add_command(mediahash.media_hash_cmd)
mediatool.add_command(motionphotos.motionphoto_cmd)


@click.group("glados")
@logging_options
def glados(verbose: int = 0, quiet: int = 0):
    log.setup_log_level(verbose=verbose, quiet=quiet)
    pass


glados.add_command(audiotranscribe.transcribe_cmd)
glados.add_command(embeddings.embeddings_cmd)
glados.add_command(texttransform.rewrite_cmd)
glados.add_command(texttransform.translate_cmd)
glados.add_command(texttransform.summarize_cmd)
glados.add_command(generativeimages.generate_cmd)
glados.add_command(generativeimages.describe_cmd)


@click.group()
@logging_options
def main(quiet: int = 0, verbose: int = 0):
    # Whop, don't handle log level here. It can end duplicated
    # log.setup_log_level(quiet=quiet, verbose=verbose)
    pass


main.add_command(glados)
main.add_command(mediatool)
main.add_command(multitool)
