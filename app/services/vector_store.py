from __future__ import annotations

from math import sqrt
import re

from app.core.config import Settings
from app.models.schemas import DocumentChunk, RetrievedChunk


class InMemoryVectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._items: list[tuple[DocumentChunk, list[float]]] = []

    def add(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        self._items.extend(zip(chunks, embeddings, strict=False))

    def search(self, query: str, query_embedding: list[float], limit: int) -> list[RetrievedChunk]:
        query_terms = self._tokenize(query)
        scored: list[RetrievedChunk] = []

        for chunk, embedding in self._items:
            semantic_score = self._cosine_similarity(query_embedding, embedding)
            lexical_score = self._lexical_overlap_score(query_terms, chunk.content)
            score = semantic_score + (self._settings.lexical_boost_weight * lexical_score)
            scored.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=score,
                    semantic_score=semantic_score,
                    lexical_score=lexical_score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return self._select_diverse_results(scored, limit)

    def _select_diverse_results(self, ranked: list[RetrievedChunk], limit: int) -> list[RetrievedChunk]:
        selected: list[RetrievedChunk] = []
        per_paper_counts: dict[str, int] = {}

        for candidate in ranked:
            paper_id = candidate.chunk.paper_id
            current_count = per_paper_counts.get(paper_id, 0)
            if current_count >= self._settings.max_chunks_per_paper:
                continue

            selected.append(candidate)
            per_paper_counts[paper_id] = current_count + 1
            if len(selected) >= limit:
                break

        return selected

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(token) > 2}

    def _lexical_overlap_score(self, query_terms: set[str], content: str) -> float:
        if not query_terms:
            return 0.0

        content_terms = self._tokenize(content)
        if not content_terms:
            return 0.0

        overlap = query_terms.intersection(content_terms)
        return len(overlap) / len(query_terms)
