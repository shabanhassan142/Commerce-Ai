"""
app/agents/tools/product_detail_tool.py

Module 10 — Product Detail Tool

Tools for fetching a single product's full data or a specific attribute
directly from PostgreSQL using the shared engine.

Deliberately does NOT use search — it fetches by exact ID or resolves by
the authoritative active_product already in state.

Never halluccinates. Returns None / "not_available" for missing fields.
"""
from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


def get_product_by_id(product_id: str) -> dict | None:
    """
    Fetch full product details from PostgreSQL by UUID.
    Returns a complete product dict or None if not found.

    Uses the shared engine singleton (no per-call engine creation).
    """
    from app.database.shared_engine import run_in_thread

    async def _fetch():
        import uuid as _uuid
        from sqlalchemy import select
        from app.database.shared_engine import get_shared_session
        from app.models.product import Product

        try:
            pid = _uuid.UUID(product_id)
        except (ValueError, AttributeError):
            return None

        async with get_shared_session() as session:
            result = await session.execute(
                select(Product).where(Product.id == pid)
            )
            p = result.scalar_one_or_none()
            return _product_to_full_dict(p) if p else None

    try:
        return run_in_thread(_fetch())
    except Exception as e:
        logger.error(f"get_product_by_id failed: {e}", exc_info=True)
        return None


def get_product_attribute(product: dict, attribute: str) -> str:
    """
    Retrieve a specific attribute from a product dict.

    Returns a human-readable string value, or a clear "not available" message
    if the attribute doesn't exist in the catalog. NEVER halluccinates.

    Args:
        product: Product dict (from active_product state or get_product_by_id)
        attribute: The attribute being asked about (e.g. "price", "warranty",
                   "country_of_origin", "weight", "usb_c", "battery")

    Returns:
        A descriptive string suitable for the response agent.
    """
    name = product.get("name", "This product")
    attr_lower = attribute.lower().strip()

    # ── Direct fields ─────────────────────────────────────────────────────────
    if attr_lower in {"price", "cost", "how much", "rate"}:
        price = product.get("price", 0)
        disc = product.get("discount_percent", 0)
        if disc and disc > 0:
            discounted = price * (1 - disc / 100)
            return (f"PKR {price:,.0f} (original), discounted to "
                    f"PKR {discounted:,.0f} ({disc}% off)")
        return f"PKR {price:,.0f}"

    if attr_lower in {"stock", "availability", "available", "in stock", "units"}:
        stock = product.get("stock", 0)
        if stock > 0:
            return f"Yes, {name} is in stock ({stock} units available)"
        return f"No, {name} is currently out of stock"

    if attr_lower in {"rating", "stars", "score"}:
        rating = product.get("rating", 0)
        reviews = product.get("review_count", 0)
        return f"{rating}/5 stars based on {reviews:,} reviews"

    if attr_lower in {"reviews", "review count", "review_count", "how many reviews"}:
        reviews = product.get("review_count", 0)
        return f"{reviews:,} customer reviews"

    if attr_lower in {"brand", "manufacturer", "made by", "who makes"}:
        brand = product.get("brand")
        if brand and brand.lower() not in {"unknown", "n/a", ""}:
            return brand
        return f"Brand information is not available for {name}"

    if attr_lower in {"sku", "code", "product code", "item number"}:
        return product.get("sku", "N/A")

    if attr_lower in {"category", "type", "kind"}:
        cat = product.get("category")
        return cat if cat else f"Category information is not available for {name}"

    if attr_lower in {"description", "about", "overview"}:
        desc = product.get("description", "")
        return desc[:500] if desc else f"No description available for {name}"

    if attr_lower in {"discount", "sale", "offer", "percent off", "discount_percent"}:
        disc = product.get("discount_percent", 0)
        if disc and disc > 0:
            return f"{disc}% discount applied"
        return f"{name} is not currently on sale"

    # ── Specifications lookup ─────────────────────────────────────────────────
    specs = product.get("specifications", {}) or {}

    # Map common attribute questions to spec keys
    spec_key_map = {
        "country": ["country_of_origin", "country of origin", "made in", "origin"],
        "origin": ["country_of_origin", "country of origin", "made in", "origin"],
        "made": ["country_of_origin", "made in", "origin"],
        "warranty": ["warranty", "warranty_period", "guarantee"],
        "battery": ["battery", "battery_life", "battery_capacity"],
        "weight": ["weight", "product_weight"],
        "color": ["color", "colour", "colors", "colours"],
        "usb": ["connector", "port", "usb", "usb_type", "usb-c", "charging"],
        "usb-c": ["connector", "port", "usb_type", "usb-c"],
        "bluetooth": ["bluetooth", "bluetooth_version", "wireless"],
        "waterproof": ["waterproof", "water_resistant", "ipx", "ip_rating", "ip rating"],
        "range": ["range", "wireless_range", "coverage"],
        "driver": ["driver", "driver_size"],
        "noise": ["noise_cancellation", "anc", "active noise cancellation"],
        "frequency": ["frequency_response", "frequency response"],
        "impedance": ["impedance"],
        "connectivity": ["connectivity", "connection"],
        "material": ["material", "fabric", "build"],
        "power": ["power", "wattage", "power output"],
        "resolution": ["resolution", "display_resolution"],
        "screen": ["screen", "display", "screen_size"],
        "processor": ["processor", "cpu", "chip"],
        "memory": ["memory", "ram"],
        "storage": ["storage", "ssd", "capacity"],
    }

    # Find matching spec keys
    for key_pattern, spec_keys in spec_key_map.items():
        if key_pattern in attr_lower:
            for sk in spec_keys:
                # Try exact key match
                if sk in specs:
                    return str(specs[sk])
                # Try case-insensitive key match
                for spec_key, spec_val in specs.items():
                    if sk.lower().replace("_", " ") in spec_key.lower().replace("_", " "):
                        return str(spec_val)

    # Try searching all spec keys for the attribute word
    for spec_key, spec_val in specs.items():
        if attr_lower.replace("_", " ") in spec_key.lower().replace("_", " "):
            return str(spec_val)

    # Nothing found — honest response, no hallucination
    return f"I don't have {attribute} information for {name} in the CommerceFlow catalog."


