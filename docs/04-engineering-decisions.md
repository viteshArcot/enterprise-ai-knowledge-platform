# Engineering Decisions (Architecture Decision Records)

**Project:** Enterprise AI Knowledge Platform  
**Format:** Lightweight ADR (status, context, decision, consequences)  
**Last Updated:** July 2026

---

## ADR-001: Backend Framework — FastAPI over Django REST Framework

**Status:** Accepted  
**Date:** July 2026

### Context

We need an async-capable Python web framework that can handle high-throughput RAG queries, stream LLM responses, and maintain a clean API contract via OpenAPI.

### Decision

Use **FastAPI** with **Uvicorn** (ASGI).

### Rationale

| Criterion | FastAPI | Django REST Framework |
|---|---|---|
| Async support | Native (Python asyncio) | Third-party (channels, sync_to_async) |
| Type safety | First-class (Pydantic v2) | Manual serializers |
| OpenAPI generation | Automatic | Manual or drf-spectacular |
| Performance | ~3× faster than DRF | Slower (WSGI default) |
| Learning curve | Low for Python + Pydantic devs | Moderate |
| Ecosystem maturity | Modern, growing fast | Mature, stable |

**Against Flask/aiohttp:** FastAPI's built-in validation, dependency injection, and auto-generated docs reduce boilerplate significantly for an API-first product.

### Consequences

- (+) Automatic OpenAPI 3.1 docs at `/api/docs`
- (+) Pydantic validation at the boundary — no manual request parsing
- (+) First-class support for streaming responses (needed for Phase 3 LLM streaming)
- (-) Smaller ecosystem than Django (fewer third-party packages)
- (-) No built-in admin interface (not needed for this project)

---

## ADR-002: Database — PostgreSQL with pgvector over Dedicated Vector DB

**Status:** Accepted  
**Date:** July 2026

### Context

Phase 3 requires vector similarity search for semantic retrieval. Options considered:
1. PostgreSQL + `pgvector` extension
2. Pinecone (managed vector DB)
3. Weaviate (open-source vector DB)
4. Qdrant (open-source vector DB)

### Decision

Use **PostgreSQL 16** for all data, with **pgvector** for vector search in Phase 3.

### Rationale

At the expected scale (< 5 million document chunks in Year 1), pgvector with HNSW indexes provides sub-100ms similarity search — adequate for our SLO.

| Criterion | PostgreSQL + pgvector | Pinecone | Weaviate |
|---|---|---|---|
| Operational complexity | Low (one DB) | Low (managed SaaS) | Medium (self-hosted) |
| Cost | Minimal | $$$+ at scale | Free + compute |
| ACID transactions | Yes | No | No |
| Hybrid search (vector + BM25) | Yes (native FTS + pgvector) | No (requires hybrid setup) | Yes |
| Joins with relational data | Yes (native SQL) | No | Limited |
| Migration complexity | None | Requires data export | Requires data export |

**Key insight:** Adding a second data store doubles operational complexity (backups, monitoring, connection pooling, migrations). pgvector eliminates this until scale demands it.

### Consequences

- (+) Single database — one backup strategy, one monitoring setup, one schema migration system
- (+) Full SQL joins between vectors and relational data (document metadata, user data)
- (+) Transactional consistency during document ingestion
- (-) pgvector HNSW index is not as fast as purpose-built vector DBs at 100M+ vectors
- (-) Migration to Pinecone/Weaviate later would require data export tooling

**Revisit trigger:** If collection size exceeds 50M chunks OR if P95 search latency exceeds 500ms under load.

---

## ADR-003: ORM — SQLAlchemy 2 Async over Raw asyncpg

**Status:** Accepted  
**Date:** July 2026

### Context

The backend needs to interact with PostgreSQL asynchronously. Options:
1. Raw `asyncpg` (lowest level)
2. SQLAlchemy 2 with async sessions (ORM layer)
3. Databases + SQLAlchemy Core (hybrid)
4. Tortoise ORM (Django-like, async-native)

### Decision

Use **SQLAlchemy 2** with the asyncio extension and `asyncpg` as the driver.

### Rationale

