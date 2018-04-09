import os
import sys
import argparse

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



class FixExtension(_BaseProcessor):
    APPLIES_ON = stat.S_IFREG

    def analyze(self, target):
        extension_repl = {
            '.jpeg': '.jpg',
            '.mpeg': '.mpg',
            '.tif': '.tiff',
        }

        ext = target.suffix.lower()

        try:
            ext = extension_repl[ext]
        except KeyError:
            pass

        dest = target.with_suffix(ext)
        if dest == target:
            return

        return fsops.Rename(destination=dest)


class FixPermissions(_BaseProcessor):
    APPLIES_ON = stat.S_IFREG | stat.S_IFDIR

    def analyze(self, target):
        if target.is_dir():
            return fsops.Chmod(mode=0o755)

        elif target.is_file():
            return fsops.Chmod(mode=0o644)

        else:
            raise ValueError(target, 'unknow type')


class DeOSXfy(_BaseProcessor):
    APPLIES_ON = stat.S_IFREG | stat.S_IFDIR

    def analyze(self, target):
        if target.is_file() and target.name == '.DS_Store':
            return fsops.Delete()

        if target.name.startswith('._'):
            return fsops.Delete()



class Mp3Deleter:
    def __init__(self, directory):
        if directory is None or not isinstance(directory, str):
            raise TypeError(directory)

        self.directory = directory

    def run(self):
        for (dirname, directories, files) in os.walk(self.directory):
            m = {dirname + '/' + x.lower(): dirname + '/' + x
                 for x in files}

            deletables = []
            for (comparable, filename) in m.items():
                check = comparable[:-5] + '.mp3'
                if check in m:
                    deletables.append(m[check])

            for filename in deletables:
                print("rm -- '{f}'".format(f=filename.replace(r"'", r"\'")))
                os.unlink(filename)

class FileRename:
    def __init__(self, directory):
        if directory is None or not isinstance(directory, str):
            raise TypeError(directory)

        self.directory = directory

    def run(self):
        for (dirname, directories, files) in os.walk(self.directory):
            for f in files:
                f2 = self.process_filename(dirname + '/' + file)

    def process_filename(self, filename):
        pass


class SubtitleExtension(FileRename):
    pass


class CaseFixerExtension(FileRename):
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', required=True)

    args = parser.parse_args(sys.argv[1:])
    kwargs = vars(args)

    x = Mp3Deleter(**kwargs)
    x.run()


if __name__ == '__main__':
    main()
