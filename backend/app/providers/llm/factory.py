"""Factory for creating the configured LLM provider."""

import structlog

from app.config.settings import Settings
from app.providers.llm.base import LLMGateway
from app.providers.llm.gemini import GeminiLLMGateway
from app.providers.llm.openrouter import OpenRouterLLMGateway
from app.providers.llm.ollama import OllamaLLMGateway

logger = structlog.get_logger(__name__)


def create_llm_gateway(config: Settings) -> LLMGateway:
    """
    Returns the configured chat provider.

    Embeddings remain Gemini.
    Chat can be:
        - Gemini
        - OpenRouter
        - Ollama
    """

    logger.info(
        "llm_provider_selected",
        provider=config.LLM_PROVIDER,
    )

    if config.LLM_PROVIDER == "openrouter":
        logger.info(
            "using_openrouter",
            model=config.OPENROUTER_MODEL,
        )
        return OpenRouterLLMGateway(config)

    if config.LLM_PROVIDER == "ollama":
        logger.info(
            "using_ollama",
            base_url=config.OLLAMA_BASE_URL,
        )
        return OllamaLLMGateway(config)

    logger.info(
        "using_gemini",
        model=config.GEMINI_CHAT_MODEL,
    )

    return GeminiLLMGateway(config)