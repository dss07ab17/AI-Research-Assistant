from app.clients.arxiv import ArxivClient
from app.core.config import Settings
from app.models.schemas import Paper


class PaperSearchService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = ArxivClient(settings)

    async def search(self, query: str, max_papers: int | None = None) -> list[Paper]:
        limit = max_papers or self._settings.max_papers
        return await self._client.search(query=query, max_results=limit)
