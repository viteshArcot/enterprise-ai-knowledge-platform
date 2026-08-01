"""
Centralized structured logging configuration.

Why structlog?
--------------
Standard library `logging` is procedural and produces unstructured text.
structlog wraps it with a processor pipeline that:

  1. Attaches context variables (request ID, user ID) automatically
  2. Produces machine-readable JSON in production for log aggregation
  3. Produces colorized, aligned text in development for readability
  4. Integrates cleanly with asyncio and FastAPI middleware

Log format strategy:
  - Production (LOG_FORMAT=json):  One JSON object per line — feeds directly
    into Datadog, CloudWatch, GCP Logging, or Elastic without parsing rules.
  - Development (LOG_FORMAT=console): Human-readable colored output so
    developers can scan logs instantly during local work.

Evolution plan:
  - Phase 2: Add request_id context binding via FastAPI middleware
  - Phase 2: Add user_id context binding in authentication middleware
  - Phase 3: Add trace_id for distributed tracing (OpenTelemetry integration)
"""

import logging
import sys

import structlog

from app.config.settings import settings


def configure_logging() -> None:
    """
    Configure the structlog pipeline and standard library logging bridge.

    This function is idempotent — safe to call multiple times.
    It MUST be called during application startup (lifespan event) before
    any log messages are emitted.
    """
    shared_processors: list[structlog.types.Processor] = [
        # Merge any context variables bound via structlog.contextvars.bind_contextvars()
        # This is where request IDs, user IDs, etc. will be injected automatically.
        structlog.contextvars.merge_contextvars,
        # Add the logger name (module path) to every log event
        structlog.stdlib.add_logger_name,
        # Add the log level name to every log event
        structlog.stdlib.add_log_level,
        # Add ISO-8601 UTC timestamp to every log event
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Render exception tracebacks as strings (not Python objects)
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        # Production pipeline: outputs one JSON object per line
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development pipeline: colored, aligned, human-readable output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge standard library logging through structlog so third-party libraries
    # (SQLAlchemy, uvicorn, httpx) also produce structured output.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
        force=True,
    )

    # Suppress overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DATABASE_ECHO else logging.WARNING
    )
