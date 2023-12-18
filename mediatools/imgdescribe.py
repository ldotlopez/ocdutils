import logging
import os

import click
import openai

from .backends import openai

LOGGER = logging.getLogger(__name__)


@click.command("img-describe")
# @click.option(
#     "-d", "--device", type=click.Choice(["cpu", "cuda"]), required=False, default=None
# )
@click.option("-m", "--model", type=str, required=False, default=None)
@click.argument("file", type=click.File(mode="rb"))
def describe_cmd(
    file: click.File,
    # device: Literal["cuda"] | Literal["cpu"] | None = None,
    model: str | None = None,
):
    envbackend = os.environ.get("IMG2TXT_BACEND", "open-ai").lower()
    Backend = {"local-ai": openai.LocalAI, "open-ai": openai.OpenAI}.get(envbackend)

    ret = Backend().describe(file.read(), model=model)  # type: ignore[attr-defined]
    print(ret)


def main(*args) -> int:
    return describe_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
