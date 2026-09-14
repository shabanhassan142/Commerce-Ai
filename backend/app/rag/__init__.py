"""
app/rag/__init__.py

RAG (Retrieval-Augmented Generation) pipeline package.
Provides document loading, chunking, embedding, indexing, and retrieval.
"""

from app.rag.retriever import Retriever

__all__ = ["Retriever"]
