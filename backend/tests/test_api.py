import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    # This assumes the app is running in the test and db is mocked/empty
    response = await client.get("/api/v1/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

from unittest import mock

@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient):
    import uuid
    file_content = f"This is a test document {uuid.uuid4()}".encode("utf-8")
    
    with mock.patch("app.services.document.DocumentService.process_document_async") as mock_process:
        response = await client.post(
            "/api/v1/documents/",
            files={"file": ("test.txt", file_content, "text/plain")},
            data={"title": "Test Doc"}
        )
        assert response.status_code == 202
        data = response.json()
        assert data["title"] == "Test Doc"
        assert data["file_name"] == "test.txt"
        mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_chat_create_conversation(client: AsyncClient):
    response = await client.post(
        "/api/v1/conversations/",
        json={"title": "Test Conversation"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "id" in data
