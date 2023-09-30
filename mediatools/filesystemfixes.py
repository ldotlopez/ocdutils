import functools
from collections.abc import Callable
from pathlib import Path

import click

from .lib import filesystem as fs


def lowercase_extension_tr(filepath: Path) -> Path:
    return filepath.parent / (filepath.stem + filepath.suffix.lower())


def replace_extension_tr(filepath: Path, haystack: list[str], repl: str):
    if fs.get_file_extension(filepath) in haystack:
        return filepath.parent / (filepath.stem + "." + repl)

    return filepath


@click.command("fix-extensions")
@click.option("--recursive", "-r", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def fix_extensions_cmd(targets, *, recursive: bool = False, verbose: bool = False):
    trs: list[Callable[[Path], Path]] = [
        lowercase_extension_tr,
        functools.partial(replace_extension_tr, haystack=["jpeg"], repl="jpg"),
        functools.partial(replace_extension_tr, haystack=["mpeg"], repl="mpg"),
        functools.partial(replace_extension_tr, haystack=["tif"], repl="tiff"),
    ]

    for file in fs.iter_files_in_targets(
        targets, recursive=recursive, error_handler=lambda x: click.echo(x, err=True)
    ):
        dst = file
        for fn in trs:
            dst = fn(dst)

        if dst == file:
            if verbose:
                click.echo(f"{click.format_filename(file)}: already OK")
            continue

        try:
            dst = fs.safe_mv(file, dst, overwrite=False)
        except FileExistsError:
            click.echo(f"{click.format_filename(file)}: file already exists", err=True)
            continue

        if verbose:
            click.echo(f"{click.format_filename(file)} → {click.format_filename(dst)}")


@click.group("filesystem-fixes")
def filesystem_fixes_cmd():
    pass


def iter_over(*paths: Path, recursive: bool, include_roots: bool):
    for root in paths:
        pass


filesystem_fixes_cmd.add_command(fix_extensions_cmd)


def main():
    import sys

    sys.exit(filesystem_fixes_cmd())
