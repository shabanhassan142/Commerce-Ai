"""
app/rag/chunker.py

Text chunking for RAG pipeline.
Splits documents into overlapping chunks for embedding and retrieval.

Uses a recursive character splitting strategy:
1. Split by double newlines (paragraphs)
2. Split by single newlines
3. Split by sentences
4. Split by characters (last resort)
"""

import re

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Separators in priority order
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]


def _split_text(text: str, separator: str) -> list[str]:
    """Split text by separator, keeping non-empty pieces."""
    pieces = text.split(separator)
    return [p.strip() for p in pieces if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    metadata: dict | None = None,
) -> list[dict]:
    """
    Split text into overlapping chunks with metadata.

    Args:
        text: The full document text to chunk.
        chunk_size: Max characters per chunk (default from settings).
        chunk_overlap: Overlap between consecutive chunks (default from settings).
        metadata: Base metadata to attach to each chunk.

    Returns:
        List of dicts with 'text', 'metadata' keys.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    metadata = metadata or {}

    if not text or not text.strip():
        return []

    # Clean the text
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse excessive newlines
    text = re.sub(r" {2,}", " ", text)       # Collapse excessive spaces

    # If text fits in one chunk, return it directly
    if len(text) <= chunk_size:
        return [
            {
                "text": text.strip(),
                "metadata": {**metadata, "chunk_index": 0, "total_chunks": 1},
            }
        ]

    # Recursive splitting
    segments = _recursive_split(text, chunk_size)

    # Merge small segments and create overlapping chunks
    chunks = _create_overlapping_chunks(segments, chunk_size, chunk_overlap)

    # Attach metadata
    result = []
    for i, chunk_text_str in enumerate(chunks):
        result.append(
            {
                "text": chunk_text_str.strip(),
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "char_count": len(chunk_text_str.strip()),
                },
            }
        )

    logger.info(
        f"Chunked document into {len(result)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return result


def _recursive_split(text: str, chunk_size: int) -> list[str]:
    """Recursively split text using separator hierarchy."""
    # Base case: text fits in chunk
    if len(text) <= chunk_size:
        return [text]

    # Try each separator
    for separator in SEPARATORS:
        pieces = _split_text(text, separator)
        if len(pieces) > 1:
            # Merge pieces back until they exceed chunk_size
            result = []
            current = ""
            for piece in pieces:
                candidate = (
                    f"{current}{separator}{piece}" if current else piece
                )
                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current:
                        result.append(current)
                    # If single piece is too large, recursively split it
                    if len(piece) > chunk_size:
                        result.extend(_recursive_split(piece, chunk_size))
                    else:
                        current = piece
            if current:
                result.append(current)
            return result

    # Last resort: hard split by character count
    result = []
    for i in range(0, len(text), chunk_size):
        result.append(text[i : i + chunk_size])
    return result


def _create_overlapping_chunks(
    segments: list[str], chunk_size: int, chunk_overlap: int
) -> list[str]:
    """Create overlapping chunks from segments."""
    if not segments:
        return []

    chunks = []
    current_chunk = ""

    for segment in segments:
        if not current_chunk:
            current_chunk = segment
        elif len(current_chunk) + len(segment) + 1 <= chunk_size:
            current_chunk = f"{current_chunk} {segment}"
        else:
            chunks.append(current_chunk)
            # Create overlap from end of current chunk
            if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                overlap_text = current_chunk[-chunk_overlap:]
                # Try to start at a word boundary
                space_idx = overlap_text.find(" ")
                if space_idx > 0:
                    overlap_text = overlap_text[space_idx + 1:]
                current_chunk = f"{overlap_text} {segment}"
            else:
                current_chunk = segment

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
