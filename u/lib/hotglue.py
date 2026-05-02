from __future__ import annotations

import importlib
from functools import lru_cache
from types import ModuleType
from typing import Self


@lru_cache
def _get_module(modstr: str) -> ModuleType:
    return importlib.import_module(modstr)


class IFaceLoader:
    def __init__(self) -> Self:
        pass
