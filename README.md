<div align="center">

# ⬡ Enterprise AI Knowledge Platform

### Production-grade AI-powered knowledge management infrastructure

[![CI](https://github.com/your-username/enterprise-ai-knowledge-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/enterprise-ai-knowledge-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**[Documentation](./docs) · [API Reference](./docs/05-api-design.md) · [Architecture](./docs/02-system-architecture.md) · [Roadmap](./docs/03-development-roadmap.md)**

</div>

---

## Overview

The Enterprise AI Knowledge Platform is a production-grade system that enables organizations to query their proprietary knowledge — documents, policies, runbooks, specifications — using natural language. It combines a Retrieval-Augmented Generation (RAG) pipeline with enterprise-grade infrastructure: Clean Architecture, async PostgreSQL, structured logging, and multi-tenant security.

This repository represents the flagship AI engineering portfolio project: built with the same architectural discipline, documentation standards, and engineering practices expected at a Staff Engineer level at companies like Google, Anthropic, Databricks, or ServiceNow.

**Current status:** Phase 1 (Engineering Foundation) complete. Phase 2 (Document Ingestion) in planning.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    React + TypeScript + Vite                      │
│              (Dark-mode SPA with live health dashboard)           │
└─────────────────────────┬────────────────────────────────────────┘
                          │ REST/JSON
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI (Python 3.12)                       │
│                                                                   │
│   API Routes (thin)  →  Services (logic)  →  Repositories (SQL)  │
│                                                                   │
│   ● Pydantic Settings v2    ● Structlog JSON    ● DI via Depends │
└─────────────────────────┬────────────────────────────────────────┘
                          │ asyncpg
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                 PostgreSQL 16 + pgvector (Phase 3)                │
└──────────────────────────────────────────────────────────────────┘
```

Clean Architecture is strictly enforced:
- **Routes** contain no business logic — they validate input and delegate
- **Services** own all business logic — no HTTP concepts allowed
- **Repositories** own all database access — services never touch SQLAlchemy directly
- **Configuration** is centralized in `app/config/settings.py`
- **Logging** is centralized in `app/core/logging.py`

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **API framework** | FastAPI 0.115 | Native async, automatic OpenAPI, Pydantic integration |
| **Language** | Python 3.12 | Latest type system features, performance improvements |
| **Data validation** | Pydantic v2 | 5–50× faster than v1, strict type enforcement |
| **Configuration** | Pydantic Settings v2 | Type-safe env vars, fail-fast at startup |
| **ORM** | SQLAlchemy 2 (async) | Industry standard, excellent Alembic migration support |
| **Database** | PostgreSQL 16 | ACID, pgvector for Phase 3 semantic search |
| **Logging** | structlog | JSON in production, colored console in development |
| **ASGI server** | Uvicorn | High-performance async server |
| **Frontend** | React 19 + TypeScript | Type-safe UI with hooks |
| **Build tool** | Vite 8 | Sub-100ms HMR, Rollup production bundles |
| **Container** | Docker + Compose | Reproducible local environment |
| **Linting (Python)** | Ruff + Black | Ruff replaces flake8+isort; Black for formatting |
| **Linting (TS)** | oxlint + Prettier | TypeScript-aware linting + formatting |
| **Testing** | pytest-asyncio | Async test support with ASGITransport |
| **CI** | GitHub Actions | Lint → Test → Build → Docker |

---

## Repository Structure

```
enterprise-ai-knowledge-platform/
│
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   └── health.py       # GET /health, GET /health/ready
│   │   │   └── router.py           # Route aggregator
│   │   ├── config/
│   │   │   └── settings.py         # Pydantic Settings v2 (all env vars)
│   │   ├── core/
│   │   │   ├── dependencies.py     # FastAPI DI providers
│   │   │   ├── exceptions.py       # Exception hierarchy + handlers
│   │   │   └── logging.py          # structlog configuration
│   │   ├── models/
│   │   │   └── base.py             # SQLAlchemy Base + UUID/Timestamp mixins
│   │   ├── repositories/
│   │   │   └── __init__.py         # Abstract BaseRepository[T]
│   │   ├── schemas/
│   │   │   └── health.py           # Pydantic response schemas
│   │   ├── services/
│   │   │   └── __init__.py         # Abstract BaseService
│   │   ├── ingestion/              # Document pipeline (Phase 2)
│   │   └── main.py                 # Application factory
│   ├── tests/
│   │   ├── conftest.py             # Shared fixtures + env setup
│   │   └── test_health.py          # Health endpoint tests (12 tests)
│   ├── Dockerfile                  # Multi-stage production build
│   └── pyproject.toml              # All tooling config (Ruff, Black, pytest)
│
├── frontend/                       # React application
│   ├── src/
│   │   ├── components/
│   │   │   └── StatusCard.tsx      # Reusable health status component
│   │   ├── hooks/
│   │   │   └── useHealth.ts        # Custom hook for API health data
│   │   ├── pages/
│   │   │   └── Home.tsx            # Main dashboard page
│   │   ├── services/
│   │   │   └── api.ts              # Centralized HTTP client
│   │   ├── App.tsx                 # Root component
│   │   └── App.css                 # Design system (CSS tokens)
│   ├── Dockerfile                  # Multi-stage: Node builder + nginx
│   └── .prettierrc                 # Prettier configuration
│
├── docker/
│   ├── nginx.conf                  # SPA-aware nginx config
│   └── postgres/
│       └── init.sql                # DB init (pgcrypto extension)
│
├── scripts/
│   ├── setup.sh                    # One-command dev environment setup
│   └── lint.sh                     # Run all linters (--fix mode available)
│
├── docs/
│   ├── 01-product-requirements.md  # PRD: users, requirements, metrics
│   ├── 02-system-architecture.md   # Architecture diagrams + component descriptions
│   ├── 03-development-roadmap.md   # Phase-by-phase task breakdown
│   ├── 04-engineering-decisions.md # 7 ADRs with alternatives and tradeoffs
│   └── 05-api-design.md            # API conventions, error envelopes, schemas
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # 5-job CI pipeline
│
├── docker-compose.yml              # Orchestrates backend + frontend + PostgreSQL
├── .env.example                    # All env vars documented with comments
├── .gitignore                      # Python + Node + Docker + IDE + OS
├── LICENSE                         # MIT
└── README.md                       # This file
```

---

## Quick Start

### Option 1: Docker (recommended)

The fastest way to get the full stack running.

```bash
# 1. Clone and enter the repository
git clone https://github.com/your-username/enterprise-ai-knowledge-platform.git
cd enterprise-ai-knowledge-platform

# 2. Create environment file
cp .env.example .env

# 3. Generate a secure secret key and set it in .env
#    Linux/macOS:
openssl rand -hex 32
#    Windows (PowerShell):
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
# Then: edit .env and set SECRET_KEY=<generated value>

# 4. Build and start all services
docker compose up --build

# Services:
#   API:       http://localhost:8000
#   API docs:  http://localhost:8000/api/docs
#   Frontend:  http://localhost:3000
#   Database:  localhost:5432
```

### Option 2: Local Development

For a faster feedback loop with hot reload.

```bash
# 1. Run the automated setup script (checks prerequisites, creates venv, installs deps)
bash scripts/setup.sh

# 2. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and ensure DATABASE_URL points to a running PostgreSQL

# 3. Start PostgreSQL (via Docker)
docker compose up db -d

# 4. Start backend (in one terminal)
cd backend
# Linux/macOS:
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Windows (PowerShell):
# .venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start frontend (in another terminal)
cd frontend
npm run dev
```

---

## Development

### Backend

```bash
cd backend

# Install all dependencies (including dev extras: pytest, ruff, black)
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Lint and format
ruff check .          # Check for issues
ruff check . --fix    # Auto-fix where possible
black .               # Format code
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Type-check
npm run build

# Lint
npm run lint
```

### Monorepo

```bash
# Run all linters (check only)
bash scripts/lint.sh

# Run all linters with auto-fix
bash scripts/lint.sh --fix
```

---

## API Reference

### Health Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | None | Liveness probe — is the process alive? |
| `GET` | `/api/v1/health/ready` | None | Readiness probe — can it serve traffic? |

**Example:**

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "uptime_seconds": 42.5
}
```

Full API reference: [docs/05-api-design.md](./docs/05-api-design.md)  
Interactive docs: `http://localhost:8000/api/docs` (development only)

---

## Roadmap

| Phase | Features | Status |
|---|---|---|
| **Phase 1** | Engineering Foundation (this release) | ✅ Complete |
| **Phase 2** | Document ingestion, PostgreSQL CRUD, Alembic migrations | 🔄 Planning |
| **Phase 3** | RAG pipeline, pgvector semantic search, LLM integration | ⬜ Upcoming |
| **Phase 4** | JWT auth, OAuth SSO, RBAC, multi-tenancy | ⬜ Upcoming |
| **Phase 5** | Evaluation framework, OpenTelemetry, Kubernetes | ⬜ Upcoming |

See the full roadmap: [docs/03-development-roadmap.md](./docs/03-development-roadmap.md)

---

## Project Status

```
Phase 1 — Engineering Foundation

  ✓ Repository structure          ✓ Structured logging (structlog)
  ✓ FastAPI application factory   ✓ Global exception handlers
  ✓ Centralized configuration     ✓ Dependency injection architecture
  ✓ Health check endpoints        ✓ SQLAlchemy Base + mixins
  ✓ Repository pattern            ✓ Service layer base
  ✓ React + TypeScript + Vite     ✓ Professional CSS design system
  ✓ Multi-stage Docker builds     ✓ Docker Compose (3 services)
  ✓ GitHub Actions CI             ✓ Five engineering docs
  ✓ Production .gitignore         ✓ .env.example (documented)
  ✓ MIT License                   ✓ 24 passing tests
```

---

## Engineering Decisions

Key architectural choices and their rationale are documented as ADRs:

| Decision | Choice |
|---|---|
| Backend framework | FastAPI (async, auto-OpenAPI, Pydantic native) |
| Primary database | PostgreSQL + pgvector (avoids separate vector DB until scale demands it) |
| ORM | SQLAlchemy 2 async (Alembic migrations, connection pooling) |
| Configuration | Pydantic Settings v2 (type-safe, fail-fast, testable) |
| Logging | structlog (JSON in production, colored console in development) |
| Frontend | Vite (not Next.js — SSR adds unnecessary complexity for an API-backend project) |

Full ADRs: [docs/04-engineering-decisions.md](./docs/04-engineering-decisions.md)

---

## Contributing

This project follows standard GitHub flow:

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feat/your-feature-name`
3. Make changes — follow the architecture principles in [docs/02-system-architecture.md](./docs/02-system-architecture.md)
4. **Run the CI checks locally:**
   ```bash
   bash scripts/lint.sh
   cd backend && pytest
   cd frontend && npm run build
   ```
5. Commit with a conventional message: `feat: add document upload endpoint`
6. Open a **pull request** against `develop`

### Code Standards

- **Backend:** No business logic in routes. Types on all function signatures. Docstrings on all public functions.
- **Frontend:** No API calls outside `src/services/`. Props must be typed. No `any`.
- **Tests:** Descriptive test names that read as sentences. One assertion per test.

---

## License

MIT — see [LICENSE](./LICENSE) for details.

---

<div align="center">

Built with discipline. Documented with care. Designed to scale.

</div>
