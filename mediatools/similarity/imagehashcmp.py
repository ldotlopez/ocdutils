import io
import itertools
import logging
from collections.abc import Callable
from concurrent import futures
from pathlib import Path

import click
import imagehash

from ..lib import filesystem as fs

UpdateFn = Callable[[Path, str], None]


_LOGGER = logging.getLogger(__name__)
_DEFAULT_HASH_SIZE = 16


def imagehash_frompath(path: Path, *, hash_size=_DEFAULT_HASH_SIZE) -> str:
    # User average_hash or phash?
    with imagehash.Image.open(fs.as_posix(path)) as img:
        return str(imagehash.average_hash(img, hash_size))


def imagehash_frombytes(data: bytes, *, hash_size=_DEFAULT_HASH_SIZE) -> str:
    with imagehash.Image.open(io.BytesIO(data)) as img:
        # FIXME: use average_hash or phash ?
        return str(imagehash.average_hash(img, hash_size))


@click.command("find-duplicates")
@click.option(
    "--hash-size",
    type=int,
    default=_DEFAULT_HASH_SIZE,
    help="powers of 2, lower values more false positives",
)
@click.argument("targets", nargs=-1, required=True, type=Path)
def find_duplicates_cmd(targets: list[Path], hash_size: int):
    click.echo(f"Reading contents of {len(targets)} targets...")
    images = [x for x in fs.iter_files(*targets) if fs.file_matches_mime(x, "image/*")]
    click.echo(f"Found {len(images)} images")

    with click.progressbar(length=len(images), label="Calculating image hashes") as bar:
        dupes = find_duplicates(
            images,
            hash_size=hash_size,
            update_fn=lambda img, imghash: bar.update(1, img),
        )

    for idx, (imghash, gr) in enumerate(dupes):
        click.echo(f"Group {idx+1}  ({imghash})")
        for img in gr:
            click.echo(f"  '{click.format_filename(img)}'")


def find_duplicates(
    images: list[Path],
    hash_size: int | None = _DEFAULT_HASH_SIZE,
    update_fn: UpdateFn | None = None,
):
    def _g(it):
        return it
        return [x for x in it]

    def map_and_update(item):
        ret = imagehash_frompath(item, hash_size=hash_size)
        if update_fn:
            update_fn(item, ret)

        return ret

    with futures.ThreadPoolExecutor() as executor:
        hashes = executor.map(map_and_update, images)

    # Zip
    zip_g = _g(zip(hashes, images))

    # Sort by hash
    sorted_g = _g(sorted(zip_g, key=lambda x: x[0]))

    # group by hash and strip imghashes
    grouped_g = _g(
        (imghash, [img for _, img in gr])
        for imghash, gr in itertools.groupby(sorted_g, lambda x: x[0])
    )
    # Strip unique items
    groups_g = _g(((imghash, gr) for imghash, gr in grouped_g if len(gr) > 1))

    return list(groups_g)
