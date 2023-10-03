import fnmatch
import hashlib
import logging
import sys
from collections.abc import Iterable
from pathlib import Path

import appdirs
import click

from .lib import filesystem as fs
from .transcribe import JSONCodec, SrtCodec, SrtTimeCodec, Transcription, transcribe

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
        transcription = JSONCodec.loads(cachefile.read_text())

    elif srtfile.exists():
        _LOGGER.debug(f"transcription found in sidecar file ({srtfile!s})")
        transcription = SrtCodec.loads(srtfile.read_text())

    else:
        _LOGGER.debug(f"transcription not found in cache or not updated")
        transcription = transcribe(file, backend=transcribe_backend)
        cachefile.parent.mkdir(exist_ok=True, parents=True)
        cachefile.write_text(JSONCodec.dumps(transcription))

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
            msstr = SrtTimeCodec.as_str(ms)
            print(f"{file} @ {msstr}: {text}")


def main():
    return audiogrep_cmd()


if __name__ == "__main__":
    sys.exit(main())
