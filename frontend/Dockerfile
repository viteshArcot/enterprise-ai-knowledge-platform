# =============================================================================
# Enterprise AI Knowledge Platform — Frontend Dockerfile
# =============================================================================
# Multi-stage build:
#   Stage 1 (builder)  — Node 20, builds the production Vite bundle
#   Stage 2 (runtime)  — nginx:alpine serves the static bundle
#
# The final image is ~25MB (nginx:alpine + static files only).
# No Node.js runtime in production.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer-cached separately from source code)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline

# Copy source and build
COPY frontend/ .
RUN npm run build


# -----------------------------------------------------------------------------
# Stage 2: Serve with nginx
# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="Enterprise AI Knowledge Platform Frontend"
LABEL org.opencontainers.image.version="0.1.0"

# Replace default nginx config with SPA-aware config
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
