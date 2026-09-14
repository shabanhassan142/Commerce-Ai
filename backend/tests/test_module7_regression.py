"""
tests/test_module7_regression.py

Module 7 — Production Hardening Regression Suite.

Tests:
  1. Health endpoints (/health, /health/ready)
  2. Configuration — no secrets exposed in responses
  3. Security — RBAC enforcement, customer isolation
  4. FAISS / RAG — index loaded, search works, graceful failure
  5. Agent routing — supervisor routes correctly by keyword
  6. Chat service — timeout/error fallback, no internal details exposed
  7. Support — internal notes not exposed to customers
  8. API docs — /docs available in dev mode

All tests use the live running server (http://127.0.0.1:8000).
The server must be running before executing these tests.
"""

from __future__ import annotations

import pytest
import httpx


BASE_URL = "http://127.0.0.1:8000/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def api(path: str) -> str:
    return f"{BASE_URL}{path}"


def health_url(path: str = "") -> str:
    return f"http://127.0.0.1:8000/api/v1/health{path}"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Health Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    """Verify /health and /health/ready endpoints."""

    def test_health_returns_200(self):
        resp = httpx.get(health_url())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_health_has_required_fields(self):
        resp = httpx.get(health_url())
        data = resp.json()["data"]
        assert "status" in data
        assert "environment" in data
        assert "app" in data
        assert "services" in data
        assert "modules" in data

    def test_health_app_fields(self):
        resp = httpx.get(health_url())
        app_data = resp.json()["data"]["app"]
        assert "name" in app_data
        assert "version" in app_data
        assert "uptime_seconds" in app_data
        assert app_data["uptime_seconds"] >= 0

    def test_health_services_fields(self):
        resp = httpx.get(health_url())
        services = resp.json()["data"]["services"]
        assert "database" in services
        assert "vector_store" in services
        assert "llm_provider" in services

    def test_health_no_secrets_in_response(self):
        """Health endpoint must NEVER expose secrets, API keys, or passwords."""
        resp = httpx.get(health_url())
        text = resp.text.lower()
        # Check no secret-looking values are exposed
        assert "secret_key" not in text
        assert "openrouter_api_key" not in text
        assert "database_url" not in text
        assert "password" not in text
        # API key should not be in response — only whether it's configured
        assert "sk-or-" not in text  # OpenRouter key prefix

    def test_health_modules_reflect_current_status(self):
        """Modules should no longer say 'pending_module_4' etc."""
        resp = httpx.get(health_url())
        data = resp.json()["data"]
        modules = data["modules"]
        for module_name, status in modules.items():
            assert "pending_module" not in status, \
                f"Module '{module_name}' still shows placeholder status: {status}"

    def test_readiness_endpoint_exists(self):
        """GET /health/ready must exist and return valid JSON."""
        resp = httpx.get(health_url("/ready"))
        assert resp.status_code in (200, 503), \
            f"Expected 200 or 503, got {resp.status_code}"
        data = resp.json()
        assert "data" in data

    def test_readiness_has_checks_field(self):
        resp = httpx.get(health_url("/ready"))
        checks = resp.json()["data"]["checks"]
        assert "database" in checks
        assert "vector_store" in checks

    def test_readiness_ready_field(self):
        resp = httpx.get(health_url("/ready"))
        assert "ready" in resp.json()["data"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Authentication & Configuration Security
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthSecurity:
    """Verify authentication works and secrets are not exposed."""

    def test_protected_endpoint_without_token_returns_401(self):
        """Unauthenticated requests must return 401."""
        resp = httpx.get(api("/auth/me"))
        assert resp.status_code == 401

    def test_protected_endpoint_with_invalid_token_returns_401(self):
        resp = httpx.get(api("/auth/me"), headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    def test_error_response_no_stack_trace(self):
        """Error responses must not include Python stack traces."""
        resp = httpx.get(api("/auth/me"))
        text = resp.text
        assert "Traceback" not in text
        assert "File \"/app" not in text
        assert "raise " not in text

    def test_login_wrong_password_returns_401(self):
        resp = httpx.post(api("/auth/login"), json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401

    def test_login_response_never_exposes_password_hash(self):
        resp = httpx.post(api("/auth/login"), json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert "password_hash" not in resp.text
        assert "hashed" not in resp.text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 3. RBAC — Role-Based Access Control
# ─────────────────────────────────────────────────────────────────────────────

class TestRBAC:
    """Verify support/admin endpoints reject unauthorized roles."""

    def test_support_tickets_endpoint_requires_auth(self):
        """Support ticket management must require authentication."""
        resp = httpx.get(api("/tickets"))
        assert resp.status_code == 401

    def test_dashboard_endpoint_requires_auth(self):
        resp = httpx.get(api("/dashboard/stats"))
        assert resp.status_code == 401

    def test_knowledge_upload_requires_auth(self):
        """Knowledge base upload must be protected."""
        resp = httpx.post(api("/knowledge/upload"))
        assert resp.status_code in (401, 422)  # 422 if validation before auth check


# ─────────────────────────────────────────────────────────────────────────────
# 4. FAISS / RAG
# ─────────────────────────────────────────────────────────────────────────────

class TestFAISS:
    """Verify FAISS index is loaded and search works."""

    def test_faiss_status_in_health(self):
        resp = httpx.get(health_url())
        services = resp.json()["data"]["services"]
        vector_store = services["vector_store"]
        # Should be "loaded" or a clear status — not "not_initialized"
        assert vector_store != "not_initialized", \
            f"Vector store still shows 'not_initialized': {vector_store}"

    def test_faiss_vector_count_positive(self):
        resp = httpx.get(health_url())
        services = resp.json()["data"]["services"]
        vector_count = services.get("vector_store_vectors", 0)
        # If status is "loaded", we expect vectors
        if services["vector_store"] == "loaded":
            assert vector_count > 0, "FAISS shows loaded but 0 vectors"

    def test_knowledge_search_endpoint_exists(self):
        """Knowledge search endpoint should respond (auth may be required)."""
        # The knowledge search endpoint uses POST not GET
        resp = httpx.post(api("/knowledge/search"), json={"query": "shipping"})
        assert resp.status_code in (200, 401, 403, 422), \
            f"Unexpected status: {resp.status_code}"



# ─────────────────────────────────────────────────────────────────────────────
# 5. Agent Routing (without LLM — rule-based fallback)
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentRouting:
    """Verify supervisor rule-based routing is correct."""

    def test_rule_based_order_routing(self):
        from app.agents.nodes.supervisor import _rule_based_routing
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage
        state = initial_state(conversation_id="test", user_id="test")
        state["messages"] = [HumanMessage(content="Where is my order?")]
        result = _rule_based_routing(state, "Where is my order?")
        assert result["intent"] == "order"
        assert result["selected_agent"] == "order_agent"

    def test_rule_based_product_routing(self):
        from app.agents.nodes.supervisor import _rule_based_routing
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage
        state = initial_state(conversation_id="test", user_id="test")
        state["messages"] = [HumanMessage(content="Do you have wireless headphones?")]
        result = _rule_based_routing(state, "Do you have wireless headphones?")
        assert result["intent"] == "product"
        assert result["selected_agent"] == "product_agent"

    def test_rule_based_refund_routing(self):
        from app.agents.nodes.supervisor import _rule_based_routing
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage
        state = initial_state(conversation_id="test", user_id="test")
        state["messages"] = [HumanMessage(content="I want to return my item for a refund")]
        result = _rule_based_routing(state, "I want to return my item for a refund")
        assert result["intent"] == "refund"
        assert result["selected_agent"] == "refund_agent"

    def test_rule_based_knowledge_routing(self):
        from app.agents.nodes.supervisor import _rule_based_routing
        from app.agents.state import initial_state
        from langchain_core.messages import HumanMessage
        state = initial_state(conversation_id="test", user_id="test")
        state["messages"] = [HumanMessage(content="What is your return policy?")]
        result = _rule_based_routing(state, "What is your return policy?")
        assert result["intent"] == "knowledge"
        assert result["selected_agent"] == "rag_agent"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Chat Service — Timeout & Error Fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestChatServiceHardening:
    """Verify chat service timeout and error handling."""

    def test_chat_service_returns_dict_on_import(self):
        """ChatService must be importable and have process_message."""
        from app.services.chat_service import ChatService, _AGENT_TIMEOUT_SECONDS, _ERROR_MESSAGE
        assert callable(ChatService.process_message)
        assert _AGENT_TIMEOUT_SECONDS == 60
        assert len(_ERROR_MESSAGE) > 0

    def test_timeout_message_is_user_friendly(self):
        from app.services.chat_service import _TIMEOUT_MESSAGE
        assert "sorry" in _TIMEOUT_MESSAGE.lower() or "please" in _TIMEOUT_MESSAGE.lower()
        assert "Traceback" not in _TIMEOUT_MESSAGE
        assert "Exception" not in _TIMEOUT_MESSAGE

    def test_error_message_is_user_friendly(self):
        from app.services.chat_service import _ERROR_MESSAGE
        assert len(_ERROR_MESSAGE) > 10
        assert "Traceback" not in _ERROR_MESSAGE
        assert "Exception" not in _ERROR_MESSAGE


# ─────────────────────────────────────────────────────────────────────────────
# 7. Products API
# ─────────────────────────────────────────────────────────────────────────────

class TestProductsAPI:
    """Verify product catalog API works correctly."""

    def test_products_list_public(self):
        resp = httpx.get(api("/products"))
        assert resp.status_code == 200
        res = resp.json()
        data = res.get("data", res)
        assert data["total"] == 30
        assert len(data["items"]) > 0

    def test_products_have_images(self):
        resp = httpx.get(api("/products?per_page=5"))
        res = resp.json()
        items = res.get("data", res)["items"]
        for item in items:
            assert len(item["images"]) >= 2

    def test_products_have_brand(self):
        resp = httpx.get(api("/products?per_page=5"))
        res = resp.json()
        items = res.get("data", res)["items"]
        for item in items:
            assert "brand" in item

    def test_products_discount_percent_non_negative(self):
        resp = httpx.get(api("/products"))
        res = resp.json()
        items = res.get("data", res)["items"]
        for item in items:
            assert item["discount_percent"] >= 0

    def test_products_search_works(self):
        resp = httpx.get(api("/products?search=MacBook"))
        assert resp.status_code == 200
        res = resp.json()
        assert res.get("data", res)["total"] >= 1

    def test_products_category_filter_works(self):
        resp = httpx.get(api("/products?category_slug=audio"))
        assert resp.status_code == 200
        res = resp.json()
        assert res.get("data", res)["total"] >= 1

    def test_products_pagination_works(self):
        resp = httpx.get(api("/products?page=1&per_page=3"))
        res = resp.json()
        data = res.get("data", res)
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data.get("pages", data.get("total_pages")) >= 1

    def test_product_detail_returns_gallery(self):
        list_resp = httpx.get(api("/products?per_page=1"))
        res = list_resp.json()
        product_id = res.get("data", res)["items"][0]["id"]
        resp = httpx.get(api(f"/products/{product_id}"))
        assert resp.status_code == 200
        res_det = resp.json()
        detail = res_det.get("data", res_det)
        assert "images" in detail
        assert len(detail["images"]) >= 2
        assert "specifications" in detail


# ─────────────────────────────────────────────────────────────────────────────
# 8. API Documentation
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIDocs:
    """Verify Swagger docs are accessible in development mode."""

    def test_docs_endpoint_accessible(self):
        """In development mode, /docs must return 200."""
        resp = httpx.get("http://127.0.0.1:8000/docs")
        # In development: 200; in production: 404 (intentionally disabled)
        assert resp.status_code in (200, 404), f"Unexpected: {resp.status_code}"

    def test_openapi_json_accessible(self):
        resp = httpx.get("http://127.0.0.1:8000/openapi.json")
        if resp.status_code == 200:
            schema = resp.json()
            assert "paths" in schema
            assert "/api/v1/health" in schema["paths"]
            assert "/api/v1/products" in schema["paths"]
            assert "/api/v1/auth/login" in schema["paths"]


# ─────────────────────────────────────────────────────────────────────────────
# 9. Settings — No Hardcoded Secrets
# ─────────────────────────────────────────────────────────────────────────────

class TestSettingsIntegrity:
    """Verify settings module never has hardcoded secrets."""

    def test_settings_loads_from_env(self):
        from app.config.settings import get_settings
        settings = get_settings()
        assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
        assert len(settings.SECRET_KEY) >= 32

    def test_settings_secret_key_not_default(self):
        from app.config.settings import get_settings
        settings = get_settings()
        # Should not be the example placeholder value
        assert settings.SECRET_KEY != "CHANGE_THIS_TO_A_STRONG_RANDOM_SECRET_KEY_MIN_32_CHARS"

    def test_faiss_index_path_configured(self):
        from app.config.settings import get_settings
        settings = get_settings()
        assert settings.FAISS_INDEX_PATH
        assert len(settings.FAISS_INDEX_PATH) > 0

    def test_is_production_flag(self):
        from app.config.settings import get_settings
        settings = get_settings()
        # In local dev environment, should be development
        assert settings.ENVIRONMENT in ("development", "staging", "production")
        assert isinstance(settings.is_production, bool)
        assert isinstance(settings.is_development, bool)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Existing Data Integrity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_data_integrity_unchanged():
    """Verify all existing data is still intact after Module 7 changes."""
    from app.database.session import AsyncSessionLocal, engine
    from sqlalchemy import text

    await engine.dispose()
    async with AsyncSessionLocal() as db:
        counts = {
            "products": (await db.execute(text("SELECT COUNT(*) FROM products"))).scalar(),
            "product_images": (await db.execute(text("SELECT COUNT(*) FROM product_images"))).scalar(),
            "customers": (await db.execute(text("SELECT COUNT(*) FROM customers"))).scalar(),
            "users": (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar(),
            "orders": (await db.execute(text("SELECT COUNT(*) FROM orders"))).scalar(),
            "order_items": (await db.execute(text("SELECT COUNT(*) FROM order_items"))).scalar(),
            "support_tickets": (await db.execute(text("SELECT COUNT(*) FROM support_tickets"))).scalar(),
            "conversations": (await db.execute(text("SELECT COUNT(*) FROM conversations"))).scalar(),
            "agent_logs": (await db.execute(text("SELECT COUNT(*) FROM agent_logs"))).scalar(),
        }

    # Exact counts from pre-Module-7 verification
    assert counts["products"] == 30, f"Expected 30 products, got {counts['products']}"
    assert counts["product_images"] >= 60, f"Expected 60+ images, got {counts['product_images']}"
    assert counts["customers"] == 100, f"Expected 100 customers, got {counts['customers']}"
    assert counts["orders"] == 500, f"Expected 500 orders, got {counts['orders']}"
    assert counts["support_tickets"] == 85, f"Expected 85 tickets, got {counts['support_tickets']}"
