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


import contextlib
import enum
import logging
import os
import random
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterator
from fnmatch import fnmatch
from pathlib import Path

import magic

from . import spawn

_DRY_RUN = os.environ.get("MEDIATOOLS_DRY_RUN", "") in ["1", "yes", "true"]
_LOGGER = logging.getLogger(__name__)


def as_posix(path: Path | str) -> str:
    return Path(path).as_posix()


def get_file_extension(file: Path) -> str:
    return file.suffix.lstrip(".")


def walk(dirpath: Path):
    if not dirpath.is_dir():
        raise NotADirectoryError(dirpath)

    for root, dirs, files in os.walk(dirpath.as_posix()):
        rootp = Path(root)
        dirs2 = [rootp / x for x in dirs]
        files2 = [rootp / x for x in files]

        yield root, dirs2, files2

        to_exclude = set(dirs) - {x.name for x in dirs2}
        for x in to_exclude:
            dirs.remove(x)


def walk_multiple(dirpaths: list[Path]):
    for dirpath in dirpaths:
        try:
            yield from walk(dirpath)
        except NotADirectoryError:
            _LOGGER.warning(f"f{dirpath}: not a directory")


def iter_files_in_targets(
    targets,
    *,
    recursive: bool = False,
    error_handler: Callable[[str], None] | None = None,
):
    def _error_handler(msg):
        print(msg, file=sys.stderr)

    error_handler = error_handler or _error_handler

    for item in targets:
        if not item.exists():
            error_handler(f"{item.as_posix()}: no such file or directory")

        elif item.is_file():
            yield item

        elif item.is_dir():
            if recursive:
                for _, _, files in walk(item):
                    yield from files

            else:
                error_handler(f"{item.as_posix()}: Is a directory, use --recursive?")

        else:
            error_handler(f"{item.as_posix()}: unknow type")


def file_matches_mime(filepath: Path, mime_glob: str) -> bool:
    mime = file_mime(filepath)
    return fnmatch(mime, mime_glob)


def file_mime(filepath: Path) -> str:
    return magic.from_file(filepath.as_posix(), mime=True)


def _random_string(len: int = 6) -> str:
    haystack = "qwertyuiopasdfghjklzxcvbnm1234567890"
    return "".join([random.choice(haystack) for _ in range(len)])


def temp_dirpath():
    return Path(tempfile.mkdtemp())


@contextlib.contextmanager
def temp_dirpath_ctx(*args, **kwargs):
    tmpd = temp_dirpath(*args, **kwargs)
    yield tmpd
    shutil.rmtree(tmpd)


def temp_filename(file: Path, *, suffix: str | None = None):
    fd, name = tempfile.mkstemp(suffix or file.suffix)
    os.close(fd)

    return Path(name)


@contextlib.contextmanager
def temp_filepath_ctx(*args, **kwargs):
    tmpf = temp_filename(*args, **kwargs)
    yield tmpf
    tmpf.unlink()


def posible_filenames(file: Path) -> Iterator[Path]:
    yield file
    while True:
        yield alternative_filename(file)


def alternative_filename(file: Path) -> Path:
    return file.parent / (file.stem + "." + _random_string() + file.suffix)


def change_file_extension(file: Path, extension: str) -> Path:
    return file.parent / (file.stem + "." + extension)


def clone_stat(src: Path, dst: Path) -> None:
    if not _DRY_RUN:
        shutil.copymode(src, dst)
        shutil.copystat(src, dst)
    else:
        print(f"touch --reference='{src}' '{dst}'")
        print(f"chmod --reference='{src}' '{dst}'")


def clone_exif(src: Path, dst: Path) -> None:
    cmdl = [
        "exiftool",
        "-preserve",
        "-overwrite_original",
        "-tagsFromFile",
        src.as_posix(),
        dst.as_posix(),
    ]
    if not _DRY_RUN:
        spawn.run(cmdl)
    else:
        print(" ".join(cmdl))


def matches_mime(filepath: Path, mime_glob: str) -> bool:
    mime = magic.from_file(filepath.as_posix(), mime=True)
    return fnmatch(mime, mime_glob)


def safe_write_text(text: str, destination: Path, overwrite: bool = False) -> Path:
    if destination.exists() and not overwrite:
        destination = alternative_filename(destination)

    destination.write_text(text)

    return destination


def safe_write_bytes(b: bytes, destination: Path, overwrite: bool = False) -> Path:
    if destination.exists() and not overwrite:
        destination = alternative_filename(destination)

    destination.write_bytes(b)

    return destination


class _CopyOrMoveOperation(enum.Enum):
    COPY = enum.auto()
    MOVE = enum.auto()


def _safe_cp_or_mv(
    source: Path,
    destination: Path,
    *,
    operation: _CopyOrMoveOperation,
    overwrite: bool = False,
) -> Path:
    if not destination.parent.is_dir():
        if _DRY_RUN:
            print(f"mkdir -p '{destination.parent}'")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)

    for dst in posible_filenames(destination):
        if not overwrite and dst.exists():
            continue

        if operation is _CopyOrMoveOperation.COPY:
            if _DRY_RUN:
                print(f"cp -P '{source}' '{dst}'")
            else:
                shutil.copy2(source, dst)

        elif operation is _CopyOrMoveOperation.MOVE:
            if _DRY_RUN:
                print(f"mv '{source}' '{dst}'")
            else:
                shutil.move(source, dst)

        else:
            raise NotADirectoryError(operation)

        break

    return dst


def safe_cp(source: Path, destination: Path, *, overwrite: bool = False) -> Path:
    return _safe_cp_or_mv(
        source, destination, operation=_CopyOrMoveOperation.COPY, overwrite=overwrite
    )


def safe_mv(source: Path, destination: Path, *, overwrite: bool = False) -> Path:
    return _safe_cp_or_mv(
        source, destination, operation=_CopyOrMoveOperation.MOVE, overwrite=overwrite
    )
