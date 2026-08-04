"""Ollama streaming chat gateway."""

import json
from collections.abc import AsyncIterator

import httpx

from app.config.settings import Settings
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.providers.llm.base import LLMGateway, PromptMessage


class OllamaLLMGateway(LLMGateway):
    """Generate answers through Ollama while exposing a provider-neutral stream."""

    def __init__(self, config: Settings) -> None:
        self.base_url = config.OLLAMA_BASE_URL.rstrip("/")
        self.model_name = config.GEMINI_CHAT_MODEL  # Assumes OLLAMA has this model name or similar mapping
        self._timeout = config.GEMINI_TIMEOUT_SECONDS
        self._retries = config.GEMINI_MAX_RETRIES

    async def complete(self, messages: list[PromptMessage]) -> str:
        """Collect a streamed Ollama response into one string."""
        return "".join([part async for part in self.stream(messages)])

    async def stream(self, messages: list[PromptMessage]) -> AsyncIterator[str]:
        """Yield text chunks from Ollama."""
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self._timeout,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data:
                                    content = data["message"].get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                pass
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError() from exc
        except Exception as exc:
            raise ProviderError(f"Ollama chat request failed: {str(exc)}") from exc
