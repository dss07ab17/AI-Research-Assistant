from __future__ import annotations

import asyncio

from fastapi import HTTPException

from app.core.config import Settings
from app.models.schemas import QueryRequest, QueryResponse
from app.services.answer_service import AnswerService
from app.services.chunking import TextChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.paper_search import PaperSearchService
from app.services.pdf_service import PDFService
from app.services.vector_store import InMemoryVectorStore


class ResearchPipeline:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._paper_search = PaperSearchService(settings)
        self._pdf_service = PDFService(settings)
        self._chunker = TextChunkingService(settings)
        self._embedding_service = EmbeddingService(settings)
        self._answer_service = AnswerService(settings.openai_api_key, settings.openai_model)

    async def run(self, request: QueryRequest) -> QueryResponse:
        papers = await self._paper_search.search(request.query, request.max_papers)
        if not papers:
            raise HTTPException(status_code=404, detail="No papers found for the supplied query.")

        parsed_documents = await self._download_and_parse_all(papers)
        chunks = [chunk for document in parsed_documents for chunk in self._chunker.chunk(document)]
        if not chunks:
            raise HTTPException(status_code=422, detail="Papers were found, but no extractable PDF text was available.")

        vector_store = InMemoryVectorStore(self._settings)
        embeddings = self._embedding_service.embed_texts([chunk.content for chunk in chunks])
        vector_store.add(chunks, embeddings)

        query_embedding = self._embedding_service.embed_query(request.query)
        retrieved_chunks = vector_store.search(request.query, query_embedding, self._settings.max_chunks)
        return self._answer_service.generate(request.query, retrieved_chunks)

    async def _download_and_parse_all(self, papers):
        results = await asyncio.gather(
            *(self._pdf_service.download_and_parse(paper) for paper in papers),
            return_exceptions=True,
        )
        parsed_documents = [result for result in results if not isinstance(result, Exception) and result.text.strip()]
        if not parsed_documents:
            raise HTTPException(status_code=502, detail="Unable to download or parse any paper PDFs.")
        return parsed_documents
