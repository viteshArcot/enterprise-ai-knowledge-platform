"""Gemini streaming chat gateway."""

import asyncio
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.config.settings import Settings
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.providers.llm.base import LLMGateway, PromptMessage


class GeminiLLMGateway(LLMGateway):
    """Generate answers through Gemini while exposing a provider-neutral stream."""

    def __init__(self, config: Settings) -> None:
        if not config.GEMINI_API_KEY:
            raise ProviderError("GEMINI_API_KEY is required for chat.")
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = config.GEMINI_CHAT_MODEL
        self._timeout = config.GEMINI_TIMEOUT_SECONDS
        self._retries = config.GEMINI_MAX_RETRIES

    async def complete(self, messages: list[PromptMessage]) -> str:
        """Collect a streamed Gemini response into one string."""
        return "".join([part async for part in self.stream(messages)])

    async def stream(self, messages: list[PromptMessage]) -> AsyncIterator[str]:
        """Yield Gemini text chunks with retry handling before first output."""
        system = next((message.content for message in messages if message.role == "system"), None)
        contents = [
            types.Content(role="model" if message.role == "assistant" else "user", parts=[types.Part(text=message.content)])
            for message in messages
            if message.role != "system"
        ]
        for attempt in range(self._retries + 1):
            emitted = False
            try:
                stream = await asyncio.wait_for(
                    self._client.aio.models.generate_content_stream(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(system_instruction=system),
                    ),
                    timeout=self._timeout,
                )
                async for response in stream:
                    if response.text:
                        emitted = True
                        yield response.text
                return
            except TimeoutError as exc:
                if emitted or attempt == self._retries:
                    raise ProviderTimeoutError() from exc
            except Exception as exc:
                if emitted or attempt == self._retries:
                    raise ProviderError("Gemini chat request failed.") from exc
            await asyncio.sleep(2**attempt)
