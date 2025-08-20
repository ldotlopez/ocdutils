import shlex
import subprocess
from math import floor, sqrt
from pathlib import Path
from typing import Any, cast

import imagehash
import rich
import rich.progress
import rich_click as click
from PIL import Image

from ..consts import FILE_OPERATIONS_CACHE_PATH, RICH_PROGRESS_ENABLED
from ..lib.clilib import target_options
from ..lib.fileopcache import Codecs, FileOperationCache, Validators
from ..lib.fslib import file_matches_mime, iter_files


class AverageHashStore(FileOperationCache):
    TABLE = "average_hash_{size}_v1"
    DEFAULT_HASH_SIZE = 16

    def __init__(
        self,
        file: Path | None = None,
        *,
        size: int = 16,
    ):
        if floor(sqrt(size)) ** 2 != size:
            raise ValueError()

        self.TABLE = self.TABLE.format(size=size)
        self.size = size
        super().__init__(file)

    def get(self, file: Path) -> str:
        return cast(str, super().get(file.resolve()))

    def calculate_validator(self, file: Path) -> str:
        return Validators.fast_checksum(file)

    def calculate_value(self, file: Path) -> str:
        with Image.open(file.as_posix()) as img:
            # self.size should be the linear dimension (e.g., 16 for 16x16)
            return str(imagehash.average_hash(img, hash_size=self.size))

    def serialize(self, native: Any) -> bytes:
        return Codecs.json_serialize(native)

    def unserialize(self, raw: bytes) -> Any:
        return Codecs.json_unserialize(raw)


@click.command
@click.option("--no-cache", is_flag=True, default=False)
@click.option("--hash-size", type=int, default=AverageHashStore.DEFAULT_HASH_SIZE)
@click.option("--cache-db", type=Path, default=FILE_OPERATIONS_CACHE_PATH)
@target_options
def img_hash_cmd(
    targets,
    *,
    recursive: bool = False,
    pre_scan: bool = False,
    no_cache: bool = False,
    hash_size: int = AverageHashStore.DEFAULT_HASH_SIZE,
    cache_db: Path | None = None,
):
    """Compute the avg hash for images"""

    files = iter_files(*targets, recursive=recursive)
    images = (f for f in files if file_matches_mime(f, "image/*"))
    if pre_scan:
        images = list(images)

    store = AverageHashStore(cache_db if not no_cache else None, size=hash_size)

    for img in rich.progress.track(images, disable=RICH_PROGRESS_ENABLED):
        h = store.get(img)
        rich.print(f"'{img}': {h}")


@click.command
@click.option("--hash-size", type=int, default=AverageHashStore.DEFAULT_HASH_SIZE)
@click.option("-x", "--command", type=str)
@click.option("--cache-db", type=Path, default=FILE_OPERATIONS_CACHE_PATH)
@click.option("--no-cache", is_flag=True, default=False)
@target_options
def find_duplicates_cmd(
    targets,
    *,
    recursive: bool = False,
    pre_scan: bool = False,
    no_cache: bool = False,
    command: str | None = None,
    hash_size: int = AverageHashStore.DEFAULT_HASH_SIZE,
    cache_db: Path | None = None,
):
    """Find duplicated images."""

    if command:
        cmd_for_groups = shlex.split(command)
    else:
        cmd_for_groups = []

    files = iter_files(*targets, recursive=recursive)
    images = (f for f in files if file_matches_mime(f, "image/*"))
    if pre_scan:
        images = list(images)  # type: ignore[assignment]

    store = AverageHashStore(cache_db if not no_cache else None, size=hash_size)
    hashes: dict[str, list[Path]] = {}
    for img in rich.progress.track(
        images, disable=RICH_PROGRESS_ENABLED, description="Calculating images hashes"
    ):
        h = store.get(img)
        if h not in hashes:
            hashes[h] = []
        hashes[h].append(img)

    duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
    if not duplicates:
        rich.print("No duplicates found")
        return

    rich.print(f"Found {len(duplicates)} groups of duplicates")
    for idx, (h, paths) in enumerate(duplicates.items()):
        if cmd_for_groups:
            subprocess.run(cmd_for_groups + [x.as_posix() for x in paths])
        else:
            rich.print(f"Group #{idx+1}")
            for path in paths:
                rich.print(f"  {path}")
