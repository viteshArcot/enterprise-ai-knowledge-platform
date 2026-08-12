import pytest
from httpx import Response
from unittest.mock import AsyncMock, patch

from app.config.settings import Settings
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.providers.embedding.openrouter import OpenRouterEmbeddingGateway

@pytest.fixture
def mock_settings():
    return Settings(
        OPENROUTER_API_KEY="test_key",
        OPENROUTER_EMBEDDING_MODEL="test-model",
        OPENROUTER_EMBEDDING_DIMENSIONS=2048,
        GEMINI_MAX_RETRIES=0
    )

@pytest.fixture
def gateway(mock_settings):
    return OpenRouterEmbeddingGateway(mock_settings)

@pytest.mark.asyncio
async def test_normal_text_embedding(gateway):
    inputs = ["Test string 1", "Test string 2"]
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"index": 0, "embedding": [0.1] * 2048},
                {"index": 1, "embedding": [0.2] * 2048}
            ]
        }
        mock_post.return_value = mock_response
        
        result = await gateway.embed(inputs)
        
        # Verify result
        assert len(result) == 2
        assert len(result[0]) == 2048
        
        # Verify payload shape
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["input"] == ["Test string 1", "Test string 2"]

@pytest.mark.asyncio
async def test_single_multimodal_request(gateway):
    inputs = [
        [
            {"type": "text", "text": "What is this?"},
            {"type": "image_url", "image_url": {"url": "data:..."}}
        ]
    ]
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"index": 0, "embedding": [0.3] * 2048}]
        }
        mock_post.return_value = mock_response
        
        await gateway.embed(inputs)
        
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        # Should be wrapped in "content" dict
        assert call_kwargs["json"]["input"] == [{"content": inputs[0]}]

@pytest.mark.asyncio
async def test_batch_multimodal_requests(gateway):
    inputs = [
        [{"type": "text", "text": "Page 1"}],
        [{"type": "text", "text": "Page 2"}],
    ]
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"index": 0, "embedding": [0.1] * 2048},
                {"index": 1, "embedding": [0.2] * 2048}
            ]
        }
        mock_post.return_value = mock_response
        
        await gateway.embed(inputs)
        
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["input"] == [{"content": inputs[0]}, {"content": inputs[1]}]

@pytest.mark.asyncio
async def test_mixed_text_and_multimodal(gateway):
    inputs = [
        "Plain text chunk",
        [{"type": "image_url", "image_url": {"url": "data:..."}}]
    ]
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"index": 0, "embedding": [0.1] * 2048},
                {"index": 1, "embedding": [0.2] * 2048}
            ]
        }
        mock_post.return_value = mock_response
        
        await gateway.embed(inputs)
        
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["input"] == [
            {"content": [{"type": "text", "text": "Plain text chunk"}]},
            {"content": inputs[1]}
        ]

@pytest.mark.asyncio
async def test_response_dimension_validation(gateway):
    inputs = ["Test"]
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        # Return 10 dimensions instead of 2048
        mock_response.json.return_value = {
            "data": [{"index": 0, "embedding": [0.1] * 10}]
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(ProviderError, match="Expected 2048 dimensions"):
            await gateway.embed(inputs)

@pytest.mark.asyncio
async def test_http_400_provider_errors(gateway):
    inputs = ["Test"]
    
    with patch("httpx.AsyncClient.post") as mock_post:
        from httpx import HTTPStatusError, Request, Response
        mock_request = Request("POST", "http://test")
        mock_response = Response(400, request=mock_request, text="Invalid input shape")
        mock_post.side_effect = HTTPStatusError("Error", request=mock_request, response=mock_response)
        
        with pytest.raises(ProviderError, match="OpenRouter embedding request failed: Invalid input shape"):
            await gateway.embed(inputs)
