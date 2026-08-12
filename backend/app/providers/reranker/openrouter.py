"""OpenRouter multimodal reranker gateway."""

import asyncio
import base64
import os
import structlog
from typing import Any

import fitz
import httpx

from app.config.settings import Settings
from app.models.chunk import Chunk
from app.providers.reranker.base import RerankerGateway, RerankResult


class OpenRouterRerankerGateway(RerankerGateway):
    """Multimodal reranking using NVIDIA Llama Nemotron via OpenRouter."""

    def __init__(self, config: Settings) -> None:
        self.api_key = config.OPENROUTER_API_KEY
        self.base_url = config.OPENROUTER_BASE_URL.rstrip("/")
        self.model_name = config.OPENROUTER_RERANK_MODEL
        self.timeout = config.RERANKER_TIMEOUT_SECONDS
        self.upload_dir = str(config.UPLOAD_DIRECTORY)
        self._logger = structlog.get_logger(__name__)

    async def rerank(
        self,
        query: str,
        candidates: list[tuple[Chunk, float]],
        top_k: int
    ) -> list[RerankResult]:
        """Rerank candidates. Falls back to original vector order on failure."""
        if not candidates or not self.api_key:
            return self._create_fallback(candidates, top_k)

        try:
            documents = self._build_documents_payload(candidates)
            if not documents:
                return self._create_fallback(candidates, top_k)

            payload = {
                "model": self.model_name,
                "query": query,
                "documents": documents,
                "top_n": top_k
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "Enterprise AI Knowledge Platform",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/rerank",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                if "results" not in data:
                    self._logger.error("reranker_invalid_response", response=data)
                    return self._create_fallback(candidates, top_k)

                results = data["results"]
                return self._map_results(results, candidates)

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self._logger.warning("reranker_rate_limited", error=str(exc))
            else:
                self._logger.error("reranker_http_error", status_code=exc.response.status_code, response=exc.response.text)
            return self._create_fallback(candidates, top_k)
        except httpx.TimeoutException:
            self._logger.warning("reranker_timeout", timeout=self.timeout)
            return self._create_fallback(candidates, top_k)
        except Exception as exc:
            self._logger.exception("reranker_unexpected_error", error=str(exc))
            return self._create_fallback(candidates, top_k)

    def _build_documents_payload(self, candidates: list[tuple[Chunk, float]]) -> list[dict[str, Any]]:
        documents = []
        # Optimization: cache parsed documents to avoid reopening the same PDF
        open_pdfs: dict[str, fitz.Document] = {}

        try:
            for chunk, _ in candidates:
                if chunk.metadata_.get("source_type") == "visual":
                    doc = self._get_visual_representation(chunk, open_pdfs)
                    if doc:
                        documents.append(doc)
                    else:
                        documents.append({"text": chunk.content})
                else:
                    # Limit text length to avoid context overflow issues
                    documents.append({"text": chunk.content[:4000]})
        finally:
            for pdf_doc in open_pdfs.values():
                pdf_doc.close()

        return documents

    def _get_visual_representation(self, chunk: Chunk, open_pdfs: dict[str, fitz.Document]) -> dict[str, Any] | None:
        """Extract page image from local PDF for multimodal reranking."""
        try:
            if not chunk.document or not chunk.page_number:
                return None

            file_path = chunk.document.file_path
            if not file_path:
                return None

            if not os.path.exists(file_path):
                fallback_path = os.path.join(self.upload_dir, os.path.basename(file_path))
                if os.path.exists(fallback_path):
                    file_path = fallback_path
                else:
                    return None

            if file_path not in open_pdfs:
                open_pdfs[file_path] = fitz.open(file_path)
            
            pdf_doc = open_pdfs[file_path]
            page_index = chunk.page_number - 1
            if page_index < 0 or page_index >= len(pdf_doc):
                return None

            page = pdf_doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
            img_data = pix.tobytes("png")
            image_base64 = base64.b64encode(img_data).decode("utf-8")

            return {
                "text": chunk.content,
                "image": f"data:image/png;base64,{image_base64}"
            }
        except Exception as exc:
            self._logger.warning("reranker_visual_extraction_failed", chunk_id=str(chunk.id), error=str(exc))
            return None

    def _map_results(self, rerank_results: list[dict[str, Any]], candidates: list[tuple[Chunk, float]]) -> list[RerankResult]:
        mapped = []
        for result in rerank_results:
            idx = result.get("index")
            if idx is None or idx < 0 or idx >= len(candidates):
                continue
                
            chunk, distance = candidates[idx]
            relevance_score = result.get("relevance_score", 0.0)
            
            mapped.append(
                RerankResult(
                    chunk=chunk,
                    vector_similarity=1.0 - distance,
                    rerank_score=relevance_score,
                    original_rank=idx
                )
            )
            
        # The results from the API are already sorted by relevance, but we maintain the order
        # as returned by the API which is expected to be descending by relevance_score.
        return mapped

    def _create_fallback(self, candidates: list[tuple[Chunk, float]], top_k: int) -> list[RerankResult]:
        """Convert original vector candidates to RerankResult, preserving order."""
        mapped = []
        for i, (chunk, distance) in enumerate(candidates[:top_k]):
            mapped.append(
                RerankResult(
                    chunk=chunk,
                    vector_similarity=1.0 - distance,
                    rerank_score=0.0,
                    original_rank=i
                )
            )
        return mapped
