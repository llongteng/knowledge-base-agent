import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import database
from app.main import app


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._engine = create_engine(
            f"sqlite:///{Path(self._tmpdir.name) / 'test.db'}",
            connect_args={"check_same_thread": False},
        )
        self._previous_engine = database.engine
        database.engine = self._engine
        database.SessionLocal.configure(bind=self._engine)
        database.Base.metadata.create_all(bind=self._engine)

    def tearDown(self):
        database.SessionLocal.configure(bind=self._previous_engine)
        database.engine = self._previous_engine
        self._tmpdir.cleanup()

    def test_history_summary_exposes_type_citations_and_confidence(self):
        client = TestClient(app)
        kb = client.post("/api/knowledge-bases", json={"name": "售后政策库", "description": ""}).json()
        client.post(
            f"/api/knowledge-bases/{kb['id']}/documents?filename=refund.txt",
            content="退款超过 7 天需要人工审核。".encode("utf-8"),
            headers={"content-type": "text/plain"},
        )
        response = client.post(
            f"/api/knowledge-bases/{kb['id']}/chat",
            json={"question": "退款超过 7 天还能处理吗？"},
        )
        self.assertEqual(response.status_code, 200)

        history = client.get(f"/api/knowledge-bases/{kb['id']}/history").json()

        self.assertEqual(history[0]["question_type"], "policy")
        self.assertGreaterEqual(history[0]["citation_count"], 1)
        self.assertEqual(history[0]["confidence_status"], "有引用依据")

    def test_delete_single_conversation_and_clear_history(self):
        client = TestClient(app)
        kb = client.post("/api/knowledge-bases", json={"name": "测试知识库", "description": ""}).json()
        for question in ["文档里有什么？", "这是测试问题吗？"]:
            client.post(f"/api/knowledge-bases/{kb['id']}/chat", json={"question": question})

        history = client.get(f"/api/knowledge-bases/{kb['id']}/history").json()
        self.assertEqual(len(history), 2)

        deleted = client.delete(f"/api/conversations/{history[0]['id']}")
        remaining = client.get(f"/api/knowledge-bases/{kb['id']}/history").json()
        cleared = client.delete(f"/api/knowledge-bases/{kb['id']}/history")
        empty = client.get(f"/api/knowledge-bases/{kb['id']}/history").json()

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(cleared.json()["deleted_count"], 1)
        self.assertEqual(empty, [])


if __name__ == "__main__":
    unittest.main()
