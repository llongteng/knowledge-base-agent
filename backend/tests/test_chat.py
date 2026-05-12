import unittest

from app.services.answer_builder import build_answer
from app.services.agent_planner import plan_question
from app.services.embedding_service import lexical_overlap_score, tokenize
from app.services.evidence_service import select_evidence
from app.services.retrieval_service import RetrievedChunk, decide_retrieval


class ChatTests(unittest.TestCase):
    def test_answer_includes_clickable_source_ids(self):
        chunks = [
            RetrievedChunk(
                chunk_id=9,
                document_id=3,
                filename="refund-policy.md",
                content="Refunds after 7 days require manual review.",
                score=0.84,
                page_number=None,
                paragraph_index=2,
                title_path="Refunds",
            )
        ]

        answer, citations = build_answer("Can refunds after 7 days be processed?", chunks)

        self.assertIn("[[S1]]", answer)
        self.assertEqual(citations[0]["id"], "S1")
        self.assertEqual(citations[0]["chunk_id"], 9)
        self.assertIn("政策", citations[0]["reason"])

    def test_low_confidence_retrieval_refuses_to_invent(self):
        decision = decide_retrieval([])

        self.assertFalse(decision.can_answer)
        self.assertIn("未找到可靠依据", decision.reason)

    def test_planner_exposes_productized_steps_not_chain_of_thought(self):
        plan = plan_question("退款超过 7 天还能处理吗？")

        self.assertEqual(plan["question_type"], "policy")
        self.assertIn("检索知识库", plan["steps"])
        self.assertNotIn("思维链", " ".join(plan["steps"]))

    def test_evidence_filters_unrelated_high_score_chunks(self):
        chunks = [
            RetrievedChunk(
                chunk_id=1,
                document_id=1,
                filename="resume.pdf",
                content="轮推理与语义纠错能力。引入情绪识别模块动态切换应答风格。",
                score=0.95,
                paragraph_index=20,
            )
        ]

        evidence = select_evidence("这是谁的简历", chunks)
        answer, citations = build_answer("这是谁的简历", chunks)

        self.assertEqual(evidence, [])
        self.assertIn("未找到可支撑答案的证据", answer)
        self.assertEqual(citations, [])

    def test_lexical_overlap_handles_policy_question_variants(self):
        score = lexical_overlap_score(
            "Can refunds after 7 days be processed?",
            "Refunds after 7 days require manual review.",
        )

        self.assertGreaterEqual(score, 0.62)

    def test_chinese_tokenizer_splits_short_resume_identity_question(self):
        tokens = tokenize("这是谁的简历")

        self.assertIn("谁", tokens)
        self.assertIn("简历", tokens)

    def test_resume_identity_question_answers_name_not_random_fragments(self):
        chunks = [
            RetrievedChunk(
                chunk_id=11,
                document_id=12,
                filename="谭博之-简历.pdf",
                content="谭博之 求职意向：AI Agentic Engineering",
                score=0.93,
                paragraph_index=1,
            ),
            RetrievedChunk(
                chunk_id=69,
                document_id=12,
                filename="谭博之-简历.pdf",
                content="轮推理与语义纠错能力。引入情绪识别模块动态切换应答风格与转人工策略。",
                score=0.71,
                paragraph_index=24,
            ),
        ]

        answer, citations = build_answer("这是谁的简历", chunks)

        self.assertIn("这是谭博之的简历", answer)
        self.assertIn("[[S1]]", answer)
        self.assertEqual(citations[0]["chunk_id"], 11)
        self.assertEqual(citations[0]["reason"], "命中简历首页身份信息")

    def test_policy_question_gets_judgment_style_answer_from_evidence(self):
        chunks = [
            RetrievedChunk(
                chunk_id=21,
                document_id=2,
                filename="售后政策.md",
                content="退款超过 7 天需要人工审核。",
                score=0.88,
                paragraph_index=3,
            )
        ]

        answer, citations = build_answer("退款超过 7 天还能处理吗？", chunks)

        self.assertIn("可以处理，但需要人工审核", answer)
        self.assertEqual(citations[0]["reason"], "命中政策条件或处理规则")


if __name__ == "__main__":
    unittest.main()
