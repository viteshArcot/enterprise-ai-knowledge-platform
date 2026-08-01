# Development Roadmap

**Project:** Enterprise AI Knowledge Platform  
**Last Updated:** July 2026  
**Status:** Phase 1 complete → Phase 2 planning

---

## Phase Summary

| Phase | Name | Status | ETA |
|---|---|---|---|
| **Phase 1** | Engineering Foundation | ✅ Complete | July 2026 |
| **Phase 2** | Document Ingestion & Storage | 🔄 Planning | Q3 2026 |
| **Phase 3** | RAG Pipeline & Semantic Search | ⬜ Upcoming | Q4 2026 |
| **Phase 4** | Authentication & Multi-tenancy | ⬜ Upcoming | Q1 2027 |
| **Phase 5** | Evaluation, Observability & Scale | ⬜ Upcoming | Q2 2027 |

---

## Phase 1 — Engineering Foundation ✅

**Goal:** Establish a production-quality codebase foundation before adding any features.

### Delivered

- [x] Repository structure (monorepo: backend + frontend + docs + docker)
- [x] FastAPI application factory with lifespan events
- [x] Centralized Pydantic Settings v2 configuration
- [x] Structured JSON logging (structlog)
- [x] Global exception handlers with consistent error envelopes
- [x] Dependency injection architecture
- [x] Liveness and readiness health check endpoints
- [x] SQLAlchemy 2 Base + timestamp/UUID mixins
- [x] Repository pattern interfaces
- [x] Service layer base class
- [x] React + TypeScript + Vite frontend
- [x] Professional CSS design system
- [x] Centralized API client
- [x] Custom React hooks
- [x] Multi-stage Docker builds (backend + frontend)
- [x] Docker Compose (backend + frontend + PostgreSQL)
- [x] GitHub Actions CI (lint + test + build + docker)
- [x] `scripts/setup.sh` and `scripts/lint.sh`
- [x] Five engineering documentation files
- [x] Production-grade `.gitignore` and `.env.example`
- [x] MIT License, outstanding README

---

## Phase 2 — Document Ingestion & Storage

**Goal:** Allow users to upload documents and have them stored, parsed, and ready for retrieval.

**Estimated duration:** 4–6 weeks

### Technical work

- [ ] Alembic migration framework setup (`alembic init`, `env.py` async config)
- [ ] `Document` ORM model (id, title, source_url, file_type, status, metadata JSONB)
- [ ] `KnowledgeBase` ORM model (id, name, description, owner)
- [ ] `Chunk` ORM model (id, document_id, content, chunk_index, token_count)
- [ ] Concrete `SqlAlchemyDocumentRepository`
- [ ] Concrete `SqlAlchemyKnowledgeBaseRepository`
- [ ] `DocumentService.upload_document()` — validates, stores, triggers processing
- [ ] `DocumentService.list_documents()` — paginated listing per knowledge base
- [ ] File upload endpoint (`POST /api/v1/documents`) — multipart/form-data
- [ ] Document status endpoint (`GET /api/v1/documents/{id}`)
- [ ] Knowledge base CRUD (`/api/v1/knowledge-bases`)
- [ ] Document parser service (Unstructured.io integration)
- [ ] Background ingestion task (ARQ or Celery) for async processing
- [ ] PostgreSQL session middleware (`get_db_session` DI implementation)
- [ ] Database connectivity check in readiness probe
- [ ] Integration tests with a real PostgreSQL instance (Docker in CI)
- [ ] React: Document upload UI with drag-and-drop
- [ ] React: Knowledge base management page
- [ ] React: Document library with status indicators

### Architecture additions

```
app/
  ingestion/
    parser.py        # Format-agnostic document parser
    chunker.py       # Text chunking strategies
  workers/
    ingestion_worker.py  # Background document processing
  database/
    session.py       # Async session factory
    engine.py        # SQLAlchemy engine configuration
```

---

## Phase 3 — RAG Pipeline & Semantic Search

**Goal:** Users can ask natural language questions and receive grounded, cited answers.

**Estimated duration:** 6–8 weeks

### Technical work

- [ ] `pgvector` PostgreSQL extension enabled
- [ ] `Embedding` ORM model (id, chunk_id, vector, model_name, dimensions)
- [ ] `EmbeddingService` — wraps OpenAI / local embedding models
- [ ] Batch embedding pipeline for all ingested chunks
- [ ] Vector similarity search via pgvector (`<=>` cosine distance operator)
- [ ] BM25 / Full-text search for sparse retrieval (PostgreSQL `ts_vector`)
- [ ] Hybrid retrieval (dense + sparse, normalized RRF fusion)
- [ ] `LLMService` — provider-agnostic abstraction (OpenAI, Anthropic, Azure)
- [ ] RAG prompt template system
- [ ] Citation extraction from LLM response
- [ ] Query endpoint (`POST /api/v1/query`)
- [ ] Response streaming support (Server-Sent Events)
- [ ] React: Chat interface with streaming
- [ ] React: Source citation display with document preview
- [ ] React: Search history

### LLM provider abstraction

```python
class LLMProvider(Protocol):
    async def complete(self, prompt: str, context: list[Chunk]) -> LLMResponse: ...

class OpenAIProvider(LLMProvider): ...
class AnthropicProvider(LLMProvider): ...
class AzureOpenAIProvider(LLMProvider): ...
```

---

## Phase 4 — Authentication & Multi-tenancy

**Goal:** Production-ready security: JWT auth, SSO, RBAC, and tenant isolation.

**Estimated duration:** 4–6 weeks

### Technical work

- [ ] `User` ORM model (id, email, hashed_password, role, tenant_id)
- [ ] `Tenant` ORM model (id, name, slug, settings JSONB)
- [ ] JWT authentication (access + refresh tokens)
- [ ] OAuth 2.0 / OIDC integration (Google, Azure AD, Okta)
- [ ] RBAC middleware: `require_permission("knowledge_base:write")`
- [ ] Tenant isolation at the database row level (Row-Level Security or middleware)
- [ ] API key management (`ApiKey` model, hashed storage)
- [ ] Rate limiting per user and per tenant
- [ ] React: Login / logout flow
- [ ] React: User settings, API key management

---

## Phase 5 — Evaluation, Observability & Scale

**Goal:** Measure quality, observe production behavior, and scale to hundreds of concurrent users.

**Estimated duration:** 4–6 weeks

### Technical work

- [ ] RAG evaluation framework (RAGAS or custom: faithfulness, context precision)
- [ ] Human feedback loop (thumbs up/down on answers)
- [ ] Answer quality dashboard
- [ ] OpenTelemetry distributed tracing (FastAPI → PostgreSQL → LLM)
- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Grafana dashboard (request latency, LLM token usage, retrieval quality)
- [ ] Horizontal scaling (Kubernetes deployment manifests)
- [ ] Production PostgreSQL (connection pooler: PgBouncer)
- [ ] CDN configuration for frontend

---

## Engineering Principles Applied Every Phase

1. **No business logic in routes.** Routes validate, delegate, return.
2. **New features start with a failing test.** TDD where practical.
3. **No premature optimization.** Profile before optimizing.
4. **Migrations are forward-only.** No rollback migrations except in development.
5. **Feature flags for risky changes.** Never break the main branch.
6. **Document decisions in ADRs.** Future engineers deserve context.
