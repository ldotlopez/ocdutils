import argparse
import logging
import os
import pathlib
import sys

from ocdutils import filesystem

# rename lowercase
# rename with stamp
# reduce jpgs


# IFS="
# "
# for x in `find . \( -size +2M -a -iname '*.jpg' \)`
# do
#   tmp="${x/jpg/tmp.jpg}"
#   convert -resize '1920x1920>' -quality 90 "$x" "$tmp" && mv "$tmp" "$x"
# done


class UnknownFileTypeError(Exception):
    pass


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
                    op = extension.main(entry, container)
                except UnknownFileTypeError as e:
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

    def main(self, p, directories, files):
        raise NotImplementedError()


class FixExtension(Extension):
    SUFFIX_MAP = {
        '.jpeg': '.jpg',
        '.mpeg': '.mpg',
        '.tif': '.tiff',
    }

    def main(self, entry, container):
        entry = pathlib.Path(x)
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
    def main(self, entry, container):
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
            raise UnknownFileTypeError(entry, 'unknow type')


class DeOSXfy(Extension):
    def main(self, entry, container):
        entry = pathlib.Path(entry)

        if entry.is_dir() and entry.name == '.DS_Store':
            return filesystem.DeleteOperation(path=entry)

        if entry.is_file() and entry.name.startswith('._'):
            realentry = entry.parent / entry.name[2:]
            if realentry.exists():
                return filesystem.DeleteOperation(path=entry)


class Mp3Deleter(Extension):
    pass
    # def main(self, entry, container):
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


class SubtitleExtension(Extension):
    pass


def main(argv=None):
    exts = (
        ('deosxfy', DeOSXfy),
        ('ext', FixExtension),
        ('perms', FixPermissions),
        ('subtitles', SubtitleExtension)
    )

    parser = App.build_parser()
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        default=False)

    args = parser.parse_args(sys.argv[1:])

    fs = filesystem.DryRunFilesystem() if args.dry_run else filesystem.Filesystem()
    logger = logging.getLogger('janitor')

    extensions = []
    for (opt, cls) in exts:
        if getattr(args, opt) or args.all:
            extensions.append(cls())

    app = App(extensions=extensions, filesystem=fs, logger=logger)
    app.run(args.paths, recurse=args.recurse)


if __name__ == '__main__':
    main()
