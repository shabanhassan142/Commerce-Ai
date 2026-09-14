"""
app/rag/retriever.py

High-level retrieval interface combining document loading,
chunking, indexing, and semantic search.

This is the main entry point for RAG operations.
"""

import os
from pathlib import Path

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.rag.chunker import chunk_text
from app.rag.document_loader import load_document, load_directory
from app.rag.indexer import FAISSIndexer

logger = get_logger(__name__)
settings = get_settings()


class Retriever:
    """
    High-level RAG retriever.

    Provides:
        - ingest_file(): Load, chunk, and index a single document
        - ingest_directory(): Bulk ingest all documents in a folder
        - ingest_texts(): Directly index text chunks (e.g., product data)
        - search(): Semantic search across all indexed content
        - stats(): Index statistics
    """

    def __init__(self, index_path: str | None = None):
        self._indexer = FAISSIndexer(index_path)
        self._loaded = False

    def _ensure_loaded(self):
        """Try loading existing index from disk."""
        if not self._loaded:
            self._indexer.load()
            self._loaded = True

    def ingest_file(self, file_path: str) -> int:
        """
        Load, chunk, and index a single document.

        Args:
            file_path: Path to the document.

        Returns:
            Number of chunks indexed from this file.
        """
        self._ensure_loaded()

        text, meta = load_document(file_path)
        chunks = chunk_text(text, metadata={"source": meta["source"], "file_type": meta["file_type"]})

        if not chunks:
            logger.warning(f"No chunks generated from {file_path}")
            return 0

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        self._indexer.add_documents(texts, metadatas)
        self._indexer.save()

        logger.info(f"Ingested {len(chunks)} chunks from {meta['source']}")
        return len(chunks)

    def ingest_directory(self, dir_path: str) -> int:
        """
        Bulk ingest all supported documents in a directory.

        Returns:
            Total number of chunks indexed.
        """
        self._ensure_loaded()

        docs = load_directory(dir_path)
        total_chunks = 0

        all_texts = []
        all_metadatas = []

        for text, meta in docs:
            chunks = chunk_text(
                text,
                metadata={"source": meta["source"], "file_type": meta["file_type"]},
            )
            for c in chunks:
                all_texts.append(c["text"])
                all_metadatas.append(c["metadata"])
            total_chunks += len(chunks)

        if all_texts:
            self._indexer.add_documents(all_texts, all_metadatas)
            self._indexer.save()

        logger.info(
            f"Ingested {total_chunks} chunks from {len(docs)} documents"
        )
        return total_chunks

    def ingest_texts(
        self,
        texts: list[str],
        source: str = "database",
        metadatas: list[dict] | None = None,
    ) -> int:
        """
        Directly index pre-processed text chunks.
        Used for indexing database content (products, FAQs, etc.)

        Args:
            texts: List of text strings to index.
            source: Source identifier for metadata.
            metadatas: Optional per-text metadata dicts.

        Returns:
            Number of texts indexed.
        """
        self._ensure_loaded()

        if not texts:
            return 0

        if metadatas is None:
            metadatas = [
                {"source": source, "chunk_index": i, "total_chunks": len(texts)}
                for i in range(len(texts))
            ]

        self._indexer.add_documents(texts, metadatas)
        self._indexer.save()

        logger.info(f"Indexed {len(texts)} texts from source: {source}")
        return len(texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> list[dict]:
        """
        Semantic search across all indexed content.

        Args:
            query: Natural language search query.
            top_k: Maximum results to return.
            score_threshold: Minimum similarity score (0-1).

        Returns:
            List of results with 'text', 'score', 'metadata'.
        """
        self._ensure_loaded()
        return self._indexer.search(query, top_k, score_threshold)

    def get_stats(self) -> dict:
        """Return index statistics."""
        self._ensure_loaded()
        return self._indexer.get_stats()

    def rebuild_index(self) -> None:
        """Clear and rebuild from scratch."""
        self._indexer.clear()
        self._loaded = True
        logger.info("Index cleared for rebuild")


# ── Module-level singleton ────────────────────────────────────────────────────

_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """Get the singleton Retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
