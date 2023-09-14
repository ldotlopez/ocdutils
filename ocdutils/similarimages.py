#!/usr/bin/env python3

import dataclasses
import itertools
import json
import logging
import os.path
from collections.abc import Iterable
from pathlib import Path
from typing import Dict, List

import imagehash

_LOGGER = logging.getLogger(__name__)
_DEFAULT_HASH_SIZE = 16


def calculate_hash(filepath: Path, *, hash_size=_DEFAULT_HASH_SIZE) -> str:
    with imagehash.Image.open(filepath) as img:
        return str(imagehash.average_hash(img, hash_size))


def build_hash_dict(
    collection: Iterable[Path], *, hash_size=_DEFAULT_HASH_SIZE
) -> dict[str, list[Path]]:
    hashes = {}
    for imgpath in collection:
        ih = calculate_hash(imgpath, hash_size=hash_size)
        if ih not in hashes:
            hashes[ih] = [imgpath]
        else:
            hashes[ih].append(imgpath)

    return hashes


def walk(targets):
    for target in targets:
        target = Path(target)
        if target.is_file():
            yield target

        else:
            for dirpath, dirnames, filenames in os.walk(target):
                dirpath = Path(dirpath)
                yield from (dirpath / x for x in filenames)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SimilarImagesGroup):
            objd = dataclasses.asdict(obj)
            objd["paths"] = [str(x) for x in objd["paths"]]
            return objd

        return json.JSONEncoder.default(self, obj)


@dataclasses.dataclass
class SimilarImagesGroup:
    hash: str
    paths: list[Path]


class SimilarImages:
    def __init__(self, hash_size: int = _DEFAULT_HASH_SIZE):
        self.hash_size = hash_size

    def search_similar(self, collection: list[Path | str]) -> list[SimilarImagesGroup]:
        collection_paths = (Path(x) for x in collection)
        images = (
            x for x in collection_paths if x.suffix.lower()[1:] in ["jpg", "jpeg"]
        )

        _LOGGER.debug(
            f"search for similar images using {self.hash_size} bytes hash size"
        )

        hashes = build_hash_dict(images, hash_size=self.hash_size)
        if not hashes:
            return []

        _LOGGER.debug(f"refine search using {self.hash_size*2} bytes hash size")

        hashes = build_hash_dict(
            itertools.chain().from_iterable(hashes.values()),
            hash_size=self.hash_size * 2,
        )

        return [
            SimilarImagesGroup(hash=ih, paths=imgs)
            for ih, imgs in hashes.items()
            if len(imgs) > 1
        ]

    def run_for_machines(self, collection: list[Path | str]) -> str:
        return JSONEncoder(indent=4).encode(self.search_similar(collection))

    def run_for_humans(self, collection: list[Path | str]):
        res = self.search_similar(collection)
        for gr in res:
            print(f"[*] Found {len(gr.paths)} similar images with hash {gr.hash}")
            for p in gr.paths:
                print(f"    '{p}'")


def main():
    import argparse

    logging.basicConfig()
    _LOGGER.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--hash-size", default=_DEFAULT_HASH_SIZE, type=int)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("targets", nargs="+")

    args = parser.parse_args()

    si = SimilarImages(hash_size=args.hash_size)
    collection = walk(args.targets)
    if args.json:
        print(si.run_for_machines(collection))
    else:
        si.run_for_humans(collection)


if __name__ == "__main__":
    main()
