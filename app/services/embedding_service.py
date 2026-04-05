from __future__ import annotations

from functools import cached_property

from sentence_transformers import SentenceTransformer

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_name = settings.embedding_model_name

    @cached_property
    def _model(self) -> SentenceTransformer:
        return SentenceTransformer(self._model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        prepared = [self._prefix_document(text) for text in texts]
        vectors = self._model.encode(
            prepared,
            batch_size=self._settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        vector = self._model.encode(
            self._prefix_query(query),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    @staticmethod
    def _prefix_document(text: str) -> str:
        return f"passage: {text.strip()}"

    @staticmethod
    def _prefix_query(query: str) -> str:
        return f"query: {query.strip()}"
