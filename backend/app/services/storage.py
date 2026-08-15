"""Storage service and gateway abstractions."""

import abc
import logging

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class StorageException(Exception):
    """Base exception for storage operations."""
    pass


class StorageGateway(abc.ABC):
    """Interface for object storage operations."""

    @abc.abstractmethod
    async def upload(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        """Upload content to the given storage path."""
        pass

    @abc.abstractmethod
    async def download_to_file(self, path: str, dest_path: str) -> None:
        """Download content from the storage path to a local file."""
        pass

    @abc.abstractmethod
    async def delete(self, path: str) -> None:
        """Delete an object at the given storage path."""
        pass


class SupabaseStorageGateway(StorageGateway):
    """Supabase implementation of the StorageGateway using its REST API."""

    def __init__(self, url: str | None = None, service_role_key: str | None = None, bucket: str | None = None):
        self.url = url or settings.SUPABASE_URL
        self.service_role_key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY
        self.bucket = bucket or settings.SUPABASE_STORAGE_BUCKET

        if not self.url or not self.service_role_key:
            logger.warning("Supabase storage is not configured properly (missing URL or KEY).")

    def _get_headers(self) -> dict[str, str]:
        if not self.service_role_key:
            raise StorageException("Supabase service role key is missing.")
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    def _get_object_url(self, path: str) -> str:
        if not self.url:
            raise StorageException("Supabase URL is missing.")
        base = self.url.rstrip("/")
        return f"{base}/storage/v1/object/{self.bucket}/{path}"

    async def upload(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        headers = self._get_headers()
        headers["Content-Type"] = content_type

        async with httpx.AsyncClient() as client:
            resp = await client.post(self._get_object_url(path), headers=headers, content=content)
            if resp.status_code not in (200, 201):
                logger.error(f"Storage upload failed: {resp.status_code} {resp.text}")
                raise StorageException(f"Failed to upload to Supabase storage: {resp.status_code}")
            logger.debug(f"Successfully uploaded to storage path: {path}")

    async def download_to_file(self, path: str, dest_path: str) -> None:
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            async with client.stream("GET", self._get_object_url(path), headers=headers) as resp:
                if resp.status_code == 404:
                    raise StorageException(f"Object not found: {path}")
                if resp.status_code != 200:
                    logger.error(f"Storage download failed: {resp.status_code} {resp.text}")
                    raise StorageException(f"Failed to download from Supabase storage: {resp.status_code}")

                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)
            logger.debug(f"Successfully downloaded from storage path: {path} to {dest_path}")

    async def delete(self, path: str) -> None:
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            resp = await client.delete(self._get_object_url(path), headers=headers)
            if resp.status_code == 404:
                # Idempotent delete
                logger.debug(f"Storage delete: object already missing: {path}")
                return
            if resp.status_code != 200:
                logger.error(f"Storage delete failed: {resp.status_code} {resp.text}")
                raise StorageException(f"Failed to delete from Supabase storage: {resp.status_code}")
            logger.debug(f"Successfully deleted storage path: {path}")


class InMemoryStorageGateway(StorageGateway):
    """In-memory mock for testing."""

    def __init__(self):
        self._storage: dict[str, bytes] = {}

    async def upload(self, path: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        self._storage[path] = content

    async def download_to_file(self, path: str, dest_path: str) -> None:
        if path not in self._storage:
            raise StorageException(f"Object not found: {path}")
        with open(dest_path, "wb") as f:
            f.write(self._storage[path])

    async def delete(self, path: str) -> None:
        self._storage.pop(path, None)
