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


from __future__ import annotations

import binascii
import itertools
import logging
from collections.abc import Iterable
from pathlib import Path

import cv2

from . import ImageDuplicateFinder, ImageGroup

# from ..lib.hashing import crc32_hash_frombytes

LOGGER = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.90


# @dataclass
# class Cluster:
#     fuzzyhash: str
#     items: list

#     # @classmethod
#     # def fromdict(cls, data: dict) -> SimilarImagesGroup:
#     #     return cls(hash=data["hash"], paths=[Path(p) for p in data["paths"]])


class CV2Matcher(ImageDuplicateFinder):
    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        if threshold < 0 or threshold > 1:
            raise ValueError("threshold must be between 0 and 1")

        self.threshold = threshold

    def find(self, files: list[Path]):
        images = [x for x in files if x.suffix.lower()[1:] in ["jpg", "jpeg"]]

        return calculate_groups(images, threshold=self.threshold)

    def similarity(self, img1: Path, img2: Path) -> float:
        return calculate_similarity(img1, img2)


def calculate_correlations(images: list[Path]) -> Iterable[tuple[Path, Path, float]]:
    histograms = [abs(normalized_histogram_frompath(img)) for img in images]

    for idx1, img1 in enumerate(images[:-1]):
        for idx2, img2 in enumerate(images[idx1 + 1 :]):
            correl = cv2.compareHist(
                histograms[idx1], histograms[idx1 + idx2], cv2.HISTCMP_CORREL
            )
            # LOGGER.warning(f"[{correl}] {img1.name} <-> {img2.name}")
            yield img1, img2, correl


def calculate_groups(
    images: list[Path], *, threshold: float = DEFAULT_THRESHOLD
) -> list[list[Path]]:
    groups = []

    # Transformate into groups
    for img1, g in itertools.groupby(calculate_correlations(images), lambda x: x[0]):
        if matching := [img2 for _, img2, correl in g if correl > threshold]:
            # LOGGER.warning(f"{img1.name} matches with {len(matching)}")
            groups.append([img1] + matching)
        else:
            # LOGGER.warning(f"{img1.name} has no matches")
            pass

    return groups


def calculate_similarity(a: Path, b: Path):
    hist_a = normalized_histogram_frompath(a)
    hist_b = normalized_histogram_frompath(b)

    similarity = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return similarity


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


# @click.command("calculate")
# @click.argument("filepaths", required=True, nargs=-1, type=Path)
# def calculate_cmd(filepaths: list[Path]):
#     for p in filepaths:
#         try:
#             val = hex_histogram_frompath(p)
#         except ValueError as e:
#             LOGGER.error(f"{p}: {e}")
#             continue

#         print(f"{p}: {val}")


# @click.command("similarity")
# @click.argument("file_a", type=Path)
# @click.argument("file_b", type=Path)
# @click.option("--quiet", "-q", is_flag=True, default=False)
# @click.option("--threshold", "-t", type=float, default=_DEFAULT_THRESHOLD)
# def similarity_cmd(file_a, file_b, threshold, quiet):
#     val = calculate_similarity(file_a, file_b)

#     if not quiet:
#         print(f"similarity: {val*100:.5f}%")

#     if threshold <= val:
#         sys.exit(0 if val >= threshold else 1)


# @click.command("group-by-histogram")
# @click.option("--target", "-t", "targets", required=True, multiple=True, type=Path)
# @click.option("--threshold", type=float, default=_DEFAULT_THRESHOLD)
# def group_cmd(targets, threshold):
#     filelist = [Path(x) for x in fs.iter_files(*targets)]
#     images = [filepath_matches_mime(x, "image/*") for x in filelist]

#     groups = group(filelist, threshold=threshold)
#     for idx, cluster in enumerate(groups):
#         print(f"[*] Group #{idx+1} (hash: {cluster.fuzzyhash})")
#         for p in cluster.items:
#             print(f"    - '{p}'")
