"""
app/agents/nodes/product_agent.py

Module 10 — Product Agent (redesigned)

Dispatches to one of three specialized handlers based on resolved_intent:

1. detail_handler  — PRODUCT_INFORMATION, PRODUCT_EXACT_LOOKUP,
                     PRICE_QUERY, STOCK_QUERY, RATING_QUERY, ATTRIBUTE_QUERY
   - Uses active_product from state (set by context_resolver)
   - NEVER calls search_products
   - Returns attribute-specific data from product dict
   - If no active_product → asks clarifying question

2. search_handler  — PRODUCT_SEARCH, PRODUCT_RECOMMENDATION
   - Calls search_products with extracted query
   - Saves results to product_search_results state
   - Supports price/category filters from context

3. comparison_handler — PRODUCT_COMPARISON
   - Calls get_product_comparison with exactly 2 product names
   - Returns structured comparison table
   - Never returns unrelated products

CRITICAL: No unconditional search fallback. If intent is unclear, the
response_agent will generate a clarification response.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import CommerceFlowState
from app.agents.tools.product_detail_tool import (
    format_product_for_response,
    get_product_attribute,
    get_product_by_id,
)
from app.agents.tools.product_tools import PRODUCT_TOOLS
from app.agents.utils.product_query import extract_search_phrase, normalize_product_query
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Intents handled by the detail handler (single product, no search)
_DETAIL_INTENTS = {
    "PRODUCT_INFORMATION", "PRODUCT_EXACT_LOOKUP",
    "PRICE_QUERY", "STOCK_QUERY", "RATING_QUERY", "ATTRIBUTE_QUERY",
}

# Map intent → attribute name for direct attribute queries
_INTENT_TO_ATTRIBUTE = {
    "PRICE_QUERY": "price",
    "STOCK_QUERY": "stock",
    "RATING_QUERY": "rating",
}

_PRODUCT_AGENT_SYSTEM = """You are the Product Specialist for CommerceFlow AI.

Your role: Help customers with product information, search, and comparisons.

Tools available:
- search_products: Search catalog by keyword/category (ONLY for broad searches)
- get_product_details: Get full details by SKU code
- get_product_comparison: Compare exactly two named products

IMPORTANT RULES:
1. NEVER call search_products for attribute/price/stock/rating questions
2. NEVER return unrelated products for specific product questions
3. NEVER hallucinate specifications not present in tool results
4. For comparison requests, call get_product_comparison with BOTH product names
5. For broad searches, call search_products with the category/keyword
"""


def product_agent_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    Product Agent: dispatch to detail, search, or comparison handler.
    """
    resolved_intent = state.get("resolved_intent", "UNKNOWN")
    logger.info(f"Product agent — intent={resolved_intent}, user={state['user_id']}")

    if resolved_intent in _DETAIL_INTENTS:
        return _detail_handler(state)
    elif resolved_intent == "PRODUCT_COMPARISON":
        return _comparison_handler(state)
    else:
        # PRODUCT_SEARCH, PRODUCT_RECOMMENDATION, or fallback
        return _search_handler(state)


# ── Handler 1: Detail (single product, attribute query) ───────────────────────

def _detail_handler(state: CommerceFlowState) -> CommerceFlowState:
    """Handle questions about a specific product's details/attributes."""
    resolved_intent = state.get("resolved_intent", "PRODUCT_INFORMATION")
    active_product = state.get("active_product")

    messages = state.get("messages", [])
    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    message_text = last_human.content if last_human else ""

    tool_results = []

    # No active product — need clarification
    if not active_product:
        logger.info("Detail handler: no active_product, requesting clarification")
        clarification = "Which product are you asking about? Please mention the product name."
        tool_results.append({
            "tool": "clarification_needed",
            "input": {"message": message_text},
            "output": clarification,
        })
        return {
            **state,
            "tool_results": tool_results,
            "selected_agent": "product_agent",
        }

    product_name = active_product.get("name", "the product")
    logger.info(f"Detail handler: answering about '{product_name}' (intent={resolved_intent})")

    # For specific attribute intents, extract the attribute from the message
    if resolved_intent in _INTENT_TO_ATTRIBUTE:
        attribute = _INTENT_TO_ATTRIBUTE[resolved_intent]
        attr_value = get_product_attribute(active_product, attribute)
        formatted = format_product_for_response(active_product, resolved_intent)
        tool_results.append({
            "tool": "product_detail",
            "input": {"product": product_name, "attribute": attribute},
            "output": formatted,
            "attribute_value": attr_value,
        })
    elif resolved_intent == "ATTRIBUTE_QUERY":
        # Extract the specific attribute being asked about from the message
        attribute = _extract_attribute_from_message(message_text)
        attr_value = get_product_attribute(active_product, attribute)
        tool_results.append({
            "tool": "product_attribute",
            "input": {"product": product_name, "attribute": attribute},
            "output": f"{product_name} — {attribute.replace('_', ' ').title()}: {attr_value}",
        })
    else:
        # Full product information
        formatted = format_product_for_response(active_product, resolved_intent)
        tool_results.append({
            "tool": "product_detail",
            "input": {"product": product_name},
            "output": formatted,
        })

    # Update active_product in state (it's now confirmed as the context product)
    return {
        **state,
        "tool_results": tool_results,
        "active_product": active_product,
        "product_context_source": state.get("product_context_source", "conversation"),
        "selected_agent": "product_agent",
    }


