"""
app/agents/nodes/context_resolver.py

Module 10 — Context Resolver Node

Resolves the "active product" for context-aware conversations.
Runs after intent_classifier and before the specialist agents.

Resolution priority:
  1. If product_id_from_detail is set (from ProductDetail page navigation)
     → Load authoritative product from PostgreSQL by UUID → set active_product
  2. If message contains an explicit product name/entity (from intent classifier)
     → Resolve product from DB by name → update active_product
  3. If message contains pronoun/reference ("it", "this", "the product")
     AND active_product is already in state → keep active_product unchanged
  4. If message mentions a new product name (overrides pronoun)
     → Update active_product to the new product
  5. If intent is GREETING or GENERAL_CONVERSATION
     → Do NOT clear active_product (preserve context across greetings)

The active_product dict contains:
    {id, name, sku, brand, price, discount_percent, rating, review_count,
     stock, description, specifications, category}
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.agents.state import CommerceFlowState
from app.agents.utils.product_query import detect_pronoun_reference, extract_search_phrase
from app.core.logging import get_logger

logger = get_logger(__name__)

# Intents that should NOT trigger product resolution (they don't need a product)
_NON_PRODUCT_INTENTS = {
    "GREETING", "GENERAL_CONVERSATION",
    "ORDER_STATUS", "ORDER_HISTORY",
    "CART_HELP", "SHIPPING_QUESTION", "PAYMENT_QUESTION",
    "RETURN_REFUND_QUESTION", "SUPPORT_REQUEST", "UNKNOWN",
}


def context_resolver_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    Context Resolver: populate active_product based on message and state.

    Called after intent_classifier and before specialist agents.
    """
    resolved_intent = state.get("resolved_intent", "UNKNOWN")
    logger.info(f"Context resolver — intent={resolved_intent}, conversation={state['conversation_id']}")

    # For non-product intents, skip resolution (but preserve existing active_product)
    if resolved_intent in _NON_PRODUCT_INTENTS:
        logger.debug(f"Skipping product resolution for intent {resolved_intent}")
        return state

    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    message_text = last_human.content if last_human else ""

    updates = {}

    # ── Priority 1: ProductDetail page product_id ────────────────────────────
    product_id = state.get("product_id_from_detail")
    if product_id:
        product = _load_product_by_id(product_id)
        if product:
            logger.info(f"Context: loaded product from detail page: {product['name']}")
            updates["active_product"] = product
            updates["product_context_source"] = "detail_page"
            # Clear product_id_from_detail so it's not reloaded on every turn
            # But keep the active_product across turns
            updates["product_id_from_detail"] = None
            return {**state, **updates}

    # ── Priority 2: Comparison — resolve both entities ───────────────────────
    if resolved_intent == "PRODUCT_COMPARISON":
        # Extract product names from the message for comparison
        # The LLM may have stored them as _product_entity_a / _product_entity_b
        entity_a = state.get("_product_entity_a")
        entity_b = state.get("_product_entity_b")
        if entity_a or entity_b:
            updates["_product_entity_a"] = entity_a
            updates["_product_entity_b"] = entity_b
        return {**state, **updates}

    # ── Priority 3: Pronoun reference → keep existing active_product ─────────
    if detect_pronoun_reference(message_text) and state.get("active_product"):
        logger.info(f"Context: pronoun reference, keeping active_product={state['active_product']['name']}")
        # No change needed — active_product already set
        return state

    # ── Priority 4: Explicit product name in message → resolve ───────────────
    # Extract a clean product name from the message
    clean_name = extract_search_phrase(message_text)
    if clean_name and len(clean_name.split()) >= 2:
        product = _search_product_by_name(clean_name)
        if product:
            logger.info(f"Context: resolved product from message: {product['name']}")
            updates["active_product"] = product
            updates["product_context_source"] = "conversation"
            return {**state, **updates}

    # ── Priority 5: Intent needs a product but none found ────────────────────
    # For PRICE/STOCK/RATING/ATTRIBUTE queries with no active_product and no pronoun,
    # we leave active_product as-is (None or previous) — the agent will ask for clarification
    logger.debug("Context resolver: no product change needed")
    return state


def _load_product_by_id(product_id: str) -> dict | None:
    """Load a product from the DB by UUID. Returns product dict or None."""
    from app.database.shared_engine import run_in_thread

    async def _fetch():
        from sqlalchemy import select
        from app.database.shared_engine import get_shared_session
        from app.models.product import Product
        import uuid

        try:
            pid = uuid.UUID(product_id)
        except (ValueError, AttributeError):
            return None

        async with get_shared_session() as session:
            result = await session.execute(
                select(Product).where(Product.id == pid, Product.is_active == True)  # noqa: E712
            )
            p = result.scalar_one_or_none()
            return _product_to_dict(p) if p else None

    try:
        return run_in_thread(_fetch())
    except Exception as e:
        logger.error(f"Context resolver load by ID failed: {e}", exc_info=True)
        return None


def _search_product_by_name(name: str) -> dict | None:
    """Search for the best matching product by name. Returns product dict or None."""
    from app.database.shared_engine import run_in_thread

    async def _fetch():
        from sqlalchemy import select, or_
        from app.database.shared_engine import get_shared_session
        from app.models.product import Product

        async with get_shared_session() as session:
            # Try exact name match first
            result = await session.execute(
                select(Product).where(
                    Product.is_active == True,  # noqa: E712
                    Product.name.ilike(f"%{name}%")
                ).order_by(Product.rating.desc()).limit(1)
            )
            p = result.scalar_one_or_none()
            if p:
                return _product_to_dict(p)

            # Try brand match
            result = await session.execute(
                select(Product).where(
                    Product.is_active == True,  # noqa: E712
                    or_(
                        Product.brand.ilike(f"%{name}%"),
                        Product.description.ilike(f"%{name}%")
                    )
                ).order_by(Product.rating.desc()).limit(1)
            )
            p = result.scalar_one_or_none()
            return _product_to_dict(p) if p else None

    try:
        return run_in_thread(_fetch())
    except Exception as e:
        logger.error(f"Context resolver name search failed: {e}", exc_info=True)
        return None


def _product_to_dict(p) -> dict:
    """Convert a Product ORM object to a clean dict for state storage."""
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
    }
