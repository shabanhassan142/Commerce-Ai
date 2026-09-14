# =============================================================================
# CommerceFlow AI — Backend Dockerfile
# =============================================================================
#
# Build:
#   docker build -t commerceflow-backend ./backend
#
# Run (standalone):
#   docker run -p 8000:8000 \
#     --env-file ./backend/.env \
#     -v $(pwd)/backend/faiss:/app/faiss:ro \
#     commerceflow-backend
#
# Notes:
#   - The FAISS index is NOT generated during build or startup.
#   - Mount the pre-built faiss/ directory as a READ-ONLY volume.
#   - If faiss/ is not mounted, RAG will be unavailable (graceful degradation).
#   - The application never runs as root (uses 'appuser').
# =============================================================================

FROM python:3.12-slim AS base

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Create non-root user ──────────────────────────────────────────────────────
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --home /app --shell /bin/bash appuser

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies first (layer cache) ───────────────────────────
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application code ──────────────────────────────────────────────────────
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# ── Create required runtime directories ───────────────────────────────────────
#    faiss/ is intentionally NOT copied here — it must be mounted as a volume.
#    If omitted, the app starts with degraded RAG (health/ready returns 503).
RUN mkdir -p logs uploads && \
    chown -R appuser:appgroup /app

# ── Switch to non-root user ────────────────────────────────────────────────────
USER appuser

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--no-access-log"]
