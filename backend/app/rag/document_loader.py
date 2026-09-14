"""
app/rag/document_loader.py

Load documents from various file formats.
Supported: .txt, .md, .pdf, .docx
"""

import os
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


def load_text_file(file_path: str) -> str:
    """Load plain text or markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_pdf_file(file_path: str) -> str:
    """Load PDF and extract text from all pages."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def load_docx_file(file_path: str) -> str:
    """Load DOCX and extract paragraph text."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


# Map extensions to loaders
LOADERS = {
    ".txt": load_text_file,
    ".md": load_text_file,
    ".pdf": load_pdf_file,
    ".docx": load_docx_file,
}


def load_document(file_path: str) -> tuple[str, dict]:
    """
    Load a document from disk. Returns (text, metadata).

    Args:
        file_path: Path to the document file.

    Returns:
        Tuple of (extracted_text, metadata_dict).

    Raises:
        ValueError: If file extension is not supported.
        FileNotFoundError: If file doesn't exist.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in LOADERS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(LOADERS.keys())}"
        )

    logger.info(f"Loading document: {path.name} ({ext})")
    text = LOADERS[ext](str(path))

    metadata = {
        "source": path.name,
        "file_path": str(path.absolute()),
        "file_type": ext,
        "file_size": os.path.getsize(file_path),
        "char_count": len(text),
    }

    logger.info(f"Loaded {metadata['char_count']} chars from {path.name}")
    return text, metadata


def load_directory(dir_path: str) -> list[tuple[str, dict]]:
    """
    Load all supported documents from a directory.

    Returns:
        List of (text, metadata) tuples.
    """
    path = Path(dir_path)
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    results = []
    for file in sorted(path.iterdir()):
        if file.suffix.lower() in LOADERS:
            try:
                text, meta = load_document(str(file))
                if text.strip():
                    results.append((text, meta))
            except Exception as e:
                logger.warning(f"Failed to load {file.name}: {e}")

    logger.info(f"Loaded {len(results)} documents from {dir_path}")
    return results
