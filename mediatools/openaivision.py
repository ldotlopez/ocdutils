import base64
import contextlib
import logging
import os

import click
import openai

LOGGER = logging.getLogger(__name__)


class OpenAIBackend:
    @contextlib.contextmanager
    def custom_api(self):
        api_base = os.environ.get("OPENAI_API_BASE", "")
        api_key = os.environ.get("OPENAI_API_KEY", "")

        kwargs = {}
        if api_base:
            kwargs["base_url"] = api_base
        if api_key:
            kwargs["api_key"] = api_key

        yield openai.OpenAI(**kwargs)

    def describe(
        self,
        contents: bytes,
        *,
        model: str | None = "gpt-4-vision-preview",
        prompt: str | None = "What’s in this image?",
    ) -> str:
        model = model or "gpt-4-vision-preview"
        prompt = prompt or "What’s in this image?"

        with self.custom_api() as client:
            img = base64.b64encode(contents).decode("utf-8")
            LOGGER.warning(f"Asking '{model}' to describe image with '{prompt}'")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            return response.choices[0].message.content.strip()


class LocalAIBackend(OpenAIBackend):
    def describe(
        self,
        contents: bytes,
        *,
        model: str | None = "llava",
        prompt: None
        | (
            str
        ) = "What’s in this image? Be brief, it’s for image alt description on a social network. Don’t write in the first person.",
    ) -> str:
        model = model or "llava"
        prompt = (
            prompt
            or "What’s in this image? Be brief, it’s for image alt description on a social network. Don’t write in the first person."
        )

        return super().describe(contents, model=model, prompt=prompt)


@click.command("openai-vision")
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
    backend = LocalAIBackend()
    ret = backend.describe(file.read(), model=model)  # type: ignore[attr-defined]
    print(ret)


def main(*args) -> int:
    return describe_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
