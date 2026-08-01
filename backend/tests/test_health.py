"""
Health endpoint tests.

Tests for GET /api/v1/health (liveness) and GET /api/v1/health/ready (readiness).

Test naming convention:
  test_<endpoint>_<scenario>_<expected_outcome>

Each test verifies one behavior. Avoid testing multiple assertions per test
unless they are inherently coupled (e.g., status code + response body).
"""

import pytest
from httpx import AsyncClient

# =============================================================================
# Liveness probe — GET /api/v1/health
# =============================================================================


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """Liveness probe must always return HTTP 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_has_status_field(client: AsyncClient) -> None:
    """Response must include a 'status' field."""
    response = await client.get("/api/v1/health")
    assert "status" in response.json()


@pytest.mark.asyncio
async def test_health_status_is_healthy(client: AsyncClient) -> None:
    """Status field must be 'healthy' while process is running."""
    response = await client.get("/api/v1/health")
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_response_includes_version(client: AsyncClient) -> None:
    """Response must include API version for traceability."""
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_health_response_includes_environment(client: AsyncClient) -> None:
    """Response must include the deployment environment."""
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "environment" in data
    assert data["environment"] in {"development", "staging", "production"}


@pytest.mark.asyncio
async def test_health_response_includes_uptime(client: AsyncClient) -> None:
    """Response must include process uptime in seconds."""
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_health_content_type_is_json(client: AsyncClient) -> None:
    """Response Content-Type must be application/json."""
    response = await client.get("/api/v1/health")
    assert "application/json" in response.headers["content-type"]


# =============================================================================
# Readiness probe — GET /api/v1/health/ready
# =============================================================================


@pytest.mark.asyncio
async def test_readiness_returns_200(client: AsyncClient) -> None:
    """Readiness probe must return 200 when all dependencies are healthy."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_readiness_response_has_status_field(client: AsyncClient) -> None:
    """Readiness response must include a 'status' field."""
    response = await client.get("/api/v1/health/ready")
    assert "status" in response.json()


@pytest.mark.asyncio
async def test_readiness_status_is_ready(client: AsyncClient) -> None:
    """Status must be 'ready' when Phase 1 dependencies are all healthy."""
    response = await client.get("/api/v1/health/ready")
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_response_has_dependencies(client: AsyncClient) -> None:
    """Readiness response must include a 'dependencies' map."""
    response = await client.get("/api/v1/health/ready")
    data = response.json()
    assert "dependencies" in data
    assert isinstance(data["dependencies"], dict)


@pytest.mark.asyncio
async def test_readiness_api_dependency_is_healthy(client: AsyncClient) -> None:
    """The 'api' dependency must report as healthy in Phase 1."""
    response = await client.get("/api/v1/health/ready")
    deps = response.json()["dependencies"]
    assert "api" in deps
    assert deps["api"]["status"] == "healthy"
