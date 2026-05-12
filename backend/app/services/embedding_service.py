from __future__ import annotations

import hashlib
import math
import re


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
STOPWORDS = {"a", "an", "the", "can", "be", "is", "are", "do", "does", "to", "of", "and", "or"}
CHINESE_STOP_CHARS = {"这", "是", "的", "了", "吗", "呢", "请", "问", "个", "一"}
CHINESE_TERMS = [
    "简历",
    "退款",
    "政策",
    "企业版",
    "个人版",
    "售后",
    "教育背景",
    "联系方式",
    "工作经历",
    "实习经历",
    "项目经历",
    "求职意向",
    "候选人",
    "知识库",
    "文档",
]


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in TOKEN_RE.findall(text):
        normalized = _normalize_token(raw_token)
        if normalized in STOPWORDS:
            continue
        if _has_chinese(normalized):
            tokens.extend(_tokenize_chinese(normalized))
        else:
            tokens.append(normalized)
    return [token for token in tokens if token]


def _normalize_token(token: str) -> str:
    lowered = token.lower()
    if len(lowered) > 3 and lowered.endswith("s"):
        return lowered[:-1]
    return lowered


def _has_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _tokenize_chinese(text: str) -> list[str]:
    tokens: list[str] = []
    for term in CHINESE_TERMS:
        if term in text:
            tokens.append(term)
    tokens.extend(
        char
        for char in text
        if "\u4e00" <= char <= "\u9fff" and char not in CHINESE_STOP_CHARS
    )
    seen: set[str] = set()
    deduped: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


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
