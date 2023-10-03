import hashlib
import logging
import sys
from pathlib import Path

import appdirs
import click

from .lib import filesystem as fs
from .transcribe import JSONCodec, SrtCodec, Transcription, transcribe

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


def grep(pattern: str, file: Path, transcribe_backend: str | None = None) -> list[str]:
    with open(file, mode="rb") as fh:
        cs = _checksum(fh)

    cachefile = Path(appdirs.user_cache_dir(f"transcriptions/{cs[0]}/{cs[0:2]}/{cs}"))

    if not cachefile.exists():
        _LOGGER.debug(f"transcription not found in cache or not updated")
        transcription = transcribe(file, backend=transcribe_backend)
        cachefile.parent.mkdir(exist_ok=True, parents=True)
        cachefile.write_text(JSONCodec.encode(transcription))

    else:
        _LOGGER.debug(f"transcription found in cache ({cachefile!s})")
        transcription = JSONCodec.decode(cachefile.read_text())

    return _grep(pattern, transcription.text)


def _grep(pattern: str, buffer: str, **kwargs) -> list[str]:
    return []


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
        grep(pattern, file, transcribe_backend=transcribe_backend)


def main():
    return audiogrep_cmd()


if __name__ == "__main__":
    sys.exit(main())
