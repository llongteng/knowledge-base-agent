from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.document_parser import ParsedSegment


@dataclass
class DocumentChunk:
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    title_path: Optional[str] = None
    row_number: Optional[int] = None
    token_count: int = 0


def chunk_segments(
    segments: list[ParsedSegment], chunk_size: int = 512, overlap: int = 80
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for segment in segments:
        text = " ".join(segment.content.split())
        if not text:
            continue
        start = 0
        while start < len(text):
            part = text[start : start + chunk_size]
            chunks.append(
                DocumentChunk(
                    content=part,
                    chunk_index=len(chunks),
                    page_number=segment.page_number,
                    paragraph_index=segment.paragraph_index,
                    title_path=segment.title_path,
                    row_number=segment.row_number,
                    token_count=max(1, len(part.split())),
                )
            )
            if start + chunk_size >= len(text):
                break
            start += max(1, chunk_size - overlap)
    return chunks
