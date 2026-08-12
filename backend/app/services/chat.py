"""Chat service."""

import uuid
from collections.abc import AsyncGenerator
import string
import os
import fitz

from app.core.exceptions import NotFoundError, ProviderError, ProviderTimeoutError
from app.models.conversation import Conversation
from app.models.message import MessageRole
from app.providers.llm.base import LLMGateway, PromptMessage
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.services.base import BaseService
from app.providers.llm.base import ImageAttachment
from app.config.settings import settings
from app.services.search import SearchService

SYSTEM_PROMPT = """You are an Enterprise AI Knowledge Assistant.
Answer the user's question using ONLY the provided context.
If the answer is not in the context, say "I don't know based on the provided documents."
"""


class ChatService(BaseService):
    """Business logic for conversations and LLM interaction."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        search_service: SearchService,
        llm_gateway: LLMGateway,
    ) -> None:
        super().__init__()
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._search_service = search_service
        self._llm_gateway = llm_gateway

    async def create_conversation(self, title: str | None = None) -> Conversation:
        """Create a new conversation."""
        data = ConversationCreate(title=title or "New Conversation")
        conversation = await self._conversation_repo.create(data)
        conversation.messages = []
        return conversation

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        """Retrieve a conversation with its messages."""
        conversation = await self._conversation_repo.get_with_messages(conversation_id)
        if not conversation:
            raise NotFoundError("Conversation", str(conversation_id))
        return conversation

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        """List all conversations."""
        return await self._conversation_repo.list_conversations(limit=limit, offset=offset)

    async def rename_conversation(self, conversation_id: uuid.UUID, title: str) -> Conversation:
        """Rename a conversation."""
        conversation = await self.get_conversation(conversation_id)
        updated = await self._conversation_repo.update(conversation.id, {"title": title})
        self._logger.info("conversation_renamed", conversation_id=str(conversation_id), new_title=title)
        return updated

    async def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        """Delete a conversation."""
        success = await self._conversation_repo.delete(conversation_id)
        if not success:
            raise NotFoundError("Conversation", str(conversation_id))
        self._logger.info("conversation_deleted", conversation_id=str(conversation_id))

    async def stream_chat(
        self, conversation_id: uuid.UUID, user_message: str
    ) -> AsyncGenerator[str, None]:
        """Process a user message, retrieve context, and stream the LLM response."""
        conversation = await self.get_conversation(conversation_id)

        # 1. Save the user message
        await self._message_repo.create(
            MessageCreate(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_message,
            )
        )

        # 1.5 Auto-generate title if it's new
        if conversation.title == "New Conversation":
            stopwords = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "from", "by", "is", "are", "was", "were", "be", "been", "am", "in", "of", "with", "as", "what", "where", "when", "why", "who", "how", "this", "that", "these", "those", "can", "could", "will", "would", "should", "do", "does", "did", "have", "has", "had", "i", "you", "we", "they", "he", "she", "it", "my", "your", "our", "their"}
            clean_msg = user_message.translate(str.maketrans('', '', string.punctuation))
            words = clean_msg.split()
            keywords = [w for w in words if w.lower() not in stopwords]
            if not keywords:
                keywords = words
            
            new_title = " ".join(keywords[:5]).strip().title()
            if new_title:
                await self._conversation_repo.update(conversation_id, {"title": new_title})
                await self._conversation_repo._session.commit()
                self._logger.info("conversation_auto_titled", conversation_id=str(conversation_id), title=new_title)

        try:
            # 2. Retrieve relevant context
            search_results = await self._search_service.search(user_message, top_k=5)
            
            context_parts = []
            citations = []
            visual_attachments = []
            rendered_pages = set()

            for i, res in enumerate(search_results, start=1):
                context_parts.append(f"--- Document: {res.document_title} ---\n{res.content}")
                citations.append(
                    {"id": i, "title": res.document_title, "score": res.score, "metadata": res.metadata}
                )

                if res.metadata.get("source_type") == "visual" and res.file_path and res.page_number is not None:
                    self._logger.debug("visual_context_detected", document_id=str(res.metadata.get("document_id", "unknown")), page_number=res.page_number)
                    doc_page_key = (res.file_path, res.page_number)
                    # Limit the maximum number of images we attach per request
                    if doc_page_key not in rendered_pages and len(visual_attachments) < 5:
                        file_path = res.file_path
                        if file_path.startswith("/tmp/uploads/") and not os.path.exists(file_path):
                            fallback = os.path.join(str(settings.UPLOAD_DIRECTORY), os.path.basename(file_path))
                            if os.path.exists(fallback):
                                file_path = fallback
                        
                        if os.path.exists(file_path):
                            try:
                                with fitz.open(file_path) as pdf_doc:
                                    page_index = res.page_number - 1
                                    if 0 <= page_index < pdf_doc.page_count:
                                        page = pdf_doc.load_page(page_index)
                                        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                                        img_data = pix.tobytes("png")
                                        visual_attachments.append(ImageAttachment(data=img_data, mime_type="image/png"))
                                        rendered_pages.add(doc_page_key)
                                        self._logger.info("visual_context_attached", page_number=res.page_number)
                                    else:
                                        self._logger.warning("visual_context_failed", file_path=file_path, page_number=res.page_number, reason="invalid page number")
                            except Exception as exc:
                                self._logger.warning("visual_context_failed", file_path=file_path, page_number=res.page_number, reason=str(exc))
                        else:
                            self._logger.warning("visual_context_failed", file_path=file_path, page_number=res.page_number, reason="file not found")

            context_text = "\n\n".join(context_parts)
            
            # 3. Build prompts
            prompt_messages = [PromptMessage(role="system", content=SYSTEM_PROMPT)]
            
            # Add history
            for msg in conversation.messages:
                prompt_messages.append(PromptMessage(role=msg.role.value, content=msg.content))
                
            # Add current user message with context
            augmented_prompt = f"Context:\n{context_text}\n\nUser Question: {user_message}"
            prompt_messages.append(PromptMessage(role="user", content=augmented_prompt, images=visual_attachments if visual_attachments else None))
        except Exception as e:
            self._logger.error(f"Context retrieval error: {str(e)}", exc_info=True, conversation_id=str(conversation_id))
            error_msg = f"\n\n[System: Document retrieval failed: {str(e)}]"
            yield error_msg
            await self._message_repo.create(
                MessageCreate(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=error_msg,
                    citations=[],
                    model_name=self._llm_gateway.model_name,
                )
            )
            return

        # 4. Stream response and capture full text
        self._logger.info(
            "streaming_response_started", 
            conversation_id=str(conversation_id),
            model=self._llm_gateway.model_name,
            retrieved_chunk_count=len(citations),
            prompt_size_chars=len(augmented_prompt)
        )
        
        full_response = ""
        try:
            async for chunk in self._llm_gateway.stream(prompt_messages):
                full_response += chunk
                yield chunk
        except ProviderTimeoutError as e:
            self._logger.error("Provider timeout", exc_info=True, conversation_id=str(conversation_id))
            error_msg = "\n\n[System: The AI provider timed out. Please try again.]"
            full_response += error_msg
            yield error_msg
        except ProviderError as e:
            self._logger.error(f"Provider error: {str(e)}", exc_info=True, conversation_id=str(conversation_id))
            error_msg = f"\n\n[System: AI provider error: {str(e)}]"
            full_response += error_msg
            yield error_msg
        except Exception as e:
            self._logger.error(f"Unexpected error: {str(e)}", exc_info=True, conversation_id=str(conversation_id))
            error_msg = f"\n\n[System: An unexpected error occurred: {str(e)}]"
            full_response += error_msg
            yield error_msg
        finally:
            # 5. Save assistant message
            await self._message_repo.create(
                MessageCreate(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    citations=citations,
                    model_name=self._llm_gateway.model_name,
                )
            )
            await self._message_repo._session.commit()
            self._logger.info(
                "streaming_response_completed", 
                conversation_id=str(conversation_id),
                completion_size_chars=len(full_response),
            )
