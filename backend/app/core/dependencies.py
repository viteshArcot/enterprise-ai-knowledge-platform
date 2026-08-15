"""Dependency injection providers."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.session import get_session
from app.ingestion.chunking.recursive import RecursiveTokenChunker
from app.ingestion.parsers.registry import ParserRegistry
from app.providers.embedding.base import EmbeddingGateway

# IMPORTANT
from app.providers.llm.base import LLMGateway
from app.providers.llm.factory import create_llm_gateway
from app.providers.reranker.base import RerankerGateway
from app.providers.reranker.factory import create_reranker_gateway
from app.repositories.chunk import ChunkRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.document import DocumentRepository
from app.repositories.message import MessageRepository
from app.services.chat import ChatService
from app.services.document import DocumentService
from app.services.search import SearchService
from app.services.storage import StorageGateway, SupabaseStorageGateway


def get_app_settings() -> Settings:
    return get_settings()


AppSettings = Annotated[Settings, Depends(get_app_settings)]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


def get_document_repository(session: DbSession) -> DocumentRepository:
    return DocumentRepository(session)


def get_chunk_repository(session: DbSession) -> ChunkRepository:
    return ChunkRepository(session)


def get_conversation_repository(session: DbSession) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(session: DbSession) -> MessageRepository:
    return MessageRepository(session)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def get_parser_registry() -> ParserRegistry:
    return ParserRegistry()


def get_recursive_chunker(settings: AppSettings) -> RecursiveTokenChunker:
    return RecursiveTokenChunker(
        chunk_size=512,
        overlap=64,
        encoding_name="cl100k_base",
    )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def get_embedding_gateway(settings: AppSettings) -> EmbeddingGateway:
    """Dependency provider for the embedding gateway."""
    from app.providers.embedding.factory import create_embedding_gateway
    return create_embedding_gateway(config=settings)


def get_llm_gateway(settings: AppSettings) -> LLMGateway:
    """
    Chat provider is selected from LLM_PROVIDER.
    """
    return create_llm_gateway(settings)


def get_reranker_gateway(settings: AppSettings) -> RerankerGateway:
    """Dependency provider for the reranker gateway."""
    return create_reranker_gateway(settings)


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def get_storage_gateway() -> StorageGateway:
    return SupabaseStorageGateway()



def get_document_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repository)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
    parser_registry: Annotated[ParserRegistry, Depends(get_parser_registry)],
    chunker: Annotated[RecursiveTokenChunker, Depends(get_recursive_chunker)],
    embedding_gateway: Annotated[
        EmbeddingGateway,
        Depends(get_embedding_gateway),
    ],
    storage_gateway: Annotated[StorageGateway, Depends(get_storage_gateway)],
) -> DocumentService:
    return DocumentService(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_gateway=embedding_gateway,
        storage_gateway=storage_gateway,
    )


def get_search_service(
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repository)],
    embedding_gateway: Annotated[
        EmbeddingGateway,
        Depends(get_embedding_gateway),
    ],
    reranker_gateway: Annotated[
        RerankerGateway,
        Depends(get_reranker_gateway),
    ],
    settings: AppSettings,
) -> SearchService:
    return SearchService(
        chunk_repo=chunk_repo,
        embedding_gateway=embedding_gateway,
        reranker_gateway=reranker_gateway,
        settings=settings,
    )


def get_chat_service(
    conversation_repo: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
    message_repo: Annotated[
        MessageRepository,
        Depends(get_message_repository),
    ],
    search_service: Annotated[
        SearchService,
        Depends(get_search_service),
    ],
    llm_gateway: Annotated[
        LLMGateway,
        Depends(get_llm_gateway),
    ],
    storage_gateway: Annotated[
        StorageGateway,
        Depends(get_storage_gateway),
    ],
) -> ChatService:
    return ChatService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        search_service=search_service,
        llm_gateway=llm_gateway,
        storage_gateway=storage_gateway,
    )
