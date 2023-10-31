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
import openai


class Tones(enum.Enum):
    CASUAL = "Use a more casual tone"
    FORMAL = "Use a more formal tone"
    KEEP = "Keep the same tone"


DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "mistral")

SUMMARIZE_PROMPT = """You are a text summarize.
I will provide a text and you will reply with a summmary of that text, and nothing more.
Use the {language} language.
"""

REWRITE_PROMP = """You are a text rewriter.
I will provide a text and you will reply with an alternative version of the text with similar length, nothing more.
{tone}.
Use the {language} language.
"""

if api_base := os.environ.get("OPENAI_BASE", ""):
    openai.api_base = api_base

if api_key := os.environ.get("OPENAI_KEY", ""):
    openai.api_key = api_key


def detect_language(text: str) -> str:
    return iso639.to_name(langdetect.detect(text)).split(";")[0].strip().lower()


def apply_prompt_on_text(prompt: str, text: str) -> str:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]

    resp = openai.ChatCompletion.create(
        model=DEFAULT_MODEL,
        messages=messages,
    )
    return resp.choices[0].message.content.strip()


def summarize(text: str, *, language: str | None = None) -> str:
    language = language or detect_language(text)
    if language is None:
        raise ValueError(f"unable to detect text language")

    return apply_prompt_on_text(SUMMARIZE_PROMPT.format(language=language), text)


def rewrite(
    text: str, *, language: str | None = None, tone: Tones | None = Tones.KEEP
) -> str:
    language = language or detect_language(text)
    if language is None:
        raise ValueError(f"unable to detect text language")

    return apply_prompt_on_text(
        REWRITE_PROMP.format(language=language, tone=tone.value), text
    )


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
    if file == "-":
        buff = sys.stdin.read()
    else:
        with open(file, encoding="utf-8") as fh:
            buff = fh.read()

    try:
        tone = tone = getattr(Tones, tone.upper())
    except AttributeError as e:
        raise ValueError(f"invalid tone: {tone}") from e

    summmary = rewrite(buff, tone=tone, language=language)
    click.echo(summmary)


@click.group("text")
def text_cmd():
    pass


text_cmd.add_command(summarize_cmd)
text_cmd.add_command(rewrite_cmd)


def main():
    import sys

    sys.exit(text_cmd())
