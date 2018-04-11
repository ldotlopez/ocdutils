import argparse
import logging
import sys
import zlib

from ocdutils import (
    dtnamer,
    filesystem,
    ocdlib,
)


class App:
    FMT = '%Y.%m.%d %H.%M.%S'
    SUFFIX_MAP = {
        '.jpeg': '.jpg',
        '.mpeg': '.mpg',
        '.tif': '.tiff'
    }

    @classmethod
    def build_parser(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-r', '--recurse',
            action='store_true',
            default=False)
        parser.add_argument(
            dest='paths',
            nargs='+')

        return parser

    def __init__(self, filesystem=None, logger=None):
        self.exif = dtnamer.ExifHandler()
        self.mtime = dtnamer.MtimeHandler()
        self.name = dtnamer.NameHandler()
        self.logger = logger or logging.getLogger('uniqnamer')
        self.filesystem = filesystem or filesystem.FileSystem()

    def run_one(self, p):
        if not p.is_file():
            return

        if p.stem[0] == '.':
            return

        dt = None

        # Extract suffix for later usage and filetype determination
        suffix = p.suffix.lower()
        try:
            suffix = self.SUFFIX_MAP[suffix]
        except KeyError:
            pass

        # EXIF compatible files
        if suffix in ('.jpg',):
            try:
                dt = self.exif.get(p)
            except dtnamer.RequiredDataNotFoundError as e:
                pass

        if dt is None:
            dt = self.mtime.get(p)

        new_p = p.parent / (
            dt.strftime(self.FMT) + ' ' + ocdlib.crc32(p) +
            suffix)

        if new_p == p:
            return

        op = filesystem.RenameOperation(p, new_p)
        try:
            self.filesystem.execute(op)
        except filesystem.OperationalError as e:
            msg = "{path}: operational error"
            msg = msg.format(path=p, err=e)
            self.logger.error(msg)
            return

    def run(self, paths, recurse=False):
        def _run_one_wrap(p):
            try:
                self.run_one(p)
            except ValueError as e:
                errmsg = "Error with path '{path}': {cls} {e}"
                errmsg = errmsg.format(
                    path=p, cls=e.__class__, e=str(e))
                print(errmsg, file=sys.stderr)

        # filesystem.walk_and_run(*paths, fn=_run_one_wrap, recurse=recurse)
        filesystem.walk_and_run(*paths, fn=self.run_one, recurse=recurse)


def main(argv=None):
    parser = App.build_parser()
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        default=False)

    args = parser.parse_args(sys.argv[1:])

    fs = (filesystem.DryRunFilesystem()
          if args.dry_run
          else filesystem.Filesystem())
    logger = logging.getLogger('ocd-photos')

    app = App(filesystem=fs, logger=logger)
    app.run(args.paths, recurse=args.recurse)


if __name__ == '__main__':
    main()
