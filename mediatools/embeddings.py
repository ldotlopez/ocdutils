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


import logging
from typing import Any, cast

import click
import numpy as np
import platformdirs

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


class MiniApp:
    def __init__(self) -> None:
        self.engine = EmbeddingsFactory()
        self.cache = CacheDir(platformdirs.user_cache_path("glados/embeddings"))

    def get_embeddings(self, text: str) -> Embeddings:
        try:
            ret = cast(Embeddings, self.cache.get(text))
            LOGGER.info(f"Found embeddings for '{text[0:20]}' in cache")
            return ret
        except MissError:
            pass

        embeddings = self.engine.get_embeddings(text)
        LOGGER.info(f"Found embeddings for '{text[0:20]}' in API")

        self.cache.set(text, embeddings)

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


@click.command("similarity")
@click.argument("text-a", type=str)
@click.argument("text-b", type=str)
def similarity_cmd(text_a: str, text_b: str):
    similarity = MiniApp().similarity(text_a, text_b)
    click.echo(similarity)


embeddings_cmd.add_command(get_cmd)
embeddings_cmd.add_command(similarity_cmd)


# def main(*args) -> int:
#     return get_embeddings(*args) or 0


# if __name__ == "__main__":
#     import sys

#     sys.exit(main(*sys.argv))
