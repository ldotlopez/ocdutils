import argparse
import logging
import random
import sys
from pathlib import Path

from .handlers import Factory


def _random_sidefile(filepath: Path) -> Path:
    filepath = filepath.absolute()

    chrs = (
        [chr(x) for x in range(ord("a"), ord("z") + 1)]
        + [chr(x) for x in range(ord("A"), ord("Z") + 1)]
        + [chr(x) for x in range(ord("0"), ord("9") + 1)]
    )

    randstr = "".join(random.choice(chrs) for _ in range(16))
    return Path(f"{filepath.parent}/{filepath.stem}.{randstr}{filepath.suffix}")


def main():
    logging.basicConfig()

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="cmd")

    readcmd = subparsers.add_parser("read", help="read metadata")
    readcmd.add_argument("-r", "--reader", default="stat")
    readcmd.add_argument("filepath", type=Path)

    args = parser.parse_args()

    if args.cmd == "read":
        reader = Factory(args.reader, args.filepath)
        print(repr(reader.get()))

    else:
        parser.print_help()
        sys.exit(255)
