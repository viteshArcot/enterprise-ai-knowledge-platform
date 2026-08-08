"""Factory for creating the configured LLM provider."""

import structlog

from app.config.settings import Settings
from app.providers.llm.base import LLMGateway
from app.providers.llm.gemini import GeminiLLMGateway
from app.providers.llm.openrouter import OpenRouterLLMGateway
from app.providers.llm.failover import FailoverLLMGateway

logger = structlog.get_logger(__name__)


def create_llm_gateway(config: Settings) -> LLMGateway:
    """
    Returns the configured chat provider wrapped in a FailoverLLMGateway.

    Priority:
        1. Gemini 3.5 Flash Lite
        2. Gemini 3.1 Flash Lite
        3. OpenRouter Nemotron 3 Ultra (free)
    """

    gateways = []

    if config.GEMINI_API_KEY:
        # 1. Gemini 3.5 Flash Lite
        config_3_5 = config.model_copy(update={"GEMINI_CHAT_MODEL": "gemini-3.5-flash-lite"})
        gateways.append(GeminiLLMGateway(config_3_5))

        # 2. Gemini 3.1 Flash Lite
        config_3_1 = config.model_copy(update={"GEMINI_CHAT_MODEL": "gemini-3.1-flash-lite"})
        gateways.append(GeminiLLMGateway(config_3_1))

    if config.OPENROUTER_API_KEY:
        # 3. OpenRouter Nemotron 3 Ultra
        config_or = config.model_copy(update={"OPENROUTER_MODEL": "nvidia/nemotron-3-ultra-550b-a55b:free"})
        gateways.append(OpenRouterLLMGateway(config_or))

    if not gateways:
        logger.warning("No LLM API keys provided. Chat generation will fail.")
        # Fallback to a dummy if none are provided, though the app will fail on generation.
        # Alternatively, we could let it fail or just create one without keys that will fail fast.
        # Let's just create a default Gemini one which will throw an error immediately if no keys.
        return GeminiLLMGateway(config)

    logger.info(
        "failover_llm_gateway_configured",
        primary_model=gateways[0].model_name,
        total_gateways=len(gateways),
    )

    return FailoverLLMGateway(gateways)