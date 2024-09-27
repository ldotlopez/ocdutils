#!/usr/bin/env python3

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

from __future__ import annotations

import dataclasses
import importlib
import logging
import os
from abc import abstractmethod
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def BaseBackendFactory(
    backend=None, *, id: str, map: dict[str, str], default: str
) -> type:
    if backend is None:
        envvar = f"MEDIATOOLS_{id}_BACKEND"
        backend = os.environ.get(envvar) or default

    cls_name = map[backend]

    try:
        m = importlib.import_module(f"..backends.{backend}", package=__package__)
    except ImportError as e:
        raise BackendError() from e

    if not hasattr(m, cls_name):
        raise BackendError()

    return getattr(m, cls_name)


class BackendError(Exception):
    pass


class TextCompletion:
    @abstractmethod
    def complete(self, system: str, text: str) -> str:
        ...


#
# Describe
#
class ImageDescriptor:
    @abstractmethod
    def describe(
        self,
        file: Path,
    ) -> str:
        ...


#
# Embeddings
#

Embeddings = list[float]


class EmbeddingsHandler:
    @abstractmethod
    def get_embeddings(self, text: str) -> Embeddings:
        ...


#
# Transcriptions
#


class AudioTranscriptor:
    @abstractmethod
    def transcribe(self, file: Path, **kwargs) -> AudioTranscription:
        ...


@dataclasses.dataclass
class AudioTranscription:
    text: str
    segments: list[AudioSegment] = dataclasses.field(default_factory=lambda: [])
    language: str | None = None


@dataclasses.dataclass
class AudioSegment:
    start: int
    end: int
    text: str


#
# Image duplicates
#
class ImageDuplicateFinder:
    @abstractmethod
    def find(self, images: list[Path], **kwargs):
        ...


class ImageGenerator:
    @abstractmethod
    def generate(self, prompt: str) -> bytes:
        ...


class ImageGroup:
    group: list[Path]
    meta: dict[str, Any]
