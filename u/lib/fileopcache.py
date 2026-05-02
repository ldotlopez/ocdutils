import hashlib
import json
import logging
import pickle
import sqlite3
import threading
import time
from abc import abstractmethod
from contextlib import contextmanager
from math import floor, sqrt
from pathlib import Path
from typing import Any, Iterator, Self, cast

import click
import imagehash
from PIL import Image

logging.basicConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class DBFile:
    def __init__(self, file: Path | None = None):
        """Initialize database connection.

        Args:
            file: Path to SQLite database file, or None for in-memory database.
        """
        filepath = file.as_posix() if file else ":memory:"
        self._db = sqlite3.connect(filepath, check_same_thread=False)
        self._lock = threading.Lock()  # Thread safety

        # Only override row_factory if subclass provided a real one
        # if self.row_factory is not DBFile.row_factory:
        #     self._db.row_factory = self.row_factory

        LOGGER.debug(f"New {self.__class__.__name__} from '{filepath}'")

    def row_factory(self, cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> Any:
        """Override if you want custom row mapping."""
        raise NotImplementedError()

    def get_cursor(self) -> sqlite3.Cursor:
        """Get database cursor."""
        return self._db.cursor()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for database transactions with proper locking."""
        with self._lock:
            c = self.get_cursor()
            try:
                yield c
                self._db.commit()
            except sqlite3.Error:
                self._db.rollback()
                raise

    def close(self) -> None:
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CacheConfig:
    pass


class FileOperationCache(DBFile):
    TABLE: str

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS `{table}` (
            filepath TEXT NOT NULL PRIMARY KEY,
            validator BLOB,
            value BLOB,
            created_at REAL DEFAULT (unixepoch('now')),
            accessed_at REAL DEFAULT (unixepoch('now'))
        )
    """

    # def __init__(self, file: Path | None = None, config: CacheConfig | None = None):
    def __init__(
        self,
        file: Path | None = None,
    ):
        super().__init__(file=file)
        # self.config = config or CacheConfig()

        # Set up validation strategy
        # self._validation_strategies = {
        #     "default": ValidationStrategy.default,
        #     "with_inode": ValidationStrategy.with_inode,
        #     "content_hash": ValidationStrategy.content_hash,
        # }

        with self.transaction() as c:
            c.execute(self.SCHEMA.format(table=self.TABLE))
            # Add index for cleanup operations
            c.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_accessed_at ON `{self.TABLE}` (accessed_at)"
            )

    @abstractmethod
    def calculate_validator(self, file: Path) -> Any: ...

    @abstractmethod
    def calculate_value(self, file: Path) -> Any: ...

    @abstractmethod
    def serialize(self, native: Any) -> bytes: ...

    @abstractmethod
    def unserialize(self, raw: bytes) -> Any: ...

    def get(self, file: Path) -> Any:
        return self.get_or_calculate(file)[0]

    def get_or_calculate(self, file: Path) -> tuple[Any, bool]:
        current_validator = self.calculate_validator(file)

        try:
            value = self._load_from_db(file, current_validator)
            self._update_access_time(file)
            # LOGGER.info(f"'{file}' found in cache")
            return value, False

        except NoResultError:
            value = self.calculate_value(file)
            validator = self.calculate_validator(file)
            self._save_to_db(file, validator, value)
            # LOGGER.info(f"'{file}' calculated and stored in cache")
            return value, True

    def _load_from_db(self, file: Path, current_validator: Any) -> Any:
        c = self.get_cursor()
        res = c.execute(
            f"SELECT * from {self.TABLE} WHERE filepath = ?", (file.as_posix(),)
        )

        row = res.fetchone()
        if row is None:
            raise NoResultError()

        _, validator, value, _, _ = row

        try:
            stored_validator = self.unserialize(validator)
        except ValueError:
            raise NoResultError()

        if stored_validator == current_validator:
            return self.unserialize(value)
        else:
            raise NoResultError()

    def _save_to_db(self, file: Path, validator: Any, value: Any):
        filepath = file.as_posix()
        _validator = self.serialize(validator)
        _value = self.serialize(value)

        with self.transaction() as c:
            c.execute(
                f"INSERT INTO `{self.TABLE}` (filepath, validator, value) "
                f"VALUES (?, ?, ?) "
                f"ON CONFLICT(filepath) DO UPDATE SET "
                f"validator=excluded.validator, value=excluded.value, "
                f"created_at=unixepoch('now'), accessed_at=unixepoch('now')",
                (filepath, _validator, _value),
            )

    def _update_access_time(self, file: Path) -> None:
        """Update last accessed time for cache entry."""
        with self.transaction() as c:
            c.execute(
                f"UPDATE `{self.TABLE}` SET accessed_at = unixepoch('now') WHERE filepath = ?",
                (file.as_posix(),),
            )


