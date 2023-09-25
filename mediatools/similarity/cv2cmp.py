from __future__ import annotations

import binascii
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import click
import cv2

from ..lib import filesystem as fs
from ..lib.hashing import crc32_hash_frombytes

_LOGGER = logging.getLogger(__name__)
_DEFAULT_HASH_SIZE = 16
_DEFAULT_THRESHOLD = 90


@dataclass
class Cluster:
    fuzzyhash: str
    items: list

    # @classmethod
    # def fromdict(cls, data: dict) -> SimilarImagesGroup:
    #     return cls(hash=data["hash"], paths=[Path(p) for p in data["paths"]])


def hex_histogram_frompath(image_path: Path) -> str:
    hist = normalized_histogram_frompath(image_path)
    return binascii.hexlify(hist.tobytes()).decode("ascii")


def normalized_histogram_frompath(image_path: Path):
    img = cv2.imread(image_path.as_posix())
    if img is None:
        raise ValueError("cannot read image")

    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    hist = cv2.calcHist([gray_img], [0], None, [256], [0, 256])
    cv2.normalize(hist, hist)

    return hist


def calculate_similarity(a: Path, b: Path):
    hist_a = normalized_histogram_frompath(a)
    hist_b = normalized_histogram_frompath(b)

    similarity = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return similarity


def group(
    collection: list[Path], threshold: float = _DEFAULT_THRESHOLD
) -> list[Cluster]:
    images = (x for x in collection if x.suffix.lower()[1:] in ["jpg", "jpeg"])

    _LOGGER.debug("Calculating histograms")
    hists = [(image, abs(normalized_histogram_frompath(image))) for image in images]
    groups = []
    for idx1, (img1, hist1) in enumerate(hists[:-1]):
        _LOGGER.debug(f"Matching histograms for image {idx1+1}/{len(hists)} images")
        similarities = [
            (img2, cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL))
            for (img2, hist2) in hists[idx1 + 1 :]
        ]
        similarities = [(img2, sim) for (img2, sim) in similarities if sim > threshold]

        if similarities:
            groups.append(
                Cluster(
                    fuzzyhash=crc32_hash_frombytes(hist1.tobytes()),
                    items=[img1] + [img2 for img2, _ in similarities],
                )
            )

    return groups


@click.command("calculate")
@click.argument("filepaths", required=True, nargs=-1, type=Path)
def calculate_cmd(filepaths: list[Path]):
    for p in filepaths:
        try:
            val = hex_histogram_frompath(p)
        except ValueError as e:
            _LOGGER.error(f"{p}: {e}")
            continue

        print(f"{p}: {val}")


@click.command("similarity")
@click.argument("file_a", type=Path)
@click.argument("file_b", type=Path)
@click.option("--quiet", "-q", is_flag=True, default=False)
@click.option("--threshold", "-t", type=float, default=_DEFAULT_THRESHOLD)
def similarity_cmd(file_a, file_b, threshold, quiet):
    val = calculate_similarity(file_a, file_b)

    if not quiet:
        print(f"similarity: {val*100:.5f}%")

    if threshold <= val:
        sys.exit(0 if val >= threshold else 1)


@click.command("group-by-histogram")
@click.option("--target", "-t", "targets", required=True, multiple=True, type=Path)
@click.option("--threshold", type=float, default=_DEFAULT_THRESHOLD)
def group_cmd(targets, threshold):
    filelist = [Path(x) for x in fs.iter_files(*targets)]
    images = [filepath_matches_mime(x, "image/*") for x in filelist]

    groups = group(filelist, threshold=threshold)
    for idx, cluster in enumerate(groups):
        print(f"[*] Group #{idx+1} (hash: {cluster.fuzzyhash})")
        for p in cluster.items:
            print(f"    - '{p}'")
