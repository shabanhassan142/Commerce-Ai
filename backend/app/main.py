"""
app/main.py

FastAPI application factory for CommerceFlow AI.

This module:
  - Creates and configures the FastAPI app
  - Registers all middleware (CORS, logging)
  - Sets up global exception handlers
  - Manages application lifespan (startup/shutdown events)
  - Mounts all API routers

Startup sequence:
  1. Configure logging
  2. Verify database connection
  3. Load FAISS index from disk (read-only — no re-embedding)
  4. Log configuration warnings (missing API keys etc.)
  5. App ready to serve requests
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import v1_router
from app.config.settings import get_settings
from app.core.logging import get_logger, log_requests_middleware, setup_logging
from app.database.session import check_database_connection

settings = get_settings()

# ── OpenAPI Tag Groups ─────────────────────────────────────────────────────────

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "System health checks and readiness probes for monitoring and orchestration.",
    },
    {
        "name": "Authentication",
        "description": "Register, login, token refresh, logout, and profile management.",
    },
    {
        "name": "Marketplace",
        "description": "Browse and search products, categories, and product details.",
    },
    {
        "name": "Orders",
        "description": "Customer order history, order details, and order tracking.",
    },
    {
        "name": "AI Chatbot",
        "description": (
            "LangGraph multi-agent customer support chat. "
            "Supervisor routes to specialist agents: Order, Product, Refund, RAG/Knowledge."
        ),
    },
    {
        "name": "Support Tickets",
        "description": "Create and track support tickets (customer-facing).",
    },
    {
        "name": "Support Operations",
        "description": "Agent/admin ticket management, assignment, replies, and SLA tracking.",
    },
    {
        "name": "Knowledge Base",
        "description": "RAG knowledge document management and FAISS vector search.",
    },
    {
        "name": "Dashboard",
        "description": "Analytics and metrics for admin and support dashboards.",
    },
]


# ── Lifespan (Startup / Shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Runs setup on startup and teardown on shutdown.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    setup_logging()
    logger = get_logger(__name__)

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # 1. Verify database connection
    db_ok = await check_database_connection()
    if not db_ok:
        logger.error(
            "Database connection failed at startup. "
            "Ensure PostgreSQL is running and DATABASE_URL is correct."
        )
    else:
        logger.info("Database connection established")

    # 2. Load FAISS index from disk (read-only — never re-embeds)
    #    The existing index at FAISS_INDEX_PATH is loaded once at startup.
    #    If the file does not exist the app still starts but RAG will be degraded.
    _load_faiss_index(logger)

    # 3. Warn if LLM API key is not configured
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_API_KEY.strip():
        logger.warning(
            "OPENROUTER_API_KEY is not set. "
            "The AI chat will operate in rule-based fallback mode. "
            "Set OPENROUTER_API_KEY in .env to enable full LLM support."
        )
    else:
        logger.info(f"LLM configured: {settings.LLM_PROVIDER} / {settings.LLM_MODEL}")

    logger.info("CommerceFlow AI is ready to serve requests")
    logger.info(f"API Docs available at: http://localhost:8000/docs")

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down CommerceFlow AI...")


def _load_faiss_index(logger) -> None:
    """
    Load the FAISS index from disk into memory at startup.

    Design decisions:
      - NEVER re-embeds or regenerates — only loads an existing index.
      - If the index file is missing, logs a warning but does NOT crash.
      - The health/ready endpoint will report degraded if index is not loaded.
      - In Docker the faiss/ directory is mounted as a read-only volume.
      - Uses get_indexer() singleton so the loaded state is shared with
        the health endpoint and all other modules.
    """
    import os
    from app.rag.indexer import get_indexer

    indexer = get_indexer()
    index_file = indexer.faiss_file

    if not os.path.exists(index_file):
        logger.warning(
            f"FAISS index not found at '{index_file}'. "
            "RAG knowledge retrieval will be unavailable. "
            "To fix: ensure the faiss/ directory is mounted or present."
        )
        return

    try:
        loaded = indexer.load()
        if loaded:
            stats = indexer.get_stats()
            logger.info(
                f"FAISS index loaded: {stats['total_vectors']} vectors "
                f"from {stats.get('unique_sources', 0)} sources"
            )
        else:
            logger.warning("FAISS index load returned False — index may be empty or corrupt")
    except Exception as exc:
        logger.error(f"FAISS index load failed: {exc}. RAG will be degraded.")


# ── Application Factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    Using factory pattern allows easy testing with different configs.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "**CommerceFlow AI** — Multi-Agent AI Customer Support & E-Commerce Platform.\n\n"
            "Powered by **LangGraph**, **FAISS RAG**, and **OpenRouter LLM**.\n\n"
            "### Architecture\n"
            "- **LangGraph** multi-agent supervisor routing\n"
            "- **FAISS** semantic knowledge retrieval\n"
            "- **PostgreSQL** with async SQLAlchemy\n"
            "- **JWT** authentication with RBAC\n"
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )

    # ── Middleware ─────────────────────────────────────────────────────────
    _register_middleware(app)

    # ── Exception Handlers ────────────────────────────────────────────────
    _register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(v1_router)

    return app


def _register_middleware(app: FastAPI) -> None:
    """Register all application middleware."""

    # CORS — must be added before request logging
    # In development we allow all origins (safe locally, avoids localhost/127.0.0.1 mismatch on Windows).
    # We use Bearer tokens (not cookies) so allow_credentials=False is correct.
    # In production, restrict to specific origins via ALLOWED_ORIGINS env var.
    cors_origins = ["*"] if settings.is_development else settings.allowed_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,  # Must be False when allow_origins=["*"]
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Request/Response logging with request IDs
    app.middleware("http")(log_requests_middleware)


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for clean error responses."""
    logger = get_logger(__name__)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        """Handle Pydantic validation errors with a clean response."""
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Validation error",
                "errors": exc.errors(),
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> ORJSONResponse:
        """Catch-all handler for unhandled exceptions. Never exposes stack traces."""
        logger.error(
            f"Unhandled exception on {request.url.path}: {type(exc).__name__}",
            exc_info=True,
        )
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Internal server error",
                "data": None,
            },
        )


# ── Entry Point ───────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
