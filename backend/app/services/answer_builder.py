from __future__ import annotations

import re

from app.services.agent_planner import plan_question
from app.services.evidence_service import Evidence, select_evidence
from app.services.retrieval_service import RetrievedChunk


def build_answer(question: str, chunks: list[RetrievedChunk]) -> tuple[str, list[dict]]:
    return build_answer_from_evidence(question, select_evidence(question, chunks))


def build_answer_from_evidence(question: str, evidence: list[Evidence]) -> tuple[str, list[dict]]:
    if not evidence:
        return "当前知识库未找到可支撑答案的证据，暂时无法回答。请补充相关文档或换个问法。", []

    question_type = plan_question(question)["question_type"]
    chunks = [item.chunk for item in evidence]

    if _is_resume_identity_question(question):
        support = _find_resume_identity_chunk(chunks)
        if support:
            name = _extract_resume_name(support)
            if name:
                citation = _citation("S1", support, evidence[0].relevance_reason, evidence[0].confidence)
                return f"这是{name}的简历。[[S1]]", [citation]

    if question_type == "policy":
        return _build_policy_answer(evidence)

    if question_type == "extraction":
        return _build_extraction_answer(question, evidence)

    if question_type == "summary":
        return _build_summary_answer(evidence)

    citations = []
    sentences = []
    for item in evidence[:3]:
        source_id = item.source_id
        chunk = item.chunk
        sentences.append(f"{_summarize(chunk.content)} [[{source_id}]]")
        citations.append(_citation(source_id, chunk, item.relevance_reason, item.confidence))
    return "\n".join(sentences), citations


def _build_policy_answer(evidence: list[Evidence]) -> tuple[str, list[dict]]:
    top = evidence[0]
    content = top.support_text
    citations = [_citation(top.source_id, top.chunk, top.relevance_reason, top.confidence)]
    if any(term in content for term in ["人工审核", "manual review", "审核"]):
        answer = f"可以处理，但需要人工审核。依据是：{_summarize(content)} [[{top.source_id}]]"
    elif any(term in content for term in ["不支持", "不能", "不可", "拒绝"]):
        answer = f"不可以直接处理。依据是：{_summarize(content)} [[{top.source_id}]]"
    else:
        answer = f"需要按文档规则判断：{_summarize(content)} [[{top.source_id}]]"
    return answer, citations


def _build_extraction_answer(question: str, evidence: list[Evidence]) -> tuple[str, list[dict]]:
    lines = []
    citations = []
    for item in evidence[:4]:
        lines.append(f"- {_summarize(item.support_text)} [[{item.source_id}]]")
        citations.append(_citation(item.source_id, item.chunk, item.relevance_reason, item.confidence))
    heading = "文档中可支持的信息如下："
    if "经历" in question or "经验" in question:
        heading = "文档中可支持的相关经历如下："
    return "\n".join([heading, *lines]), citations


def _build_summary_answer(evidence: list[Evidence]) -> tuple[str, list[dict]]:
    lines = []
    citations = []
    for item in evidence[:4]:
        lines.append(f"- {_summarize(item.support_text)} [[{item.source_id}]]")
        citations.append(_citation(item.source_id, item.chunk, item.relevance_reason, item.confidence))
    return "\n".join(["基于当前可检索到的证据，关键内容包括：", *lines]), citations


def _citation(source_id: str, chunk: RetrievedChunk, reason: str | None = None, score: float | None = None) -> dict:
    return {
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
        "reason": reason or _citation_reason(chunk),
        "score": score if score is not None else chunk.score,
    }


def _is_resume_identity_question(question: str) -> bool:
    return "简历" in question and any(marker in question for marker in ["谁", "姓名", "本人", "候选人"])


def _find_resume_identity_chunk(chunks: list[RetrievedChunk]) -> RetrievedChunk | None:
    resume_chunks = [chunk for chunk in chunks if "简历" in chunk.filename or "简历" in chunk.content]
    if not resume_chunks:
        return None
    resume_chunks.sort(key=lambda chunk: (chunk.paragraph_index or 9999, -chunk.score))
    return resume_chunks[0]


def _extract_resume_name(chunk: RetrievedChunk) -> str | None:
    filename_stem = re.sub(r"\.[^.]+$", "", chunk.filename)
    filename_name = re.split(r"[-_—－\s]*简历", filename_stem)[0].strip(" -_—－")
    if _looks_like_name(filename_name):
        return filename_name

    content = chunk.content.strip()
    content = re.sub(r"简历$", "", content)
    match = re.match(r"([\u4e00-\u9fff]{2,4})", content)
    if match:
        return match.group(1)
    return None


def _citation_reason(chunk: RetrievedChunk) -> str:
    filename = chunk.filename.lower()
    lowered_content = chunk.content.lower()
    content = chunk.content
    if "简历" in filename or "简历" in content:
        if (chunk.paragraph_index or 999) <= 2:
            return "命中简历首页身份信息"
        return "命中简历相关片段"
    if any(term in content for term in ["退款", "退费", "售后", "人工审核"]) or any(
        term in filename or term in lowered_content for term in ["refund", "policy", "review"]
    ):
        return "命中政策条件或处理规则"
    if chunk.title_path:
        return f"命中文档章节：{chunk.title_path}"
    if chunk.row_number:
        return "命中表格行内容"
    return "命中问题关键词"


def _looks_like_name(value: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{2,4}", value))


def _summarize(content: str) -> str:
    stripped = " ".join(content.split())
    if len(stripped) <= 160:
        return stripped
    return stripped[:157].rstrip() + "..."
