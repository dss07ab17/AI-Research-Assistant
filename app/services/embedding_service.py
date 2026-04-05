from __future__ import annotations

from openai import OpenAI

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_name = settings.embedding_model_name
        self._client = OpenAI(api_key=settings.openai_api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        prepared = [self._prefix_document(text) for text in texts]
        response = self._client.embeddings.create(
            model=self._model_name,
            input=prepared,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        response = self._client.embeddings.create(
            model=self._model_name,
            input=self._prefix_query(query),
        )
        return response.data[0].embedding

    @staticmethod
    def _prefix_document(text: str) -> str:
        return f"passage: {text.strip()}"

    @staticmethod
    def _prefix_query(query: str) -> str:
        return f"query: {query.strip()}"
