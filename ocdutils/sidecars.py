#!/usr/bin/env python3

import argparse
import itertools
import logging
import mimetypes
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

logging.basicConfig()

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


# @lru_cache
# def is_image(target: Path | str) -> bool:
#     type_, encoding = mimetypes.guess_type(target)
#     if type_ is None:
#         _LOGGER.warning(f"{target!s}: Unknow mimetype")
#         return False

#     return type_.startswith("image/")


# @lru_cache
# def is_video(target: Path | str) -> bool:
#     type_, encoding = mimetypes.guess_type(target)
#     if type_ is None:
#         _LOGGER.warning(f"{target!s}: Unknow mimetype")
#         return False

#     return type_.startswith("video/")


@lru_cache
def is_mimetype(filepath: Path | str, mimetype: str) -> bool:
    if not mimetype:
        raise ValueError(mimetype)

    type_, encoding = mimetypes.guess_type(filepath)
    if type_ is None:
        _LOGGER.warning(f"{filepath!s}: Unknow mimetype")
        return False

    if "/" not in mimetype:
        return type_.startswith(mimetype + "/")
    else:
        return type_ == mimetype


is_image = lambda x: is_mimetype(x, "image")
is_video = lambda x: is_mimetype(x, "video")


@lru_cache
def is_sidecar_for(
    image: Path | str, candidate: Path | str, ignore_case: bool = False
) -> bool:
    image_cmp = str(Path)
    candidate_cmp = str(Path)

    if ignore_case:
        image_cmp = image_cmp.lower()
        candidate_cmp = candidate_cmp.lower()

    return (
        os.path.splitext(image_cmp)[0] == os.path.splitext(candidate_cmp)[0]
    ) and is_video(candidate)


def find_sidecar_videos(
    dirpath: Path, ignore_case: bool = False
) -> list[tuple[Path, list[Path]]]:
    def _get_name(fullname: str) -> str:
        nonlocal ignore_case
        if ignore_case:
            fullname = fullname.lower()

        return os.path.splitext(fullname)[0]

    sets = {}

    for root, dirs, files in os.walk(dirpath):
        # Group files by name (without ext)
        by_name = {}
        for name, group in itertools.groupby(sorted(files), key=_get_name):
            by_name[name] = list(group)

        for name, group in by_name.items():
            # Find image in group
            images = [x for x in group if is_image(x)]
            if len(images) == 0:
                _LOGGER.info(f"{name}: No images in group")
                continue

            if len(images) > 1:
                _LOGGER.info(f"{name}: Multiple images in group")
                continue

            image = images[0]
            sidecars = [
                x for x in group if is_sidecar_for(image, x, ignore_case=ignore_case)
            ]

            root_as_str = Path(root)
            sets[root_as_str / Path(image)] = [root_as_str / Path(x) for x in sidecars]

        return list(sets.items())


def remove_file(filepath: Path, dry_run: bool = False):
    if dry_run:
        print(f"rm -f -- '{filepath}'")
    else:
        os.unlink(filepath)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("targets", nargs="+")

    args = parser.parse_args()

    for target in args.targets:
        dirpath = Path(target)
        if not dirpath.is_dir():
            _LOGGER.warning(f"{dirpath}: Skip non-directory")
            continue

        for master, sidecars in find_sidecar_videos(
            dirpath, ignore_case=args.ignore_case
        ):
            for sidecar in sidecars:
                remove_file(sidecar, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
