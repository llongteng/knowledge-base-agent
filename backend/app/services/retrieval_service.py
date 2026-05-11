from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    filename: str
    content: str
    score: float
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    title_path: Optional[str] = None
    row_number: Optional[int] = None


@dataclass
class RetrievalDecision:
    can_answer: bool
    reason: str
    confidence_label: str


def decide_retrieval(chunks: list[RetrievedChunk]) -> RetrievalDecision:
    if not chunks:
        return RetrievalDecision(False, "当前知识库未找到可靠依据", "none")

    top_score = chunks[0].score
    if top_score >= 0.72:
        return RetrievalDecision(True, "找到高置信知识库依据", "high")
    if top_score >= 0.62:
        return RetrievalDecision(True, "找到可用依据，但内容可能不完整", "medium")
    return RetrievalDecision(False, "当前知识库未找到可靠依据", "low")
