"""
app/rag/build_index.py

Build the initial FAISS index from knowledge docs and product data.

Usage:
    cd backend
    venv\\Scripts\\python.exe -m app.rag.build_index
"""

import asyncio
import os
import sys


async def build_index():
    """Build the FAISS index from knowledge docs and product data."""
    # Lazy imports to avoid circular import issues
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config.settings import get_settings
    from app.database.base import Base  # noqa: F401 — triggers model registration
    from app.models.product import Product
    from app.rag.retriever import Retriever

    settings = get_settings()
    retriever = Retriever()

    print("=" * 60)
    print("Building CommerceFlow AI Knowledge Base Index")
    print("=" * 60)

    # ── 1. Index knowledge documents ──────────────────────────────────
    docs_dir = os.path.join(os.getcwd(), "knowledge_docs")
    if os.path.isdir(docs_dir):
        print(f"\n[1/2] Indexing knowledge docs from: {docs_dir}")
        chunks = retriever.ingest_directory(docs_dir)
        print(f"  [+] Indexed {chunks} chunks from knowledge docs")
    else:
        print(f"\n[1/2] Knowledge docs directory not found: {docs_dir}")
        print("  [!] Skipping knowledge docs")

    # ── 2. Index product data ─────────────────────────────────────────
    print(f"\n[2/2] Indexing product data from database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(Product).where(Product.is_active == True)  # noqa: E712
        )
        products = result.scalars().all()

        if products:
            texts = []
            metadatas = []

            for p in products:
                cat_name = p.category.name if p.category else "Uncategorized"
                seller_name = p.seller.name if p.seller else "Unknown"

                text = (
                    f"Product: {p.name}\n"
                    f"Category: {cat_name}\n"
                    f"Seller: {seller_name}\n"
                    f"Price: PKR {p.price}\n"
                    f"Rating: {p.rating}/5 ({p.review_count} reviews)\n"
                    f"Stock: {'In Stock' if p.stock > 0 else 'Out of Stock'}\n"
                    f"SKU: {p.sku}\n"
                    f"Description: {p.description}"
                )
                texts.append(text)
                metadatas.append({
                    "source": "products_db",
                    "product_id": str(p.id),
                    "product_name": p.name,
                    "category": cat_name,
                })

            count = retriever.ingest_texts(texts, source="products_db", metadatas=metadatas)
            print(f"  [+] Indexed {count} products")
        else:
            print("  [!] No active products found in database")

    await engine.dispose()

    # ── Summary ───────────────────────────────────────────────────────
    stats = retriever.get_stats()
    print("\n" + "=" * 60)
    print("Knowledge Base Index Built Successfully!")
    print("=" * 60)
    print(f"  Total vectors: {stats.get('total_vectors', 0)}")
    print(f"  Dimension:     {stats.get('dimension', 'N/A')}")
    print(f"  Sources:       {stats.get('unique_sources', 0)}")
    if "sources" in stats:
        for src, count in stats["sources"].items():
            print(f"    - {src}: {count} chunks")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(build_index())
