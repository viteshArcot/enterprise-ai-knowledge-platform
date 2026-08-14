# =============================================================================
# Enterprise AI Knowledge Platform — Backend Dockerfile
# =============================================================================

# -----------------------------------------------------------------------------
# Production dependency builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir setuptools wheel

RUN pip install --no-cache-dir --prefix=/install .


# -----------------------------------------------------------------------------
# Test dependency builder
# -----------------------------------------------------------------------------
FROM builder AS test-builder

RUN pip install --no-cache-dir --prefix=/install ".[dev]"


# -----------------------------------------------------------------------------
# Test runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS test

LABEL org.opencontainers.image.title="Enterprise AI Knowledge Platform API (Test)"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

RUN mkdir -p /app/uploads && \
    chown appuser:appgroup /app/uploads

COPY --from=test-builder /install /usr/local

COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup tests/ ./tests/
COPY --chown=appuser:appgroup pyproject.toml .

USER appuser

CMD ["python", "-m", "pytest"]


# -----------------------------------------------------------------------------
# Production runtime
#
# IMPORTANT:
# This must remain the final Docker stage so a normal Docker build produces
# the production image rather than the test image.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Enterprise AI Knowledge Platform API"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Production API server"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

RUN mkdir -p /app/uploads && \
    chown appuser:appgroup /app/uploads

COPY --from=builder /install /usr/local

COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup alembic/ ./alembic/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/api/v1/health" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]