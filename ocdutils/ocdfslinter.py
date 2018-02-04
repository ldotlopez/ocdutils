#!/usr/bin/env python


import argparse
import logging
import pathlib
import sys


from ocdutils import filesystem as ocdfs


class OCDFilesystemLinter:
    SUFFIX_MAP = {
        '.tif': '.tiff',
        '.jpeg': '.jpg',
        '.mpeg4': '.mp4'
    }

    def __init__(self, filesystem=None, logger=None):
        self.filesystem = filesystem or ocdfs.Filesystem()
        self.logger = logger or logging.getLogger('ocd-fslinter')

    @classmethod
    def build_parser(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-r', '--recurse',
            action='store_true',
            default=False)
        parser.add_argument(
            '--skip-hidden',
            action='store_true',
            default=False)
        parser.add_argument(
            dest='paths',
            nargs='+')

        return parser

    def fix_extension(self, path):
        if not path.is_file():
            return

        suffix = path.suffix.lower()
        try:
            suffix = self.SUFFIX_MAP[suffix]
        except KeyError:
            pass

        newpath = path.parent / (path.stem + suffix)
        if newpath != path:
            return ocdfs.RenameOperation(path, newpath)

    def deosify(self, path):
        if path.is_file() and path.name == '.DS_Store':
            return ocdfs.DeleteOp(path)

        if path.is_file() and path.name.startswith('._'):
            return ocdfs.DeleteOp(path)

    def subtitle_extension(self, path):
        if not (path.is_file() and path.suffix.lower() == '.srt'):
            return

        self.logger.info('Not implemented')

    def run(self, paths, recurse=False, skip_hidden=False):
        for path in paths:
            if not recurse:
                self.run_one(path)

            else:
                for (dirpath, dirnames, filenames) in ocdfs.walk(path):
                    if skip_hidden:
                        self._strip_hidden(dirnames)
                        self._strip_hidden(filenames)

                    children = dirnames + filenames
                    children = [pathlib.Path(dirpath) / x for x in children]

                    for child in children:
                        self.run_one(child)

    def run_one(self, path):
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)

        for fn in [self.fix_extension, self.deosify]:
            self.filesystem.execute(fn(path))

    def _strip_hidden(self, l):
        for x in l:
            if x[0] == '.':
                l.remove(x)


def main(argv=None):
    parser = OCDFilesystemLinter.build_parser()
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        default=False)

    args = parser.parse_args(sys.argv[1:])

    if args.dry_run:
        fs = ocdfs.DryRunFilesystem()
    else:
        fs = ocdfs.Filesystem()

    app = OCDFilesystemLinter(filesystem=fs)
    app.run(args.paths, recurse=args.recurse, skip_hidden=args.skip_hidden)


if __name__ == '__main__':
    main()
