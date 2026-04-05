from __future__ import annotations

import re

from app.core.config import Settings
from app.models.schemas import DocumentChunk, ParsedDocument


class TextChunkingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]:
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        index = 0
        current_parts: list[str] = []
        current_length = 0

        for paragraph in self._split_paragraphs(text):
            paragraph_length = len(paragraph)
            if current_parts and current_length + paragraph_length > self._settings.chunk_size:
                snippet = "\n\n".join(current_parts).strip()
                chunks.append(self._build_chunk(document, index, snippet))
                index += 1
                current_parts = self._carry_overlap(snippet)
                current_length = sum(len(part) for part in current_parts)

            if paragraph_length > self._settings.chunk_size:
                oversized_segments = self._split_oversized_paragraph(paragraph)
                for segment in oversized_segments:
                    segment = segment.strip()
                    if not segment:
                        continue
                    if current_parts and current_length + len(segment) > self._settings.chunk_size:
                        snippet = "\n\n".join(current_parts).strip()
                        chunks.append(self._build_chunk(document, index, snippet))
                        index += 1
                        current_parts = self._carry_overlap(snippet)
                        current_length = sum(len(part) for part in current_parts)

                    current_parts.append(segment)
                    current_length += len(segment)
            else:
                current_parts.append(paragraph)
                current_length += paragraph_length

        if current_parts:
            snippet = "\n\n".join(current_parts).strip()
            if snippet:
                chunks.append(self._build_chunk(document, index, snippet))

        return chunks

    def _build_chunk(self, document: ParsedDocument, index: int, content: str) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=f"{document.paper.paper_id}-{index}",
            paper_id=document.paper.paper_id,
            title=document.paper.title,
            content=content,
            source_url=document.paper.entry_url,
        )

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        return paragraphs or [text]

    def _split_oversized_paragraph(self, paragraph: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        if len(sentences) <= 1:
            return [paragraph[i:i + self._settings.chunk_size] for i in range(0, len(paragraph), self._settings.chunk_size)]

        segments: list[str] = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            projected = f"{current} {sentence}".strip()
            if current and len(projected) > self._settings.chunk_size:
                segments.append(current.strip())
                current = sentence
            else:
                current = projected

        if current:
            segments.append(current.strip())

        return segments

    def _carry_overlap(self, content: str) -> list[str]:
        if self._settings.chunk_overlap <= 0:
            return []

        overlap_text = content[-self._settings.chunk_overlap :].strip()
        if not overlap_text:
            return []

        overlap_paragraphs = self._split_paragraphs(overlap_text)
        return overlap_paragraphs[-1:]
