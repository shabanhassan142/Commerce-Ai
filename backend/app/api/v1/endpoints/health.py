"""
app/api/v1/endpoints/health.py

System health check endpoints.

Two endpoints:
  GET /api/v1/health        - Full health report (always 200)
  GET /api/v1/health/ready  - Readiness probe (503 if not ready)

Used by:
  - Load balancers and orchestrators (Kubernetes liveness/readiness probes)
  - Monitoring systems (UptimeRobot, Datadog, etc.)
  - Developers verifying the system is running correctly

Never exposes secrets, API keys, or passwords.
"""

import os
import platform
import time

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.database.session import check_database_connection
from app.utils.responses import success_response

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()
logger = get_logger(__name__)

# Track application start time
_start_time = time.time()


def _get_faiss_status() -> dict:
    """Return FAISS index status without raising."""
    try:
        from app.rag.indexer import get_indexer
        indexer = get_indexer()
        # Check if index file exists on disk
        index_on_disk = os.path.exists(indexer.faiss_file)
        stats = indexer.get_stats()
        if stats["status"] == "loaded":
            return {
                "status": "loaded",
                "total_vectors": stats.get("total_vectors", 0),
                "unique_sources": stats.get("unique_sources", 0),
                "on_disk": stats.get("on_disk", False),
            }
        if not index_on_disk:
            return {"status": "unavailable", "detail": "Index file not found on disk", "total_vectors": 0}
        return {
            "status": "on_disk_not_loaded",
            "detail": "Index file exists but not loaded into memory",
            "total_vectors": 0,
            "on_disk": True,
        }
    except Exception as exc:
        logger.warning(f"FAISS status check failed: {exc}")
        return {"status": "error", "detail": str(exc), "total_vectors": 0}



def _get_llm_status() -> dict:
    """Return LLM configuration status (never exposes key value)."""
    api_key_set = bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip())
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "api_key_configured": api_key_set,
        "fallback_mode": not api_key_set,
    }


@router.get(
    "",
    summary="Full system health report",
    response_description="Health status of all system components",
    tags=["Health"],
)
async def health_check():
    """
    Returns a comprehensive health report for all system components.

    Always returns HTTP 200. Check the `status` field to determine health:
      - `"healthy"` — all systems operational
      - `"degraded"` — some components unavailable but app is running

    Checks:
      - Application uptime and version
      - PostgreSQL database connectivity
      - FAISS vector index status
      - LLM provider configuration

    **Never exposes secrets, API keys, or passwords.**
    """
    db_healthy = await check_database_connection()
    faiss_status = _get_faiss_status()
    llm_status = _get_llm_status()
    uptime_seconds = round(time.time() - _start_time, 2)

    faiss_healthy = faiss_status["status"] in ("loaded",)
    overall_healthy = db_healthy and faiss_healthy

    health_data = {
        "status": "healthy" if overall_healthy else "degraded",
        "environment": settings.ENVIRONMENT,
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "uptime_seconds": uptime_seconds,
            "python_version": platform.python_version(),
            "debug": settings.DEBUG,
        },
        "services": {
            "database": "connected" if db_healthy else "disconnected",
            "vector_store": faiss_status["status"],
            "vector_store_vectors": faiss_status.get("total_vectors", 0),
            "llm_provider": "configured" if llm_status["api_key_configured"] else "fallback_mode",
            "llm_model": llm_status["model"],
        },
        "modules": {
            "auth": "active",
            "marketplace": "active",
            "orders": "active",
            "rag": "active" if faiss_healthy else "degraded",
            "multi_agent": "active",
            "support": "active",
            "observability": "active",
        },
    }

    return success_response(data=health_data, message="Health check complete")


@router.get(
    "/ready",
    summary="Readiness probe",
    response_description="Returns 200 if ready, 503 if not",
    tags=["Health"],
)
async def readiness_check():
    """
    Readiness probe for orchestrators (Kubernetes, Docker health checks, load balancers).

    Returns:
      - **HTTP 200** — application is ready to serve traffic
      - **HTTP 503** — one or more critical dependencies are unavailable

    Critical dependencies checked:
      - PostgreSQL database connection
      - FAISS vector index loaded in memory

    Non-critical (will not block readiness):
      - LLM API key (fallback mode available)
    """
    db_healthy = await check_database_connection()
    faiss_status = _get_faiss_status()
    faiss_ready = faiss_status["status"] == "loaded"

    is_ready = db_healthy and faiss_ready

    readiness_data = {
        "ready": is_ready,
        "checks": {
            "database": "pass" if db_healthy else "fail",
            "vector_store": "pass" if faiss_ready else "fail",
            "llm_api_key": "pass" if (settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip()) else "warn",
        },
        "environment": settings.ENVIRONMENT,
    }

    if not is_ready:
        return ORJSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Service not ready",
                "data": readiness_data,
            },
        )

    return success_response(data=readiness_data, message="Service ready")
