import unittest

from app.services.answer_builder import build_answer
from app.services.agent_planner import plan_question
from app.services.embedding_service import lexical_overlap_score
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

    def test_low_confidence_retrieval_refuses_to_invent(self):
        decision = decide_retrieval([])

        self.assertFalse(decision.can_answer)
        self.assertIn("未找到可靠依据", decision.reason)

    def test_planner_exposes_productized_steps_not_chain_of_thought(self):
        plan = plan_question("退款超过 7 天还能处理吗？")

        self.assertEqual(plan["question_type"], "policy")
        self.assertIn("检索知识库", plan["steps"])
        self.assertNotIn("思维链", " ".join(plan["steps"]))

    def test_lexical_overlap_handles_policy_question_variants(self):
        score = lexical_overlap_score(
            "Can refunds after 7 days be processed?",
            "Refunds after 7 days require manual review.",
        )

        self.assertGreaterEqual(score, 0.62)


if __name__ == "__main__":
    unittest.main()
