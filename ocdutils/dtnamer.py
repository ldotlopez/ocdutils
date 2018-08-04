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
import random
import re
import subprocess
import sqlite3
import sys
from datetime import datetime, timedelta


import piexif
from ocdutils import filesystem as ocdfs


class InvalidFileTypeError(Exception):
    pass


class RequiredDataNotFoundError(Exception):
    pass


class BaseHandler:
    @classmethod
    def get_subclass(cls, name):
        me = cls.__name__.lower()[:-len('handler')]
        if me == name:
            return cls

        for subcls in cls.__subclasses__():
            x = subcls.get_subclass(name)
            if x:
                return x

    def get(self, p):
        raise NotImplementedError()

    def set(self, p, dt):
        raise NotImplementedError()


class ExifHandler(BaseHandler):
    def get(self, p):
        t = {
            'original': (piexif.ExifIFD.DateTimeOriginal,
                         piexif.ExifIFD.OffsetTimeOriginal),
            'digitized': (piexif.ExifIFD.DateTimeDigitized,
                          piexif.ExifIFD.OffsetTimeDigitized),
        }

        try:
            exif = piexif.load(str(p))
        except piexif.InvalidImageDataError as e:
            raise InvalidFileTypeError() from e

        for (key, (dt_tag, offset_tag)) in t.items():
            try:
                dt = exif['Exif'][dt_tag].decode('ascii')
            except KeyError:
                t[key] = None
                continue

            delta = timedelta()
            try:
                offset = exif['Exif'][offset_tag].decode('ascii')
                delta += timedelta(seconds=int(offset))
            except (KeyError, ValueError):
                pass

            # Some cameras use hour '24' incorrectly.
            # Quoting python bugtracker:
            # > Indeed anything beyond 24:0:0 is invalid
            if dt.find(' 24:') > 0:
                dt = dt.replace(' 24:', ' 00:')
                delta += timedelta(days=1)

            dt = datetime.strptime(dt, '%Y:%m:%d %H:%M:%S')
            dt = dt + delta

            t[key] = dt

        if not any(t.values()):
            msg = "exif tags not found"
            raise RequiredDataNotFoundError(msg)

        if all(t.values()) and t['original'] != t['digitized']:
            msg = "original:{original} != dititized{digitized}"
            msg = msg.format(original=t['original'], digitized=t['digitized'])
            raise ValueError(msg)

        return t['digitized'] or t['original']

    def set(self, p, dt):
        return ocdfs.CustomOperation(self.write_exif_tag, p, dt)

    def write_exif_tag(self, p, dt):
        filepath = str(p)

        if filepath.lower().endswith('.jpg'):
            self._write_jpeg_exif_tag(filepath, dt)
        elif filepath.lower().endswith('.mp4'):
            self._write_mp4_exif_tag(filepath, dt)

    def _write_jpeg_exif_tag(self, filepath, dt):
        data = piexif.load(filepath)
        if 'Exif' not in data:
            data['Exif'] = {}

        dtbytes = datetime.strftime(dt, '%Y:%m:%d %H:%M:%S').encode('ascii')

        data["Exif"][piexif.ExifIFD.DateTimeOriginal] = dtbytes
        data["Exif"][piexif.ExifIFD.DateTimeDigitized] = dtbytes
        for tag in [
                piexif.ExifIFD.OffsetTime,
                piexif.ExifIFD.OffsetTimeOriginal,
                piexif.ExifIFD.OffsetTimeDigitized]:
            try:
                del(data['Exif'][tag])
            except KeyError:
                pass

        piexif.insert(piexif.dump(data), filepath)

    def _write_mp4_exif_tag(self, filepath, dt):
        def _random_sidefile():
            chrs = (
                [chr(x) for x in range(ord('a'), ord('z') + 1)] +
                [chr(x) for x in range(ord('A'), ord('Z') + 1)] +
                [chr(x) for x in range(ord('0'), ord('9') + 1)])

            name, ext = os.path.splitext(filepath)
            return '{name}-{rand}{ext}'.format(
                name=name,
                rand=''.join(random.choice(chrs) for _ in range(16)),
                ext=ext)

        # Seems that XMP tags are interpreted in UTC
        xmp_dt = dt - dt.astimezone().utcoffset()
        xmp_dt = datetime.strftime(xmp_dt, '%Y:%m:%d %H:%M:%S')

        tf = _random_sidefile()
        subprocess.run([
            'ffmpeg',
            '-loglevel', 'warning',
            '-i', filepath,
            '-vcodec', 'copy',
            '-acodec', 'copy',
            tf])
        subprocess.run([
            'exiftool',
            '-quiet',
            '-overwrite_original',
            '-CreateDate=' + xmp_dt,
            '-ModifyDate=' + xmp_dt,
            '-MediaCreateDate=' + xmp_dt,
            '-MediaModifyDate=' + xmp_dt,
            '-TrackCreateDate=' + xmp_dt,
            '-TrackModifyDate=' + xmp_dt,
            tf])

        os.rename(tf, filepath)

        timestamp = dt.timestamp()
        os.utime(filepath, (timestamp, timestamp))


