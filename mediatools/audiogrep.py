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


import fnmatch
import hashlib
import logging
import sys
from collections.abc import Iterable
from pathlib import Path

import appdirs
import click

from .lib import filesystem as fs
from .transcribe import JSONFmt, SrtFmt, SrtTimeFmt, Transcription, transcribe

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


def _checksum(fh) -> str:
    m = hashlib.sha1()

    curr = fh.tell()
    fh.seek(0)
    while buff := fh.read():
        m.update(buff)
    fh.seek(curr)

    return m.hexdigest()


def grep(
    pattern: str, file: Path, transcribe_backend: str | None = None
) -> Iterable[tuple[int, str]]:
    with open(file, mode="rb") as fh:
        cs = _checksum(fh)

    cachefile = Path(appdirs.user_cache_dir(f"transcriptions/{cs[0]}/{cs[0:2]}/{cs}"))
    srtfile = fs.change_file_extension(file, "srt")

    if cachefile.exists():
        _LOGGER.debug(f"transcription found in cache ({cachefile!s})")
        transcription = JSONFmt.loads(cachefile.read_text())

    elif srtfile.exists():
        _LOGGER.debug(f"transcription found in sidecar file ({srtfile!s})")
        transcription = SrtFmt.loads(srtfile.read_text())

    else:
        _LOGGER.debug(f"transcription not found in cache or not updated")
        transcription = transcribe(file, backend=transcribe_backend)
        cachefile.parent.mkdir(exist_ok=True, parents=True)
        cachefile.write_text(JSONFmt.dumps(transcription))

    yield from _grep(pattern, transcription)


def _grep(pattern: str, transcription: Transcription) -> Iterable[tuple[int, str]]:
    pattern = f"*{pattern}*"
    for s in transcription.segments:
        if fnmatch.fnmatch(s.text, pattern):
            yield (s.start, s.text)


@click.command("agrep")
@click.option("--transcribe-backend")
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.argument("pattern", type=str)
@click.argument("files", type=Path, nargs=-1, required=True)
def audiogrep_cmd(
    pattern: str,
    files: list[Path],
    recursive: bool,
    transcribe_backend: str | None = None,
):
    for file in fs.iter_files_in_targets(files, recursive=recursive):
        for ms, text in grep(pattern, file, transcribe_backend=transcribe_backend):
            msstr = SrtTimeFmt.int_to_str(ms)
            print(f"{file} @ {msstr}: {text}")


def main():
    return audiogrep_cmd()


if __name__ == "__main__":
    sys.exit(main())
