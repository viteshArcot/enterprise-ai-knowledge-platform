"""
Service layer — base interface and service registry.

Services contain ALL business logic. They are the heart of the application.
Everything above them (API routes) is transport layer.
Everything below them (repositories) is persistence layer.

Service rules (enforced during code review):
  ✓ Services MAY call repositories
  ✓ Services MAY call other services (via DI, not direct instantiation)
  ✓ Services MAY call external APIs (LLM providers, embedding APIs)
  ✗ Services MUST NOT import from app.api or reference FastAPI/HTTP concepts
  ✗ Services MUST NOT construct HTTP responses
  ✗ Services MUST NOT call the database directly (use repositories)
  ✗ Services MUST NOT be instantiated with `new` — use DI

Why a base class?
  Provides a hook for cross-cutting concerns:
    - Structured logging (every service gets a bound logger)
    - Metrics instrumentation (Phase 5)
    - Feature flag evaluation (Phase 4)

Evolution plan:
  Phase 2: Add DocumentService, KnowledgeBaseService
  Phase 3: Add SearchService, EmbeddingService
  Phase 4: Add AuthService, ApiKeyService
"""

import structlog


class BaseService:
    """
    Abstract base class for all application services.

    Provides a pre-configured structlog logger bound to the concrete class name.
    Subclasses should call super().__init__() to initialize the logger.

    Usage:
        class DocumentService(BaseService):
            def __init__(self, repo: DocumentRepository) -> None:
                super().__init__()
                self._repo = repo

            async def create_document(self, data: DocumentCreate) -> Document:
                # Business logic here
                ...
    """

    def __init__(self) -> None:
        self._logger = structlog.get_logger(type(self).__name__)
