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


from collections.abc import Callable, Iterable
from concurrent import futures
from typing import Any

MapFunction = Callable[[Any], Any]
ClusteringCompareFunction = Callable[[Any, Any], Any]
ClusteringFilterFunction = Callable[[Any], bool]


def map_with_progress(
    collection: Iterable,
    map_fn: MapFunction,
    update_fn: Callable[[Any], Any] | None = None,
) -> Iterable[Any]:
    def _map_and_update(item):
        ret = map_fn(item)
        if update_fn:
            update_fn(item)
        return ret

    with futures.ThreadPoolExecutor() as executor:
        return executor.map(_map_and_update, collection)


def build_matrix(
    collection: list[Any], compare_fn: ClusteringCompareFunction, unfold: bool = False
):
    def _similarity_matrix():
        for idx1 in range(len(collection) - 1):
            for idx2 in range(idx1 + 1, len(collection)):
                yield collection[idx1], collection[idx2], compare_fn(
                    collection[idx1], collection[idx2]
                )

    ret = list(_similarity_matrix())
    if unfold:
        ret.extend([(b, a, x) for (a, b, x) in ret])

    return ret
