import argparse
import logging
import sys
import zlib

from ocdutils import (
    dt as ocddt,
    filesystem as ocdfs
)


def crc32(p):
    fh = p.open('rb')
    value = 0
    while True:
        buff = fh.read(1024*1024*4)
        if not buff:
            break

        value = zlib.crc32(buff, value)

    return hex(value)[2:]


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
        self.exif = ocddt.ExifHandler()
        self.mtime = ocddt.MtimeHandler()
        self.name = ocddt.NameHandler()
        self.logger = logger or logging.getLogger('uniqnamer')
        self.filesystem = filesystem or ocdfs.FileSystem()

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
            except RequiredDataNotFoundError as e:
                pass

        if dt is None:
            dt = self.mtime.get(p)

        new_p = p.parent / (
            dt.strftime(self.FMT) + ' ' + crc32(p) +
            suffix)

        if new_p == p:
            return

        op = ocdfs.RenameOperation(p, new_p)
        try:
            self.filesystem.execute(op)
        except ocdfs.OperationalError as e:
            msg = "{path}: operational error"
            msg = msg.format(path=p, err=e)
            self.logger.error(msg)
            return

    def run(self, paths, recurse=False):
        ocdfs.walk_and_run(*paths, fn=self.run_one, recurse=recurse)


def extract_subarguments(args, name):
    prefix = name + '_'
    for (k, v) in vars(args).items():
        if k.startswith(prefix) and v is not None:
            yield (k[len(prefix):], v)


def main(argv=None):
    parser = App.build_parser()
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        default=False)

    args = parser.parse_args(sys.argv[1:])

    fs = ocdfs.DryRunFilesystem() if args.dry_run else ocdfs.Filesystem()
    logger = logging.getLogger('ocd-photos')

    app = App(filesystem=fs, logger=logger)
    app.run(args.paths, recurse=args.recurse)


if __name__ == '__main__':
    main()