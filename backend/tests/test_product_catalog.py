"""
tests/test_product_catalog.py

Regression test suite for product catalog data quality and image integrity.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import AsyncSessionLocal, engine
from app.models.product import Product, ProductImage


@pytest.mark.asyncio
async def test_product_catalog_integrity():
    """Verify database product catalog data quality directly against PostgreSQL."""
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).options(selectinload(Product.images))
        )
        products = result.scalars().all()

        assert len(products) == 30, f"Expected 30 curated products, found {len(products)}"

        for product in products:
            assert product.name, "Product name cannot be empty"
            assert product.price > 0, f"Product {product.name} price must be > 0"
            assert product.stock >= 0, f"Product {product.name} stock must be >= 0"
            assert product.rating >= 0 and product.rating <= 5, f"Invalid rating for {product.name}"
            assert product.review_count >= 0

            # Original price & discount check
            if product.original_price is not None:
                assert product.original_price >= product.price, (
                    f"Original price ({product.original_price}) must be >= price ({product.price}) for {product.name}"
                )
                expected_discount = round(
                    float((product.original_price - product.price) / product.original_price * 100), 1
                )
                assert product.discount_percent == expected_discount, (
                    f"Discount percent mismatch: expected {expected_discount}, got {product.discount_percent}"
                )

            # Image gallery check
            assert len(product.images) >= 2, f"Product {product.name} should have at least 2 images"
            primary_images = [img for img in product.images if img.is_primary]
            assert len(primary_images) >= 1, f"Product {product.name} must have a primary image"

            for img in product.images:
                assert img.image_url.startswith("https://images.unsplash.com/"), f"Invalid image URL: {img.image_url}"
                assert img.product_id == product.id


@pytest.mark.asyncio
async def test_products_api_returns_gallery():
    """Verify /api/v1/products API returns images list, brand, and correct schema over HTTP."""
    async with AsyncClient(base_url="http://127.0.0.1:8000") as client:
        response = await client.get("/api/v1/products?per_page=5")
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) == 5

        for item in data["items"]:
            assert "images" in item
            assert len(item["images"]) >= 2
            assert "brand" in item
            assert "discount_percent" in item
