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


class BackendError(Exception):
    pass


def get_backend_name(sub_module_name: str, *, default: str) -> str:
    return os.environ.get(f"MEDIATOOLS_{id}_BACKEND", default)


def get_backend_from_map(name: str, m: dict[str, str]) -> type:
    return get_backend(name, m[name])


def get_backend(name: str, clsname: str) -> type:
    try:
        m = importlib.import_module(f"..backends.{name}", package=__package__)
    except ImportError as e:
        raise BackendError() from e

    if not hasattr(m, clsname):
        raise BackendError()

    return getattr(m, clsname)


def get_backend_plus(name: str, cls: str) -> type | None:
    try:
        return get_backend(name, cls)
    except BackendError as e:
        LOGGER.critical(f"Unable to load backend '{name}'")
        return None


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
# Transcriptions
#


class Transcriptor:
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


#
# Image duplicates
#
class ImageDuplicateFinder:
    @abstractmethod
    def find(self, images: list[Path], **kwargs):
        ...


class ImageGroup:
    group: list[Path]
    meta: dict[str, Any]
