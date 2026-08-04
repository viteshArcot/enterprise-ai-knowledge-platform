"""Document service."""

import uuid
from typing import Any

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


class DocumentService(BaseService):
    """Business logic for document ingestion and lifecycle management."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        parser_registry: ParserRegistry,
        chunker: RecursiveTokenChunker,
        embedding_gateway: EmbeddingGateway,
    ) -> None:
        super().__init__()
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._parser_registry = parser_registry
        self._chunker = chunker
        self._embedding_gateway = embedding_gateway

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
            text_chunks = self._chunker.chunk(parsed_doc.text)
            if not text_chunks:
                raise IngestionError("Document produced no text chunks after parsing.")

            # 3. Embedding (Batched within the gateway)
            texts_to_embed = [tc.content for tc in text_chunks]
            embeddings = await self._embedding_gateway.embed(texts_to_embed)

            # 4. Persistence
            chunk_creates = []
            for tc, embedding in zip(text_chunks, embeddings, strict=True):
                chunk_creates.append(
                    ChunkCreate(
                        document_id=document_id,
                        content=tc.content,
                        chunk_index=tc.chunk_index,
                        token_count=tc.token_count,
                        char_count=tc.char_count,
                        embedding=embedding,
                        metadata_=parsed_doc.metadata,
                    )
                )

            await self._chunk_repo.create_many(chunk_creates)

            # 5. Finalize Document
            # Retrieve the document again to get current metadata
            doc = await self._document_repo.get_by_id(document_id)
            current_metadata = doc.metadata_ if doc and doc.metadata_ else {}
            
            await self._document_repo.update(
                document_id,
                DocumentUpdate(
                    status=DocumentStatus.READY,
                    chunk_count=len(chunk_creates),
                    metadata_={**current_metadata, **parsed_doc.metadata},
                ),
            )
            await self._document_repo._session.commit()
            self._logger.info(
                "document_processing_complete",
                document_id=str(document_id),
                chunk_count=len(chunk_creates),
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
            
        file_path = doc.file_path
        
        success = await self._document_repo.delete(document_id)
        if success:
            await self._document_repo._session.commit()
            
            import os
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                
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
