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


import importlib
import os
from collections.abc import Callable
from functools import lru_cache
from types import ModuleType
from typing import Any

HookFunc = Callable[..., Any]


class HookHub:
    """
    A hub for managing and firing hooks.

    A hook is a function that can be registered to be executed when a certain event
    occurs.
    The HookHub allows you to register multiple functions (hooks) for each event, and
    then fires all of them when the event is triggered.

    Example:

    hub = HookHub()
    @hub.hook("my_event")
    def my_hook(arg: str):
        print(f"Received arg: {arg}")

    # Fire the hook
    hub.fire("my_event", "Hello, world!")
    """

    def __init__(self) -> None:
        self.hooks: dict[str, list[HookFunc]] = {}

    def _get_hooks(self, name: str) -> list[HookFunc]:
        return self.hooks.get(name) or []

    def register_hook(self, name: str, callable: HookFunc) -> None:
        self.hooks[name] = self._get_hooks(name) + [callable]
        print(f"{callable} registered for {name}")

    def hook(self, name: str) -> Callable[[HookFunc], None]:
        def register_fn(fn):
            self.register_hook(name, fn)

        return register_fn

    def fire(self, name: str, *args: Any, **kwargs: Any) -> None:
        for fn in self._get_hooks(name):
            fn(*args, **kwargs)


class IfacesHub:
    """A registry for interfaces, where names are used as identifiers to store and
    retrieve objects.

    This class allows registering objects under specific names, ensuring that each name
    is unique.
    Attempting to register an object with a duplicate name will raise an exception.
    """

    def __init__(self) -> None:
        self._reg: dict[str, object] = {}

    def register(self, name: str, obj: object) -> None:
        if name in self._reg:
            raise Exception()

        self._reg[name] = obj


class PluginHub:
    """A hub for registering and managing plugins.

    This class allows registering objects that implement specific interfaces,
    grouping them by their interface types. Each plugin is registered under its
    associated interface type, allowing for easy lookup and management of plugins.
    """

    def __init__(self) -> None:
        self._ifaces: dict[type, IfacesHub] = {}

    def register(self, name: str, iface: type, obj: object) -> None:
        if iface not in self._ifaces:
            self._ifaces[iface] = IfacesHub()

        self._ifaces[iface].register(name, obj)


class HotLoader:
    """A dynamic module loader that allows registering and loading modules at runtime.

    This class enables loading of modules by storing their names and import specs,
    then importing them on demand using the importlib module.
    """

    def __init__(self) -> None:
        self.reg: dict[str, str | ModuleType | None] = {}

    def register(self, name: str, modstr: str):
        self.reg[name] = modstr

    def get(self, name: str) -> ModuleType:
        target = self.reg[name]

        if isinstance(target, str):
            try:
                m = importlib.import_module(target)
            except Exception:
                self.reg[name] = None
                raise
            self.reg[name] = m
            return m

        elif target is None:
            raise Exception()

        elif isinstance(target, ModuleType):
            return target

        raise Exception()


class BackendDefer:
    def __init__(self, basemod: str | None = None) -> None:
        self.basemod = basemod

    @lru_cache
    def get(self, name: str):
        if self.basemod:
            name = f"{self.basemod}.{name}"

        return importlib.import_module(name)


# ENVIRON_KEY = "AUDIO_TRANSCRIPTOR"
# DEFAULT_BACKEND = "openai"
# BACKENDS = {
#     "openai": "OpenAI",
#     "whisper": "WhisperPy",
#     "whispercpp": "WhisperCpp",
# }


class BackendFactory(BackendDefer):
    def __init__(self, basemod: str, backends: list[tuple[str, str]]) -> None:
        super().__init__(basemod)

        self.default = backends[0][0]
        self.backends = backends
        self.envvar = ""

    def get(self, name: str | None = None) -> object:
        name = os.environ.get(self.envvar) or self.default or name
        raise NotImplementedError()


"""

impl = get_backend(
    [
        ("foo", "foo.Foo"),
        ("bar", "foo.Bar")
    ],

)

"""


def test_hooks():
    hh = HookHub()

    @hh.hook("events.foo")
    def test_hook_decorated(*args, **kwargs):
        print("test_hook_decorated")

    def test_hook_fn(*args, **kwargs):
        print("test_hook_fn")

    hh.register_hook("events.foo", test_hook_fn)

    hh.fire("events.foo")


if __name__ == "__main__":
    test_hooks()
