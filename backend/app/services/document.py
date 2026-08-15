"""Document service."""

import uuid

from app.core.exceptions import IngestionError, NotFoundError
from app.ingestion.chunking.recursive import RecursiveTokenChunker
from app.ingestion.parsers.registry import ParserRegistry
from app.models.document import Document, DocumentStatus
from app.providers.embedding.base import EmbeddingGateway
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository
from app.schemas.chunk import ChunkCreate
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.base import BaseService
from app.services.storage import StorageGateway


class DocumentService(BaseService):
    """Business logic for document ingestion and lifecycle management."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        parser_registry: ParserRegistry,
        chunker: RecursiveTokenChunker,
        embedding_gateway: EmbeddingGateway,
        storage_gateway: StorageGateway,
    ) -> None:
        super().__init__()
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._parser_registry = parser_registry
        self._chunker = chunker
        self._embedding_gateway = embedding_gateway
        self._storage_gateway = storage_gateway

    async def create_document(
        self, title: str, file_name: str, file_type: str, file_size_bytes: int, file_path: str, metadata_: dict | None = None
    ) -> Document:
        """Create a new document record in UPLOADING status."""
        doc_data = DocumentCreate(
            title=title,
            file_name=file_name,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_path=file_path,
            status=DocumentStatus.UPLOADING,
            metadata_=metadata_ or {}
        )
        document = await self._document_repo.create(doc_data)
        await self._document_repo._session.commit()
        await self._document_repo._session.refresh(document)
        self._logger.info("document_created", document_id=str(document.id), file_name=file_name)
        return document

    async def list_documents(self, limit: int = 50, offset: int = 0) -> list[Document]:
        """Retrieve a paginated list of documents."""
        return await self._document_repo.list(limit=limit, offset=offset)

    async def process_document_async(
        self, document_id: uuid.UUID, content: bytes, file_name: str
    ) -> None:
        """Background task to parse, chunk, embed, and persist document content."""
        self._logger.info("document_processing_started", document_id=str(document_id))

        # Update status to processing
        await self._document_repo.update(
            document_id, DocumentUpdate(status=DocumentStatus.PROCESSING)
        )
        await self._document_repo._session.commit()

        try:
            # 1. Parsing
            parser = self._parser_registry.get_parser(file_name)
            parsed_doc = parser.parse(content, file_name)

            # 2. Chunking
            chunks_to_persist = []
            chunk_index = 0

            if getattr(parsed_doc, "pages", None):
                for page in parsed_doc.pages:
                    # Text chunks for this page
                    if page.text.strip():
                        text_chunks = self._chunker.chunk(page.text, start_index=chunk_index, page_number=page.page_number)
                        for tc in text_chunks:
                            chunks_to_persist.append(
                                ChunkCreate(
                                    document_id=document_id,
                                    content=tc.content,
                                    chunk_index=tc.chunk_index,
                                    token_count=tc.token_count,
                                    char_count=tc.char_count,
                                    page_number=tc.page_number,
                                    metadata_={"source_type": "text"},
                                )
                            )
                        chunk_index += len(text_chunks)

                    # Visual representation for this page
                    if page.image_base64:
                        chunks_to_persist.append(
                            ChunkCreate(
                                document_id=document_id,
                                content=f"[Visual representation of {file_name}, page {page.page_number}]",
                                chunk_index=chunk_index,
                                token_count=0,
                                char_count=0,
                                page_number=page.page_number,
                                metadata_={"source_type": "visual", "image_base64": page.image_base64},
                            )
                        )
                        chunk_index += 1
            else:
                # Fallback for parsers without pages
                text_chunks = self._chunker.chunk(parsed_doc.text)
                for tc in text_chunks:
                    chunks_to_persist.append(
                        ChunkCreate(
                            document_id=document_id,
                            content=tc.content,
                            chunk_index=tc.chunk_index,
                            token_count=tc.token_count,
                            char_count=tc.char_count,
                            page_number=None,
                            metadata_={"source_type": "text"},
                        )
                    )

            if not chunks_to_persist:
                raise IngestionError("Document produced no chunks after parsing.")

            # 3. Embedding (Batched within the gateway)
            inputs_to_embed = []
            for chunk_create in chunks_to_persist:
                if chunk_create.metadata_.get("source_type") == "visual":
                    inputs_to_embed.append([
                        {"type": "text", "text": f"Document: {file_name}, Page: {chunk_create.page_number}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{chunk_create.metadata_['image_base64']}"}}
                    ])
                else:
                    inputs_to_embed.append(chunk_create.content)

            embeddings = await self._embedding_gateway.embed(inputs_to_embed)

            # 4. Persistence
            for chunk_create, embedding in zip(chunks_to_persist, embeddings, strict=True):
                chunk_create.embedding = embedding
                # Drop large base64 image data before DB persistence
                if "image_base64" in chunk_create.metadata_:
                    del chunk_create.metadata_["image_base64"]

            await self._chunk_repo.create_many(chunks_to_persist)

            # 5. Finalize Document
            # Retrieve the document again to get current metadata
            doc = await self._document_repo.get_by_id(document_id)
            current_metadata = doc.metadata_ if doc and doc.metadata_ else {}

            await self._document_repo.update(
                document_id,
                DocumentUpdate(
                    status=DocumentStatus.READY,
                    chunk_count=len(chunks_to_persist),
                    metadata_={**current_metadata, **parsed_doc.metadata},
                ),
            )
            await self._document_repo._session.commit()
            self._logger.info(
                "document_processing_complete",
                document_id=str(document_id),
                chunk_count=len(chunks_to_persist),
            )

        except Exception as exc:
            self._logger.exception("document_processing_failed", document_id=str(document_id))
            await self._document_repo.update(
                document_id,
                DocumentUpdate(status=DocumentStatus.FAILED, error_message=str(exc)),
            )
            await self._document_repo._session.commit()

    async def get_document(self, document_id: uuid.UUID) -> Document:
        """Retrieve a specific document or raise NotFoundError."""
        doc = await self._document_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("Document", str(document_id))
        return doc

    async def get_document_by_hash(self, file_hash: str) -> Document | None:
        """Find a document by its file hash."""
        return await self._document_repo.get_by_file_hash(file_hash)

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """Delete a document, its physical file, and its associated chunks idempotently."""
        doc = await self._document_repo.get_by_id(document_id)
        if not doc:
            self._logger.info("document_delete_skipped_not_found", document_id=str(document_id))
            return

        import os

        from app.config.settings import settings

        file_path = doc.file_path

        if file_path and not os.path.exists(file_path) and file_path.startswith("/tmp/uploads/"):
            fallback_path = os.path.join(str(settings.UPLOAD_DIRECTORY), os.path.basename(file_path))
            if os.path.exists(fallback_path):
                file_path = fallback_path

        success = await self._document_repo.delete(document_id)
        if success:
            await self._document_repo._session.commit()

            if file_path and os.path.exists(file_path):
                os.remove(file_path)

            if doc.storage_path:
                try:
                    await self._storage_gateway.delete(doc.storage_path)
                except Exception as e:
                    self._logger.warning("document_storage_delete_failed", document_id=str(document_id), error=str(e))

            self._logger.info("document_deleted", document_id=str(document_id))
        else:
            self._logger.warning("document_delete_failed", document_id=str(document_id))

    async def reindex_document(self, document_id: uuid.UUID) -> Document:
        """Trigger re-indexing of a document. Delete old chunks and reset status."""
        doc = await self.get_document(document_id)
        if doc.status in (DocumentStatus.UPLOADING, DocumentStatus.PROCESSING):
            raise ValueError(f"Document {document_id} is already being processed (status: {doc.status}).")

        # Delete existing chunks
        await self._chunk_repo.delete_by_document_id(document_id)

        # Reset status
        await self._document_repo.update(
            document_id,
            DocumentUpdate(
                status=DocumentStatus.UPLOADING,
                chunk_count=0,
                error_message=None
            )
        )
        await self._document_repo._session.commit()
        await self._document_repo._session.refresh(doc)

        self._logger.info("document_reindex_started", document_id=str(document_id))
        return doc
