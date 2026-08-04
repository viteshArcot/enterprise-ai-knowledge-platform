"""OpenRouter streaming chat gateway."""

import json
from collections.abc import AsyncIterator

import httpx

from app.config.settings import Settings
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.providers.llm.base import LLMGateway, PromptMessage


class OpenRouterLLMGateway(LLMGateway):
    """Generate answers through OpenRouter while exposing a provider-neutral stream."""

    def __init__(self, config: Settings) -> None:
        if not config.OPENROUTER_API_KEY:
            raise ProviderError("OPENROUTER_API_KEY is required for OpenRouter chat.")
        self.api_key = config.OPENROUTER_API_KEY
        self.model_name = config.OPENROUTER_MODEL
        self.base_url = config.OPENROUTER_BASE_URL.rstrip("/")
        self._timeout = config.GEMINI_TIMEOUT_SECONDS
        self._retries = config.GEMINI_MAX_RETRIES

    async def complete(self, messages: list[PromptMessage]) -> str:
        """Collect a streamed OpenRouter response into one string."""
        return "".join([part async for part in self.stream(messages)])

    async def stream(self, messages: list[PromptMessage]) -> AsyncIterator[str]:
        """Yield text chunks from OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Enterprise AI Knowledge Platform",
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self._timeout,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                pass
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError() from exc
        except Exception as exc:
            raise ProviderError(f"OpenRouter chat request failed: {str(exc)}") from exc
