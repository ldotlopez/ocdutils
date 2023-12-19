#! /bin/env python3

# Copyright (C) 2022- Luis López <luis@cuarentaydos.com>
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


# pip install appdirs salesforce-lavis
# https://github.com/salesforce/LAVIS#image-captioning


import logging
import os
import pickle
from pathlib import Path
from typing import Literal

import appdirs
import torch
from lavis.models import load_model_and_preprocess
from PIL import Image

from . import ImageDescriptor

LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get("LAVIS_DEFAULT_MODEL", "base_coco")
DEFAULT_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_default_captioner = None


def get_default_captioner():
    global _default_captioner

    if _default_captioner is None:
        _default_captioner = Captioner()

    return _default_captioner


def with_cache(fn, *, filepath):
    try:
        with open(filepath, "rb") as fh:
            return pickle.load(fh)

    except FileNotFoundError:
        pass

    ret = fn()
    with open(filepath, "wb") as fh:
        pickle.dump(ret, fh)

    return ret


class LAVIS:
    def __init__(
        self,
        device: Literal["cuda"] | Literal["cpu"] | None = DEFAULT_DEVICE,
        model: str | None = DEFAULT_MODEL,
    ):
        device = device or DEFAULT_DEVICE
        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
            LOGGER.warning("cuda is not available in this system, fallback to cpu")

        model = model or DEFAULT_MODEL

        self.device = torch.device(device)
        LOGGER.debug(f"Init device: {self.device!r}")

        self.model, self.vis_processors = self._load_model_and_preprocess(model)

    def _load_model_and_preprocess(self, model: str, *, cache: bool = True):
        cache_dirpath = appdirs.user_cache_dir("captionimg")
        os.makedirs(cache_dirpath, exist_ok=True)

        cache_filepath = f"{cache_dirpath}/{model}.{self.device.type}.bin"

        def from_lavis():
            m, p, _ = load_model_and_preprocess(
                name="blip_caption",
                model_type=model,
                is_eval=True,
                device=self.device,
            )
            return m, p

        def from_cache():
            with open(cache_filepath, "rb") as fh:
                return pickle.load(fh)

        def save_cache(m, p):
            with open(cache_filepath, "wb") as fh:
                pickle.dump((m, p), fh)

        if cache:
            try:
                m, p = from_cache()
                LOGGER.debug(f"model and processors loaded from '{cache_filepath}'")
                return m, p

            except FileNotFoundError:
                pass

        LOGGER.debug("loading model and processors for first time, may take a while")
        m, p, _ = load_model_and_preprocess(
            name="blip_caption",
            model_type=model,
            is_eval=True,
            device=self.device,
        )
        LOGGER.debug("model and processors loaded")

        if cache:
            save_cache(m, p)
            LOGGER.debug(f"model and preprocess saved to '{cache_filepath}'")

        return m, p

    def describe(self, file: Path) -> str:
        img = Image.open(file)
        if isinstance(image, (str, Path)):
            image = Image.open(image)

        image = image.convert("RGB")
        image = self.vis_processors["eval"](image).unsqueeze(0).to(self.device)
        return self.model.generate({"image": image})[0]
