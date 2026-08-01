# System Architecture

**Project:** Enterprise AI Knowledge Platform  
**Version:** 1.0 (Phase 1 baseline)  
**Status:** Phase 1 implemented  
**Last Updated:** July 2026

---

## 1. Architecture Overview

The platform follows **Clean Architecture** principles: business logic is isolated at the center, with infrastructure (database, HTTP, LLM providers) at the edges. The direction of dependency always points inward.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              nginx (SPA Server / Reverse Proxy)                  │
│              React + TypeScript + Vite                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP / REST
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  API Layer (Routes / Schemas / Exception Handlers)      │   │
│  │  — Thin. No business logic. Validates input, returns    │   │
│  │    output. Delegates everything to the service layer.   │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │  Service Layer (Business Logic)                         │   │
│  │  — Orchestrates repositories, applies domain rules,     │   │
│  │    coordinates between multiple data sources.           │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │  Repository Layer (Data Access)                         │   │
│  │  — Abstract interface. Concrete impl uses SQLAlchemy.   │   │
│  │    All SQL lives here. Services never touch ORM.        │   │
│  └─────────────────────┬───────────────────────────────────┘   │
└────────────────────────┼────────────────────────────────────────┘
                         │
          ┌──────────────┼────────────────┐
          ▼              ▼                ▼
    ┌──────────┐  ┌─────────────┐  ┌──────────────┐
    │PostgreSQL│  │Vector Store │  │  LLM API     │
    │  (SQLAlc)│  │(pgvector /  │  │(OpenAI /     │
    │          │  │ Pinecone)   │  │ Anthropic)   │
    └──────────┘  └─────────────┘  └──────────────┘
                  (Phase 3)         (Phase 2)
```

---

## 2. Component Descriptions

### 2.1 Frontend (React + Vite)

| Concern | Implementation |
|---|---|
| Framework | React 19 (functional components, hooks) |
| Language | TypeScript (strict mode) |
| Build tool | Vite 8 |
| State management | Local state (Phase 1); React Query Phase 2+ |
| HTTP client | Native `fetch` via centralized `apiClient` |
| Styling | Vanilla CSS with design tokens |
| Deployment | nginx:alpine container |

**Directory structure:**
```
src/
  components/    # Reusable UI components
  pages/         # Route-level components
  hooks/         # Custom React hooks (data fetching, state)
  services/      # API client, external service wrappers
  assets/        # Static images and fonts
```

### 2.2 Backend (FastAPI)

| Concern | Implementation |
|---|---|
| Framework | FastAPI 0.115+ (ASGI) |
| Language | Python 3.12 |
| Validation | Pydantic v2 |
| Configuration | Pydantic Settings v2 (env vars) |
| Logging | Structlog (JSON / console) |
| ORM | SQLAlchemy 2 (async via asyncpg) |
| Migrations | Alembic (Phase 2) |
| Server | Uvicorn (with Gunicorn in production Phase 3+) |

**Clean Architecture layers:**
```
app/
  api/           # HTTP: routes, request/response schemas, exception handlers
  config/        # Pydantic Settings — all environment configuration
  core/          # Cross-cutting: logging, exceptions, DI providers
  services/      # Business logic — orchestrates repositories
  repositories/  # Data access — all database queries live here
  models/        # SQLAlchemy ORM models
  schemas/       # Pydantic API schemas (separate from ORM models)
  ingestion/     # Document processing pipeline (Phase 2+)
```

### 2.3 Database (PostgreSQL 16)

PostgreSQL was chosen as the primary data store because:
- pgvector extension provides native vector similarity search (Phase 3)
- Eliminates the need for a separate vector database in Phase 3
- ACID transactions for reliable document ingestion
- Mature ecosystem, excellent async support via asyncpg
- Well-understood operational characteristics

### 2.4 Infrastructure

| Component | Phase 1 | Phase 3+ |
|---|---|---|
| Container runtime | Docker + Compose | Kubernetes / ECS |
| Reverse proxy | nginx (frontend only) | nginx / ALB |
| Secret management | .env file | AWS Secrets Manager / Vault |
| CI/CD | GitHub Actions | GitHub Actions + deployment jobs |

---

## 3. Data Flow — Phase 3 (Reference)

```
User Query
    │
    ▼
API Layer (FastAPI)
    │  validate & route
    ▼
QueryService
    │  1. Embed query (EmbeddingService → OpenAI text-embedding-3-small)
    │  2. Retrieve top-K chunks (VectorRepository → pgvector)
    │  3. Retrieve sparse candidates (BM25Repository → PostgreSQL FTS)
    │  4. Re-rank results (RerankService → Cohere / cross-encoder)
    │  5. Generate answer (LLMService → OpenAI GPT-4o)
    │
    ▼
API Response (answer + citations + sources)
```

---

## 4. Deployment Architecture (Phase 3 Target)

```
Internet
    │
    ▼
Load Balancer (AWS ALB / GCP HTTPS LB)
    │
    ├── /api/*  ──► Backend pods (2–10 replicas, auto-scaling)
    │                    │
    │                    └── PostgreSQL (managed: RDS / Cloud SQL)
    │
    └── /*      ──► Frontend CDN (CloudFront / Cloud CDN)
                        └── S3 / GCS (static assets)
```

---

## 5. Security Architecture

| Layer | Control |
|---|---|
| Transport | TLS 1.2+ everywhere |
| Authentication | JWT (Phase 4): short-lived access + refresh tokens |
| Authorization | RBAC: Viewer / Editor / Admin per Knowledge Base |
| API | Rate limiting per user/IP (Phase 4) |
| Secrets | Never in code or logs; env vars → secrets manager |
| Container | Non-root user; read-only filesystem where possible |
| Database | Connection pool user has SELECT/INSERT/UPDATE/DELETE only |

---

## 6. Architecture Decision Records

See [04-engineering-decisions.md](./04-engineering-decisions.md) for full ADRs.

| Decision | Choice | Alternatives Considered |
|---|---|---|
| Backend framework | FastAPI | Django REST, Flask, aiohttp |
| Database | PostgreSQL + pgvector | Separate Pinecone/Weaviate |
| ORM | SQLAlchemy 2 async | raw asyncpg, Tortoise ORM |
| Configuration | Pydantic Settings v2 | dynaconf, python-decouple |
| Logging | structlog | Python stdlib logging |
| Frontend | React + TypeScript + Vite | Next.js, SvelteKit |
