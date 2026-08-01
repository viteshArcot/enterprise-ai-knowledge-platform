"""
Pydantic schemas for health check API responses.

Why schemas separate from models?
  SQLAlchemy models represent database rows.
  Pydantic schemas represent API contracts (request/response shapes).
  Keeping them separate means:
    - Database schema changes don't break API consumers automatically
    - You can add computed fields, rename for clarity, or version schemas
      without touching database models
    - Clear separation of persistence concerns from transport concerns
"""

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """
    Status of a single external dependency.

    Used in the readiness probe to report on each dependency individually,
    allowing monitoring systems to pinpoint which dependency is failing.
    """

    status: str = Field(
        ...,
        description="'healthy' | 'unhealthy' | 'degraded'",
        examples=["healthy"],
    )
    detail: str | None = Field(
        default=None,
        description="Error message or additional context when status is not healthy.",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds for the dependency check.",
    )


class HealthResponse(BaseModel):
    """
    Liveness probe response body.

    Returned by GET /api/v1/health.
    This endpoint always returns 200 while the process is alive.
    """

    status: str = Field(
        ...,
        description="'healthy' | 'unhealthy'",
        examples=["healthy"],
    )
    environment: str = Field(
        ...,
        description="Deployment environment (development | staging | production).",
        examples=["development"],
    )
    version: str = Field(
        ...,
        description="Application version following semver.",
        examples=["0.1.0"],
    )
    uptime_seconds: float = Field(
        ...,
        description="Seconds elapsed since the process started.",
        examples=[42.5],
    )


class ReadinessResponse(BaseModel):
    """
    Readiness probe response body.

    Returned by GET /api/v1/health/ready.
    Returns 200 only when all critical dependencies are reachable.
    """

    status: str = Field(
        ...,
        description="'ready' | 'not_ready'",
        examples=["ready"],
    )
    dependencies: dict[str, DependencyStatus] = Field(
        default_factory=dict,
        description="Per-dependency health status keyed by dependency name.",
        examples=[{"api": {"status": "healthy"}, "database": {"status": "healthy"}}],
    )
