"""
Pytest fixtures for RAG integration tests.

These tests shouldn't require real OpenAI credentials. We provide a deterministic
embedding generator so `RAGService` can ingest and retrieve documents offline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

import pytest


def _fake_embed(text: str) -> List[float]:
    """Deterministic tiny embedding vector based on MD5 (16 floats)."""
    digest = hashlib.md5(text.encode("utf-8")).digest()  # 16 bytes
    # Map bytes to [-1, 1) range, ensure non-zero norm for typical text.
    return [(b - 128) / 128.0 for b in digest]


class FakeEmbeddingGenerator:
    """Drop-in replacement for `src.rag.embedding_generator.EmbeddingGenerator`."""

    def __init__(self, api_key=None, model: str = "fake-embedding"):
        self.api_key = api_key
        self.model = model

    def generate_embedding(self, text: str) -> List[float]:
        return _fake_embed(text.strip().replace("\n", " "))

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        # We don't need true batching here; keep it simple and deterministic.
        return [self.generate_embedding(t) for t in texts]

    def get_embedding_dimension(self) -> int:
        return 16


@pytest.fixture(scope="function")
def rag_service(tmp_path, monkeypatch):
    """
    Create an initialized RAGService with a temporary vector store and
    deterministic embeddings.
    """
    # Patch the embedding generator used by RAGService at construction time.
    import src.rag.rag_service as rag_service_module

    monkeypatch.setattr(rag_service_module, "EmbeddingGenerator", FakeEmbeddingGenerator)

    from src.rag import RAGService

    rag_db = tmp_path / "rag_vectors.db"
    rag = RAGService(
        chunk_size=300,
        chunk_overlap=50,
        embedding_model="fake-embedding",
        vector_store_path=str(rag_db),
        enable_cache=False,  # avoid writing cache DB into repo's data/
    )

    # Create a couple sample documents in the temp directory
    python_doc = tmp_path / "python_guide.txt"
    python_doc.write_text(
        "Python is a high-level programming language. Key features include readability and a large ecosystem.\n",
        encoding="utf-8",
    )

    flask_doc = tmp_path / "flask_guide.txt"
    flask_doc.write_text(
        "Flask is a lightweight Python web framework. It is used for building APIs and web apps.\n",
        encoding="utf-8",
    )

    # Ingest the documents
    rag.ingest_document(str(python_doc))
    rag.ingest_document(str(flask_doc))

    return rag


