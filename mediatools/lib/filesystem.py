import enum
import os
import random
import shutil
import tempfile
from collections.abc import Iterator
from fnmatch import fnmatch
from pathlib import Path

import magic

from . import spawn

_DRY_RUN = os.environ.get("MEDIATOOLS_FS_EFFECTIVE_RUN", 0) != "1"


def as_posix(path: Path | str) -> str:
    return Path(path).as_posix()


def get_file_extension(file: Path) -> str:
    return file.suffix.lstrip(".")


def walk(*targets: Path):
    for target in targets:
        if target.is_file():
            yield target.parent, [], [target]

        else:
            for root, dirs, files in os.walk(target.as_posix()):
                rootp = Path(root)
                dirs2 = [rootp / x for x in dirs]
                files2 = [rootp / x for x in files]

                yield root, dirs2, files2

                to_exclude = set(dirs) - {x.name for x in dirs2}
                for x in to_exclude:
                    dirs.remove(x)


def iter_files(*targets: Path):
    for _, _, files in walk(*targets):
        yield from files


def file_matches_mime(filepath: Path, mime_glob: str) -> bool:
    mime = file_mime(filepath)
    return fnmatch(mime, mime_glob)


def file_mime(filepath: Path) -> str:
    return magic.from_file(filepath.as_posix(), mime=True)


def _random_string(len: int = 6) -> str:
    haystack = "qwertyuiopasdfghjklzxcvbnm1234567890"
    return "".join([random.choice(haystack) for _ in range(len)])


def temp_filename(file: Path) -> Path:
    fd, name = tempfile.mkstemp(file.suffix)
    os.close(fd)

    return Path(name)


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
        spawn.run(*cmdl)
    else:
        print(" ".join(cmdl))


def matches_mime(filepath: Path, mime_glob: str) -> bool:
    mime = magic.from_file(filepath.as_posix(), mime=True)
    return fnmatch(mime, mime_glob)


class _CopyOrMoveOperation(enum.Enum):
    COPY = enum.auto()
    MOVE = enum.auto()


def safe_cp_or_mv(
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
    return safe_cp_or_mv(
        source, destination, operation=_CopyOrMoveOperation.COPY, overwrite=overwrite
    )


def safe_mv(source: Path, destination: Path, *, overwrite: bool = False) -> Path:
    return safe_cp_or_mv(
        source, destination, operation=_CopyOrMoveOperation.MOVE, overwrite=overwrite
    )
