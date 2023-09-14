#!/usr/bin/env python3

import argparse
import dataclasses
import itertools
import json
import logging
import os.path
import sys
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import imagehash
import magic

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

_DEFAULT_HASH_SIZE = 16

PathOrStr = Path | str


def as_posix_path(path: PathOrStr) -> str:
    if isinstance(path, Path):
        return path.as_posix()

    elif isinstance(path, str):
        return path

    else:
        raise TypeError(type(path))


def walk_files(
    targets, filter_fn: Callable[[Path], bool] | None = None
) -> Iterator[Path]:
    for target in targets:
        target = Path(target)

        if target.is_file():
            yield target

        else:
            for dirpath, dirnames, filenames in os.walk(target):
                dirpath = Path(dirpath)
                ret = (dirpath / x for x in filenames)
                if filter_fn:
                    ret = (path for path in ret if filter_fn(path))

                yield from ret


def calculate_hash(path: PathOrStr, hash_size: int = _DEFAULT_HASH_SIZE):
    """
    See https://github.com/JohannesBuchner/imagehash#example-2-art-dataset
    """
    with imagehash.Image.open(as_posix_path(path)) as img:
        return str(imagehash.phash(img, hash_size=hash_size))


def group_paths_by_hash(
    files: Iterator[Path], *, hash_size: int = _DEFAULT_HASH_SIZE
) -> list[list[Path]]:
    groups: dict[str, list[Path]] = {}

    for file in files:
        mime = magic.from_file(as_posix_path(file), mime=True)
        if not mime.startswith("image/"):
            _LOGGER.info(f"'{file!s}': not an image ({mime})")
            continue

        h = calculate_hash(file, hash_size=hash_size)
        groups[h] = groups.get(h, []) + [file]

        _LOGGER.debug(f"'{file!s}' hash: {h}")

    return list(groups.values())


def similarity_matrix(medias: list[Path]) -> list[tuple[Path, Path, float]]:
    def _normalized_histogram(pathstr):
        img = cv2.imread(pathstr)

        # Convertir a escala de grises
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Calcular los histogramas
        hist = cv2.calcHist([gray_img], [0], None, [256], [0, 256])

        # Normalizar los histogramas
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist

    hists = [_normalized_histogram(media.as_posix()) for media in medias]

    def _similarity_matrix():
        for idx1 in range(len(medias) - 1):
            for idx2 in range(idx1 + 1, len(medias)):
                yield medias[idx1], medias[idx2], cv2.compareHist(
                    hists[idx1], hists[idx2], cv2.HISTCMP_CORREL
                )

    return list(_similarity_matrix())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hash-size", default=_DEFAULT_HASH_SIZE, type=int)
    parser.add_argument("--min-similarity", default=0.90, type=float)
    parser.add_argument("target", nargs="+")

    args = parser.parse_args()

    files = walk_files(args.target)
    groups = group_paths_by_hash(files, hash_size=args.hash_size)
    groups = [gr for gr in groups if len(gr) > 1]

    print(f"Found {len(groups)} ")
    for idx, gr in enumerate(groups):
        print(f"Group #{idx+1}: {len(gr)} elements")

        for p1, p2, correlation in similarity_matrix(gr):
            print(f"{correlation} '{p1!s}' '{p2!s}'")


if __name__ == "__main__":
    main()
