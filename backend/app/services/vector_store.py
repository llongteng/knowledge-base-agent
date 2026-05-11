from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app import models
from app.services.embedding_service import EmbeddingService, cosine_similarity, lexical_overlap_score
from app.services.retrieval_service import RetrievedChunk


class SQLiteVectorStore:
    def __init__(self, embedding_service: EmbeddingService | None = None):
        self.embedding_service = embedding_service or EmbeddingService()

    def encode(self, content: str) -> str:
        return json.dumps(self.embedding_service.embed(content))

    def search(self, db: Session, knowledge_base_id: int, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        query_vector = self.embedding_service.embed(query)
        rows = (
            db.query(models.DocumentChunk, models.Document)
            .join(models.Document, models.DocumentChunk.document_id == models.Document.id)
            .filter(
                models.Document.knowledge_base_id == knowledge_base_id,
                models.Document.status == "ready",
            )
            .all()
        )

        results: list[RetrievedChunk] = []
        for chunk, document in rows:
            score = max(
                cosine_similarity(query_vector, json.loads(chunk.vector)),
                lexical_overlap_score(query, chunk.content),
            )
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    filename=document.filename,
                    content=chunk.content,
                    score=score,
                    page_number=chunk.page_number,
                    paragraph_index=chunk.paragraph_index,
                    title_path=chunk.title_path,
                    row_number=chunk.row_number,
                )
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]


vector_store = SQLiteVectorStore()
