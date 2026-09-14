"""
app/rag/embedder.py

Embedding model manager using sentence-transformers.
Singleton pattern ensures the model is loaded only once.

Default model: BAAI/bge-small-en-v1.5 (384 dimensions, fast, accurate)
"""

import threading

import numpy as np

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingModel:
    """
    Singleton embedding model using sentence-transformers.

    Thread-safe lazy initialization — model loads on first use.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def _ensure_loaded(self):
        """Load the model on first use."""
        if not self._initialized:
            from sentence_transformers import SentenceTransformer

            model_name = settings.EMBEDDING_MODEL
            logger.info(f"Loading embedding model: {model_name}")

            self._model = SentenceTransformer(model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            self._initialized = True

            logger.info(
                f"Embedding model loaded: {model_name} "
                f"(dimension={self._dimension})"
            )

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        self._ensure_loaded()
        return self._dimension

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed a list of texts (documents/chunks).

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (len(texts), dimension).
        """
        self._ensure_loaded()

        if not texts:
            return np.array([]).reshape(0, self._dimension)

        logger.debug(f"Embedding {len(texts)} texts")
        embeddings = self._model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
            batch_size=32,
        )
        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query string.

        For BGE models, we prepend the query instruction.

        Args:
            query: The search query.

        Returns:
            numpy array of shape (1, dimension).
        """
        self._ensure_loaded()

        # BGE models benefit from a query prefix
        model_name = settings.EMBEDDING_MODEL.lower()
        if "bge" in model_name:
            query = f"Represent this sentence for searching relevant passages: {query}"

        embedding = self._model.encode(
            [query],
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(embedding, dtype=np.float32)


# Module-level singleton
_embedder = None


def get_embedder() -> EmbeddingModel:
    """Get the singleton embedding model instance."""
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingModel()
    return _embedder
