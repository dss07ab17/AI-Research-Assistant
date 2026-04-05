from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from app.models.schemas import Citation, QueryResponse, RetrievedChunk


logger = logging.getLogger(__name__)


class AnswerService:
    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def generate(self, query: str, chunks: list[RetrievedChunk]) -> QueryResponse:
        try:
            return self._generate_with_openai(query, chunks)
        except Exception as exc:
            logger.warning("OpenAI synthesis failed, falling back to extractive mode: %s", exc)
            return self._generate_extractively(query, chunks)

    def _generate_with_openai(self, query: str, chunks: list[RetrievedChunk]) -> QueryResponse:
        client = OpenAI(api_key=self._api_key)
        context = "\n\n".join(
            [
                (
                    f"[{index + 1}] Title: {item.chunk.title}\n"
                    f"Source: {item.chunk.source_url}\n"
                    f"Semantic score: {item.semantic_score:.3f}\n"
                    f"Lexical score: {item.lexical_score:.3f}\n"
                    f"Excerpt: {item.chunk.content}"
                )
                for index, item in enumerate(chunks)
            ]
        )
        prompt = (
            "Answer the user's research question using only the supplied context. "
            "Do not invent evidence beyond the context. "
            "Return strict JSON with keys answer, key_points, citations. "
            "The answer must be a concise synthesis that mentions supporting paper titles in prose when useful. "
            "key_points must be an array of short evidence-backed bullets. "
            "citations must be an array of unique objects, each with title and link.\n\n"
            f"Question: {query}\n\nContext:\n{context}"
        )

        response = client.responses.create(
            model=self._model,
            input=prompt,
            temperature=0.2,
        )
        payload = self._parse_json_payload(response.output_text)
        return self._sanitize_response(QueryResponse(**payload))

    def _generate_extractively(self, query: str, chunks: list[RetrievedChunk]) -> QueryResponse:
        citations = self._build_unique_citations(chunks)
        top_chunks = chunks[:3]
        evidence_sentences = [summary for item in top_chunks if (summary := self._summarize_chunk(item))]
        key_points = [point for item in chunks[:5] if (point := self._build_key_point(item))]

        if evidence_sentences:
            answer = (
                f"Based on the retrieved papers, the evidence for '{query}' points to "
                + " ".join(evidence_sentences)
            )
        else:
            answer = f"No relevant research content was found for '{query}'."

        response = QueryResponse(
            answer=answer,
            key_points=key_points or ["No extractable evidence was available from the retrieved papers."],
            citations=citations,
        )
        return self._sanitize_response(response)

    def _build_unique_citations(self, chunks: list[RetrievedChunk]) -> list[Citation]:
        citations: list[Citation] = []
        seen_links: set[str] = set()
        for item in chunks:
            link = str(item.chunk.source_url)
            if link in seen_links:
                continue
            citations.append(Citation(title=item.chunk.title, link=link))
            seen_links.add(link)
        return citations

    def _summarize_chunk(self, item: RetrievedChunk) -> str:
        snippet = self._clean_excerpt(item.chunk.content, 220)
        if not snippet:
            return ""
        return f"{item.chunk.title} suggests {snippet}"

    def _build_key_point(self, item: RetrievedChunk) -> str:
        snippet = self._clean_excerpt(item.chunk.content, 170)
        if not snippet:
            return ""
        return f"{snippet} ({item.chunk.title})"

    def _clean_excerpt(self, text: str, limit: int) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= limit:
            return normalized
        clipped = normalized[:limit].rsplit(" ", maxsplit=1)[0].strip()
        return f"{clipped}..."

    def _parse_json_payload(self, payload: str) -> dict:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", payload, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    def _sanitize_response(self, response: QueryResponse) -> QueryResponse:
        deduped_citations: list[Citation] = []
        seen_links: set[str] = set()

        for citation in response.citations:
            link = str(citation.link).strip()
            title = citation.title.strip()
            if not link or not title or link in seen_links:
                continue
            deduped_citations.append(Citation(title=title, link=link))
            seen_links.add(link)

        key_points = [point.strip() for point in response.key_points if point.strip()]
        answer = response.answer.strip()

        return QueryResponse(
            answer=answer or "No answer could be synthesized from the retrieved evidence.",
            key_points=key_points[:5] or ["No extractable evidence was available from the retrieved papers."],
            citations=deduped_citations,
        )