class Validators:
    @classmethod
    def mtime(cls, file: Path) -> float:
        return file.stat().st_mtime

    @classmethod
    def size(cls, file: Path) -> int:
        return file.stat().st_size

    @classmethod
    def fast_checksum(cls, file: Path) -> str:
        return fast_file_hexhash(file)

    @classmethod
    def full(cls, file: Path) -> tuple[float, int, str]:
        return (cls.mtime(file), cls.size(file), cls.fast_checksum(file))


class NoResultError(Exception):
    pass


class MultipleResultError(Exception):
    pass


class FileHashStore(FileOperationCache):
    TABLE = "file_hash_v1"
    HASH_ALGORITHM = "sha1"

    def get(self, file: Path) -> str:
        return str(super().get(file))

    def calculate_validator(self, file: Path) -> tuple[float, int, str]:
        return Validators.full(file)

    def calculate_value(self, file: Path) -> str:
        with file.open("rb") as fh:
            return hashlib.file_digest(fh, self.HASH_ALGORITHM).hexdigest()

    def serialize(self, native: Any) -> bytes:
        return Codecs.json_serialize(native)

    def unserialize(self, raw: bytes) -> Any:
        return Codecs.json_unserialize(raw)


def fast_file_hexhash(file: Path, size: int = 1024, digest=hashlib.sha1) -> str:
    with file.open("rb") as fh:
        start = fh.read(size)
        fh.seek(-size, 2)
        end = fh.read(size)

    d = digest()
    d.update(start + end)
    return d.hexdigest()


class Codecs:
    @classmethod
    def json_unserialize(cls, raw: bytes) -> Any:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeError, TypeError) as e:
            raise ValueError() from e

    @classmethod
    def json_serialize(cls, native: Any) -> bytes:
        return json.dumps(native).encode("utf-8")

    @classmethod
    def pickle_serialize(cls, native: Any) -> bytes:
        return pickle.dumps(native)

    @classmethod
    def pickle_unserialize(cls, raw: bytes) -> Any:
        return pickle.loads(raw)


class PerfMonitor:
    def __init__(self) -> None:
        self.start_ns: float = 0
        self.end_ns: float = 0
        self.time_elapsed_ns: float = 0

    @property
    def start(self) -> float:
        return self.start_ns / 1_000

    @property
    def end(self) -> float:
        return self.end_ns / 1_000

    @property
    def time_elapsed(self) -> float:
        return self.time_elapsed_ns / 1_000

    def __enter__(self) -> Self:
        self.start_ns = time.monotonic_ns()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_ns = time.monotonic_ns()
        self.time_elapsed_ns = self.end_ns - self.start_ns


@click.command
@click.option("--db", type=Path)
@click.argument("files", type=Path, required=True, nargs=-1)
def main(db: Path, files: list[Path]):
    ops = AverageHashStore(file=db)
    for f in files:
        with PerfMonitor() as m:
            value, calc = ops.get_or_calculate(f)

        print(f"'{f}': value={value} (calc={calc}, time={m.time_elapsed})")


if __name__ == "__main__":
    main()
