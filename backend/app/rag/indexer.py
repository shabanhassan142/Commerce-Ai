"""
app/rag/indexer.py

FAISS vector index manager.
Handles creating, saving, loading, and querying the FAISS index.
Stores document metadata alongside the index in a pickle sidecar.
"""

import json
import os
import pickle
from pathlib import Path

import faiss
import numpy as np

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.rag.embedder import get_embedder

logger = get_logger(__name__)
settings = get_settings()


# ── Module-level singleton ────────────────────────────────────────────────────
# All parts of the app (main.py startup, health.py, knowledge endpoint, agents)
# share the same FAISSIndexer instance via get_indexer().

_indexer_singleton: "FAISSIndexer | None" = None


def get_indexer() -> "FAISSIndexer":
    """Return the shared FAISSIndexer singleton (create if not exists)."""
    global _indexer_singleton
    if _indexer_singleton is None:
        _indexer_singleton = FAISSIndexer()
    return _indexer_singleton


class FAISSIndexer:
    """
    Manages a FAISS vector index with metadata sidecar.

    Files on disk:
        {index_path}.faiss     — FAISS binary index
        {index_path}.meta.pkl  — Pickled metadata list
        {index_path}.stats.json — Human-readable stats
    """

    def __init__(self, index_path: str | None = None):
        self.index_path = index_path or settings.FAISS_INDEX_PATH
        self.embedder = get_embedder()

        self._index: faiss.IndexFlatIP | None = None
        self._metadata: list[dict] = []
        self._texts: list[str] = []

    @property
    def faiss_file(self) -> str:
        return f"{self.index_path}.faiss"

    @property
    def meta_file(self) -> str:
        return f"{self.index_path}.meta.pkl"

    @property
    def stats_file(self) -> str:
        return f"{self.index_path}.stats.json"

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    @property
    def total_vectors(self) -> int:
        if self._index is None:
            return 0
        return self._index.ntotal

    def create_index(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
    ) -> int:
        """
        Create a new FAISS index from texts.

        Args:
            texts: Document chunks to index.
            metadatas: Optional metadata for each chunk.

        Returns:
            Number of vectors added.
        """
        if not texts:
            logger.warning("No texts provided, creating empty index")
            self._index = faiss.IndexFlatIP(self.embedder.dimension)
            self._metadata = []
            self._texts = []
            return 0

        metadatas = metadatas or [{} for _ in texts]
        assert len(texts) == len(metadatas), "texts and metadatas must match"

        logger.info(f"Creating FAISS index with {len(texts)} vectors")

        # Generate embeddings
        embeddings = self.embedder.embed_texts(texts)

        # Create index (Inner Product for cosine similarity with normalized vectors)
        dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)
        self._index.add(embeddings)

        self._texts = list(texts)
        self._metadata = list(metadatas)

        logger.info(
            f"FAISS index created: {self._index.ntotal} vectors, "
            f"dimension={dimension}"
        )
        return self._index.ntotal

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
    ) -> int:
        """
        Add documents to an existing index.

        Args:
            texts: New document chunks to add.
            metadatas: Optional metadata for each chunk.

        Returns:
            Total number of vectors after addition.
        """
        if not texts:
            return self.total_vectors

        metadatas = metadatas or [{} for _ in texts]

        if self._index is None:
            return self.create_index(texts, metadatas)

        embeddings = self.embedder.embed_texts(texts)
        self._index.add(embeddings)
        self._texts.extend(texts)
        self._metadata.extend(metadatas)

        logger.info(
            f"Added {len(texts)} vectors to index. "
            f"Total: {self._index.ntotal}"
        )
        return self._index.ntotal

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """
        Search the index for the most relevant chunks.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            score_threshold: Minimum similarity score (0-1).

        Returns:
            List of dicts with 'text', 'score', 'metadata' keys,
            sorted by relevance (highest score first).
        """
        if self._index is None or self._index.ntotal == 0:
            logger.warning("Search attempted on empty index")
            return []

        query_embedding = self.embedder.embed_query(query)
        scores, indices = self._index.search(query_embedding, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for missing results
                continue
            if score < score_threshold:
                continue

            results.append(
                {
                    "text": self._texts[idx],
                    "score": float(score),
                    "metadata": self._metadata[idx],
                }
            )

        return results

    def save(self) -> None:
        """Save the index and metadata to disk."""
        if self._index is None:
            logger.warning("No index to save")
            return

        # Create directory
        index_dir = os.path.dirname(self.index_path)
        if index_dir:
            os.makedirs(index_dir, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self._index, self.faiss_file)

        # Save metadata and texts
        with open(self.meta_file, "wb") as f:
            pickle.dump(
                {"texts": self._texts, "metadata": self._metadata}, f
            )

        # Save human-readable stats
        stats = {
            "total_vectors": self._index.ntotal,
            "dimension": self.embedder.dimension,
            "unique_sources": len(
                set(m.get("source", "unknown") for m in self._metadata)
            ),
            "index_path": self.index_path,
        }
        with open(self.stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        logger.info(
            f"Index saved: {self._index.ntotal} vectors -> {self.faiss_file}"
        )

    def load(self) -> bool:
        """
        Load the index and metadata from disk.

        Returns:
            True if loaded successfully, False if files don't exist.
        """
        if not os.path.exists(self.faiss_file):
            logger.info(f"No index file found at {self.faiss_file}")
            return False

        if not os.path.exists(self.meta_file):
            logger.warning(f"Index exists but metadata missing: {self.meta_file}")
            return False

        self._index = faiss.read_index(self.faiss_file)

        with open(self.meta_file, "rb") as f:
            data = pickle.load(f)
            self._texts = data["texts"]
            self._metadata = data["metadata"]

        logger.info(
            f"Index loaded: {self._index.ntotal} vectors from {self.faiss_file}"
        )
        return True

    def get_stats(self) -> dict:
        """Return index statistics."""
        if self._index is None:
            return {
                "status": "not_loaded",
                "total_vectors": 0,
                "on_disk": os.path.exists(self.faiss_file),
            }

        sources = {}
        for meta in self._metadata:
            src = meta.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        return {
            "status": "loaded",
            "total_vectors": self._index.ntotal,
            "dimension": self.embedder.dimension,
            "unique_sources": len(sources),
            "sources": sources,
            "on_disk": os.path.exists(self.faiss_file),
        }

    def clear(self) -> None:
        """Clear the in-memory index."""
        self._index = None
        self._metadata = []
        self._texts = []
        logger.info("Index cleared from memory")
