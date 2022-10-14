import unittest
from fnmatch import fnmatch
from pathlib import Path

from ocdutils.ng import (
    _random_sidefile,
)  # JpegHandler,; VideoHandler,; handler_for_file,; MissingHandlerError,


class NgTest(unittest.TestCase):
    def test_handler_for_jpg(self):
        self.assertEqual(handler_for_file(Path("test.jpg")), JpegHandler)
        self.assertEqual(handler_for_file(Path("test.JPG")), JpegHandler)
        self.assertEqual(handler_for_file(Path("test.jpeg")), JpegHandler)

    def test_handler_for_video(self):
        self.assertEqual(handler_for_file(Path("test.mov")), VideoHandler)
        self.assertEqual(handler_for_file(Path("test.mp4")), VideoHandler)
        self.assertEqual(handler_for_file(Path("test.m4v")), VideoHandler)
        self.assertEqual(handler_for_file(Path("test.M4V")), VideoHandler)

        with self.assertRaises(MissingHandlerError):
            handler_for_file(Path("test.txt"))

    def test_missing_handler(self):
        with self.assertRaises(MissingHandlerError):
            handler_for_file(Path("test.txt"))

    def test_sidefile(self):
        src = Path("test")
        sidefile = _random_sidefile(src)

        self.assertTrue(sidefile.is_absolute())
        self.assertTrue(fnmatch(str(sidefile.name), "test.*"))

        sidefile = _random_sidefile(Path("foo.jpg"))
        self.assertTrue(fnmatch(str(sidefile.name), "foo.*.jpg"))


if __name__ == "__main__":
    unittest.main()
