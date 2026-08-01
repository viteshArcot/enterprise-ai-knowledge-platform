"""
Health check endpoints.

Provides two probes required by every production container deployment:

  GET /api/v1/health        — Liveness probe
  GET /api/v1/health/ready  — Readiness probe

Liveness vs Readiness (Kubernetes semantics):
  - Liveness:  "Is the process alive?" — if this fails, the container restarts.
               Checks process health only. Never checks external dependencies.
  - Readiness: "Can this instance serve traffic?" — if this fails, the instance
               is temporarily removed from the load balancer rotation.
               Checks ALL critical external dependencies (database, etc.).

Design rules:
  - Both endpoints MUST NOT require authentication
  - Liveness MUST be extremely fast (no I/O)
  - Readiness MAY be slightly slower (network I/O to check dependencies)
  - Both MUST return structured JSON

Evolution plan:
  Phase 2: Add database connectivity check to readiness probe
  Phase 3: Add vector store connectivity check
"""

import time

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.schemas.health import DependencyStatus, HealthResponse, ReadinessResponse

logger = structlog.get_logger(__name__)

router = APIRouter()

# Captured at module import time — used to compute process uptime
_PROCESS_START: float = time.monotonic()


# =============================================================================
# Liveness probe
# =============================================================================


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description=(
        "Returns HTTP 200 if the application process is running. "
        "Used by container orchestration to determine if the container should be restarted. "
        "**Does not check external dependencies.**"
    ),
    operation_id="health_check",
)
async def health_check() -> HealthResponse:
    """
    Liveness probe — no external I/O.

    Response time should be <10ms. No database or network calls.
    """
    logger.debug("liveness_probe_called")
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.API_VERSION,
        uptime_seconds=round(time.monotonic() - _PROCESS_START, 3),
    )


# =============================================================================
# Readiness probe
# =============================================================================


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Returns HTTP 200 only if the application is ready to serve traffic. "
        "Returns HTTP 503 if any critical dependency is unavailable. "
        "Used by load balancers to determine if traffic should be routed to this instance."
    ),
    operation_id="readiness_check",
)
async def readiness_check() -> JSONResponse:
    """
    Readiness probe — checks external dependency connectivity.

    Returns 200 if ALL critical dependencies are healthy.
    Returns 503 if ANY critical dependency is degraded or unreachable.
    """
    dependencies: dict[str, DependencyStatus] = {}
    all_ready = True

    # ── API process ──────────────────────────────────────────────────────────
    # Always healthy if this code is executing
    dependencies["api"] = DependencyStatus(status="healthy")

    # ── Database (Phase 2) ───────────────────────────────────────────────────
    # Uncomment and implement when async engine is configured in Phase 2:
    #
    # db_start = time.monotonic()
    # try:
    #     async with async_session_factory() as session:
    #         await session.execute(text("SELECT 1"))
    #     dependencies["database"] = DependencyStatus(
    #         status="healthy",
    #         latency_ms=round((time.monotonic() - db_start) * 1000, 2),
    #     )
    # except Exception as exc:
    #     all_ready = False
    #     dependencies["database"] = DependencyStatus(
    #         status="unhealthy",
    #         detail=str(exc),
    #         latency_ms=round((time.monotonic() - db_start) * 1000, 2),
    #     )
    #     logger.warning("readiness_database_check_failed", error=str(exc))

    response = ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        dependencies=dependencies,
    )

    http_status = (
        status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    logger.debug("readiness_probe_called", overall_status=response.status)

    return JSONResponse(
        status_code=http_status,
        content=response.model_dump(),
    )
