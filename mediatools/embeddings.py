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
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import click
import magic
import numpy as np
import platformdirs

from mediatools.lib import filesystem as fs
from mediatools.lib.cache import CacheDir, MissError

from .backends import BaseBackendFactory, Embeddings, EmbeddingsHandler

LOGGER = logging.getLogger(__name__)

ENVIRON_KEY = "TEXT_EMBEDDINGS"
DEFAULT_BACKEND = "openai"
BACKENDS = {"openai": "OpenAI"}


def cosine_similarity(embedding1: Embeddings, embedding2: Embeddings) -> float:
    """Calculate the cosine similarity between two embeddings."""
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    if norm1 == 0 or norm2 == 0:
        return 0.0  # Avoid division by zero
    return dot_product / (norm1 * norm2)


def euclidean_distance(
    embedding1: Embeddings, embedding2: Embeddings
) -> np.floating[Any]:
    """Calculate the Euclidean distance between two embeddings."""
    return np.linalg.norm(np.array(embedding1) - np.array(embedding2))


def compare_embeddings(
    embedding1: Embeddings, embedding2: Embeddings
) -> tuple[float, np.floating[Any]]:
    """Compare two sets of embeddings and return cosine similarity and Euclidean distance."""
    cos_sim = cosine_similarity(embedding1, embedding2)
    euc_dist = euclidean_distance(embedding1, embedding2)
    return cos_sim, euc_dist


def get_embeddings(text: str) -> Embeddings:
    return EmbeddingsFactory().get_embeddings(text)


def EmbeddingsFactory(backend: str | None = None, **kwargs) -> EmbeddingsHandler:
    return BaseBackendFactory(
        backend=backend, id=ENVIRON_KEY, map=BACKENDS, default=DEFAULT_BACKEND
    )(**kwargs)

    # return BackendHandler()(backend)(**kwargs)


class BaseBackendHandler:
    def __init__(self):
        pass

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass


class BackendHandler(BaseBackendHandler):
    BASE_MODULE = "mediatools.backends"
    ENVIRON_VAR = "MEDIATOOLS_TEXT_EMBEDDINGS_BACKEND"
    HANDLERS = {"openai": "openai.OpenAI"}


@dataclasses.dataclass
class EmbeddingsRecord:
    _: dataclasses.KW_ONLY
    id: str
    path: Path
    embeddings: Embeddings
    text_checksum: str
    mtime: int

    @classmethod
    def cursor_factory(cls, _: sqlite3.Cursor, row: sqlite3.Row) -> EmbeddingsRecord:
        id, path, text_checksum, mtime, embeddings = row
        return cls(
            id=id,
            path=Path(path),
            mtime=mtime,
            text_checksum=text_checksum,
            embeddings=json.loads(embeddings),
        )


class Storage:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(exist_ok=True, parents=True)
        self.conn = sqlite3.connect(db_path)

        with self.cursor_ctx() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL UNIQUE,
                    text_checksum TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    embeddings TEXT NOT NULL
                );
            """
            )
        self.conn.commit()

    @contextmanager
    def cursor_ctx(self):
        yield self.conn.cursor()

    def query(self, *, file: str | Path) -> EmbeddingsRecord:
        with self.cursor_ctx() as cursor:
            cursor.row_factory = EmbeddingsRecord.cursor_factory
            cursor.execute(
                """
                SELECT * FROM embeddings WHERE path = ?;
                """,
                (file,),
            )

            return cursor.fetchone()

    def insert(
        self,
        *,
        file: str | Path,
        text_checksum: str,
        mtime: float,
        embeddings: Embeddings,
    ):
        if isinstance(file, Path):
            file = file.as_posix()

        embeddings_ = json.dumps(embeddings)

        with self.cursor_ctx() as cursor:
            cursor.execute(
                """
                INSERT INTO embeddings (path, text_checksum, mtime, embeddings)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    embeddings = excluded.embeddings,
                    text_checksum = excluded.text_checksum,
                    mtime = excluded.mtime;
                """,
                (file, text_checksum, mtime, embeddings_),
            )

        self.conn.commit()


class MiniApp:
    def __init__(self) -> None:
        self.storage = Storage(
            platformdirs.user_data_path("glados/embeddings/db.sqlite3")
        )
        self.engine = EmbeddingsFactory()

    def index(self, file: Path, *, force: bool = False):
        @lru_cache
        def mime_is_compatible(mime: str) -> bool:
            return mime in ["text/plain"] or mime.startswith("text/x-script.")

        record = self.storage.query(file=file.as_posix())
        file_mtime = file.stat().st_mtime
        needs_update = force or record is None or (file_mtime > record.mtime)

        if not needs_update:
            LOGGER.info(f"{file}: already indexed")
            return

        mime = magic.from_file(file, mime=True)

        compatible = mime_is_compatible(mime)
        if not compatible:
            LOGGER.info(f"{file}: not compatible")
            return

        text = file.read_text()
        embedings = self.engine.get_embeddings(text)
        text_checksum = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.storage.insert(
            file=file,
            embeddings=embedings,
            text_checksum=text_checksum,
            mtime=file_mtime,
        )
        return

    def get_embeddings(self, text: str) -> Embeddings:
        # try:
        #     ret = cast(Embeddings, self.cache.get(text))
        #     LOGGER.info(f"Found embeddings for '{text[0:20]}' in cache")
        #     return ret
        # except MissError:
        #     pass

        embeddings = self.engine.get_embeddings(text)

        # LOGGER.info(f"Found embeddings for '{text[0:20]}' in API")
        # self.cache.set(text, embeddings)

        return embeddings

    def similarity(self, a: str, b: str) -> float:
        a_vec = self.get_embeddings(a)
        b_vec = self.get_embeddings(b)

        return cosine_similarity(a_vec, b_vec)


@click.group("embeddings")
def embeddings_cmd():
    pass


@click.command("get")
@click.argument("text", type=str)
def get_cmd(text: str):
    embeddings = MiniApp().get_embeddings(text)
    click.echo(embeddings)


@click.command("scan")
@click.option("-f", "--force", is_flag=True, default=False)
@click.argument("targets", nargs=-1, required=True, type=Path)
def scan_cmd(targets: list[Path], force: bool = False):
    app = MiniApp()

    for file in fs.iter_files_in_targets(targets, recursive=True):
        app.index(file, force=force)
        print(file)


@click.command("similarity")
@click.argument("text-a", type=str)
@click.argument("text-b", type=str)
def similarity_cmd(text_a: str, text_b: str):
    similarity = MiniApp().similarity(text_a, text_b)
    click.echo(similarity)


embeddings_cmd.add_command(get_cmd)
embeddings_cmd.add_command(similarity_cmd)
embeddings_cmd.add_command(scan_cmd)

# def main(*args) -> int:
#     return get_embeddings(*args) or 0


# if __name__ == "__main__":
#     import sys

#     sys.exit(main(*sys.argv))
