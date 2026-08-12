import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.config.settings import Settings
from app.models.chunk import Chunk
from app.providers.reranker.openrouter import OpenRouterRerankerGateway


@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.OPENROUTER_API_KEY = "test_key"
    return settings


@pytest.fixture
def mock_candidates():
    c1 = Chunk(id="1", content="first", chunk_index=1, token_count=1, char_count=5, metadata_={"source_type": "text"})
    c2 = Chunk(id="2", content="second", chunk_index=2, token_count=1, char_count=6, metadata_={"source_type": "text"})
    return [(c1, 0.1), (c2, 0.2)]  # chunk, distance


@pytest.mark.asyncio
async def test_reranker_success(mock_settings, mock_candidates):
    gateway = OpenRouterRerankerGateway(mock_settings)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"index": 1, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.8}
        ]
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        results = await gateway.rerank("query", mock_candidates, top_k=2)
        
    assert len(results) == 2
    # Verify mapping (order preserved as returned by API)
    assert results[0].chunk.id == "2"
    assert results[0].rerank_score == 0.9
    assert results[0].vector_similarity == 0.8  # 1.0 - 0.2
    
    assert results[1].chunk.id == "1"
    assert results[1].rerank_score == 0.8
    assert results[1].vector_similarity == 0.9  # 1.0 - 0.1


@pytest.mark.asyncio
async def test_reranker_fallback_on_429(mock_settings, mock_candidates):
    gateway = OpenRouterRerankerGateway(mock_settings)
    
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limited"
    
    mock_post = MagicMock()
    mock_post.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=mock_response)
    mock_response.raise_for_status = mock_post.raise_for_status
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        results = await gateway.rerank("query", mock_candidates, top_k=2)
        
    assert len(results) == 2
    # Falls back to original vector order
    assert results[0].chunk.id == "1"
    assert results[0].rerank_score == 0.0
    assert results[1].chunk.id == "2"


@pytest.mark.asyncio
async def test_reranker_fallback_on_timeout(mock_settings, mock_candidates):
    gateway = OpenRouterRerankerGateway(mock_settings)
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        results = await gateway.rerank("query", mock_candidates, top_k=2)
        
    assert len(results) == 2
    assert results[0].chunk.id == "1"


@pytest.mark.asyncio
async def test_visual_payload_construction(mock_settings):
    gateway = OpenRouterRerankerGateway(mock_settings)
    
    c = Chunk(id="1", content="visual", chunk_index=1, token_count=1, char_count=6, metadata_={"source_type": "visual"}, page_number=1)
    
    # We mock _get_visual_representation since we don't have a real PDF here
    with patch.object(gateway, "_get_visual_representation", return_value={"text": "visual", "image": "data:image/png;base64,123"}):
        payload = gateway._build_documents_payload([(c, 0.1)])
        
    assert len(payload) == 1
    assert "image" in payload[0]
    assert payload[0]["image"] == "data:image/png;base64,123"
    assert payload[0]["text"] == "visual"


@pytest.mark.asyncio
async def test_reranker_fallback_invalid_index(mock_settings, mock_candidates):
    gateway = OpenRouterRerankerGateway(mock_settings)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    # API returns out of bounds index
    mock_response.json.return_value = {
        "results": [
            {"index": 99, "relevance_score": 0.9}
        ]
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        results = await gateway.rerank("query", mock_candidates, top_k=2)
        
    # Result should be skipped if index is invalid
    assert len(results) == 0
