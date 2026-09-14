"""
app/agents/nodes/intent_classifier.py

Module 10 — Intent Classifier Node

Classifies user messages into a fine-grained 19-intent taxonomy BEFORE
any product retrieval or tool execution.

Design:
  1. Rule-based fast path handles the most common unambiguous cases
     WITHOUT an LLM call (GREETING, pure pronoun follow-ups, clear
     comparison patterns, clear order number references).
  2. LLM path handles ambiguous messages using a structured JSON prompt.
  3. Result is stored in state["resolved_intent"] and entities extracted
     into state for use by context_resolver and product_agent.

Intents:
    GREETING              — "hello", "hi", "hey", "good morning"
    GENERAL_CONVERSATION  — "what can you do?", "thanks", "that's helpful"
    PRODUCT_INFORMATION   — "Tell me about JBL Charge 5"
    PRODUCT_EXACT_LOOKUP  — from ProductDetail button / "get details of"
    PRICE_QUERY           — "What's the price?" / "How much is it?"
    STOCK_QUERY           — "Is it in stock?" / "Is JBL Charge 5 available?"
    RATING_QUERY          — "What's the rating?" / "How many reviews?"
    ATTRIBUTE_QUERY       — "Where is it made?" / "What's the warranty?"
    PRODUCT_SEARCH        — "Show me Bluetooth speakers under PKR 20,000"
    PRODUCT_RECOMMENDATION — "Recommend a good speaker for travel"
    PRODUCT_COMPARISON    — "Compare JBL Charge 5 and Sony WH-1000XM5"
    ORDER_STATUS          — "Where is my order CF-20260801-001?"
    ORDER_HISTORY         — "What are my recent orders?"
    CART_HELP             — "What's in my cart?"
    SHIPPING_QUESTION     — "How much is shipping?" / "Free shipping?"
    PAYMENT_QUESTION      — "How does payment work?"
    RETURN_REFUND_QUESTION — "Can I return this?" / "What is your refund policy?"
    SUPPORT_REQUEST       — "I need human help" / "escalate"
    UNKNOWN               — catch-all
"""
from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import CommerceFlowState
from app.agents.utils.product_query import detect_pronoun_reference
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── All valid intents ──────────────────────────────────────────────────────────
VALID_INTENTS = {
    "GREETING", "GENERAL_CONVERSATION",
    "PRODUCT_INFORMATION", "PRODUCT_EXACT_LOOKUP",
    "PRICE_QUERY", "STOCK_QUERY", "RATING_QUERY", "ATTRIBUTE_QUERY",
    "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON",
    "ORDER_STATUS", "ORDER_HISTORY",
    "CART_HELP", "SHIPPING_QUESTION", "PAYMENT_QUESTION",
    "RETURN_REFUND_QUESTION", "SUPPORT_REQUEST", "UNKNOWN",
}

