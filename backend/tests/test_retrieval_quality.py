import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import database
from app.main import app
from app.services.vector_store import vector_store


class RetrievalQualityTests(unittest.TestCase):
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
        self.client = TestClient(app)

    def tearDown(self):
        database.SessionLocal.configure(bind=self._previous_engine)
        database.engine = self._previous_engine
        self._tmpdir.cleanup()

    def test_hybrid_retrieval_prefers_policy_clause_over_generic_overlap(self):
        kb = self.client.post("/api/knowledge-bases", json={"name": "售后政策库", "description": ""}).json()
        self.client.post(
            f"/api/knowledge-bases/{kb['id']}/documents?filename=售后政策.md",
            content="退款超过 7 天需要人工审核。\n退款流程由售后团队处理。".encode("utf-8"),
            headers={"content-type": "text/plain"},
        )
        self.client.post(
            f"/api/knowledge-bases/{kb['id']}/documents?filename=客服能力.md",
            content="客服团队擅长处理复杂流程、人工转接、情绪识别和多轮对话。".encode("utf-8"),
            headers={"content-type": "text/plain"},
        )

        with database.SessionLocal() as db:
            results = vector_store.search(db, kb["id"], "退款超过 7 天还能处理吗？")

        self.assertIn("退款超过 7 天", results[0].content)

    def test_retrieval_deduplicates_identical_chunks(self):
        kb = self.client.post("/api/knowledge-bases", json={"name": "制度库", "description": ""}).json()
        self.client.post(
            f"/api/knowledge-bases/{kb['id']}/documents?filename=制度.txt",
            content="退款超过 7 天需要人工审核。\n退款超过 7 天需要人工审核。".encode("utf-8"),
            headers={"content-type": "text/plain"},
        )

        with database.SessionLocal() as db:
            results = vector_store.search(db, kb["id"], "退款超过 7 天还能处理吗？", top_k=5)

        matching = [result for result in results if result.content == "退款超过 7 天需要人工审核。"]
        self.assertEqual(len(matching), 1)


if __name__ == "__main__":
    unittest.main()
