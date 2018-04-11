import pathlib


class InvalidFileTypeError(Exception):
    pass


class RequiredDataNotFoundError(Exception):
    pass


def crc32(p, block_size=1024*1024*4):
    """
    Calculate crc32 for a path object.
    CRC32 is returned as a hexadecimal string
    """

    if not isinstance(p, pathlib.Path):
        p = pathlib.Path(p)

    with p.open('rb') as fh:
        value = 0
        while True:
            buff = fh.read(block_size)
            if not buff:
                break

            value = zlib.crc32(buff, value)

        return hex(value)[2:]
