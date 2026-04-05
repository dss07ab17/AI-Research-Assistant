from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET

import httpx
from fastapi import HTTPException

from app.core.config import Settings
from app.models.schemas import Paper


logger = logging.getLogger(__name__)


class ArxivClient:
    base_url = "https://export.arxiv.org/api/query"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, query: str, max_results: int) -> list[Paper]:
        headers = {"User-Agent": self._settings.user_agent}
        query_candidates = self._build_query_candidates(query)

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds, headers=headers) as client:
            last_error: Exception | None = None

            for candidate in query_candidates:
                params = {
                    "search_query": f"all:{candidate}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                }

                for attempt in range(3):
                    try:
                        response = await client.get(self.base_url, params=params)
                        response.raise_for_status()
                        papers = self._parse_feed(response.text)
                        if papers:
                            return papers
                        break
                    except httpx.HTTPStatusError as exc:
                        last_error = exc
                        status_code = exc.response.status_code
                        logger.warning(
                            "arXiv search failed for candidate '%s' with status %s on attempt %s",
                            candidate,
                            status_code,
                            attempt + 1,
                        )
                        if status_code < 500:
                            break
                        await asyncio.sleep(1.0 * (attempt + 1))
                    except httpx.HTTPError as exc:
                        last_error = exc
                        logger.warning(
                            "arXiv search transport error for candidate '%s' on attempt %s: %s",
                            candidate,
                            attempt + 1,
                            exc,
                        )
                        await asyncio.sleep(1.0 * (attempt + 1))

            if last_error is not None:
                raise HTTPException(
                    status_code=502,
                    detail="Paper search is temporarily unavailable from arXiv. Please retry with a shorter topic phrase.",
                ) from last_error

        return []

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
        normalized = query.lower()
        normalized = re.sub(r"[^\w\s-]", " ", normalized)
        normalized = re.sub(r"\b(what|are|is|the|latest|recent|improvements|improvement|for|in|on|of|to|a|an)\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _build_query_candidates(self, query: str) -> list[str]:
        raw = re.sub(r"\s+", " ", query).strip()
        normalized = self._normalize_query(query)
        candidates = [candidate for candidate in [normalized, raw] if candidate]

        if normalized:
            keywords = normalized.split()
            if len(keywords) > 4:
                candidates.append(" ".join(keywords[:4]))
            if len(keywords) > 2:
                candidates.append(" AND ".join(keywords[:3]))

        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate not in seen:
                deduped.append(candidate)
                seen.add(candidate)

        return deduped or ["research"]

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
