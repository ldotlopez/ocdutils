#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# Copyright (C) 2022 Luis López <luis@cuarentaydos.com>
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


import hashlib
import unittest

from ocdutils.motionphotos import MotionPhotoBytes
from pathlib import Path

DIRPATH = Path(__file__).parent / "assets"
COMPOSED_FILEPATH = DIRPATH / "motionphoto-composed.jpg"
COMPOSED_CHECKSUM = "5ad78ec9091940273eff389f0969fbb2"
IMAGE_FILEPATH = DIRPATH / "motionphoto-image.jpg"
IMAGE_CHECKSUM = "e3fd19e2b735ff750633183716a9a63b"
VIDEO_FILEPATH = DIRPATH / "motionphoto-video.mp4"
VIDEO_CHECKSUM = "45405c1f7333e477394391c478920ad0"


def md5(buff: bytes) -> str:
    return hashlib.md5(buff).hexdigest()


class MotionPhotoTest(unittest.TestCase):
    def test_load_simple(self):
        mp = MotionPhotoBytes.fromfile(IMAGE_FILEPATH)
        self.assertFalse(mp.has_video)
        self.assertEqual(md5(mp.image), IMAGE_CHECKSUM)
        self.assertEqual(mp.video, None)

    def test_load_composed(self):
        mp = MotionPhotoBytes.fromfile(COMPOSED_FILEPATH)

        self.assertTrue(mp.has_video)

        self.assertEqual(md5(mp.image), IMAGE_CHECKSUM)
        self.assertEqual(md5(mp.video), VIDEO_CHECKSUM)

    def test_insert_video(self):
        mp = MotionPhotoBytes.fromfile(IMAGE_FILEPATH)
        self.assertEqual(md5(mp.image), IMAGE_CHECKSUM)
        with open(VIDEO_FILEPATH, "rb") as fh:
            mp.insert_video(fh.read())

        self.assertEqual(md5(mp.image), IMAGE_CHECKSUM)
        self.assertEqual(md5(mp.video), VIDEO_CHECKSUM)
        self.assertEqual(md5(mp.data), COMPOSED_CHECKSUM)

    def test_drop_video(self):
        mp = MotionPhotoBytes.fromfile(COMPOSED_FILEPATH)
        mp.drop_video()

        self.assertEqual(md5(mp.image), IMAGE_CHECKSUM)
        self.assertEqual(md5(mp.data), IMAGE_CHECKSUM)


if __name__ == "__main__":
    unittest.main()
