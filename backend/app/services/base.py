"""Base service interface."""

import structlog

class BaseService:
    """Base class for all business logic services."""
    def __init__(self) -> None:
        self._logger = structlog.get_logger(self.__class__.__name__)
