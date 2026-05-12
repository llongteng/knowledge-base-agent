from __future__ import annotations

import json
import math
from collections import Counter

from sqlalchemy.orm import Session

from app import models
from app.services.embedding_service import EmbeddingService, cosine_similarity, lexical_overlap_score, tokenize
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

        corpus_stats = _build_corpus_stats(rows)
        results: list[RetrievedChunk] = []
        for chunk, document in rows:
            score = self._score(query, query_vector, chunk, document, corpus_stats)
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
        return _dedupe_results(results)[:top_k]

    def _score(
        self,
        query: str,
        query_vector: list[float],
        chunk: models.DocumentChunk,
        document: models.Document,
        corpus_stats: dict,
    ) -> float:
        content_overlap = lexical_overlap_score(query, chunk.content)
        filename_overlap = lexical_overlap_score(query, document.filename)
        title_overlap = lexical_overlap_score(query, chunk.title_path or "")
        vector_score = cosine_similarity(query_vector, json.loads(chunk.vector))
        bm25_score = _bm25_score(query, chunk.content, corpus_stats)
        score = (
            bm25_score * 0.38
            + content_overlap * 0.27
            + vector_score * 0.18
            + filename_overlap * 0.11
            + title_overlap * 0.06
        )

        if filename_overlap > 0:
            score += 0.16
        if title_overlap > 0:
            score += 0.08
        if (chunk.paragraph_index or 999) <= 2:
            score += 0.04
        if chunk.row_number:
            score += 0.03
        if _is_resume_identity_question(query, document.filename) and (chunk.paragraph_index or 999) <= 2:
            score += 0.45
        if "简历" in query and "简历" not in document.filename and "简历" not in chunk.content:
            score *= 0.45

        return min(score, 1.0)


def _is_resume_identity_question(query: str, filename: str) -> bool:
    return "简历" in query and any(marker in query for marker in ["谁", "姓名", "本人", "候选人"]) and "简历" in filename


def _build_corpus_stats(rows: list[tuple[models.DocumentChunk, models.Document]]) -> dict:
    tokenized_docs = [tokenize(chunk.content) for chunk, _document in rows]
    doc_freq: Counter[str] = Counter()
    for tokens in tokenized_docs:
        doc_freq.update(set(tokens))
    avg_length = sum(len(tokens) for tokens in tokenized_docs) / max(1, len(tokenized_docs))
    return {
        "doc_count": len(tokenized_docs),
        "doc_freq": doc_freq,
        "avg_length": avg_length,
    }


def _bm25_score(query: str, content: str, corpus_stats: dict) -> float:
    query_tokens = tokenize(query)
    content_tokens = tokenize(content)
    if not query_tokens or not content_tokens:
        return 0.0

    term_counts = Counter(content_tokens)
    doc_count = corpus_stats["doc_count"]
    doc_freq = corpus_stats["doc_freq"]
    avg_length = corpus_stats["avg_length"] or 1.0
    k1 = 1.4
    b = 0.72
    raw_score = 0.0
    for token in set(query_tokens):
        frequency = term_counts[token]
        if frequency == 0:
            continue
        idf = math.log(1 + (doc_count - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5))
        denominator = frequency + k1 * (1 - b + b * len(content_tokens) / avg_length)
        raw_score += idf * frequency * (k1 + 1) / denominator
    return raw_score / (raw_score + 2.0) if raw_score > 0 else 0.0


def _dedupe_results(results: list[RetrievedChunk]) -> list[RetrievedChunk]:
    deduped: list[RetrievedChunk] = []
    seen_fingerprints: set[str] = set()
    for result in results:
        fingerprint = " ".join(tokenize(result.content)[:24])
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        deduped.append(result)
    return deduped


vector_store = SQLiteVectorStore()
