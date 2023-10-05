#!/usr/bin/env python3

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


import subprocess


class ProcessFailure(Exception):
    def __init__(self, *, args, rc, stdout, stderr):
        self.args = args
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr


def run(argv: list[str], expected_rc: int | list[int] = 0):
    if isinstance(expected_rc, int):
        expected_rc = [expected_rc]
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    stdout, stderr = proc.communicate()
    if proc.returncode not in expected_rc:
        raise ProcessFailure(
            args=argv, rc=proc.returncode, stdout=stdout, stderr=stderr
        )
