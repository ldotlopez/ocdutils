#!/usr/bin/env python3

import itertools
from pathlib import Path
from typing import Iterable

from ..lib import fslib
from ..lib.clilib import click, print, print_error, rich, target_options

# Type aliases for clarity
# SidecarGroupSet = list[tuple[str, list[Path]]]

SidecarGroupSet = list[str, tuple[str, Path]]


def scan_for_sidecars(
    files: Iterable[Path], include_singles: bool = False
) -> SidecarGroupSet:

    groups_by_base = {}

    for f in files:
        base = str(f.parent / f.stem)
        if base not in groups_by_base:
            groups_by_base[base] = []

        ext = f.suffix.lstrip(".")
        groups_by_base[base].append((ext, f))

    groups: SidecarGroupSet = list(groups_by_base.items())

    if not include_singles:
        groups = [(base, pairs) for (base, pairs) in groups if len(pairs) > 1]

    return groups

    # if not include_singles:
    #     m = {k: v for k, v in m.items() if len(v) > 1}

    # return list(m.items())


def find_for_file(file: Path):
    candidates = file.parent.iterdir()

    results = scan_for_sidecars(candidates)

    results_map = dict(results)

    sidecars = results_map.get(_get_base_for_file(file))
    if not sidecars or len(sidecars) == 1:
        return None

    return sidecars


def filter_group_set_by_extensions(
    gs: SidecarGroupSet, extensions: list[str], ignore_case: bool = True
) -> SidecarGroupSet:

    ret = {}
    req_set = set(extensions)
    for base, pairs in gs:
        found_set = {x[0].lower() if ignore_case else x[0] for x in pairs}
        if found_set.issuperset(req_set):
            pairs = [(k, v) for k, v in pairs if k in req_set]
            ret[base] = pairs

    return list(ret.items())


@click.group
def sidecars_cmd():
    """Scan and search for sidecar files."""
    pass


@sidecars_cmd.command
@click.option(
    "--extension",
    "-e",
    "extensions",
    multiple=True,
    help="Only show groups with all specified extensions",
)
@click.option(
    "--cs",
    "case_sensitive",
    is_flag=True,
    default=False,
    help="case sensitive matching of extensions",
)
@target_options
def scan_cmd(
    targets: list[Path],
    case_sensitive: bool,
    recursive: bool,
    pre_scan: bool,
    extensions: tuple[str, ...],
):
    """Scan directories for sidecar file groups."""
    if extensions and len(extensions) < 2:
        print_error("Error: Provide at least two extensions")
        return 1

    files = fslib.iter_files(*targets, recursive=recursive)
    if pre_scan:
        files = list(files)  # type: ignore[assignment]

    extension_list = list(extensions) if extensions else None

    results = scan_for_sidecars(files)
    if extension_list:
        results = filter_group_set_by_extensions(
            results, extensions=extension_list, ignore_case=not case_sensitive
        )

    for basename, pairs in results:
        print(f"'{basename}' group")
        for ext, file in pairs:
            extension = file.suffix.lstrip(".")
            if not case_sensitive:
                extension = extension.lower()
            print(f"  {extension}: {file}")


@sidecars_cmd.command
@click.argument("file", type=Path)
def find_cmd(
    file: Path,
):
    """Find all sidecar files for a specific file."""
    if not file.is_file():
        print_error(f"Error: {file} is not a file")
        return 1

    sidecars = find_for_file(file)

    if not sidecars:
        print("No sidecar files found")
        return 0

    for _, file in sidecars:
        print(file)


def _get_base_for_file(file: Path):
    return str(file.parent / file.stem)
