from __future__ import annotations

import hashlib
import math
import re


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
STOPWORDS = {"a", "an", "the", "can", "be", "is", "are", "do", "does", "to", "of", "and", "or"}


def tokenize(text: str) -> list[str]:
    return [
        normalized
        for token in TOKEN_RE.findall(text)
        if (normalized := _normalize_token(token)) not in STOPWORDS
    ]


def _normalize_token(token: str) -> str:
    lowered = token.lower()
    if len(lowered) > 3 and lowered.endswith("s"):
        return lowered[:-1]
    return lowered


class EmbeddingService:
    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def lexical_overlap_score(query: str, content: str) -> float:
    query_tokens = set(tokenize(query))
    content_tokens = set(tokenize(content))
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = query_tokens & content_tokens
    return len(overlap) / min(len(query_tokens), len(content_tokens))
