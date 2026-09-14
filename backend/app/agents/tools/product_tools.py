"""
app/agents/tools/product_tools.py

Tools for product search and comparison queries.

Module 10 changes:
  - search_products now returns clean structured output (no raw "Found N products matching...")
  - Added get_product_comparison() tool for side-by-side product comparison
  - Uses shared engine (no per-call engine creation)
  - Module 9 exact-product retrieval (4-phase) is preserved inside _search_products_async
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Async helpers (use shared engine) ─────────────────────────────────────────

async def _search_products_async(query: str, limit: int = 5) -> list[dict]:
    from sqlalchemy import select, or_, and_
    from app.database.shared_engine import get_shared_session
    from app.models.product import Product
    from app.agents.utils.product_query import normalize_product_query, extract_search_phrase

    clean_phrase = extract_search_phrase(query)
    normalized = normalize_product_query(query)
    tokens = normalized.split() if normalized else ([clean_phrase] if clean_phrase else [query])

    async with get_shared_session() as session:
        # Phase 1: Exact SKU match
        sku_stmt = select(Product).where(
            Product.is_active == True,  # noqa: E712
            Product.sku.ilike(f"%{clean_phrase.strip()}%")
        )
        sku_res = (await session.execute(sku_stmt)).scalars().all()
        if sku_res:
            return [_format_product_dict(p) for p in sku_res[:limit]]

        # Phase 2: Exact product name / brand phrase match
        if clean_phrase and len(clean_phrase) >= 3:
            phrase_stmt = select(Product).where(
                Product.is_active == True,  # noqa: E712
                or_(
                    Product.name.ilike(f"%{clean_phrase}%"),
                    Product.brand.ilike(f"%{clean_phrase}%")
                )
            ).order_by(Product.rating.desc()).limit(limit)
            phrase_res = (await session.execute(phrase_stmt)).scalars().all()
            if phrase_res:
                return [_format_product_dict(p) for p in phrase_res]

        # Phase 3: High-relevance multi-token AND match
        if len(tokens) >= 2:
            and_filters = [
                or_(
                    Product.name.ilike(f"%{t}%"),
                    Product.brand.ilike(f"%{t}%"),
                    Product.description.ilike(f"%{t}%")
                )
                for t in tokens if len(t) > 1
            ]
            if and_filters:
                and_stmt = select(Product).where(
                    Product.is_active == True,  # noqa: E712
                    and_(*and_filters)
                ).order_by(Product.rating.desc()).limit(limit)
                and_res = (await session.execute(and_stmt)).scalars().all()
                if and_res:
                    return [_format_product_dict(p) for p in and_res]

        # Phase 4: Scoring-based fallback (Module 9 behavior preserved)
        token_filters = [
            or_(
                Product.name.ilike(f"%{t}%"),
                Product.brand.ilike(f"%{t}%"),
                Product.description.ilike(f"%{t}%")
            )
            for t in tokens
        ]
        stmt = select(Product).where(
            Product.is_active == True,  # noqa: E712
            or_(*token_filters) if token_filters else Product.name.ilike(f"%{query}%")
        ).order_by(Product.rating.desc()).limit(limit * 2)

        candidates = (await session.execute(stmt)).scalars().all()

        scored = []
        for p in candidates:
            p_text = f"{p.name} {p.brand} {p.description}".lower()
            match_score = sum(1 for t in tokens if t.lower() in p_text)
            min_required = 1 if len(tokens) <= 2 else (len(tokens) // 2)
            if match_score >= min_required:
                scored.append((match_score, float(p.rating), p))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        results = [x[2] for x in scored[:limit]]
        return [_format_product_dict(p) for p in results]


async def _get_comparison_products_async(name_a: str, name_b: str) -> tuple[dict | None, dict | None]:
    """Fetch exactly 2 products for comparison by name."""
    from sqlalchemy import select, or_
    from app.database.shared_engine import get_shared_session
    from app.models.product import Product
    from app.agents.utils.product_query import extract_search_phrase

    async def _find_one(session, name: str) -> Any | None:
        clean = extract_search_phrase(name) or name
        result = await session.execute(
            select(Product).where(
                Product.is_active == True,  # noqa: E712
                or_(
                    Product.name.ilike(f"%{clean}%"),
                    Product.brand.ilike(f"%{clean}%")
                )
            ).order_by(Product.rating.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async with get_shared_session() as session:
        p_a = await _find_one(session, name_a)
        p_b = await _find_one(session, name_b)
        return (
            _format_product_dict(p_a) if p_a else None,
            _format_product_dict(p_b) if p_b else None,
        )


def _format_product_dict(p) -> dict:
    discount_pct = 0.0
    if p.original_price and p.original_price > p.price:
        discount_pct = round(float((p.original_price - p.price) / p.original_price * 100), 1)
    return {
        "id": str(p.id),
        "name": p.name,
        "price": float(p.price),
        "discount_percent": discount_pct,
        "rating": p.rating,
        "review_count": p.review_count,
        "stock": p.stock,
        "sku": p.sku,
        "brand": p.brand or "N/A",
        "specifications": p.specifications or {},
        "description": p.description[:300] if p.description else "",
        "category": p.category.name if p.category else None,
    }


# ── LangChain tool definitions ─────────────────────────────────────────────────

@tool
def search_products(query: str) -> str:
    """
    Search for products by name, category, or description keyword.
    Use when the customer asks to FIND, BROWSE, or GET RECOMMENDATIONS for
    multiple products — NOT for follow-up questions about a specific product.

    Args:
        query: Search keywords (e.g. "wireless headphones", "bluetooth speakers under 20000")

    Returns:
        Structured list of matching products with price, rating, and stock info.
        Output is always natural language — never exposes raw search internals.
    """
    from app.database.shared_engine import run_in_thread
    products = run_in_thread(_search_products_async(query))

    if not products:
        return f"No products found for '{query}'. Try different keywords or browse by category."

    if len(products) == 1:
        p = products[0]
        stock_status = f"In Stock ({p['stock']} units)" if p["stock"] > 0 else "Out of Stock"
        price_str = f"PKR {p['price']:,.2f}"
        if p["discount_percent"] > 0:
            discounted = p["price"] * (1 - p["discount_percent"] / 100)
            price_str = f"PKR {discounted:,.0f} (was PKR {p['price']:,.0f}, {p['discount_percent']}% off)"

        spec_lines = []
        if p.get("specifications"):
            for k, v in list(p["specifications"].items())[:5]:
                spec_lines.append(f"  • {k.replace('_', ' ').title()}: {v}")

        spec_text = ("\n\nSpecifications:\n" + "\n".join(spec_lines)) if spec_lines else ""
        desc_text = f"\n\n{p['description']}" if p.get("description") else ""

        return (
            f"PRODUCT: {p['name']}\n"
            f"Brand: {p.get('brand', 'N/A')} | SKU: {p['sku']}\n"
            f"Price: {price_str}\n"
            f"Rating: {p['rating']}/5 ({p['review_count']:,} reviews) | {stock_status}"
            f"{desc_text}"
            f"{spec_text}"
        )

    # Multiple products — structured format (response_agent synthesizes natural language)
    lines = [f"SEARCH RESULTS ({len(products)} products):\n"]
    for i, p in enumerate(products, 1):
        stock_status = "In Stock" if p["stock"] > 0 else "Out of Stock"
        price_str = f"PKR {p['price']:,.0f}"
        if p["discount_percent"] > 0:
            discounted = p["price"] * (1 - p["discount_percent"] / 100)
            price_str = f"PKR {discounted:,.0f} ({p['discount_percent']}% off)"

        lines.append(
            f"{i}. {p['name']}\n"
            f"   Brand: {p.get('brand', 'N/A')} | SKU: {p['sku']}\n"
            f"   Price: {price_str} | Rating: {p['rating']}/5 ({p['review_count']:,} reviews) | {stock_status}"
        )
    return "\n".join(lines)


@tool
def get_product_details(sku: str) -> str:
    """
    Get full details of a specific product by SKU code.
    Use when the customer asks about a specific product they already have the SKU for.

    Args:
        sku: The product SKU code (e.g. SKU-01234)

    Returns:
        Complete product details including description, price, and availability.
    """
    from app.database.shared_engine import run_in_thread

    async def _fetch():
        from sqlalchemy import select
        from app.database.shared_engine import get_shared_session
        from app.models.product import Product

        async with get_shared_session() as session:
            result = await session.execute(
                select(Product).where(Product.sku == sku.upper())
            )
            p = result.scalar_one_or_none()
            if not p:
                return {"error": f"No product found with SKU {sku}"}

            discount_pct = 0.0
            if p.original_price and p.original_price > p.price:
                discount_pct = round(float((p.original_price - p.price) / p.original_price * 100), 1)
            discounted_price = float(p.price) * (1 - discount_pct / 100)

            return {
                "id": str(p.id),
                "name": p.name,
                "sku": p.sku,
                "brand": p.brand,
                "price": float(p.price),
                "discount_percent": discount_pct,
                "discounted_price": round(discounted_price, 2),
                "rating": p.rating,
                "review_count": p.review_count,
                "stock": p.stock,
                "is_active": p.is_active,
                "description": p.description,
                "specifications": p.specifications or {},
            }

    result = run_in_thread(_fetch())

    if "error" in result:
        return f"Error: {result['error']}"

    stock_status = f"In Stock ({result['stock']} units)" if result["stock"] > 0 else "Out of Stock"
    lines = [
        f"Product: {result['name']}",
        f"SKU: {result['sku']}",
        f"Brand: {result.get('brand', 'N/A')}",
        f"Price: PKR {result['price']:,.0f}",
    ]
    if result["discount_percent"] > 0:
        lines.append(
            f"Discounted Price: PKR {result['discounted_price']:,.0f} "
            f"({result['discount_percent']}% off)"
        )
    lines += [
        f"Rating: {result['rating']}/5 ({result['review_count']:,} reviews)",
        f"Availability: {stock_status}",
        f"\nDescription: {result['description']}",
    ]
    if result.get("specifications"):
        lines.append("\nSpecifications:")
        for k, v in list(result["specifications"].items())[:8]:
            lines.append(f"  • {k.replace('_', ' ').title()}: {v}")
    return "\n".join(lines)


@tool
def get_product_comparison(product_a: str, product_b: str) -> str:
    """
    Compare two specific products side-by-side.
    Use ONLY when the customer explicitly asks to compare two named products.

    Args:
        product_a: Name or identifier of the first product
        product_b: Name or identifier of the second product

    Returns:
        Structured comparison of both products. Only includes data from the
        database — never invents specifications.
    """
    from app.database.shared_engine import run_in_thread
    pa, pb = run_in_thread(_get_comparison_products_async(product_a, product_b))

    if not pa and not pb:
        return f"Could not find '{product_a}' or '{product_b}' in the catalog. Please check the product names."
    if not pa:
        return f"Could not find '{product_a}' in the catalog. Found '{pb['name']}' for comparison only."
    if not pb:
        return f"Could not find '{product_b}' in the catalog. Found '{pa['name']}' for comparison only."

    def price_str(p):
        price = p["price"]
        disc = p["discount_percent"]
        if disc > 0:
            discounted = price * (1 - disc / 100)
            return f"PKR {discounted:,.0f} ({disc}% off)"
        return f"PKR {price:,.0f}"

    def stock_str(p):
        return f"In Stock ({p['stock']} units)" if p["stock"] > 0 else "Out of Stock"

    lines = [
        f"PRODUCT COMPARISON: {pa['name']} vs {pb['name']}",
        "",
        f"| Feature | {pa['name']} | {pb['name']} |",
        "|---|---|---|",
        f"| Brand | {pa.get('brand', 'N/A')} | {pb.get('brand', 'N/A')} |",
        f"| Price | {price_str(pa)} | {price_str(pb)} |",
        f"| Rating | {pa['rating']}/5 ({pa['review_count']:,} reviews) | {pb['rating']}/5 ({pb['review_count']:,} reviews) |",
        f"| Availability | {stock_str(pa)} | {stock_str(pb)} |",
        f"| SKU | {pa['sku']} | {pb['sku']} |",
    ]

    # Add matching spec keys
    specs_a = pa.get("specifications", {}) or {}
    specs_b = pb.get("specifications", {}) or {}
    all_spec_keys = set(list(specs_a.keys())[:6]) | set(list(specs_b.keys())[:6])
    for key in sorted(all_spec_keys)[:8]:
        val_a = specs_a.get(key, "Not available")
        val_b = specs_b.get(key, "Not available")
        lines.append(f"| {key.replace('_', ' ').title()} | {val_a} | {val_b} |")

    return "\n".join(lines)


PRODUCT_TOOLS = [search_products, get_product_details, get_product_comparison]
