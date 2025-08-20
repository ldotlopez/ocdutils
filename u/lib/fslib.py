import logging
import os
import random
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from fnmatch import fnmatch
from math import log
from pathlib import Path
from typing import Callable, Iterator

import magic

LOGGER = logging.getLogger(__name__)

_DRY_RUN = False

if (_WHICH_TEST := shutil.which("exiftool")) is None:
    raise SystemError("exiftool not in PATH")

EXIFTOOL_PATH: str = _WHICH_TEST


def iter_files(
    *paths: Path,
    recursive: bool = False,
    sort: bool = False,
    error_handler: Callable[[Path], None] | None = None,
) -> Iterator[Path]:
    if error_handler:
        LOGGER.warning("error_handler not supported")

    def iter_one(path: Path) -> Iterator[Path]:
        if not path.exists():
            LOGGER.error(f"'{path}': not such file or directory")
            return

        if path.is_file():
            yield path

        elif path.is_dir():
            children = path.iterdir()
            if sort:
                children = sorted(children)

            for c in children:
                if c.is_file():
                    yield c
                elif c.is_dir():
                    yield from iter_one(c)
                else:
                    LOGGER.warning(f"'{path}': unknown type")

        else:
            LOGGER.warning(f"'{path}': unknown type")

    if sort:
        paths = tuple(sorted(paths))  # Convert back to tuple to maintain type

    for p in paths:
        yield from iter_one(p)


def file_matches_mime(filepath: Path, mime_glob: str) -> bool:
    mime = file_mime(filepath)
    return fnmatch(mime, mime_glob)


def file_mime(filepath: Path) -> str:
    return magic.from_file(filepath.as_posix(), mime=True)


def _random_string(len: int = 6) -> str:
    haystack = "qwertyuiopasdfghjklzxcvbnm1234567890"
    return "".join([random.choice(haystack) for _ in range(len)])


# --- Temp files and paths, with or without contexts --- #
def temp_dirpath():
    return Path(tempfile.mkdtemp())


@contextmanager
def temp_dirpath_ctx(*args, **kwargs):
    tmpd = temp_dirpath(*args, **kwargs)
    yield tmpd
    shutil.rmtree(tmpd)


def temp_filepath(*args, **kwargs):
    fd, name = tempfile.mkstemp(*args, **kwargs)
    os.close(fd)

    return Path(name)


@contextmanager
def temp_filepath_ctx(*args, **kwargs):
    tmpf = temp_filepath(*args, **kwargs)
    yield tmpf
    tmpf.unlink()


# def temp_filepath(file: Path, *, suffix: str | None = None):
#     fd, name = tempfile.mkstemp(suffix or file.suffix)
#     os.close(fd)

#     return Path(name)


# @contextmanager
# def temp_filepath_ctx(file: Path, *, suffix: str | None = None):
#     tmpf = temp_filepath(file, suffix=suffix)
#     yield tmpf
#     tmpf.unlink()


# --- Alter filepaths --- #
def change_file_extension(file: Path, extension: str) -> Path:
    return file.parent / (file.stem + "." + extension)


def posible_filenames(file: Path) -> Iterator[Path]:
    yield file
    while True:
        yield alternative_filename(file)


def alternative_filename(file: Path) -> Path:
    return file.parent / (file.stem + "." + _random_string() + file.suffix)


# --- Keeping attributes --- #


def clone_stat(src: Path, dst: Path) -> None:
    if _DRY_RUN:
        print(f"touch --reference='{src}' '{dst}'")
        print(f"chmod --reference='{src}' '{dst}'")
        return

    shutil.copymode(src, dst)
    shutil.copystat(src, dst)


def clone_exif(src: Path, dst: Path) -> None:
    cmdl = [
        EXIFTOOL_PATH,
        "-preserve",
        "-overwrite_original",
        "-tagsFromFile",
        src.as_posix(),
        dst.as_posix(),
    ]
    if not _DRY_RUN:
        print(" ".join(cmdl))
        return

    subprocess.run(cmdl)


# --- safer versions or cp and mv --- #
def safe_file_for(file: Path, *, overwrite: bool = False):
    for dst in posible_filenames(file):
        if overwrite or not dst.exists():
            return dst


import enum


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
