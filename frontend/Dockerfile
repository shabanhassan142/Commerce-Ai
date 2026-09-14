# =============================================================================
# CommerceFlow AI — Frontend Dockerfile (Multi-Stage)
# =============================================================================
#
# Stage 1 (builder): Installs Node dependencies and builds the Vite app.
# Stage 2 (runtime): Serves the static build with nginx:alpine.
#
# Build:
#   docker build -t commerceflow-frontend ./frontend \
#     --build-arg VITE_API_URL=http://your-backend-host/
#
# The VITE_API_URL build arg sets where the frontend points API calls.
# Leave empty ("") to use the nginx proxy (recommended for Docker Compose).
# =============================================================================

# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better layer caching
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

# Build args for environment configuration
# Leave empty to use nginx proxy (/api/ → backend container)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM nginx:alpine AS runtime

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config to avoid conflicts
RUN rm -f /etc/nginx/conf.d/default.conf.dpkg-old 2>/dev/null || true

# Copy nginx config (overwrite default)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
