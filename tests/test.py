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

import unittest


from datetime import datetime
from pathlib import Path


from ocdutils import (
    dtnamer,
    filesystem
)


class DatetimeTest(unittest.TestCase):
    def test_name_set_op(self):
        x = dtnamer.NameHandler(format='foo-%Y%m%d.%H%M%S')
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=5)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, filesystem.RenameOperation))
        self.assertEqual(op.dest, Path("/path/foo-19920102.030405.ext"))

    def test_mtime_set_op(self):
        x = dtnamer.MtimeHandler(set_atime=True)
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=5)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, filesystem.SetTimestampOperation))
        self.assertEqual(int(op.timestamp), 694317845)
        self.assertEqual(op.set_mtime, True)
        self.assertEqual(op.set_atime, True)

    def test_exif_set_op(self):
        x = dtnamer.ExifHandler()
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=5)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, filesystem.CustomOperation))
        self.assertEqual(op.fn, x.write_exif_tag)
        self.assertEqual(op.args, (Path('/path/foo.ext'), dt))

    def test_exif_set_op_with_zero(self):
        x = dtnamer.ExifHandler()
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=0)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, filesystem.CustomOperation))
        self.assertEqual(op.fn, x.write_exif_tag)
        self.assertEqual(op.args, (Path('/path/foo.ext'), dt))


if __name__ == '__main__':
    unittest.main()
