from __future__ import annotations

from pathlib import Path
import re

import httpx
from pypdf import PdfReader

from app.core.config import Settings
from app.models.schemas import Paper, ParsedDocument


class PDFService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def download_and_parse(self, paper: Paper) -> ParsedDocument:
        pdf_path = await self._download_pdf(paper)
        text, page_count = self._parse_pdf(pdf_path)
        return ParsedDocument(paper=paper, pdf_path=str(pdf_path), text=text, page_count=page_count)

    async def _download_pdf(self, paper: Paper) -> Path:
        safe_name = self._safe_filename(paper.paper_id)
        target = self._settings.download_dir / f"{safe_name}.pdf"
        if target.exists() and target.stat().st_size > 0:
            return target

        headers = {"User-Agent": self._settings.user_agent}
        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds, headers=headers, follow_redirects=True) as client:
            response = await client.get(str(paper.pdf_url))
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            raise ValueError(f"Downloaded file for {paper.paper_id} is not a valid PDF response.")

        target.write_bytes(response.content)
        if target.stat().st_size == 0:
            target.unlink(missing_ok=True)
            raise ValueError(f"Downloaded PDF for {paper.paper_id} was empty.")

        return target

    def _parse_pdf(self, pdf_path: Path) -> tuple[str, int]:
        reader = PdfReader(str(pdf_path))
        pages = []
        extracted_page_count = 0

        for page in reader.pages:
            content = self._normalize_text(page.extract_text() or "")
            if content:
                pages.append(content)
                extracted_page_count += 1

        return "\n\n".join(pages).strip(), extracted_page_count

    @staticmethod
    def _safe_filename(value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
        return sanitized or "paper"

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.replace("\x00", " ")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()
