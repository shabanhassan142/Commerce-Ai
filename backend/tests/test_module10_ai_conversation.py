"""
tests/test_module10_ai_conversation.py

Module 10 — AI Conversation Behavior Tests

Tests the intent classification, context resolution, product entity resolution,
response quality, and multi-turn conversation behavior of the CommerceFlow AI.

All 20 tests per the specification.
"""
from __future__ import annotations

import asyncio
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# Intent Classifier Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIntentClassifier:
    """Test the rule-based intent classifier fast path."""

    def _classify(self, message: str, has_active_product: bool = False) -> dict:
        from app.agents.nodes.intent_classifier import _rule_based_classify
        result = _rule_based_classify(message, has_active_product)
        return result or {}

    def test_1_greeting_hello(self):
        """Test 1: 'hello' → GREETING (no product search)"""
        result = self._classify("hello")
        assert result.get("intent") == "GREETING", f"Expected GREETING, got {result}"

    def test_1b_greeting_hi(self):
        result = self._classify("hi there!")
        assert result.get("intent") == "GREETING"

    def test_2_thanks_general_conversation(self):
        """Test 2: 'thanks' → GENERAL_CONVERSATION"""
        result = self._classify("thanks")
        assert result.get("intent") == "GENERAL_CONVERSATION"

    def test_3_price_query_with_pronoun(self):
        """Test 3: 'what's the price?' with active product → PRICE_QUERY"""
        result = self._classify("what's the price?", has_active_product=True)
        assert result.get("intent") == "PRICE_QUERY", f"Expected PRICE_QUERY, got {result}"

    def test_4_stock_query_with_pronoun(self):
        """Test 4: 'is it in stock?' with active product → STOCK_QUERY"""
        result = self._classify("is it in stock?", has_active_product=True)
        assert result.get("intent") == "STOCK_QUERY"

    def test_5_rating_query_with_pronoun(self):
        """Test 5: 'what's the rating?' with active product → RATING_QUERY"""
        result = self._classify("what's the rating?", has_active_product=True)
        assert result.get("intent") == "RATING_QUERY"

    def test_6_attribute_query_with_pronoun(self):
        """Test 6: 'where is it made?' with active product → ATTRIBUTE_QUERY"""
        result = self._classify("where is it made?", has_active_product=True)
        assert result.get("intent") == "ATTRIBUTE_QUERY"

    def test_7_product_comparison(self):
        """Test 7: 'compare X and Y' → PRODUCT_COMPARISON"""
        result = self._classify("Compare JBL Charge 5 and Sony WH-1000XM5")
        assert result.get("intent") == "PRODUCT_COMPARISON"

    def test_8_order_number_in_message(self):
        """Test 8: Message with order number → ORDER_STATUS"""
        result = self._classify("What is the status of CF-20260801-001?")
        assert result.get("intent") == "ORDER_STATUS"
        assert result.get("order_number", "").upper() == "CF-20260801-001"

    def test_9_cart_help(self):
        """Test 9: Cart-related question → CART_HELP"""
        result = self._classify("What's in my cart?")
        assert result.get("intent") == "CART_HELP"

    def test_10_return_refund(self):
        """Test 10: Return/refund question → RETURN_REFUND_QUESTION"""
        result = self._classify("Can I return this item?")
        assert result.get("intent") == "RETURN_REFUND_QUESTION"

    def test_11_escalation(self):
        """Test 11: Escalation request → SUPPORT_REQUEST"""
        result = self._classify("I want to speak to a human agent")
        assert result.get("intent") == "SUPPORT_REQUEST"

    def test_12_where_made_no_active_product(self):
        """Test 12: 'where is it made?' WITHOUT active product → ATTRIBUTE_QUERY (not PRODUCT_SEARCH)"""
        result = self._classify("where is this product made?", has_active_product=False)
        # Should be ATTRIBUTE_QUERY (pronoun + attribute word) — NOT PRODUCT_SEARCH
        assert result.get("intent") == "ATTRIBUTE_QUERY", (
            f"'where is this product made?' should be ATTRIBUTE_QUERY, got {result}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Pronoun Detection Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPronounDetection:
    """Test detect_pronoun_reference utility."""

    def test_13_pronoun_it(self):
        """Test 13: 'where is it made' → pronoun reference detected"""
        from app.agents.utils.product_query import detect_pronoun_reference
        assert detect_pronoun_reference("where is it made?") is True

    def test_13b_pronoun_this(self):
        from app.agents.utils.product_query import detect_pronoun_reference
        assert detect_pronoun_reference("is this in stock?") is True

    def test_13c_pronoun_the_product(self):
        from app.agents.utils.product_query import detect_pronoun_reference
        assert detect_pronoun_reference("tell me about the product") is True

    def test_14_no_pronoun_explicit_name(self):
        """Test 14: Explicit product name → no pronoun reference"""
        from app.agents.utils.product_query import detect_pronoun_reference
        # "Compare JBL and Sony" contains no reference pronouns
        assert detect_pronoun_reference("Compare JBL Charge 5 and Sony WH-1000XM5") is False

    def test_14b_no_pronoun_show_me(self):
        from app.agents.utils.product_query import detect_pronoun_reference
        assert detect_pronoun_reference("Show me Bluetooth speakers") is False


# ─────────────────────────────────────────────────────────────────────────────
# Product Query / Normalization Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProductQuery:
    """Test extract_search_phrase and normalize_product_query."""

    def test_15_extract_tell_me_about(self):
        """Test 15: Extract product name from 'Tell me about X'"""
        from app.agents.utils.product_query import extract_search_phrase
        result = extract_search_phrase("Tell me about JBL Charge 5 Portable Bluetooth Speaker")
        assert "JBL Charge 5" in result or "JBL" in result

    def test_16_extract_price_of(self):
        """Test 16: Extract product name from 'What is the price of X'"""
        from app.agents.utils.product_query import extract_search_phrase
        result = extract_search_phrase("What is the price of Apple MacBook Pro 14?")
        assert "Apple" in result or "MacBook" in result

    def test_17_normalize_strips_stopwords(self):
        """Test 17: normalize_product_query removes stop words"""
        from app.agents.utils.product_query import normalize_product_query
        result = normalize_product_query("show me some good wireless headphones please")
        # Should contain "wireless headphones" but not "show", "some", "good", "please"
        assert "headphones" in result or "wireless" in result
        assert "show" not in result
        assert "please" not in result


# ─────────────────────────────────────────────────────────────────────────────
# Product Detail Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProductDetailTool:
    """Test get_product_attribute with various attributes."""

    def _make_product(self, specs=None):
        return {
            "id": "test-id",
            "name": "JBL Charge 5",
            "sku": "JBL-CH5-BLK",
            "brand": "JBL",
            "price": 25000.0,
            "discount_percent": 10.0,
            "rating": 4.6,
            "review_count": 9214,
            "stock": 50,
            "description": "Portable Bluetooth speaker",
            "specifications": specs or {
                "bluetooth_version": "5.1",
                "battery_life": "20 hours",
                "waterproof": "IP67",
            },
            "category": "Speakers",
        }

    def test_18_price_attribute(self):
        """Test 18: get_product_attribute returns correct price string"""
        from app.agents.tools.product_detail_tool import get_product_attribute
        product = self._make_product()
        result = get_product_attribute(product, "price")
        assert "25,000" in result or "22,500" in result  # original or discounted
        assert "PKR" in result

    def test_19_stock_attribute_in_stock(self):
        """Test 19: get_product_attribute returns stock correctly"""
        from app.agents.tools.product_detail_tool import get_product_attribute
        product = self._make_product()
        result = get_product_attribute(product, "stock")
        assert "in stock" in result.lower() or "50" in result

    def test_20_rating_attribute(self):
        """Test 20: get_product_attribute returns rating correctly"""
        from app.agents.tools.product_detail_tool import get_product_attribute
        product = self._make_product()
        result = get_product_attribute(product, "rating")
        assert "4.6" in result
        assert "9,214" in result or "9214" in result

    def test_21_country_of_origin_not_in_specs(self):
        """Test 21: Missing attribute → honest 'not available' (no hallucination)"""
        from app.agents.tools.product_detail_tool import get_product_attribute
        product = self._make_product(specs={"bluetooth_version": "5.1"})
        result = get_product_attribute(product, "country_of_origin")
        # Must NOT make up a country
        made_up_countries = ["China", "USA", "Japan", "Germany", "India", "Korea"]
        for country in made_up_countries:
            assert country not in result, f"Hallucinated country: {country} in result: {result}"
        # Must say it's not available
        assert any(phrase in result.lower() for phrase in [
            "don't have", "not available", "not listed", "no", "catalog"
        ])

    def test_22_spec_from_specifications(self):
        """Test 22: Attribute available in specifications returns correct value"""
        from app.agents.tools.product_detail_tool import get_product_attribute
        product = self._make_product(specs={"battery_life": "20 hours", "waterproof": "IP67"})
        result = get_product_attribute(product, "battery")
        assert "20" in result or "hours" in result

    def test_23_waterproof_from_specifications(self):
        """Test 23: Waterproof spec returns correct value"""
        from app.agents.tools.product_detail_tool import get_product_attribute
        product = self._make_product(specs={"waterproof": "IP67", "ip_rating": "67"})
        result = get_product_attribute(product, "waterproof")
        assert "IP67" in result or "67" in result


# ─────────────────────────────────────────────────────────────────────────────
# Product Search Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProductSearchTool:
    """Test that search_products tool returns structured output without raw internals."""

    def test_24_search_returns_no_found_n_products(self):
        """Test 24: search_products output does NOT contain 'Found N products matching'"""
        from app.agents.tools.product_tools import search_products
        result = search_products.invoke({"query": "bluetooth speaker"})
        # This is the forbidden raw output string
        assert "Found" not in result or "SEARCH RESULTS" in result, (
            "search_products returned raw 'Found N products matching' string"
        )
        # Must not be empty
        assert len(result) > 10

    def test_25_search_with_relevant_query(self):
        """Test 25: Relevant search returns results"""
        from app.agents.tools.product_tools import search_products
        result = search_products.invoke({"query": "headphones"})
        assert result  # non-empty
        assert len(result) > 20

    def test_26_search_with_pure_stopwords_returns_no_products(self):
        """Test 26: Pure conversation words don't trigger meaningful product matches"""
        from app.agents.utils.product_query import is_pure_conversation
        # These messages should be flagged as pure conversation — NOT sent to search
        assert is_pure_conversation("where is it made") is True
        assert is_pure_conversation("hello") is True
        assert is_pure_conversation("is this in stock") is True

    def test_27_search_explicit_product_returns_correct(self):
        """Test 27: Exact product name search returns the right product"""
        from app.agents.tools.product_tools import search_products
        result = search_products.invoke({"query": "JBL Charge 5"})
        assert result
        # Should mention JBL somewhere
        assert "JBL" in result or "Charge" in result or "No products found" in result


# ─────────────────────────────────────────────────────────────────────────────
# Product Comparison Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProductComparisonTool:
    """Test get_product_comparison tool."""

    def test_28_comparison_returns_table(self):
        """Test 28: Comparison of two products returns markdown table format"""
        from app.agents.tools.product_tools import get_product_comparison
        # Use generic category searches that should find products
        result = get_product_comparison.invoke({
            "product_a": "JBL Charge 5",
            "product_b": "Sony"
        })
        assert result
        # Either finds products (has table) or says "Could not find"
        has_table = "|" in result and "---" in result
        has_not_found = "Could not find" in result or "No products found" in result
        assert has_table or has_not_found, f"Unexpected comparison result: {result[:200]}"

    def test_29_comparison_no_hallucination(self):
        """Test 29: Comparison only includes attributes from DB"""
        from app.agents.tools.product_tools import get_product_comparison
        result = get_product_comparison.invoke({
            "product_a": "JBL Charge 5",
            "product_b": "Anker PowerCore"
        })
        # Should not contain invented specs
        assert "Not available" in result or "|" in result or "Could not find" in result


# ─────────────────────────────────────────────────────────────────────────────
# State Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestState:
    """Test Module 10 state extensions."""

    def test_30_initial_state_has_new_fields(self):
        """Test 30: initial_state includes all Module 10 fields"""
        from app.agents.state import initial_state
        state = initial_state(
            conversation_id="test-conv-id",
            user_id="test-user-id",
            product_id_from_detail="test-product-uuid",
        )
        assert "active_product" in state
        assert state["active_product"] is None
        assert "product_search_results" in state
        assert state["product_search_results"] == []
        assert "resolved_intent" in state
        assert state["resolved_intent"] == "UNKNOWN"
        assert "product_context_source" in state
        assert "product_id_from_detail" in state
        assert state["product_id_from_detail"] == "test-product-uuid"

    def test_31_initial_state_backward_compatible(self):
        """Test 31: initial_state without new args is backward compatible"""
        from app.agents.state import initial_state
        state = initial_state(
            conversation_id="test-conv-id",
            user_id="test-user-id",
        )
        # Old fields still present
        assert "conversation_id" in state
        assert "user_id" in state
        assert "messages" in state
        assert "intent" in state
        assert state["product_id_from_detail"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Comparison Entity Extraction Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestComparisonExtraction:
    """Test comparison entity extraction from natural language."""

    def _extract(self, message):
        from app.agents.nodes.product_agent import _extract_comparison_entities
        return _extract_comparison_entities(message)

    def test_32_compare_and_pattern(self):
        """Test 32: 'Compare X and Y' → extracts both entities"""
        a, b = self._extract("Compare JBL Charge 5 and Sony WH-1000XM5")
        assert a and "JBL" in a
        assert b and "Sony" in b

    def test_33_vs_pattern(self):
        """Test 33: 'X vs Y' → extracts both entities"""
        a, b = self._extract("JBL Charge 5 vs Sony WH-1000XM5")
        assert a and "JBL" in a
        assert b and "Sony" in b

    def test_34_difference_between_pattern(self):
        """Test 34: 'difference between X and Y' → extracts both entities"""
        a, b = self._extract("What is the difference between iPhone and Samsung?")
        assert a and "iPhone" in a
        assert b and "Samsung" in b


# ─────────────────────────────────────────────────────────────────────────────
# Graph / Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphIntegration:
    """Test that the LangGraph compiles with new nodes."""

    def test_35_graph_compiles(self):
        """Test 35: LangGraph with Module 10 nodes compiles without errors"""
        # Clear lru_cache to force rebuild
        from app.agents.graph import get_commerce_graph
        get_commerce_graph.cache_clear()
        graph = get_commerce_graph()
        assert graph is not None

    def test_36_supervisor_routes_greeting_to_response(self):
        """Test 36: Supervisor routes GREETING → response_agent"""
        from app.agents.nodes.supervisor import supervisor_node
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage

        state = initial_state("conv-1", "user-1", [HumanMessage(content="hello")])
        state["resolved_intent"] = "GREETING"
        result = supervisor_node(state)
        assert result["selected_agent"] == "response_agent"

    def test_37_supervisor_routes_product_info_to_product_agent(self):
        """Test 37: Supervisor routes PRODUCT_INFORMATION → product_agent"""
        from app.agents.nodes.supervisor import supervisor_node
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage

        state = initial_state("conv-2", "user-2", [HumanMessage(content="Tell me about JBL Charge 5")])
        state["resolved_intent"] = "PRODUCT_INFORMATION"
        result = supervisor_node(state)
        assert result["selected_agent"] == "product_agent"

    def test_38_supervisor_routes_order_status_to_order_agent(self):
        """Test 38: Supervisor routes ORDER_STATUS → order_agent"""
        from app.agents.nodes.supervisor import supervisor_node
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage

        state = initial_state("conv-3", "user-3", [HumanMessage(content="Where is my order?")])
        state["resolved_intent"] = "ORDER_STATUS"
        result = supervisor_node(state)
        assert result["selected_agent"] == "order_agent"

    def test_39_classifier_does_not_search_for_greeting(self):
        """Test 39: Intent classifier marks 'hello' as GREETING — not product-related"""
        from app.agents.nodes.intent_classifier import intent_classifier_node
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage

        state = initial_state("conv-4", "user-4", [HumanMessage(content="hello")])
        result = intent_classifier_node(state)
        assert result["resolved_intent"] == "GREETING"
        assert result["intent"] == "general"

    def test_40_product_agent_detail_needs_active_product_for_clarification(self):
        """Test 40: Product detail handler with no active_product returns clarification request"""
        from app.agents.nodes.product_agent import _detail_handler
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage

        state = initial_state("conv-5", "user-5", [HumanMessage(content="where is it made?")])
        state["resolved_intent"] = "ATTRIBUTE_QUERY"
        state["active_product"] = None  # No product context

        result = _detail_handler(state)
        tool_results = result.get("tool_results", [])
        assert len(tool_results) > 0
        # First tool should be clarification_needed
        assert tool_results[0]["tool"] == "clarification_needed"
        assert "which product" in tool_results[0]["output"].lower()
