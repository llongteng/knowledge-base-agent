from __future__ import annotations

from app.services.retrieval_service import RetrievedChunk


def build_answer(question: str, chunks: list[RetrievedChunk]) -> tuple[str, list[dict]]:
    if not chunks:
        return "当前知识库未找到可靠依据，暂时无法回答。请补充相关文档或换个问法。", []

    citations = []
    sentences = []
    for index, chunk in enumerate(chunks[:3], start=1):
        source_id = f"S{index}"
        sentences.append(f"{_summarize(chunk.content)} [[{source_id}]]")
        citations.append(
            {
                "id": source_id,
                "source_type": "knowledge_base",
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "document": chunk.filename,
                "page": chunk.page_number,
                "paragraph": chunk.paragraph_index,
                "title_path": chunk.title_path,
                "row": chunk.row_number,
                "snippet": chunk.content,
                "score": chunk.score,
            }
        )
    return "\n".join(sentences), citations


def _summarize(content: str) -> str:
    stripped = " ".join(content.split())
    if len(stripped) <= 160:
        return stripped
    return stripped[:157].rstrip() + "..."
