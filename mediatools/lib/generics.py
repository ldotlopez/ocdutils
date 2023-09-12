import warnings
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


def build_hash_table(
    collection: Iterable[Any], hash_fn: MapFunction
) -> dict[str, list[Any]]:
    warnings.warn("deprecated, use itertools.groupby")
    with futures.ThreadPoolExecutor() as executor:
        results = executor.map(lambda x: (x, hash_fn(x)), collection)

    tbl = {}
    for item, ih in results:
        if ih not in tbl:
            tbl[ih] = [item]
        else:
            tbl[ih].append(item)

    return tbl


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
