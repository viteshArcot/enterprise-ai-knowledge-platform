"""Failover LLM Gateway."""

from collections.abc import AsyncIterator

import structlog

from app.core.exceptions import ProviderFatalError, ProviderRetryableError
from app.providers.llm.base import LLMGateway, PromptMessage

logger = structlog.get_logger(__name__)


class FailoverLLMGateway(LLMGateway):
    """Wraps multiple LLM gateways and fails over on retryable errors."""

    def __init__(self, gateways: list[LLMGateway]) -> None:
        if not gateways:
            raise ValueError("FailoverLLMGateway requires at least one gateway.")
        self._gateways = gateways
        self.model_name = gateways[0].model_name  # Represents primary model

    async def complete(self, messages: list[PromptMessage]) -> str:
        """Collect a streamed response from the first successful gateway."""
        return "".join([part async for part in self.stream(messages)])

    async def stream(self, messages: list[PromptMessage]) -> AsyncIterator[str]:
        """Stream from the first successful gateway, failing over on errors."""
        last_error = None

        for idx, gateway in enumerate(self._gateways):
            try:
                logger.info(
                    "attempting_llm_generation",
                    model=gateway.model_name,
                    attempt=idx + 1,
                    total_gateways=len(self._gateways),
                )
                
                # If we successfully yield the first chunk, we commit to this gateway
                emitted_chunk = False
                
                async for chunk in gateway.stream(messages):
                    emitted_chunk = True
                    yield chunk
                
                # If we get here without exceptions, generation was successful
                logger.info(
                    "llm_generation_successful",
                    model=gateway.model_name,
                )
                return

            except ProviderFatalError as e:
                # Do not retry on 400, 401, 403, invalid prompt, etc.
                logger.error(
                    "llm_fatal_error",
                    model=gateway.model_name,
                    error=str(e),
                )
                raise

            except ProviderRetryableError as e:
                last_error = e
                # If we already yielded chunks, we can't cleanly fail over the stream
                if emitted_chunk:
                    logger.error(
                        "llm_error_during_stream",
                        model=gateway.model_name,
                        error=str(e),
                    )
                    raise
                
                # Otherwise, log and continue to the next gateway
                logger.warning(
                    "llm_provider_unavailable",
                    model=gateway.model_name,
                    error=str(e),
                    action="failing_over" if idx + 1 < len(self._gateways) else "exhausted_providers",
                )
                continue
            
            except Exception as e:
                # Treat unknown errors before streaming as retryable
                last_error = e
                if emitted_chunk:
                    logger.error(
                        "llm_unexpected_error_during_stream",
                        model=gateway.model_name,
                        error=str(e),
                    )
                    raise
                
                logger.warning(
                    "llm_unexpected_error",
                    model=gateway.model_name,
                    error=str(e),
                    action="failing_over" if idx + 1 < len(self._gateways) else "exhausted_providers",
                )
                continue

        # If we exhausted all gateways without success
        raise ProviderRetryableError(
            f"All LLM providers failed. Last error: {str(last_error)}"
        ) from last_error