# ── Regex helpers ──────────────────────────────────────────────────────────────
_ORDER_NUM_RE = re.compile(r"\bCF-\d{8}-\d+\b", re.IGNORECASE)
_COMPARE_RE = re.compile(
    r"\b(?:compare|comparison|vs\.?|versus|difference between)\b", re.IGNORECASE
)
_PRICE_RE = re.compile(
    r"\b(?:price|cost|how much|pkr|rupees?|dollars?|rate|fee|charge|cheap(?:er)?)\b",
    re.IGNORECASE,
)
_STOCK_RE = re.compile(
    r"\b(?:in stock|out of stock|available|availability|units?|inventory|left)\b",
    re.IGNORECASE,
)
_RATING_RE = re.compile(
    r"\b(?:rating|rated|reviews?|stars?|score|how good|quality)\b", re.IGNORECASE
)
_ATTR_RE = re.compile(
    r"\b(?:made|manufactured|origin|country|warranty|guarantee|usb|port|battery|weight|"
    r"dimension|size|color|colour|material|fabric|connector|feature|spec|specification|"
    r"compatible|compatibility|water\s*proof|dust\s*proof|range|power)\b",
    re.IGNORECASE,
)
_GREETING_RE = re.compile(
    r"^(?:hi+|hello+|hey+|good\s+(?:morning|afternoon|evening|day)|howdy|sup|greetings?)"
    r"(?:[\s,!.]*(?:there|everyone|friend|guys|all))?[\s!.]*$",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(
    r"^(?:thanks?(?:\s+you)?|thank\s+you|thx|ty|cheers|great|nice|awesome|perfect|ok|okay|got\s+it|i\s+see|cool|makes?\s+sense)[\s!.]*$",
    re.IGNORECASE,
)
_CART_RE = re.compile(
    r"\b(?:cart|basket|bag|added|add to cart|remove from cart|checkout)\b", re.IGNORECASE
)
_SHIPPING_RE = re.compile(
    r"\b(?:shipping|delivery|ship|deliver|dispatch|courier|free shipping|express)\b",
    re.IGNORECASE,
)
_PAYMENT_RE = re.compile(
    r"\b(?:payment|pay|credit card|debit card|bank transfer|wallet|cod|cash on delivery|"
    r"easypaisa|jazzcash|stripe|checkout|billing)\b",
    re.IGNORECASE,
)
_RETURN_RE = re.compile(
    r"\b(?:return|refund|exchange|replace|damaged|broken|wrong item|cancel|policy|"
    r"money back|warranty claim)\b",
    re.IGNORECASE,
)
_ESCALATE_RE = re.compile(
    r"\b(?:human|agent|manager|supervisor|escalate|complaint|speak to|talk to|live chat|"
    r"frustrated|angry|urgent|not resolved)\b",
    re.IGNORECASE,
)
_ORDER_RE = re.compile(
    r"\b(?:my order|orders?|tracking|track my|where is my|shipped|delivered|delivery status|"
    r"order history|recent orders?|order status|order number)\b",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"\b(?:show me|find|search|list|browse|look for|looking for|display|any|all|"
    r"under|below|above|cheap|budget|affordable|best|top|recommend(?:ation)?s?|"
    r"suggest(?:ion)?s?)\b",
    re.IGNORECASE,
)
_INFO_RE = re.compile(
    r"\b(?:tell me about|what is|describe|details?|about|info|information|more about|"
    r"explain|overview)\b",
    re.IGNORECASE,
)

# LLM PROMPT for ambiguous cases
_CLASSIFIER_SYSTEM = """You are an intent classifier for CommerceFlow AI, an e-commerce platform.

Classify the user's latest message into EXACTLY ONE of these intents:
- GREETING: "hello", "hi", "good morning"
- GENERAL_CONVERSATION: "what can you do?", "thanks", "that's helpful", general chit-chat
- PRODUCT_INFORMATION: asking about a specific named product ("Tell me about JBL Charge 5")
- PRODUCT_EXACT_LOOKUP: direct product detail request with explicit name/SKU
- PRICE_QUERY: asking specifically about price ("how much is it", "what's the price of X")
- STOCK_QUERY: asking about availability/stock ("is X in stock", "is it available")
- RATING_QUERY: asking about ratings or reviews ("what's the rating", "how many reviews")
- ATTRIBUTE_QUERY: asking about a specific product attribute ("where is it made", "does it have USB-C")
- PRODUCT_SEARCH: searching for multiple products ("show me Bluetooth speakers under PKR 20k")
- PRODUCT_RECOMMENDATION: asking for suggestions ("recommend a good speaker for travel")
- PRODUCT_COMPARISON: comparing 2+ products ("compare JBL and Sony")
- ORDER_STATUS: asking about a specific order status
- ORDER_HISTORY: asking about recent orders
- CART_HELP: cart-related questions
- SHIPPING_QUESTION: shipping/delivery questions
- PAYMENT_QUESTION: payment method questions
- RETURN_REFUND_QUESTION: return, refund, or exchange questions
- SUPPORT_REQUEST: wants human help or escalation
- UNKNOWN: genuinely cannot determine

IMPORTANT RULES:
1. "where is it made" = ATTRIBUTE_QUERY (NOT PRODUCT_SEARCH)
2. "is it in stock" = STOCK_QUERY (NOT PRODUCT_SEARCH)
3. "what's its price" = PRICE_QUERY (NOT PRODUCT_SEARCH)
4. "hello" / "thanks" = GREETING or GENERAL_CONVERSATION (NEVER product-related)
5. ATTRIBUTE_QUERY/PRICE_QUERY/STOCK_QUERY can use pronouns ("it", "this") when context exists
6. PRODUCT_SEARCH requires actual searching for multiple products by category/type/filter

Respond ONLY with valid JSON:
{
  "intent": "<INTENT>",
  "product_entity_a": "<primary product name or null>",
  "product_entity_b": "<second product name for comparison or null>",
  "price_max": <number or null>,
  "price_min": <number or null>,
  "category": "<product category keyword or null>",
  "reasoning": "<brief explanation>"
}"""


def _rule_based_classify(message: str, has_active_product: bool) -> dict | None:
    """
    Fast-path rule-based classifier. Returns classification dict or None
    if the message is ambiguous and needs LLM.

    Only fires for unambiguous cases to avoid LLM latency.
    """
    msg = message.strip()
    msg_lower = msg.lower()

    # Greeting
    if _GREETING_RE.match(msg):
        return {"intent": "GREETING", "product_entity_a": None, "product_entity_b": None}

    # Thanks / acknowledgements
    if _THANKS_RE.match(msg):
        return {"intent": "GENERAL_CONVERSATION", "product_entity_a": None, "product_entity_b": None}

    # "What can you do?" / "help me" (without product context words)
    if msg_lower in {"what can you do?", "what can you do", "what do you do", "help", "help me",
                     "how can you help", "how can you help me", "what are your capabilities"}:
        return {"intent": "GENERAL_CONVERSATION", "product_entity_a": None, "product_entity_b": None}

    # Order number present → ORDER_STATUS
    if _ORDER_NUM_RE.search(msg):
        return {"intent": "ORDER_STATUS", "product_entity_a": None, "product_entity_b": None,
                "order_number": _ORDER_NUM_RE.search(msg).group(0).upper()}

    # Comparison
    if _COMPARE_RE.search(msg):
        return {"intent": "PRODUCT_COMPARISON", "product_entity_a": None, "product_entity_b": None}

    # Escalation
    if _ESCALATE_RE.search(msg):
        return {"intent": "SUPPORT_REQUEST", "product_entity_a": None, "product_entity_b": None}

    # Cart
    if _CART_RE.search(msg):
        return {"intent": "CART_HELP", "product_entity_a": None, "product_entity_b": None}

    # Return/Refund (check before order to avoid "cancel my order" conflict)
    if _RETURN_RE.search(msg) and not _ORDER_NUM_RE.search(msg):
        return {"intent": "RETURN_REFUND_QUESTION", "product_entity_a": None, "product_entity_b": None}

    # Shipping (no product entity words)
    if _SHIPPING_RE.search(msg) and not any(w in msg_lower for w in ["product", "item", "this", "it"]):
        return {"intent": "SHIPPING_QUESTION", "product_entity_a": None, "product_entity_b": None}

    # Payment
    if _PAYMENT_RE.search(msg) and not any(w in msg_lower for w in ["product", "buy", "this"]):
        return {"intent": "PAYMENT_QUESTION", "product_entity_a": None, "product_entity_b": None}

    # Order history (without specific order number)
    if _ORDER_RE.search(msg):
        if "history" in msg_lower or "recent" in msg_lower or "latest" in msg_lower or "all my" in msg_lower:
            return {"intent": "ORDER_HISTORY", "product_entity_a": None, "product_entity_b": None}
        return {"intent": "ORDER_STATUS", "product_entity_a": None, "product_entity_b": None}

    # Pure pronoun reference WITH an active product → attribute/price/stock intent
    if has_active_product and detect_pronoun_reference(msg):
        # Determine which attribute they're asking about
        if _PRICE_RE.search(msg):
            return {"intent": "PRICE_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _STOCK_RE.search(msg):
            return {"intent": "STOCK_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _RATING_RE.search(msg):
            return {"intent": "RATING_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _ATTR_RE.search(msg):
            return {"intent": "ATTRIBUTE_QUERY", "product_entity_a": None, "product_entity_b": None}
        # Generic follow-up about the product
        return {"intent": "PRODUCT_INFORMATION", "product_entity_a": None, "product_entity_b": None}

    # Active product context + standalone attribute query (even without pronoun)
    # e.g. "what's the price?" or "what's the rating?" when a product is being discussed
    if has_active_product:
        if _PRICE_RE.search(msg) and len(msg.split()) <= 8:
            return {"intent": "PRICE_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _STOCK_RE.search(msg) and len(msg.split()) <= 8:
            return {"intent": "STOCK_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _RATING_RE.search(msg) and len(msg.split()) <= 8:
            return {"intent": "RATING_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _ATTR_RE.search(msg) and len(msg.split()) <= 8:
            return {"intent": "ATTRIBUTE_QUERY", "product_entity_a": None, "product_entity_b": None}

    # Pure pronoun WITHOUT active product → can't determine, need clarification
    if detect_pronoun_reference(msg) and not has_active_product:
        if _PRICE_RE.search(msg):
            return {"intent": "PRICE_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _STOCK_RE.search(msg):
            return {"intent": "STOCK_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _RATING_RE.search(msg):
            return {"intent": "RATING_QUERY", "product_entity_a": None, "product_entity_b": None}
        if _ATTR_RE.search(msg):
            return {"intent": "ATTRIBUTE_QUERY", "product_entity_a": None, "product_entity_b": None}

    # Ambiguous — let LLM handle
    return None


def intent_classifier_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    Intent Classifier Node — classifies the user's latest message into
    one of 19 fine-grained intents. Sets resolved_intent in state.

    Uses rule-based fast path first; falls back to LLM for ambiguous cases.
    """
    logger.info(f"Intent classifier processing conversation {state['conversation_id']}")

    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )

    if not last_human:
        return {**state, "resolved_intent": "UNKNOWN", "intent": "general"}

    message_text = last_human.content
    has_active_product = bool(state.get("active_product"))

    # ── 1. Rule-based fast path ──────────────────────────────────────────────
    rule_result = _rule_based_classify(message_text, has_active_product)

    if rule_result:
        intent = rule_result["intent"]
        logger.info(f"Rule-based intent: {intent} (no LLM needed)")
        updates = {
            "resolved_intent": intent,
            "intent": _map_to_legacy_intent(intent),
            "error": None,
        }
        # Carry forward order number if extracted
        if rule_result.get("order_number") and not state.get("order_context"):
            updates["order_context"] = {"order_number": rule_result["order_number"]}
        return {**state, **updates}

    # ── 2. LLM classification for ambiguous cases ────────────────────────────
    if not settings.OPENROUTER_API_KEY:
        # No LLM — use legacy rule-based fallback from supervisor
        return _legacy_fallback(state, message_text)

    try:
        # Build conversation context (last 4 turns)
        recent = [m for m in messages[-8:] if not isinstance(m, AIMessage) or m != messages[-1]]
        context_lines = []
        for m in recent:
            role = "Customer" if isinstance(m, HumanMessage) else "Assistant"
            context_lines.append(f"{role}: {m.content[:200]}")
        context = "\n".join(context_lines)

        active_product_note = ""
        if state.get("active_product"):
            active_product_note = f"\n[Currently discussing: {state['active_product'].get('name', 'unknown product')}]"

        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.0,
            max_tokens=256,
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://commerceflow.ai",
                "X-Title": "CommerceFlow AI",
            },
        )

        response = llm.invoke([
            SystemMessage(content=_CLASSIFIER_SYSTEM),
            HumanMessage(content=f"Conversation:{active_product_note}\n{context}\n\nClassify the latest customer message."),
        ])

        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        classification = json.loads(raw)
        intent = classification.get("intent", "UNKNOWN")
        if intent not in VALID_INTENTS:
            intent = "UNKNOWN"

        logger.info(f"LLM intent: {intent} — {classification.get('reasoning', '')[:80]}")

        updates = {
            "resolved_intent": intent,
            "intent": _map_to_legacy_intent(intent),
            "error": None,
        }

        # Store extracted entities for downstream use
        if classification.get("product_entity_a"):
            updates["_product_entity_a"] = classification["product_entity_a"]
        if classification.get("product_entity_b"):
            updates["_product_entity_b"] = classification["product_entity_b"]

        return {**state, **updates}

    except Exception as e:
        logger.warning(f"Intent classifier LLM failed ({e}), using legacy fallback")
        return _legacy_fallback(state, message_text)


def _map_to_legacy_intent(resolved_intent: str) -> str:
    """Map 19-intent to the 6-intent legacy system for backward compatibility."""
    mapping = {
        "GREETING": "general",
        "GENERAL_CONVERSATION": "general",
        "PRODUCT_INFORMATION": "product",
        "PRODUCT_EXACT_LOOKUP": "product",
        "PRICE_QUERY": "product",
        "STOCK_QUERY": "product",
        "RATING_QUERY": "product",
        "ATTRIBUTE_QUERY": "product",
        "PRODUCT_SEARCH": "product",
        "PRODUCT_RECOMMENDATION": "product",
        "PRODUCT_COMPARISON": "product",
        "ORDER_STATUS": "order",
        "ORDER_HISTORY": "order",
        "CART_HELP": "knowledge",
        "SHIPPING_QUESTION": "knowledge",
        "PAYMENT_QUESTION": "knowledge",
        "RETURN_REFUND_QUESTION": "refund",
        "SUPPORT_REQUEST": "escalation",
        "UNKNOWN": "general",
    }
    return mapping.get(resolved_intent, "general")


def _legacy_fallback(state: CommerceFlowState, message: str) -> CommerceFlowState:
    """Legacy keyword-based routing when no LLM is available."""
    msg = message.lower()

    if any(w in msg for w in ["hello", "hi ", "hi!", "hey"]):
        intent, resolved = "general", "GREETING"
    elif _ORDER_NUM_RE.search(message):
        intent, resolved = "order", "ORDER_STATUS"
    elif any(w in msg for w in ["my order", "track", "delivery", "shipped", "delivered"]):
        intent, resolved = "order", "ORDER_HISTORY"
    elif any(w in msg for w in ["return", "refund", "exchange", "damaged", "broken"]):
        intent, resolved = "refund", "RETURN_REFUND_QUESTION"
    elif any(w in msg for w in ["shipping", "delivery cost", "free shipping"]):
        intent, resolved = "knowledge", "SHIPPING_QUESTION"
    elif any(w in msg for w in ["payment", "pay", "credit card", "cod"]):
        intent, resolved = "knowledge", "PAYMENT_QUESTION"
    elif any(w in msg for w in ["return policy", "refund policy"]):
        intent, resolved = "knowledge", "RETURN_REFUND_QUESTION"
    elif any(w in msg for w in ["compare", "vs ", "versus"]):
        intent, resolved = "product", "PRODUCT_COMPARISON"
    elif any(w in msg for w in ["recommend", "suggest", "best for", "good for"]):
        intent, resolved = "product", "PRODUCT_RECOMMENDATION"
    elif any(w in msg for w in ["show me", "find", "search", "looking for"]):
        intent, resolved = "product", "PRODUCT_SEARCH"
    elif any(w in msg for w in ["price", "cost", "how much"]):
        intent, resolved = "product", "PRICE_QUERY"
    elif any(w in msg for w in ["in stock", "available", "availability"]):
        intent, resolved = "product", "STOCK_QUERY"
    elif any(w in msg for w in ["rating", "review", "stars"]):
        intent, resolved = "product", "RATING_QUERY"
    elif any(w in msg for w in ["made", "warranty", "spec", "feature"]):
        intent, resolved = "product", "ATTRIBUTE_QUERY"
    elif any(w in msg for w in ["tell me about", "what is", "describe", "info"]):
        intent, resolved = "product", "PRODUCT_INFORMATION"
    elif any(w in msg for w in ["human", "agent", "escalate", "manager"]):
        intent, resolved = "escalation", "SUPPORT_REQUEST"
    else:
        intent, resolved = "general", "UNKNOWN"

    return {**state, "resolved_intent": resolved, "intent": intent, "error": None}
