import zlib
from pathlib import Path


def crc32_hash_frombytes(data: bytes):
    return hex(zlib.crc32(data))[2:]


def crc32_hash_frompath(filepath: Path):
    with open(filepath, "rb") as fh:
        return crc32_hash_frombytes(fh.read())
