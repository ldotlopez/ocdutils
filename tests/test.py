import unittest

import datetime

from housekeeper import filesystem as hkfs
from ocdutils import ocdphotos


class PhotosTest(unittest.TestCase):
    def test_name_set_op(self):
        x = ocdphotos.NameHandler(format='foo-%Y%m%d.%H%M%S')
        dt = datetime.datetime(year=1992, month=1, day=2,
                               hour=3, minute=4, second=5)

        op = x.set('/path/foo.ext', dt)
        self.assertTrue(isinstance(op, hkfs.RenameOperation))
        self.assertEqual(op.dest, "/path/foo-19920102.030405.ext")

    def test_mtime_set_op(self):
        x = ocdphotos.MtimeHandler(set_atime=True)
        dt = datetime.datetime(year=1992, month=1, day=2,
                               hour=3, minute=4, second=5)

        op = x.set('/path/foo.ext', dt)
        self.assertTrue(isinstance(op, hkfs.SetTimestampOperation))
        self.assertEqual(int(op.timestamp), 694317845)
        self.assertEqual(op.set_mtime, True)
        self.assertEqual(op.set_atime, True)

    def test_exif_set_op(self):
        x = ocdphotos.ExifHandler()
        dt = datetime.datetime(year=1992, month=1, day=2,
                               hour=3, minute=4, second=5)

        op = x.set('/path/foo.ext', dt)
        self.assertTrue(isinstance(op, hkfs.CustomOperation))
        self.assertEqual(op.fn, x.write_exif_tag)
        self.assertEqual(op.args, ('/path/foo.ext', dt))

    def test_exif_set_op_with_zero(self):
        x = ocdphotos.ExifHandler()
        dt = datetime.datetime(year=1992, month=1, day=2,
                               hour=3, minute=4, second=0)

        op = x.set('/path/foo.ext', dt)
        self.assertTrue(isinstance(op, hkfs.CustomOperation))
        self.assertEqual(op.fn, x.write_exif_tag)
        self.assertEqual(op.args, ('/path/foo.ext', dt))


if __name__ == '__main__':
    unittest.main()
