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


import argparse
import logging
import os
import pathlib
import sys


from PIL import Image


from ocdutils import (
    filesystem,
    ocdlib
)


# Some possible additions:
# Reduce jpgs (useful por archive if not Hi-Res required)
# ```
# for x in listing():
#   if filesize(x) > threshold or resolution(x) > (max_x, max_y):
#     resize(x)
# ```


class App:
    @classmethod
    def build_parser(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--all',
            action='store_true'
        ),
        parser.add_argument(
            '--deosxfy',
            action='store_true',
        ),
        parser.add_argument(
            '--ext',
            action='store_true',
        ),
        parser.add_argument(
            '--image-reduce',
            action='store_true',
        ),
        parser.add_argument(
            '--perms',
            action='store_true',
        ),
        parser.add_argument(
            '--subtitles',
            action='store_true',
        ),
        parser.add_argument(
            '-r', '--recurse',
            action='store_true',
            default=False)
        parser.add_argument(
            dest='paths',
            nargs='+')

        return parser

    def __init__(self, extensions=None, filesystem=None, logger=None):
        if not extensions:
            extensions = []
        self.logger = logger or logging.getLogger('janitor')
        self.filesystem = filesystem or filesystem.FileSystem()
        self.extensions = extensions

    def run(self, paths, **kwargs):
        for ext in self.extensions:
            self._run_extension(ext, paths, **kwargs)

    def _run_extension(self, extension, paths, **kwargs):
        for path in paths:
            self._run_extension_on_path(extension, path)

    def _run_extension_on_path(self, extension, path, **kwargs):
        for (dirname, directories, files) in os.walk(str(path)):
            for (entry, container) in (
                    [(x, directories) for x in directories] +
                    [(x, files) for x in files]):
                entry = os.path.join(dirname, entry)

                try:
                    op = extension.process(entry, container)
                except ocdlib.InvalidFileTypeError as e:
                    self.logger.error(e)
                    continue

                if op is None or isinstance(op, filesystem.NoopOperation):
                    continue

                self.filesystem.execute(op)


class Extension:
    def pathify(self, x, dirname=None):
        x = pathlib.Path(x)
        if dirname:
            x = pathlib.Path(dirname) / x

        return x

    def process(self, entry, container):
        raise NotImplementedError()


class DeOSXfy(Extension):
    def process(self, entry, container):
        entry = pathlib.Path(entry)

        if entry.is_dir() and entry.name == '.DS_Store':
            return filesystem.DeleteOperation(path=entry)

        if entry.is_file() and entry.name.startswith('._'):
            realentry = entry.parent / entry.name[2:]
            if realentry.exists():
                return filesystem.DeleteOperation(path=entry)

        if entry.is_file() and entry.name == 'Icon\r':
            return filesystem.DeleteOperation(path=entry)


class FixExtension(Extension):
    SUFFIX_MAP = {
        '.jpeg': '.jpg',
        '.mpeg': '.mpg',
        '.tif': '.tiff',
    }

    def process(self, entry, container):
        entry = pathlib.Path(entry)
        if not entry.is_file():
            return

        dirname = entry.parent
        name = entry.stem
        suffix = entry.suffix.lower()

        try:
            dest = dirname / (name + self.SUFFIX_MAP[suffix])
        except KeyError:
            return

        if entry != dest:
            return filesystem.RenameOp(src=entry, dest=dest)


class FixPermissions(Extension):
    def process(self, entry, container):
        entry = pathlib.Path(entry)
        try:
            mode = oct(entry.stat().st_mode)[-3:]  # This is a bit hacky
        except FileNotFoundError as e:
            if entry.is_symlink():
                return
            raise

        if entry.is_dir() and mode != '755':
            return filesystem.ChmodOperation(path=entry, mode=0o755)

        elif entry.is_file() and mode != '644':
            return filesystem.ChmodOperation(path=entry, mode=0o644)

        else:
            raise ocdlib.InvalidFileTypeError(entry, 'unknow type')


class ImageReduce(Extension):
    THRESHOLD = 2160

    def process(self, entry, container):
        p = pathlib.Path(entry)
        if not p.is_file():
            return

        try:
            img = Image.open(entry)
        except OSError:
            return

        (w, h) = img.size
        max_dim = max(img.size)
        ratio = w / h

        if max_dim == w and w > self.THRESHOLD:
            w = self.THRESHOLD
            h = self.THRESHOLD / ratio

        elif max_dim == h and h > self.THRESHOLD:
            w = self.THRESHOLD * ratio
            h = self.THRESHOLD

        else:
            return

        return filesystem.CustomOperation(
            self.resize,
            entry,
            w,
            h)

    def resize(self, entry, w, h):
        pass


class Mp3Deleter(Extension):
    def process(self, entry, container):
        #     for (dirname, directories, files) in os.walk(self.directory):
        #         m = {dirname + '/' + x.lower(): dirname + '/' + x
        #              for x in files}

        #         deletables = []
        #         for (comparable, filename) in m.items():
        #             check = comparable[:-5] + '.mp3'
        #             if check in m:
        #                 deletables.append(m[check])

        #         for filename in deletables:
        #             print("rm -- '{f}'".format(f=filename.replace(r"'", r"\'")))
        #             os.unlink(filename)
        pass


class SubtitleExtension(Extension):
    def process(self, entry, container):
        # Integrate txtflar
        pass


def main(argv=None):
    exts = (
        ('deosxfy', DeOSXfy),
        ('ext', FixExtension),
        ('image_reduce', ImageReduce),
        ('perms', FixPermissions),
        ('subtitles', SubtitleExtension)
    )

    parser = App.build_parser()
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        default=False)

    args = parser.parse_args(sys.argv[1:])

    fs = (
        filesystem.DryRunFilesystem()
        if args.dry_run
        else filesystem.Filesystem())

    logger = logging.getLogger('janitor')

    extensions = []
    for (opt, cls) in exts:
        if getattr(args, opt) or args.all:
            extensions.append(cls())

    app = App(extensions=extensions, filesystem=fs, logger=logger)
    app.run(args.paths, recurse=args.recurse)


if __name__ == '__main__':
    main()
