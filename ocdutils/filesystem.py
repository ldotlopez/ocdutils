#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Copyright (C) 2018 Luis López <luis@cuarentaydos.com>
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


import abc
import os
import pathlib
import shutil
from datetime import datetime


class OperationalError(Exception):
    pass


class Operation:
    pass


class NoopOperation(Operation):
    pass


class CustomOperation(Operation):
    def __init__(self, fn, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class RenameOperation(Operation):
    def __init__(self, src, dest):
        self.src = src
        self.dest = dest


class ChmodOperation(Operation):
    def __init__(self, path, mode):
        self.path = path
        self.mode = mode


class DeleteOperation(Operation):
    def __init__(self, path):
        self.path = path


class SetTimestampOperation(Operation):
    def __init__(self, path, timestamp, set_mtime=True, set_atime=True):
        self.path = path
        self.timestamp = timestamp
        self.set_mtime = set_mtime
        self.set_atime = set_atime


class _BaseFilesystem:
    @abc.abstractmethod
    def execute(self):
        pass


class Filesystem(_BaseFilesystem):
    def execute(self, op):
        if op is None or isinstance(op, NoopOperation):
            pass

        elif isinstance(op, RenameOperation):
            if os.path.exists(op.dest):
                raise OperationalError(op, "Destination exists")

            shutil.move(op.src, op.dest)

        elif isinstance(op, SetTimestampOperation):
            st = os.stat(op.path)

            if op.set_mtime:
                mtime = op.timestamp
            else:
                mtime = st.st_mtime

            if op.set_atime:
                atime = op.timestamp
            else:
                atime = st.st_atime

            os.utime(op.path, (atime, mtime))

        elif isinstance(op, CustomOperation):
            return op.fn(*op.args, **op.kwargs)

        else:
            raise NotImplementedError(op)


class DryRunFilesystem(_BaseFilesystem):
    def escape(self, path):
        pathstr = str(path)
        pathstr = pathstr.replace("\\", "\\\\").replace("'", "\\'")
        return pathlib.Path(pathstr)

    def execute(self, op):
        if op is None or isinstance(op, NoopOperation):
            print(": noop")

        elif isinstance(op, RenameOperation):
            cmd = "mv -b '{src}' '{dest}'"
            cmd = cmd.format(src=self.escape(op.src), dest=self.escape(op.dest))
            print(cmd)

        elif isinstance(op, SetTimestampOperation):
            cmd = "touch {atime} {mtime} " "-t '{timestamp}' " "'{path}'"

            cmd = cmd.format(
                path=self.escape(op.path),
                atime="-a" if op.set_atime else "",
                mtime="-m" if op.set_atime else "",
                timestamp=datetime.fromtimestamp(int(op.timestamp)).strftime(
                    "%Y%m%d%H%M.%S"
                ),
            )

            print(cmd)

        elif isinstance(op, CustomOperation):
            args = ", ".join([repr(x) for x in op.args])
            kwargs = ", ".join(
                ["{}={}".format(k, repr(v)) for (k, v) in op.kwargs.items()]
            )

            if kwargs:
                args += ", " + kwargs

            cmd = "{fnname}({args})".format(fnname=op.fn.__name__, args=args)
            print(cmd)

        elif isinstance(op, ChmodOperation):
            cmd = "chmod {mode:o} '{path}'"
            cmd = cmd.format(path=op.path, mode=op.mode)
            print(cmd)

        elif isinstance(op, DeleteOperation):
            cmd = "rm -rf -- '{path}'"
            cmd = cmd.format(path=str(op.path))
            print(cmd)

        else:
            raise NotImplementedError(op)


def walk(path, *args, **kwargs):
    if not isinstance(path, str):
        path = str(path)

    yield from os.walk(path, *args, **kwargs)


def walk_and_run(*ps, fn=None, filter_fn=None, recurse=True, **kwargs):
    for p in ps:
        if isinstance(p, pathlib.Path):
            p_str = str(p)
        else:
            p_str = p
            p = pathlib.Path(p_str)

        if p.is_file() or not recurse:
            fn(p)

        else:
            for (dirname, dirs, files) in os.walk(p_str, **kwargs):
                if filter_fn:
                    filter_fn(dirname, dirs, files)

                for child in dirs + files:
                    fn(pathlib.Path(dirname) / child)
