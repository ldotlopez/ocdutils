import sys
from functools import wraps
from pathlib import Path
from typing import Callable

import rich
import rich_click as click
from rich import print


def print_error(*args, **kwargs):
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


def target_options(fn: Callable) -> Callable:
    @click.option(
        "--pre-scan",
        is_flag=True,
        default=False,
        help="Scan targets before start operation",
    )
    @click.option(
        "-r", "--recursive", is_flag=True, default=False, help="Recurse into targets"
    )
    @click.argument(
        "targets",
        type=Path,
        nargs=-1,
        required=True,
    )
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


def file_conversion_options(fn: Callable) -> Callable:
    @click.option(
        "--overwrite",
        is_flag=True,
        default=False,
        help="Overwrite destination file if exists",
    )
    @click.option("--rm", is_flag=True, default=False, help="Remove original files")
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper
