"""
backend/tests/test_module9_ai_and_images.py

Module 9 Automated Tests:
1. Exact product query test (JBL Charge 5 priority match, 0 unrelated items).
2. SKU lookup test.
3. Unknown product handling.
4. Image HTTP health audit test (verifies product image URLs in database return 200 OK).
5. Chat service compatibility & contract test.
"""

import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import AsyncSessionLocal
from app.models.product import Product
from app.agents.tools.product_tools import _search_products_async, _get_product_by_sku_async, search_products
from app.agents.utils.product_query import extract_search_phrase, normalize_product_query


@pytest.mark.asyncio
async def test_exact_product_query_prioritization():
    """Verify exact product inquiry returns ONLY the exact product without generic multi-item noise."""
    query = "Tell me more about: JBL Charge 5 Portable Bluetooth Speaker"
    
    # 1. Check phrase extraction
    phrase = extract_search_phrase(query)
    assert "JBL Charge 5" in phrase

    # 2. Execute product search
    results = await _search_products_async(query)
    assert len(results) == 1
    item = results[0]
    assert "JBL" in item["name"] or "JBL" in item["brand"]
    assert item["sku"] == "AUD-SPK-011"
    assert float(item["price"]) > 0


@pytest.mark.asyncio
async def test_sku_lookup_tool():
    """Verify SKU lookup tool returns complete product details."""
    result = await _get_product_by_sku_async("ELEC-MBP-001")
    assert "error" not in result
    assert result["name"] == "Apple MacBook Pro 14\" M3 Chip"
    assert result["price"] == 1799.0
    assert result["stock"] > 0


@pytest.mark.asyncio
async def test_unknown_product_search():
    """Verify search for non-existent product handles gracefully without crashing."""
    results = await _search_products_async("NonExistentSuperWidget999")
    assert isinstance(results, list)
    assert len(results) == 0

    tool_output = search_products.invoke({"query": "NonExistentSuperWidget999"})
    assert "No products found" in tool_output


@pytest.mark.asyncio
async def test_image_urls_http_health():
    """Audit product image URLs in PostgreSQL to ensure primary image URLs return HTTP 200 OK."""
    async with AsyncSessionLocal() as session:
        stmt = select(Product).options(selectinload(Product.images)).limit(10)
        products = (await session.execute(stmt)).scalars().all()
        assert len(products) > 0, "No products found in database"

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for p in products:
                assert p.image_url is not None and len(p.image_url) > 0
                resp = await client.get(p.image_url)
                assert resp.status_code == 200, f"Primary image URL broken for product '{p.name}': {p.image_url}"


@pytest.mark.asyncio
async def test_search_phrase_extraction_utility():
    """Test extract_search_phrase utility across conversational patterns."""
    assert extract_search_phrase("Tell me more about: Dyson Supersonic Hair Dryer") == "Dyson Supersonic Hair Dryer"
    assert extract_search_phrase("What is the price of Apple MacBook Pro 14?") == "Apple MacBook Pro 14"
    assert extract_search_phrase("Show me details on Sony WF-1000XM5") == "Sony WF-1000XM5"
