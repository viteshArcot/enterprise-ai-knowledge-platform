import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.search import SearchService, SearchResult
from app.repositories.chunk import ChunkRepository
from app.providers.embedding.base import EmbeddingGateway

from app.config.settings import Settings
from app.providers.reranker.base import RerankerGateway, RerankResult

@pytest.fixture
def mock_chunk_repo():
    return AsyncMock(spec=ChunkRepository)

@pytest.fixture
def mock_embedding_gateway():
    return AsyncMock(spec=EmbeddingGateway)

@pytest.fixture
def mock_reranker_gateway():
    return AsyncMock(spec=RerankerGateway)

@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.RERANKER_ENABLED = False
    return settings

@pytest.fixture
def search_service(mock_chunk_repo, mock_embedding_gateway, mock_reranker_gateway, mock_settings):
    return SearchService(
        chunk_repo=mock_chunk_repo,
        embedding_gateway=mock_embedding_gateway,
        reranker_gateway=mock_reranker_gateway,
        settings=mock_settings
    )

@pytest.mark.asyncio
async def test_search_valid_2048d_embeddings(search_service, mock_chunk_repo, mock_embedding_gateway):
    """Test search with valid 2048D embeddings."""
    # Mock embedding gateway to return 2048D vector
    mock_embedding = [0.1] * 2048
    mock_embedding_gateway.embed.return_value = [mock_embedding]
    
    # Mock chunk repo to return some similar chunks
    mock_chunk = MagicMock()
    mock_chunk.id = "chunk1"
    mock_chunk.content = "Test content"
    mock_chunk.document.title = "Test Doc"
    mock_chunk.metadata_ = {}
    
    mock_chunk_repo.find_similar.return_value = [(mock_chunk, 0.2)]
    
    results = await search_service.search("test query")
    
    assert len(results) == 1
    assert results[0].content == "Test content"
    assert results[0].score == 0.8
    assert results[0].document_title == "Test Doc"
    mock_chunk_repo.find_similar.assert_called_once_with(mock_embedding, limit=5, page_number=None)

@pytest.mark.asyncio
async def test_search_excludes_invalid_embedding_dimension(search_service, mock_chunk_repo, mock_embedding_gateway):
    """Test search fails cleanly when embedding dimension is incorrect."""
    # Mock embedding gateway to return 768D vector instead of 2048D
    mock_embedding = [0.1] * 768
    mock_embedding_gateway.embed.return_value = [mock_embedding]
    
    results = await search_service.search("test query")
    
    assert len(results) == 0
    mock_chunk_repo.find_similar.assert_not_called()

@pytest.mark.asyncio
async def test_search_defensively_handles_null_distances(search_service, mock_chunk_repo, mock_embedding_gateway):
    """Test search safely skips chunks returned with None distance."""
    # Mock embedding gateway to return 2048D vector
    mock_embedding = [0.1] * 2048
    mock_embedding_gateway.embed.return_value = [mock_embedding]
    
    # Mock chunk repo to return one valid chunk and one chunk with None distance
    valid_chunk = MagicMock()
    valid_chunk.content = "Valid content"
    valid_chunk.document.title = "Valid Doc"
    valid_chunk.metadata_ = {}
    
    invalid_chunk = MagicMock()
    invalid_chunk.content = "Invalid content"
    
    mock_chunk_repo.find_similar.return_value = [
        (valid_chunk, 0.1),
        (invalid_chunk, None)
    ]
    
    results = await search_service.search("test query")
    
    # Only the valid chunk should be returned
    assert len(results) == 1
    assert results[0].content == "Valid content"
    assert results[0].score == 0.9

@pytest.mark.asyncio
async def test_search_empty_retrieval(search_service, mock_chunk_repo, mock_embedding_gateway):
    """Test search handles empty retrieval results cleanly."""
    mock_embedding = [0.1] * 2048
    mock_embedding_gateway.embed.return_value = [mock_embedding]
    
    mock_chunk_repo.find_similar.return_value = []
    
    results = await search_service.search("test query")
    assert len(results) == 0

@pytest.mark.asyncio
async def test_search_page_aware_query(search_service, mock_chunk_repo, mock_embedding_gateway):
    """Test search extracts page constraint and passes to repo."""
    mock_embedding = [0.1] * 2048
    mock_embedding_gateway.embed.return_value = [mock_embedding]
    
    mock_chunk_repo.find_similar.return_value = []
    
    await search_service.search("What is on page 20?")
    
    mock_chunk_repo.find_similar.assert_called_once_with(mock_embedding, limit=5, page_number=20)

@pytest.mark.asyncio
async def test_search_normal_query_with_numbers(search_service, mock_chunk_repo, mock_embedding_gateway):
    """Test normal search does not pass page constraint even if numbers exist."""
    mock_embedding = [0.1] * 2048
    mock_embedding_gateway.embed.return_value = [mock_embedding]
    
    mock_chunk_repo.find_similar.return_value = []
    
    await search_service.search("What are the 20 most important ideas?")
    
    mock_chunk_repo.find_similar.assert_called_once_with(mock_embedding, limit=5, page_number=None)
