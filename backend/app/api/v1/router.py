"""
API v1 router — aggregates all versioned endpoint routers.

How to add a new feature endpoint:
  1. Create backend/app/api/v1/endpoints/my_feature.py
  2. Define a router = APIRouter() in that module
  3. Import it here and call api_v1_router.include_router(...)

This file is the only place where routers are combined.
It keeps the route tree visible in one location.

Current routes (Phase 1):
  GET  /api/v1/health        — Liveness probe
  GET  /api/v1/health/ready  — Readiness probe

Planned routes:
  Phase 2: /api/v1/documents      — Document CRUD
  Phase 2: /api/v1/knowledge-bases — Knowledge base management
  Phase 3: /api/v1/search         — Hybrid semantic + keyword search
  Phase 4: /api/v1/auth           — Authentication (login, refresh, logout)
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_v1_router = APIRouter()

# ── Health ────────────────────────────────────────────────────────────────────
# No auth required. These endpoints are called by load balancers and monitoring.
api_v1_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

from app.api.v1.endpoints import documents, chat
api_v1_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_v1_router.include_router(chat.router, prefix="/conversations", tags=["Chat"])