def _extract_attribute_from_message(message: str) -> str:
    """Extract the specific product attribute being queried from a message."""
    msg = message.lower()

    attribute_keywords = {
        "price": ["price", "cost", "how much", "pkr", "rupees"],
        "stock": ["stock", "available", "availability", "in stock", "units"],
        "rating": ["rating", "review", "stars", "score"],
        "country_of_origin": ["made", "manufactured", "origin", "country", "where"],
        "warranty": ["warranty", "guarantee", "guarantee period"],
        "battery": ["battery", "battery life", "battery capacity"],
        "weight": ["weight", "how heavy", "how light"],
        "color": ["color", "colour", "colors"],
        "connectivity": ["connect", "bluetooth", "wireless", "usb"],
        "material": ["material", "fabric", "build", "made of"],
        "waterproof": ["waterproof", "water resistant", "ipx", "ip rating"],
        "specifications": ["spec", "specification", "feature", "details"],
        "brand": ["brand", "manufacturer", "who makes"],
        "description": ["describe", "description", "tell me", "about", "overview"],
    }

    for attr, keywords in attribute_keywords.items():
        if any(kw in msg for kw in keywords):
            return attr

    return "specifications"  # fallback


# ── Handler 2: Search (multi-product) ─────────────────────────────────────────

def _search_handler(state: CommerceFlowState) -> CommerceFlowState:
    """Handle product search and recommendation requests."""
    messages = state.get("messages", [])
    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    if not last_human:
        return {**state, "tool_results": [], "selected_agent": "product_agent"}

    tool_results = []
    message_text = last_human.content

    # No LLM — use direct search
    if not settings.OPENROUTER_API_KEY:
        query = normalize_product_query(message_text)
        if not query or len(query.strip()) < 2:
            query = extract_search_phrase(message_text) or message_text
        output = PRODUCT_TOOLS[0].invoke({"query": query})
        tool_results.append({
            "tool": "search_products",
            "input": {"query": query},
            "output": output,
        })
        return {**state, "tool_results": tool_results, "selected_agent": "product_agent"}

    try:
        api_key = settings.OPENROUTER_API_KEY
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            openai_api_key=api_key,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            default_headers={"HTTP-Referer": "https://commerceflow.ai", "X-Title": "CommerceFlow AI"},
        ).bind_tools([PRODUCT_TOOLS[0]])  # Only search_products for search handler

        response = llm.invoke([
            SystemMessage(content=_PRODUCT_AGENT_SYSTEM),
            HumanMessage(content=message_text),
        ])

        tool_map = {t.name: t for t in PRODUCT_TOOLS}
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_func = tool_map.get(tc["name"])
                if tool_func:
                    args = dict(tc.get("args", {}))
                    # Normalize search query
                    if tc["name"] == "search_products" and args.get("query"):
                        raw_q = str(args["query"])
                        clean = extract_search_phrase(raw_q) or raw_q
                        args["query"] = normalize_product_query(clean) or clean
                    output = tool_func.invoke(args)
                    tool_results.append({"tool": tc["name"], "input": args, "output": output})

        # If LLM didn't call any tools, extract query and search directly
        if not tool_results:
            query = normalize_product_query(message_text)
            if not query or len(query.strip()) < 2:
                query = extract_search_phrase(message_text) or message_text
            if query:
                output = PRODUCT_TOOLS[0].invoke({"query": query})
                tool_results.append({"tool": "search_products", "input": {"query": query}, "output": output})

    except Exception as e:
        logger.error(f"Search handler LLM failed: {e}", exc_info=True)
        query = normalize_product_query(message_text)
        output = PRODUCT_TOOLS[0].invoke({"query": query or message_text})
        tool_results.append({"tool": "search_products", "input": {"query": query}, "output": output})

    return {**state, "tool_results": tool_results, "selected_agent": "product_agent"}


# ── Handler 3: Comparison ──────────────────────────────────────────────────────

def _comparison_handler(state: CommerceFlowState) -> CommerceFlowState:
    """Handle product comparison requests for exactly 2 products."""
    messages = state.get("messages", [])
    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    if not last_human:
        return {**state, "tool_results": [], "selected_agent": "product_agent"}

    message_text = last_human.content
    tool_results = []

    # Try to extract product names from state (set by intent_classifier)
    entity_a = state.get("_product_entity_a")
    entity_b = state.get("_product_entity_b")

    # If not in state, parse from message
    if not entity_a or not entity_b:
        entity_a, entity_b = _extract_comparison_entities(message_text)

    if entity_a and entity_b:
        output = PRODUCT_TOOLS[2].invoke({"product_a": entity_a, "product_b": entity_b})
        tool_results.append({
            "tool": "get_product_comparison",
            "input": {"product_a": entity_a, "product_b": entity_b},
            "output": output,
        })
    else:
        tool_results.append({
            "tool": "clarification_needed",
            "input": {"message": message_text},
            "output": "Please specify the two products you'd like to compare. For example: 'Compare JBL Charge 5 and Sony WH-1000XM5'",
        })

    return {**state, "tool_results": tool_results, "selected_agent": "product_agent"}


def _extract_comparison_entities(message: str) -> tuple[str | None, str | None]:
    """Extract two product names from a comparison message."""
    import re

    # "Compare X and Y" / "X vs Y" / "X versus Y" / "difference between X and Y"
    patterns = [
        r"compare\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)[\?\.]?$",
        r"(.+?)\s+vs\.?\s+(.+?)[\?\.]?$",
        r"(.+?)\s+versus\s+(.+?)[\?\.]?$",
        r"between\s+(.+?)\s+and\s+(.+?)[\?\.]?$",
        r"(.+?)\s+and\s+(.+?)\s+(?:comparison|compare|difference)[\?\.]?$",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    return None, None
