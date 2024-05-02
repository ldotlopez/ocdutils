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


import enum
import os
import sys

import click
import iso639
import langdetect

from .backends import TextCompletion, get_backend_from_map

BACKEND_MAP = {"openai": "OpenAI"}
DEFAULT_BACKEND = "openai"


class Tones(enum.Enum):
    CASUAL = "Use a more casual tone"
    FORMAL = "Use a more formal tone"
    KEEP = "Keep the same tone"


SUMMARIZE_PROMPT = """You are a text summarize.
I will provide a text and you will reply with a summmary of that text, and nothing more.
Use the {language} language.
"""

REWRITE_PROMP = """You are a text rewriter.
I will provide a text and you will reply with an alternative version of the text with similar length, nothing more.
{tone}.
Use the {language} language.
"""


def TextCompletionFactory(
    backend: str | None = DEFAULT_BACKEND, **kwargs
) -> TextCompletion:
    Completion = get_backend_from_map(
        os.environ.get("MEDIATOOLS_COMPLETION_BACKEND", backend or DEFAULT_BACKEND),
        BACKEND_MAP,
    )

    return Completion()


def complete(
    system: str, text: str, *, backend: str | None = DEFAULT_BACKEND, **kwargs
) -> str:
    return TextCompletionFactory(backend=backend).complete(system, text, **kwargs)


def summarize(text: str, *, language: str | None = None) -> str:
    language = language or detect_language(text)

    if language is None:
        raise ValueError("unable to detect text language")

    return complete(SUMMARIZE_PROMPT.format(language=language), text)


def rewrite(
    text: str, *, language: str | None = None, tone: Tones | None = Tones.KEEP
) -> str:
    language = language or detect_language(text)
    tone = tone or Tones.KEEP

    if language is None:
        raise ValueError("unable to detect text language")

    return complete(REWRITE_PROMP.format(language=language, tone=tone.value), text)


def detect_language(text: str) -> str:
    return iso639.to_name(langdetect.detect(text)).split(";")[0].strip().lower()


@click.command("summarize")
@click.option("-l", "--language", help="Override autodetected language", type=str)
@click.argument("file", type=str)
def summarize_cmd(file: str | None = None, language: str | None = None):
    if file == "-":
        buff = sys.stdin.read()
    else:
        with open(file, encoding="utf-8") as fh:  # type: ignore[arg-type]
            buff = fh.read()

    summmary = summarize(buff, language=language)
    click.echo(summmary)


@click.command("rewrite")
@click.option(
    "-t",
    "--tone",
    help="Tone to use",
    type=click.Choice(["formal", "casual", "keep"]),
    default="keep",
)
@click.option("-l", "--language", help="Override autodetected language", type=str)
@click.argument("file", type=str)
def rewrite_cmd(
    file: str | None = None, tone: str = "keep", language: str | None = None
):
    if file is None:
        raise ValueError(file)

    elif file == "-":
        buff = sys.stdin.read()

    elif isinstance(file, str):
        with open(file, encoding="utf-8") as fh:
            buff = fh.read()

    else:
        raise ValueError(file)

    try:
        tone = tone = getattr(Tones, tone.upper())
    except AttributeError as e:
        raise ValueError(f"invalid tone: {tone}") from e

    summmary = rewrite(buff, tone=tone, language=language)
    click.echo(summmary)


@click.group("text-transform")
def text_transform_cmd():
    pass


text_transform_cmd.add_command(summarize_cmd)
text_transform_cmd.add_command(rewrite_cmd)


def main(*args) -> int:
    return text_transform_cmd(*args) or 0


if __name__ == "__main__":
    import sys

    sys.exit(main(*sys.argv))
