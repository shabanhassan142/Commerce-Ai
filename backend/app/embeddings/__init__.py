"""
embeddings/ — Embedding Model Wrapper (Module 3)

Provides a unified interface for generating text embeddings:
  - EmbeddingModel: Wraps SentenceTransformers
  - Model: BAAI/bge-small-en-v1.5 (local, no API cost)
  - embed_text(text): Returns a single embedding vector
  - embed_batch(texts): Returns a list of embedding vectors

The model is loaded once at startup and reused across requests.

Implemented in Module 3.
"""
