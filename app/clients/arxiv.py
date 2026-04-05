from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from app.core.config import Settings
from app.models.schemas import Paper


class ArxivClient:
    base_url = "https://export.arxiv.org/api/query"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, query: str, max_results: int) -> list[Paper]:
        normalized_query = self._normalize_query(query)
        params = {
            "search_query": f"all:{normalized_query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds, headers=headers) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()

        return self._parse_feed(response.text)

    def _parse_feed(self, xml_text: str) -> list[Paper]:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_text)
        papers: list[Paper] = []

        for entry in root.findall("atom:entry", ns):
            paper_id = entry.findtext("atom:id", default="", namespaces=ns).rsplit("/", maxsplit=1)[-1]
            title = self._clean_text(entry.findtext("atom:title", default="", namespaces=ns) or "")
            summary = self._clean_text(entry.findtext("atom:summary", default="", namespaces=ns) or "")
            entry_url = entry.findtext("atom:id", default="", namespaces=ns) or ""
            published = entry.findtext("atom:published", default="", namespaces=ns)
            authors = [
                self._clean_text(author.findtext("atom:name", default="", namespaces=ns) or "")
                for author in entry.findall("atom:author", ns)
                if self._clean_text(author.findtext("atom:name", default="", namespaces=ns) or "")
            ]

            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("rel") == "alternate" and link.attrib.get("href"):
                    entry_url = link.attrib["href"]
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href", "")
                    break

            if not paper_id or not title:
                continue

            if not pdf_url:
                pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

            papers.append(
                Paper(
                    paper_id=paper_id,
                    title=title,
                    summary=summary,
                    pdf_url=pdf_url,
                    entry_url=entry_url,
                    published=published,
                    authors=authors,
                )
            )

        return papers

    @staticmethod
    def _normalize_query(query: str) -> str:
        return re.sub(r"\s+", " ", query).strip()

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
