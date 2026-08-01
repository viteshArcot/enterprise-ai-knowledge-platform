# =============================================================================
# Enterprise AI Knowledge Platform — Backend Dockerfile
# =============================================================================
# Multi-stage build:
#   Stage 1 (builder)  — Install all Python dependencies
#   Stage 2 (runtime)  — Lean production image with non-root user
#
# Security principles applied:
#   - Non-root user (appuser)
#   - Minimal base image (python:3.12-slim)
#   - No dev dependencies in production image
#   - HEALTHCHECK built into the image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Dependency builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# System dependencies required to build native Python extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the project definition first to leverage Docker layer caching.
# Rebuilds are fast if only application source changes.
COPY pyproject.toml .
RUN pip install --no-cache-dir setuptools wheel

# Install production dependencies into a prefix directory
RUN pip install --no-cache-dir --prefix=/install .


# -----------------------------------------------------------------------------
# Stage 2: Production runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Enterprise AI Knowledge Platform API"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Production API server"

# Install runtime-only system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root system user for security
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY --chown=appuser:appgroup app/ ./app/

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check uses the liveness endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production: single worker per container; scale horizontally via orchestration
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]