def format_product_for_response(product: dict, intent: str = "PRODUCT_INFORMATION") -> str:
    """
    Format a product dict into a readable string for the response agent.

    Tailored to the intent — PRICE_QUERY returns just price, etc.
    """
    name = product.get("name", "Product")
    price = product.get("price", 0)
    disc = product.get("discount_percent", 0)
    rating = product.get("rating", 0)
    reviews = product.get("review_count", 0)
    stock = product.get("stock", 0)
    brand = product.get("brand", "N/A")
    sku = product.get("sku", "N/A")
    desc = product.get("description", "")
    specs = product.get("specifications", {}) or {}

    price_str = f"PKR {price:,.0f}"
    if disc and disc > 0:
        discounted = price * (1 - disc / 100)
        price_str = f"PKR {discounted:,.0f} (was PKR {price:,.0f}, {disc}% off)"

    stock_str = f"In Stock ({stock} units)" if stock > 0 else "Out of Stock"

    if intent == "PRICE_QUERY":
        return f"**{name}**\nPrice: {price_str}"

    if intent == "STOCK_QUERY":
        return f"**{name}**\nAvailability: {stock_str}"

    if intent == "RATING_QUERY":
        return f"**{name}**\nRating: {rating}/5 stars ({reviews:,} reviews)"

    # Full product info (PRODUCT_INFORMATION, PRODUCT_EXACT_LOOKUP, ATTRIBUTE_QUERY)
    lines = [
        f"**{name}**",
        f"Brand: {brand} | SKU: {sku}",
        f"Price: {price_str}",
        f"Rating: {rating}/5 ({reviews:,} reviews) | {stock_str}",
    ]
    if desc:
        lines.append(f"\n{desc[:400]}")
    if specs:
        lines.append("\nSpecifications:")
        for k, v in list(specs.items())[:8]:
            lines.append(f"  • {k.replace('_', ' ').title()}: {v}")
    return "\n".join(lines)


def _product_to_full_dict(p) -> dict:
    """Convert a Product ORM object to a clean dict."""
    discount_pct = 0.0
    if p.original_price and p.original_price > p.price:
        discount_pct = round(float((p.original_price - p.price) / p.original_price * 100), 1)

    category_name = None
    try:
        if p.category:
            category_name = p.category.name
    except Exception:
        pass

    return {
        "id": str(p.id),
        "name": p.name,
        "sku": p.sku,
        "brand": p.brand or "Unknown",
        "price": float(p.price),
        "discount_percent": discount_pct,
        "rating": p.rating,
        "review_count": p.review_count,
        "stock": p.stock,
        "description": p.description or "",
        "specifications": p.specifications or {},
        "category": category_name,
        "is_active": p.is_active,
    }
