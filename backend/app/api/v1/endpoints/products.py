"""
app/api/v1/endpoints/products.py

Product listing and detail endpoints.
Read-only — products are managed via admin panel or seed data.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.category import Category
from app.models.product import Product, ProductImage
from app.schemas.product import CategoryResponse, ProductListItem, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=dict,
    summary="List products with pagination and filtering",
)
async def list_products(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category_slug: str | None = Query(None, description="Filter by category slug"),
    search: str | None = Query(None, description="Search by product name"),
    min_price: float | None = Query(None, ge=0, description="Minimum price"),
    max_price: float | None = Query(None, ge=0, description="Maximum price"),
    in_stock: bool | None = Query(None, description="Only show in-stock products"),
):
    """
    List marketplace products with pagination, category filtering,
    and search. Returns products with their category, seller, and images.
    """
    query = select(Product).where(Product.is_active == True)  # noqa: E712

    # Apply filters
    if category_slug:
        query = query.join(Category).where(Category.slug == category_slug)

    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    if min_price is not None:
        query = query.where(Product.price >= min_price)

    if max_price is not None:
        query = query.where(Product.price <= max_price)

    if in_stock is True:
        query = query.where(Product.stock > 0)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate — eagerly load images
    offset = (page - 1) * per_page
    query = (
        query
        .offset(offset)
        .limit(per_page)
        .order_by(Product.created_at.desc())
        .options(selectinload(Product.images))
    )

    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "items": [ProductListItem.from_orm_product(p) for p in products],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List all product categories",
)
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Return all product categories."""
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details with full image gallery",
)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return full details for a single product including image gallery."""
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductResponse.from_orm_product(product)
