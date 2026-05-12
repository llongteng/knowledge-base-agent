from __future__ import annotations

from dataclasses import dataclass

from app.services.agent_planner import plan_question
from app.services.embedding_service import tokenize
from app.services.retrieval_service import RetrievedChunk


@dataclass
class Evidence:
    source_id: str
    chunk: RetrievedChunk
    claim_type: str
    support_text: str
    relevance_reason: str
    confidence: float


def select_evidence(question: str, chunks: list[RetrievedChunk], limit: int = 4) -> list[Evidence]:
    question_type = plan_question(question)["question_type"]
    evidence: list[Evidence] = []
    for chunk in chunks:
        confidence, reason = _support_score(question, question_type, chunk)
        if confidence < 0.52:
            continue
        evidence.append(
            Evidence(
                source_id=f"S{len(evidence) + 1}",
                chunk=chunk,
                claim_type=question_type,
                support_text=chunk.content,
                relevance_reason=reason,
                confidence=confidence,
            )
        )
        if len(evidence) >= limit:
            break
    return evidence


def _support_score(question: str, question_type: str, chunk: RetrievedChunk) -> tuple[float, str]:
    text = chunk.content
    filename = chunk.filename.lower()
    tokens = set(tokenize(question))
    content_tokens = set(tokenize(text))
    overlap = len(tokens & content_tokens) / max(1, min(len(tokens), len(content_tokens)))
    score = max(chunk.score, overlap)
    reason = "命中问题关键词"

    if question_type == "resume_identity":
        if ("简历" in filename or "简历" in text) and (chunk.paragraph_index or 999) <= 2:
            return min(1.0, score + 0.35), "命中简历首页身份信息"
        return 0.0, "未命中简历身份字段"

    if question_type == "policy":
        policy_terms = {"退款", "退费", "售后", "条件", "规则", "人工审核", "超过", "7", "七"}
        if policy_terms & content_tokens or any(term in text.lower() for term in ["refund", "manual review"]):
            if "7" in tokens and not ({"7", "七"} & content_tokens or "7" in text):
                score *= 0.72
            return min(1.0, score + 0.16), "命中政策条件或处理规则"
        return score * 0.4, "未命中政策条件"

    if question_type == "extraction":
        extraction_terms = {"教育背景", "联系方式", "工作经历", "项目经历", "经验", "经历", "agent", "ai"}
        if extraction_terms & content_tokens or any(term in text.lower() for term in ["agent", "ai"]):
            return min(1.0, score + 0.12), "命中信息抽取字段"
        return score * 0.45, "未命中目标字段"

    if question_type == "summary":
        if chunk.title_path or overlap > 0:
            return min(1.0, score + 0.08), "命中可总结内容"
        return score * 0.6, "总结依据较弱"

    return score, reason
