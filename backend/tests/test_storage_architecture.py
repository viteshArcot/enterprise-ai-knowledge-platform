"""Tests for the new persistent storage architecture."""

from uuid import uuid4

import pytest

from app.core.dependencies import get_storage_gateway
from app.main import app


# Mark as integration because we need the DB for endpoints
@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_persists_original_pdf(client):
    """Test A & B: Upload persists original PDF and populates storage_path."""
    mock_storage = app.dependency_overrides[get_storage_gateway]()

    import random
    file_content = f"%PDF-1.4 mock pdf data for upload {random.randint(0, 1000000)}".encode()
    files = {"file": ("test_upload.pdf", file_content, "application/pdf")}
    data = {"title": "Test Storage PDF"}

    response = await client.post("/api/v1/documents/", files=files, data=data)
    assert response.status_code == 202

    resp_data = response.json()
    doc_id = resp_data["id"]

    # Check that storage_path exists in our mock storage
    # The path format is documents/{document_id}/{safe_filename}
    found_path = None
    for path in mock_storage._storage.keys():
        if f"documents/{doc_id}/" in path:
            found_path = path
            break

    assert found_path is not None, "File was not uploaded to storage gateway."
    assert mock_storage._storage[found_path] == file_content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_storage_upload_handled_correctly(client, monkeypatch):
    """Test C: Failed storage upload cleans up and returns 500."""
    mock_storage = app.dependency_overrides[get_storage_gateway]()

    # Force upload to fail
    async def mock_upload_fail(*args, **kwargs):
        raise Exception("Simulated storage failure")

    monkeypatch.setattr(mock_storage, "upload", mock_upload_fail)

    import random
    file_content = f"%PDF-1.4 mock pdf data {random.randint(0, 1000000)}".encode()
    files = {"file": ("test_fail.pdf", file_content, "application/pdf")}

    response = await client.post("/api/v1/documents/", files=files)
    assert response.status_code == 500
    assert "Failed to persist document to storage" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_document_cleans_up_storage(client):
    """Test K: Document deletion handles storage cleanup."""
    mock_storage = app.dependency_overrides[get_storage_gateway]()

    import random
    file_content = f"pdf content {random.randint(0, 1000000)}".encode()
    files = {"file": ("test_delete.pdf", file_content, "application/pdf")}
    response = await client.post("/api/v1/documents/", files=files)
    assert response.status_code == 202

    doc_id = response.json()["id"]

    found_path = None
    for path in mock_storage._storage.keys():
        if f"documents/{doc_id}/" in path:
            found_path = path
            break

    assert found_path is not None
    assert found_path in mock_storage._storage

    # Now delete the document
    del_resp = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_resp.status_code == 204

    # Verify it was removed from storage
    assert found_path not in mock_storage._storage


# Mocking chat visual context requires setting up search results and fitz.
# We'll use unittest.mock to mock fitz and SearchService in a unit test.

from unittest.mock import MagicMock, patch

from app.services.chat import ChatService
from app.services.storage import InMemoryStorageGateway


@pytest.mark.asyncio
async def test_chat_visual_downloads_pdf_once_and_handles_missing(monkeypatch):
    """Test D, E, F, G, H: Chat visual context downloading logic."""
    from app.services.search import SearchResult

    mock_search = MagicMock()
    async def mock_search_func(*args, **kwargs):
        return [
            SearchResult(content="text", document_title="Doc1", score=0.9, metadata={"source_type": "visual"}, storage_path="doc1.pdf", page_number=1),
            SearchResult(content="text", document_title="Doc1", score=0.8, metadata={"source_type": "visual"}, storage_path="doc1.pdf", page_number=2),
            SearchResult(content="text", document_title="Doc2", score=0.7, metadata={"source_type": "visual"}, storage_path="doc2.pdf", page_number=1),
            SearchResult(content="text", document_title="Doc3", score=0.6, metadata={"source_type": "visual"}, storage_path=None, page_number=1), # Missing path
            SearchResult(content="text", document_title="Doc4", score=0.5, metadata={"source_type": "visual"}, storage_path="doc4.pdf", page_number=1), # Missing object
        ]
    mock_search.search = mock_search_func

    mock_llm = MagicMock()
    mock_llm.model_name = "test-model"

    async def mock_stream(*args, **kwargs):
        yield "Response"
    mock_llm.stream.return_value = mock_stream()

    mock_conv_repo = MagicMock()
    mock_conv = MagicMock()
    mock_conv.messages = []
    mock_conv.title = "Existing"

    async def mock_get_with_messages(*args, **kwargs):
        return mock_conv
    mock_conv_repo.get_with_messages = mock_get_with_messages

    mock_msg_repo = MagicMock()
    async def mock_create_msg(*args, **kwargs):
        return MagicMock()
    mock_msg_repo.create = mock_create_msg

    mock_session = MagicMock()
    async def mock_commit(*args, **kwargs):
        pass
    mock_session.commit = mock_commit
    mock_msg_repo._session = mock_session
    mock_conv_repo._session = mock_session

    storage = InMemoryStorageGateway()
    storage._storage["doc1.pdf"] = b"PDF1"
    storage._storage["doc2.pdf"] = b"PDF2"
    # doc4.pdf is deliberately NOT in storage

    chat_service = ChatService(
        conversation_repo=mock_conv_repo,
        message_repo=mock_msg_repo,
        search_service=mock_search,
        llm_gateway=mock_llm,
        storage_gateway=storage
    )

    # We must patch fitz.open to not crash on dummy bytes
    mock_fitz_doc = MagicMock()
    mock_fitz_doc.page_count = 5
    mock_page = MagicMock()
    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"pngdata"
    mock_page.get_pixmap.return_value = mock_pix
    mock_fitz_doc.load_page.return_value = mock_page

    mock_fitz_open = MagicMock()
    mock_fitz_open.return_value.__enter__.return_value = mock_fitz_doc

    # We also want to intercept how many times download_to_file is called on storage
    download_calls = []
    original_download = storage.download_to_file

    async def track_download(path, dest_path):
        download_calls.append(path)
        await original_download(path, dest_path)

    monkeypatch.setattr(storage, "download_to_file", track_download)

    with patch("app.services.chat.fitz.open", mock_fitz_open):
        # Consume the generator
        async for chunk in chat_service.stream_chat(uuid4(), "Test"):
            pass

    # doc1.pdf downloaded ONCE despite 2 pages
    # doc2.pdf downloaded ONCE
    # doc4.pdf attempted but failed (caught gracefully)
    assert download_calls.count("doc1.pdf") == 1
    assert download_calls.count("doc2.pdf") == 1
    assert download_calls.count("doc4.pdf") == 1

    # fitz.open called for doc1 p1, doc1 p2, doc2 p1
    assert mock_fitz_open.call_count == 3

    # LLM was invoked with images
    call_args = mock_llm.stream.call_args[0][0]
    user_msg = next(m for m in call_args if m.role == "user")

    # 3 images should be attached: doc1 p1, doc1 p2, doc2 p1
    assert len(user_msg.images) == 3