class MtimeHandler(BaseHandler):
    def __init__(self, *args, set_atime=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_atime = set_atime

    def get(self, p):
        stamp = os.stat(str(p)).st_mtime
        return datetime.fromtimestamp(stamp)

    def set(self, p, dt):
        timestamp = dt.timestamp()
        return ocdfs.SetTimestampOperation(
            p, timestamp,
            set_mtime=True, set_atime=self.set_atime)


class NameHandler(BaseHandler):
    def __init__(self, format='%s', *args, default_datetime=datetime.now(),
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.default_dt = default_datetime
        self.format = format

        self._counter = 1
        self._tbl = {
            # '%': r'%',
            # The day of the month as a decimal number (range 01 to 31).
            'd': r'\d{2}',
            # The hour as a decimal number using a 24-hour clock (range 00 to
            # 23).
            'H': r'\d{2}',
            # The minute as a decimal number (range 00 to 59).
            'M': r'\d{2}',
            # The month as a decimal number (range 01 to 12).
            'm': r'\d{2}',
            # The second as a decimal number (range 00 to 60).
            'S': r'\d{2}',
            # The number of seconds since the Epoch, 1970-01-01 00:00:00 +0000
            # (UTC).
            's': r'\d+',
            # The year as a decimal number including the century.
            'Y': r'\d{4}',
            # The year as a decimal number without a century (range 00 to 99).
            'y': r'\d{4}',
        }

        self._tbl = {
            k: '(?P<{k}>{v})'.format(k=k, v=v)
            for (k, v) in self._tbl.items()
        }

    def validate_format(self, format):
        i = 0
        while i < len(format):
            if format[i] == '%':
                try:
                    param = format[i+1]
                except IndexError as e:
                    raise ValueError() from e

                if param != '%' and param not in self._tbl:
                    raise ValueError('%' + param)

                i += 2

            else:
                i += 1

    def regexify_fmt(self, fmt):
        self.validate_format(fmt)

        for (k, v) in self._tbl.items():
            fmt = fmt.replace('%' + k, v)

        return fmt

    def get(self, p):
        regexp = self.regexify_fmt(self.format)
        m = re.search(regexp, p.name)
        if not m:
            msg = "'{name}' doesn't match '{format}'"
            msg = msg.format(name=p, format=self.format)
            raise ValueError(msg)

        gd = m.groupdict()

        if 's' in gd and len(gd) == 1:
            return datetime.fromtimestamp(int(gd.get('s')))

        dt_args = (
            gd.get('Y') or self.default_dt.year,
            gd.get('m') or self.default_dt.month,
            gd.get('d') or self.default_dt.day,
            gd.get('H') or self.default_dt.hour,
            gd.get('M') or self.default_dt.minute,
            gd.get('S') or self.default_dt.second
        )
        dt_args = [int(x) for x in dt_args]

        return datetime(*dt_args)

    def set(self, p, dt):
        fmt = re.sub(r'%([0-9]*)i', r'{_ocd_index:\1}', self.format)

        fmt = fmt.format(_ocd_index=self._counter)
        name = dt.strftime(fmt)
        self._counter += 1

        new_p = p.parent / (name + p.suffix)
        if new_p != p:
            return ocdfs.RenameOperation(p, new_p)


class ShotwellHandler(BaseHandler):
    def __init__(self, format='%s', *args, default_datetime=datetime.now(),
                 **kwargs):
        super().__init__(*args, **kwargs)
        db = sqlite3.connect(os.path.expanduser(
            '~/.local/share/shotwell/data/photo.db'))
        self.cursor = db.cursor()

    def get(self, p):
        full_path = str(p.absolute())

        exposure_time = None
        basequery = "SELECT exposure_time from {table} where filename = ?"

        for table in ('PhotoTable', 'VideoTable'):
            query = basequery.format(table=table)
            row = self.cursor.execute(query, (full_path,)).fetchone()
            if row is None:
                continue

            (exposure_time, ) = row
            break

        # exposure_time = 997182000
        if exposure_time is None:
            errmsg = "File not found in shotwell database"
            raise RequiredDataNotFoundError(errmsg)

        if exposure_time is 0:
            errmsg = "Timestamp is 0"
            raise RequiredDataNotFoundError(errmsg)

        return datetime.fromtimestamp(exposure_time)

    def set(self, p, dt):
        raise NotImplementedError()


class App:
    HANDLERS = {
        'exif': ExifHandler,
        'mtime': MtimeHandler,
        'name': NameHandler,
    }

    @classmethod
    def build_parser(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-f', '--from',
            dest='src',
            choices=['exif', 'mtime', 'name', 'shotwell'],
            required=True)
        parser.add_argument(
            '-s', '--set',
            dest='dest',
            choices=['exif', 'mtime', 'name'],
            required=True)
        parser.add_argument(
            '--name-format',
            required=False)
        parser.add_argument(
            '--mtime-set-atime',
            action='store_false')
        parser.add_argument(
            '-r', '--recurse',
            action='store_true',
            default=False)
        parser.add_argument(
            dest='paths',
            nargs='+')

        return parser

    def __init__(self, src, dest, filesystem=None, logger=None):
        self.src = src
        self.dest = dest
        self.logger = logger or logging.getLogger('ocd-photos')
        self.filesystem = filesystem or ocdfs.FileSystem()

    def run_one(self, p):
        if not p.is_file():
            return

        try:
            dt = self.src.get(p)
        except RequiredDataNotFoundError as e:
            msg = "{path}: {err}"
            msg = msg.format(path=p, err=e)
            self.logger.error(msg)
            return
        except ValueError as e:
            msg = "{path}: {err}"
            msg = msg.format(path=p, err=e)
            self.logger.error(msg)
            return
        except InvalidFileTypeError as e:
            msg = "{path}: ignoring file as it's not compatible"
            msg = msg.format(path=p)
            self.logger.warning(msg)
            return

        op = self.dest.set(p, dt)
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

    if args.dry_run:
        fs = ocdfs.DryRunFilesystem()
    else:
        fs = ocdfs.Filesystem()

    src_handler_cls = BaseHandler.get_subclass(args.src)
    src_args = dict(extract_subarguments(args, args.src))
    src_handler = src_handler_cls(**src_args)

    dest_handler_cls = BaseHandler.get_subclass(args.dest)
    dest_args = dict(extract_subarguments(args, args.dest))
    dest_handler = dest_handler_cls(**dest_args)

    logger = logging.getLogger('ocd-photos')

    app = App(src=src_handler, dest=dest_handler, filesystem=fs, logger=logger)
    app.run(args.paths, recurse=args.recurse)


if __name__ == '__main__':
    main()
