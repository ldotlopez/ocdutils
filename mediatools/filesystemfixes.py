import functools
from collections.abc import Callable
from pathlib import Path

import click

from .lib import filesystem as fs


def lowercase_extension_tr(filepath: Path) -> Path:
    return filepath.parent / (filepath.stem + filepath.suffix.lower())


def lowercase_extension_op(filepath: Path) -> Path:
    dest = lowercase_extension_tr(filepath)
    if dest.exists():
        raise FileExistsError(dest)

    filepath.rename(dest)
    return dest


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
    ]

    if recursive:
        g = fs.iter_files(*targets)
    else:
        g = targets

    for path in g:
        if not path.is_file():
            click.echo(f"{click.format_filename(path)}: not a file", err=True)
            continue

        dst = path
        for fn in trs:
            dst = fn(dst)

        if dst == path:
            if verbose:
                click.echo(f"{click.format_filename(path)}: already OK")
            continue

        try:
            dst = fs.safe_mv(path, dst, overwrite=False)
        except FileExistsError:
            click.echo(f"{click.format_filename(path)}: file already exists", err=True)
            continue

        if verbose:
            click.echo(f"{click.format_filename(path)} → {click.format_filename(dst)}")


def main():
    import sys

    sys.exit(fix_extensions_cmd())
