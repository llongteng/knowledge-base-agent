from __future__ import annotations

import os
import re
from typing import Protocol

from app.services.evidence_service import Evidence


class ChatClient(Protocol):
    class chat(Protocol):
        class completions(Protocol):
            @staticmethod
            def create(**kwargs): ...


def generate_llm_answer(question: str, evidence: list[Evidence], client: ChatClient | None = None) -> str | None:
    if not evidence:
        return None

    client = client or _default_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _user_prompt(question, evidence)},
            ],
            temperature=0.2,
        )
    except Exception:
        return None

    content = _response_text(response)
    return _validate_answer(content, evidence)


def _default_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _system_prompt() -> str:
    return (
        "你是一个证据约束的知识库问答 Agent。"
        "只能使用用户提供的 Evidence 回答。"
        "如果 Evidence 不足，必须明确说无法从当前文档回答。"
        "每个关键结论后必须带来源标记，例如 [[S1]]。"
        "不要编造 Evidence 之外的事实。"
        "用简洁中文回答。"
    )


def _user_prompt(question: str, evidence: list[Evidence]) -> str:
    evidence_lines = []
    for item in evidence:
        evidence_lines.append(
            "\n".join(
                [
                    f"{item.source_id}:",
                    f"证据类型：{item.claim_type}",
                    f"支撑原因：{item.relevance_reason}",
                    f"原文：{item.support_text}",
                ]
            )
        )
    return "\n\n".join(
        [
            f"问题：{question}",
            "Evidence:",
            "\n\n".join(evidence_lines),
            "请基于 Evidence 直接回答，并在结论后标注来源。",
        ]
    )


def _response_text(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "") if message else ""
    return str(content).strip()


def _validate_answer(answer: str, evidence: list[Evidence]) -> str | None:
    if not answer:
        return None
    allowed_ids = {item.source_id for item in evidence}
    cited_ids = set(re.findall(r"\[\[(S\d+)\]\]", answer))
    if not cited_ids:
        return None
    if not cited_ids <= allowed_ids:
        return None
    return answer
