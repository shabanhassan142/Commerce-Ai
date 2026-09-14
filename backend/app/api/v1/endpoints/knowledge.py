"""
app/api/v1/endpoints/knowledge.py

Knowledge base API endpoints for RAG pipeline.
Handles document upload, semantic search, product indexing, and stats.
"""

import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, require_role
from app.config.settings import get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.models.product import Product
from app.models.user import User, UserRole
from app.rag.retriever import get_retriever
from app.utils.responses import error_response, success_response

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])
logger = get_logger(__name__)
settings = get_settings()


@router.post(
    "/upload",
    summary="Upload a document to the knowledge base",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, TXT, DOCX, MD)"),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Upload and index a document into the knowledge base.
    Admin only — the document is chunked, embedded, and added to the FAISS index.
    """
    # Validate extension
    allowed = settings.allowed_extensions_list
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext.lstrip(".") not in allowed:
        return error_response(
            message=f"Unsupported file type: {ext}. Allowed: {allowed}",
            status_code=400,
        )

    # Validate size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        return error_response(
            message=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB",
            status_code=400,
        )

    # Save to uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Index the document
    try:
        retriever = get_retriever()
        chunks_count = retriever.ingest_file(file_path)

        return success_response(
            data={
                "filename": file.filename,
                "saved_as": safe_name,
                "chunks_indexed": chunks_count,
                "file_size": len(content),
            },
            message=f"Document indexed successfully ({chunks_count} chunks)",
            status_code=201,
        )
    except Exception as e:
        logger.error(f"Failed to index document: {e}", exc_info=True)
        # Clean up the saved file
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response(
            message=f"Failed to index document: {str(e)}",
            status_code=500,
        )


@router.post(
    "/search",
    summary="Semantic search across the knowledge base",
)
async def search_knowledge(
    query: str = Query(..., min_length=2, description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Max results"),
    user: User = Depends(get_current_active_user),
):
    """
    Semantic search using the FAISS vector index.
    Returns the most relevant document chunks for the given query.
    """
    try:
        retriever = get_retriever()
        results = retriever.search(query, top_k=top_k)

        return success_response(
            data={
                "query": query,
                "results": results,
                "count": len(results),
            },
            message=f"Found {len(results)} relevant results",
        )
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return error_response(
            message=f"Search failed: {str(e)}",
            status_code=500,
        )


@router.post(
    "/index-products",
    summary="Index product data from the database",
)
async def index_products(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Pull all active products from the database and index them
    into the FAISS knowledge base. This enables the AI chatbot
    to answer product-related questions.
    """
    try:
        result = await db.execute(
            select(Product).where(Product.is_active == True)  # noqa: E712
        )
        products = result.scalars().all()

        if not products:
            return error_response(message="No active products found", status_code=404)

        texts = []
        metadatas = []

        for p in products:
            # Create a rich text representation of each product
            cat_name = p.category.name if p.category else "Uncategorized"
            seller_name = p.seller.name if p.seller else "Unknown Seller"

            text = (
                f"Product: {p.name}\n"
                f"Category: {cat_name}\n"
                f"Seller: {seller_name}\n"
                f"Price: PKR {p.price}\n"
                f"Rating: {p.rating}/5 ({p.review_count} reviews)\n"
                f"Stock: {'In Stock' if p.stock > 0 else 'Out of Stock'} ({p.stock} units)\n"
                f"SKU: {p.sku}\n"
                f"Description: {p.description}"
            )
            texts.append(text)
            metadatas.append({
                "source": "products_db",
                "product_id": str(p.id),
                "product_name": p.name,
                "category": cat_name,
                "seller": seller_name,
                "price": float(p.price),
                "sku": p.sku,
            })

        retriever = get_retriever()
        count = retriever.ingest_texts(texts, source="products_db", metadatas=metadatas)

        return success_response(
            data={"products_indexed": count},
            message=f"Indexed {count} products into knowledge base",
        )
    except Exception as e:
        logger.error(f"Product indexing failed: {e}", exc_info=True)
        return error_response(
            message=f"Product indexing failed: {str(e)}",
            status_code=500,
        )


@router.post(
    "/index-docs",
    summary="Index all knowledge documents from the docs folder",
)
async def index_knowledge_docs(
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Index all documents from the knowledge_docs/ directory.
    These are policy documents, FAQs, shipping info, etc.
    """
    docs_dir = os.path.join(os.getcwd(), "knowledge_docs")

    if not os.path.isdir(docs_dir):
        return error_response(
            message=f"Knowledge docs directory not found: {docs_dir}",
            status_code=404,
        )

    try:
        retriever = get_retriever()
        chunks_count = retriever.ingest_directory(docs_dir)

        return success_response(
            data={"chunks_indexed": chunks_count, "source_dir": docs_dir},
            message=f"Indexed {chunks_count} chunks from knowledge docs",
        )
    except Exception as e:
        logger.error(f"Knowledge docs indexing failed: {e}", exc_info=True)
        return error_response(
            message=f"Indexing failed: {str(e)}",
            status_code=500,
        )


@router.get(
    "/stats",
    summary="Get knowledge base statistics",
)
async def knowledge_stats(
    user: User = Depends(get_current_active_user),
):
    """Return statistics about the FAISS knowledge base index."""
    try:
        retriever = get_retriever()
        stats = retriever.get_stats()

        return success_response(
            data=stats,
            message="Knowledge base statistics",
        )
    except Exception as e:
        logger.error(f"Stats failed: {e}", exc_info=True)
        return error_response(
            message=f"Failed to get stats: {str(e)}",
            status_code=500,
        )
