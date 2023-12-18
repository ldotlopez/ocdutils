# pip install appdirs salesforce-lavis
# https://github.com/salesforce/LAVIS#image-captioning


import logging
import os
import pickle
from pathlib import Path
from typing import Literal

import appdirs
import click
import PIL
import torch

# from lavis.models import load_model_and_preprocess
from PIL import Image

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = "base_coco"

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


class Captioner:
    def __init__(
        self,
        device: Literal["cuda"] | Literal["cpu"] | None = None,
        model: str | None = None,
    ):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        elif device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
            LOGGER.warning("cuda is not available in this system, fallback to cpu")

        model = model or DEFAULT_MODEL

        self.device = torch.device(device)
        LOGGER.debug(f"Init device: {self.device!r}")

        # self.model, self.vis_processors = self._load_model_and_preprocess(model)

    # def _load_model_and_preprocess(self, model: str, *, cache: bool = True):
    #     cache_dirpath = appdirs.user_cache_dir("captionimg")
    #     os.makedirs(cache_dirpath, exist_ok=True)

    #     cache_filepath = f"{cache_dirpath}/{model}.{self.device.type}.bin"

    #     def from_lavis():
    #         m, p, _ = load_model_and_preprocess(
    #             name="blip_caption",
    #             model_type=model,
    #             is_eval=True,
    #             device=self.device,
    #         )
    #         return m, p

    #     def from_cache():
    #         with open(cache_filepath, "rb") as fh:
    #             return pickle.load(fh)

    #     def save_cache(m, p):
    #         with open(cache_filepath, "wb") as fh:
    #             pickle.dump((m, p), fh)

    #     if cache:
    #         try:
    #             m, p = from_cache()
    #             LOGGER.debug(f"model and processors loaded from '{cache_filepath}'")
    #             return m, p

    #         except FileNotFoundError:
    #             pass

    #     LOGGER.debug("loading model and processors for first time, may take a while")
    #     m, p, _ = load_model_and_preprocess(
    #         name="blip_caption",
    #         model_type=model,
    #         is_eval=True,
    #         device=self.device,
    #     )
    #     LOGGER.debug("model and processors loaded")

    #     if cache:
    #         save_cache(m, p)
    #         LOGGER.debug(f"model and preprocess saved to '{cache_filepath}'")

    #     return m, p

    def caption(self, image: Image.Image | Path | str) -> str:
        if isinstance(image, (str, Path)):
            image = Image.open(image)
        elif isinstance(image, Image.Image):
            image = image

        raise NotImplementedError()

        # image = image.convert("RGB")
        # image = self.vis_processors["eval"](image).unsqueeze(0).to(self.device)
        # return self.model.generate({"image": image})[0]


def caption(
    image: Image.Image | Path | str, *, captioner: Captioner | None = None
) -> str:
    captioner = captioner or get_default_captioner()
    return captioner.caption(image)


# def main():
#     logging.basicConfig()
#     LOGGER.setLevel(logging.DEBUG)

#     parser = argparse.ArgumentParser()
#     parser.add_argument("-d", "--device", default=None)
#     parser.add_argument("-m", "--model", default="base_coco")
#     parser.add_argument("imgs", nargs="*")

#     args = parser.parse_args()

#     captioner = Captioner(device=args.device, model=args.model)
#     for x in args.imgs:
#         print(f"{x}: {captioner.caption(Path(x))}")


@click.command("describe")
@click.option(
    "-d", "--device", type=click.Choice(["cpu", "cuda"]), required=False, default=None
)
@click.option("-m", "--model", type=str, required=False, default=DEFAULT_MODEL)
@click.argument("file", type=click.File(mode="rb"))
def describe_cmd(
    file: click.File,
    device: Literal["cuda"] | Literal["cpu"] | None = None,
    model: str | None = DEFAULT_MODEL,
):
    captioner = Captioner(device=device, model=model)
    with Image.open(file) as img:
        click.echo(captioner.caption(img))


def main(*args) -> int:
    return describe_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
