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

import contextlib
import dataclasses
import importlib
import io
import json
import logging
import os
import sys
from abc import abstractmethod
from pathlib import Path

import click
import ffmpeg
import openai
import pysrt

from .lib import filesystem as fs
from .lib import spawn

DEFAULT_BACKEND = "openai"

_LOGGER = logging.getLogger(__name__)

_BACKENDS: dict[str, type[BaseTranscriptor]] = {}


class BaseTranscriptor:
    @abstractmethod
    def transcribe(self, file: Path, **kwargs) -> Transcription:
        ...


@dataclasses.dataclass
class Transcription:
    text: str
    segments: list[Segment] = dataclasses.field(default_factory=lambda: [])
    language: str | None = None


@dataclasses.dataclass
class Segment:
    start: int
    end: int
    text: str


class SrtTimeFmt:
    @staticmethod
    def str_to_int(text: str) -> int:
        return pysrt.SubRipTime.from_string(text).ordinal

    @staticmethod
    def int_to_str(ms: int) -> str:
        return str(pysrt.SubRipTime.from_ordinal(ms))


class JSONFmt:
    @staticmethod
    def loads(text: str) -> Transcription:
        data = json.loads(text)
        return Transcription(
            text=data["text"],
            segments=[
                Segment(start=s["start"], end=s["end"], text=s["text"])
                for s in data.get("segments", [])
            ],
            language=data.get("language", None),
        )

    @staticmethod
    def dumps(transcription: Transcription) -> str:
        if transcription.segments is None:
            segments = None
        else:
            segments = [dataclasses.asdict(x) for x in transcription.segments]

        return json.dumps(
            dict(
                text=transcription.text,
                segments=segments,
                language=transcription.language,
            )
        )


class SrtFmt:
    @staticmethod
    def loads(text) -> Transcription:
        sub = pysrt.from_string(text)
        segments = [
            Segment(start=x.start.ordinal, end=x.end.ordinal, text=x.text) for x in sub
        ]
        text = "".join([x.text for x in sub]).strip()

        return Transcription(text=text, segments=segments)

    @staticmethod
    def dumps(transcription: Transcription) -> str:
        srt = pysrt.SubRipFile(
            items=[
                pysrt.SubRipItem(
                    index=idx + 1,
                    start=pysrt.SubRipTime.from_ordinal(s.start * 1000),
                    end=pysrt.SubRipTime.from_ordinal(s.end * 1000),
                    text=s.text,
                )
                for idx, s in enumerate(transcription.segments)
            ]
        )

        buff = io.StringIO()
        srt.write_into(buff)
        ret = buff.getvalue()
        buff.close()

        return ret


class OpenAI(BaseTranscriptor):
    def __init__(
        self,
        *,
        model: str = os.environ.get("WHISPER_MODEL", "whisper-1"),
        api_base=os.environ.get("OPENAI_API_BASE", ""),
        api_key: str = os.environ.get("OPENAI_API_KEY", ""),
    ) -> None:
        self.model = model
        self.api_base = api_base
        self.api_key = api_key

    @contextlib.contextmanager
    def custom_api_ctx(self):
        base = openai.api_base
        key = openai.api_key

        if self.api_base:
            openai.api_base = self.api_base
        if self.api_key:
            openai.api_key = self.api_key
        yield

        openai.api_base = base
        openai.api_key = key

    def transcribe(self, file: Path) -> Transcription:  # type: ignore[override]
        import openai  # Already loaded, but fixes linter warnings

        with self.custom_api_ctx():
            with fs.temp_dirpath() as tmpd:
                wav = tmpd / "transcribe.m4a"

                (
                    ffmpeg.input(file.as_posix())
                    .audio.output(wav.as_posix(), format="mp4")
                    .overwrite_output()
                    .run()
                )

                with open(wav, "rb") as fh:
                    resp = openai.Audio.transcribe(self.model, fh)

                return Transcription(
                    text=resp["text"].strip(),
                    segments=[
                        Segment(
                            start=x["start"] // 1_000_000_000,
                            end=x["end"] // 1_000_000_000,
                            text=x["text"].strip(),
                        )
                        for x in resp.get("segments") or []
                    ],
                    language=resp.get("language"),
                )


