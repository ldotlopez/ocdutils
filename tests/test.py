import unittest

from datetime import datetime
from pathlib import Path

from ocdutils import (
    dt as ocddt,
    filesystem as ocdfs
)


class DatetimeTest(unittest.TestCase):
    def test_name_set_op(self):
        x = ocddt.NameHandler(format='foo-%Y%m%d.%H%M%S')
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=5)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, ocdfs.RenameOperation))
        self.assertEqual(op.dest, Path("/path/foo-19920102.030405.ext"))

    def test_mtime_set_op(self):
        x = ocddt.MtimeHandler(set_atime=True)
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=5)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, ocdfs.SetTimestampOperation))
        self.assertEqual(int(op.timestamp), 694317845)
        self.assertEqual(op.set_mtime, True)
        self.assertEqual(op.set_atime, True)

    def test_exif_set_op(self):
        x = ocddt.ExifHandler()
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=5)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, ocdfs.CustomOperation))
        self.assertEqual(op.fn, x.write_exif_tag)
        self.assertEqual(op.args, (Path('/path/foo.ext'), dt))

    def test_exif_set_op_with_zero(self):
        x = ocddt.ExifHandler()
        dt = datetime(year=1992, month=1, day=2,
                      hour=3, minute=4, second=0)

        op = x.set(Path('/path/foo.ext'), dt)
        self.assertTrue(isinstance(op, ocdfs.CustomOperation))
        self.assertEqual(op.fn, x.write_exif_tag)
        self.assertEqual(op.args, (Path('/path/foo.ext'), dt))


if __name__ == '__main__':
    unittest.main()
