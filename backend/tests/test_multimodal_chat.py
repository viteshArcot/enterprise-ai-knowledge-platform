import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.services.chat import ChatService
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.search import SearchService, SearchResult
from app.providers.llm.base import LLMGateway, PromptMessage, ImageAttachment
from app.models.conversation import Conversation
from app.models.message import MessageRole


class MockLLMGateway(LLMGateway):
    model_name = "mock-model"
    
    async def complete(self, messages):
        return "response"

    async def stream(self, messages):
        self.received_messages = messages
        yield "response"


@pytest.fixture
def mock_conversation_repo():
    repo = AsyncMock(spec=ConversationRepository)
    conversation = MagicMock(spec=Conversation)
    conversation.id = uuid.uuid4()
    conversation.title = "Test Convo"
    conversation.messages = []
    repo.get_with_messages.return_value = conversation
    return repo


@pytest.fixture
def mock_message_repo():
    repo = AsyncMock(spec=MessageRepository)
    repo._session = AsyncMock()
    return repo


@pytest.fixture
def mock_search_service():
    return AsyncMock(spec=SearchService)


@pytest.fixture
def mock_llm_gateway():
    return MockLLMGateway()


@pytest.fixture
def chat_service(mock_conversation_repo, mock_message_repo, mock_search_service, mock_llm_gateway):
    return ChatService(
        conversation_repo=mock_conversation_repo,
        message_repo=mock_message_repo,
        search_service=mock_search_service,
        llm_gateway=mock_llm_gateway
    )


@pytest.mark.asyncio
async def test_text_only_request(chat_service, mock_search_service, mock_llm_gateway):
    """Test 1 - Text-only request produces text-only PromptMessages."""
    mock_search_service.search.return_value = [
        SearchResult(content="text", document_title="doc1", score=0.9, metadata={"source_type": "text"})
    ]

    async for chunk in chat_service.stream_chat(uuid.uuid4(), "test"):
        pass

    assert len(mock_llm_gateway.received_messages) == 2
    system_msg = mock_llm_gateway.received_messages[0]
    user_msg = mock_llm_gateway.received_messages[1]
    
    assert system_msg.role == "system"
    assert user_msg.role == "user"
    assert user_msg.images is None


@pytest.mark.asyncio
@patch("app.services.chat.os.path.exists")
@patch("app.services.chat.fitz.open")
async def test_visual_chunk(mock_fitz_open, mock_exists, chat_service, mock_search_service, mock_llm_gateway):
    """Test 2 - Visual chunk loads image and attaches to PromptMessage."""
    mock_exists.return_value = True
    
    mock_pdf = MagicMock()
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.page_count = 5
    mock_page = MagicMock()
    mock_pdf.load_page.return_value = mock_page
    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"fake_image_data"
    mock_page.get_pixmap.return_value = mock_pix
    mock_fitz_open.return_value = mock_pdf
    
    mock_search_service.search.return_value = [
        SearchResult(
            content="visual chunk text", 
            document_title="doc1", 
            score=0.9, 
            metadata={"source_type": "visual"},
            file_path="/path/to/pdf.pdf",
            page_number=3
        )
    ]

    async for chunk in chat_service.stream_chat(uuid.uuid4(), "test"):
        pass

    user_msg = mock_llm_gateway.received_messages[1]
    assert user_msg.images is not None
    assert len(user_msg.images) == 1
    assert user_msg.images[0].data == b"fake_image_data"
    assert user_msg.images[0].mime_type == "image/png"
    
    mock_pdf.load_page.assert_called_with(2) # 0-indexed


@pytest.mark.asyncio
@patch("app.services.chat.os.path.exists")
@patch("app.services.chat.fitz.open")
async def test_duplicate_visual_page(mock_fitz_open, mock_exists, chat_service, mock_search_service, mock_llm_gateway):
    """Test 5 - Duplicate visual page renders only once."""
    mock_exists.return_value = True
    mock_pdf = MagicMock()
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.page_count = 5
    mock_page = MagicMock()
    mock_pdf.load_page.return_value = mock_page
    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"fake_image_data"
    mock_page.get_pixmap.return_value = mock_pix
    mock_fitz_open.return_value = mock_pdf
    
    mock_search_service.search.return_value = [
        SearchResult(
            content="visual chunk text 1", 
            document_title="doc1", 
            score=0.9, 
            metadata={"source_type": "visual"},
            file_path="/path/to/pdf.pdf",
            page_number=3
        ),
        SearchResult(
            content="visual chunk text 2", 
            document_title="doc1", 
            score=0.8, 
            metadata={"source_type": "visual"},
            file_path="/path/to/pdf.pdf",
            page_number=3
        )
    ]

    async for chunk in chat_service.stream_chat(uuid.uuid4(), "test"):
        pass

    user_msg = mock_llm_gateway.received_messages[1]
    assert user_msg.images is not None
    assert len(user_msg.images) == 1 # Only one image attached
    mock_pdf.load_page.assert_called_once() # Rendered only once


@pytest.mark.asyncio
@patch("app.services.chat.os.path.exists")
async def test_missing_pdf(mock_exists, chat_service, mock_search_service, mock_llm_gateway):
    """Test 6 - Missing PDF doesn't crash."""
    mock_exists.return_value = False
    
    mock_search_service.search.return_value = [
        SearchResult(
            content="visual chunk text", 
            document_title="doc1", 
            score=0.9, 
            metadata={"source_type": "visual"},
            file_path="/path/to/pdf.pdf",
            page_number=3
        )
    ]

    async for chunk in chat_service.stream_chat(uuid.uuid4(), "test"):
        pass

    user_msg = mock_llm_gateway.received_messages[1]
    assert user_msg.images is None


@pytest.mark.asyncio
@patch("app.services.chat.os.path.exists")
@patch("app.services.chat.fitz.open")
async def test_invalid_page(mock_fitz_open, mock_exists, chat_service, mock_search_service, mock_llm_gateway):
    """Test 7 - Invalid page doesn't crash."""
    mock_exists.return_value = True
    
    mock_pdf = MagicMock()
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.page_count = 2 # Page 3 is out of bounds
    mock_fitz_open.return_value = mock_pdf
    
    mock_search_service.search.return_value = [
        SearchResult(
            content="visual chunk text", 
            document_title="doc1", 
            score=0.9, 
            metadata={"source_type": "visual"},
            file_path="/path/to/pdf.pdf",
            page_number=3
        )
    ]

    async for chunk in chat_service.stream_chat(uuid.uuid4(), "test"):
        pass

    user_msg = mock_llm_gateway.received_messages[1]
    assert user_msg.images is None