class WhisperPy(BaseTranscriptor):
    def __init__(
        self, *, model_name: str | None = os.environ.get("WHISPER_MODEL")
    ) -> None:
        if not model_name:
            raise ValueError("model not defined")

        self.model_name = model_name

    @property
    def model(self):
        if self._model is None:
            self._model = whisper.load_model(self.model_name)

        return self._model

    def transcribe(  # type: ignore[override]
        self,
        file: Path,
        *,
        language: str | None = os.environ.get("WHISPER_LANGUAGE", None),
    ) -> Transcription:
        with fs.temp_dirpath_ctx() as tmpd:
            wav = tmpd / "audio.wav"
            (
                ffmpeg.input(file.as_posix())
                .output(
                    wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000
                )
                .overwrite_output()
                .run(quiet=True)
            )
            res = self.model.transcribe(file.as_posix(), language=language)

            return Transcription(
                text=res["text"].strip(),
                segments=[
                    Segment(start=x["start"], end=x["end"], text=x["text"].strip())
                    for x in res["segments"]
                ],
                language=res.get("language"),
            )


def check_availability(name: str) -> bool:
    for path in os.environ.get("PATH", "").split(":"):
        test = f"{path}/{name}"

        if not os.path.exists(test):
            continue

        if os.access(test, os.X_OK):
            return True

    return False


class WhisperCpp(BaseTranscriptor):
    def __init__(
        self, model_filepath: str | Path | None = os.environ.get("WHISPER_MODEL")
    ) -> None:
        if isinstance(model_filepath, str):
            model_filepath = Path(model_filepath)

        if model_filepath is None:
            raise ValueError("model not defined")

        self.model_filepath = model_filepath

    def transcribe(
        self,
        file: Path,
        *,
        language: str | None = os.environ.get("WHISPER_LANGUAGE", "auto"),
    ) -> Transcription:
        language = language or "auto"
        with fs.temp_dirpath_ctx() as tmpd:
            base = tmpd / "transcribe"
            wav = tmpd / "transcribe.wav"
            srt = tmpd / "transcribe.srt"

            _LOGGER.debug(f"whisper.cpp model: {self.model_filepath}")
            _LOGGER.debug(f"whisper.cpp language: {language}")

            (
                ffmpeg.input(file.as_posix())
                .output(
                    wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000
                )
                .overwrite_output()
                .run(quiet=True)
            )

            spawn.run(
                [
                    "whisper.cpp",
                    "-l",
                    language,
                    "--output-srt",
                    "-of",
                    base.as_posix(),
                    "-m",
                    self.model_filepath.as_posix(),
                    wav.as_posix(),
                ]
            )

            return SrtFmt.loads(srt.read_text())


def transcribe(
    file: Path, *, backend: str | None = DEFAULT_BACKEND, **kwargs
) -> Transcription:
    return TranscriptorFactory(backend=backend).transcribe(file, **kwargs)


def TranscriptorFactory(
    backend: str | None = DEFAULT_BACKEND, **kwargs
) -> BaseTranscriptor:
    backend = backend or DEFAULT_BACKEND
    return _BACKENDS[backend](**kwargs)


@click.command("transcribe")
@click.option("--backend", type=str)
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def transcribe_cmd(
    targets: list[Path],
    backend: str,
    overwrite: bool = False,
    recursive: bool = False,
):
    transcriptor = TranscriptorFactory(backend=backend)

    for file in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        mime = fs.file_mime(file)
        if not mime.startswith("video/") and not mime.startswith("audio/"):
            click.echo(f"{file}: not a media file", err=True)
            continue

        transcription = transcriptor.transcribe(file)
        dest = fs.change_file_extension(file, "srt")
        if dest.exists() and not overwrite:
            click.echo(f"{dest}: already exists")
            continue

        dest.write_text(SrtFmt.dumps(transcription))


for name, cls in [
    ("openai", OpenAI),
    ("whisper", WhisperPy),
]:
    try:
        importlib.import_module(name)
        _BACKENDS[name] = cls
    except ImportError:
        _LOGGER.warning(f"package {name} not installed, backend will be not available")
        pass

if check_availability("whisper.cpp"):
    _BACKENDS["whisper.cpp"] = WhisperCpp


def main():
    return transcribe_cmd()


if __name__ == "__main__":
    sys.exit(main())
