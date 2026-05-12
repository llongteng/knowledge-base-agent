import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.evidence_service import Evidence
from app.services.llm_service import generate_llm_answer
from app.services.retrieval_service import RetrievedChunk


class LLMServiceTests(unittest.TestCase):
    def test_missing_api_key_disables_llm_generation(self):
        with patch.dict(os.environ, {}, clear=True):
            answer = generate_llm_answer("退款超过 7 天还能处理吗？", [_evidence()])

        self.assertIsNone(answer)

    def test_accepts_answer_when_citations_match_evidence(self):
        answer = generate_llm_answer(
            "退款超过 7 天还能处理吗？",
            [_evidence()],
            client=_FakeClient("可以处理，但需要人工审核。[[S1]]"),
        )

        self.assertEqual(answer, "可以处理，但需要人工审核。[[S1]]")

    def test_rejects_answer_with_unknown_citation(self):
        answer = generate_llm_answer(
            "退款超过 7 天还能处理吗？",
            [_evidence()],
            client=_FakeClient("可以处理。[[S9]]"),
        )

        self.assertIsNone(answer)

    def test_rejects_answer_without_citation(self):
        answer = generate_llm_answer(
            "退款超过 7 天还能处理吗？",
            [_evidence()],
            client=_FakeClient("可以处理，但需要人工审核。"),
        )

        self.assertIsNone(answer)


class _FakeClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: _response(content))
        )


def _response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _evidence() -> Evidence:
    return Evidence(
        source_id="S1",
        chunk=RetrievedChunk(
            chunk_id=1,
            document_id=1,
            filename="售后政策.md",
            content="退款超过 7 天需要人工审核。",
            score=0.91,
            paragraph_index=1,
        ),
        claim_type="policy",
        support_text="退款超过 7 天需要人工审核。",
        relevance_reason="命中政策条件或处理规则",
        confidence=0.91,
    )


if __name__ == "__main__":
    unittest.main()