- SQLAlchemy 2's `AsyncSession` + `async_sessionmaker` provides proper connection pool management with zero boilerplate
- The Repository pattern abstracts ORM details from business logic — engineers add repositories, not raw SQL
- Alembic (SQLAlchemy's migration tool) is the industry standard; its auto-generate feature makes schema migrations reliable
- Tortoise ORM is less mature and lacks Alembic integration

### Consequences

- (+) Alembic auto-generates migrations from model changes
- (+) Connection pooling managed by SQLAlchemy (not manual)
- (+) Query builder prevents SQL injection by construction
- (-) More complex than raw asyncpg for one-off scripts
- (-) `AsyncSession` requires explicit commit/rollback management (handled in `get_db_session` dependency)

---

## ADR-004: Configuration — Pydantic Settings v2 over dynaconf/python-decouple

**Status:** Accepted  
**Date:** July 2026

### Context

Application configuration must be:
- Loaded from environment variables (12-factor app compliance)
- Validated at startup (fail fast on misconfiguration)
- Type-safe throughout the codebase
- Testable (overridable in tests without patching)

### Decision

Use **Pydantic Settings v2** (`pydantic-settings`).

### Rationale

- Pydantic v2 validators give us type checking, regex validation, and min/max bounds on config values — free
- `lru_cache` on `get_settings()` ensures settings are parsed once and shared — no performance overhead
- Works seamlessly with FastAPI's `Depends()` system
- `.env` file loading is built in — no separate `load_dotenv()` call needed
- Tests can call `get_settings.cache_clear()` and set `os.environ` to override settings

### Consequences

- (+) Misconfigured deployments fail loudly at startup with a clear error
- (+) Settings are typed — `settings.DATABASE_POOL_SIZE` is an `int`, not a string
- (+) All configuration visible in one file with docstrings
- (-) Requires `pydantic-settings` as a dependency (small, no transitive deps)

---

## ADR-005: Logging — structlog over Python stdlib logging

**Status:** Accepted  
**Date:** July 2026

### Context

Production observability requires logs that are:
- Machine-parseable (JSON) for log aggregation (Datadog, CloudWatch, GCP Logging)
- Human-readable in development (colored, aligned)
- Context-aware (request ID, user ID automatically attached)

### Decision

Use **structlog** with a two-mode processor pipeline (JSON in production, console in development).

### Rationale

Python's stdlib `logging` module produces unstructured text. Parsing unstructured text in log aggregation systems requires fragile regex rules that break when log formats change. Structlog outputs one JSON object per line — parseable without configuration.

### Consequences

- (+) Zero-configuration log ingestion in Datadog/CloudWatch
- (+) Request IDs can be added via `structlog.contextvars.bind_contextvars()` — no thread-local hacks
- (+) Level filtering happens in structlog, not in log aggregation (cheaper)
- (-) One additional dependency
- (-) Slight learning curve for engineers unfamiliar with structlog

---

## ADR-006: Frontend Routing — React Router deferred to Phase 4

**Status:** Accepted  
**Date:** July 2026

### Context

Phase 1 has a single page (health dashboard). React Router would add complexity without benefit.

### Decision

Defer React Router installation to **Phase 4**, when authenticated and public route trees need to be defined simultaneously.

### Rationale

Installing a router in Phase 1 and leaving it configured with one route creates debt: future engineers must understand the routing config before making changes. A single-page app with no router is simpler and the refactor to add Router is mechanical (one file change in `App.tsx`).

### Consequences

- (+) Simpler Phase 1 codebase
- (+) No decisions locked in about hash vs history routing mode before requirements are clear
- (-) Cannot use `<Link>` components in Phase 1 (use `<a>` tags instead)

---

## ADR-007: Frontend Build Tool — Vite over Create React App / Next.js

**Status:** Accepted  
**Date:** July 2026

### Context

Phase 1 requires a React + TypeScript frontend. Options:
1. Create React App (CRA) — deprecated
2. Vite — fast build tool, official React template
3. Next.js — full-stack meta-framework with SSR/SSG

### Decision

Use **Vite** with the `react-ts` template.

### Rationale

- CRA is deprecated as of 2023 — eliminated immediately
- Next.js SSR is unnecessary overhead when the backend is a separate FastAPI service; we don't need server-side rendering
- Vite provides < 100ms HMR (Hot Module Replacement) vs Webpack's 1–5 seconds
- Vite's production build uses Rollup — mature, tree-shaking, excellent chunk splitting

### Consequences

- (+) Sub-100ms hot reload in development
- (+) Simple configuration — no webpack configuration files
- (+) First-class TypeScript support
- (-) If we ever need SSR (for SEO), migrating to Next.js is non-trivial
