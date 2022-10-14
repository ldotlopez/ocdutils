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


from setuptools import setup


import datetime


setup(
    name="ocdutils",
    version="1.0.0-alpha" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
    author="Luis López",
    author_email="luis@cuarentaydos.com",
    packages=["ocdutils"],
    scripts=[],
    url="https://github.com/ldotlopez/ocdutils",
    license="LICENSE.txt",
    description=(
        'Utils for control your "Obsessive-Compulsive Disorder" with your data'
    ),
    long_description=open("README.md").read(),
    install_requires=["piexif", "pillow", "py-dateutil"],
    entry_points={
        "console_scripts": [
            "ocd-remove-sidecar-videos=ocdutils.sidecars:main",
            "ocd-dt-namer=ocdutils.dtnamer:main",
            "ocd-uniq-namer=ocdutils.uniqnamer:main",
            "ocd-fs-janitor=ocdutils.fsjanitor:main",
        ]
    },
)
