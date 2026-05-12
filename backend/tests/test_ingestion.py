import unittest
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import database
from app.main import app
from app.services.chunker import chunk_segments
from app.services.document_parser import SUPPORTED_EXTENSIONS, parse_bytes


class IngestionTests(unittest.TestCase):
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

    def test_markdown_keeps_heading_path_in_chunks(self):
        segments = parse_bytes(
            filename="policy.md",
            content=b"# Refunds\n\n## Enterprise\nRefunds after 7 days require manual review.",
            content_type="text/markdown",
        )

        chunks = chunk_segments(segments, chunk_size=80, overlap=10)

        self.assertEqual(chunks[0].title_path, "Refunds > Enterprise")
        self.assertIn("manual review", chunks[0].content)
        self.assertEqual(chunks[0].paragraph_index, 1)

    def test_csv_rows_become_traceable_row_chunks(self):
        segments = parse_bytes(
            filename="plans.csv",
            content="plan,refund_window\nEnterprise,14 days\nPersonal,7 days\n".encode(),
            content_type="text/csv",
        )

        self.assertEqual(len(segments), 2)
        self.assertIn("plan: Enterprise", segments[0].content)
        self.assertEqual(segments[0].row_number, 2)
        self.assertEqual(segments[1].row_number, 3)

    def test_docx_paragraphs_and_tables_become_traceable_segments(self):
        segments = parse_bytes(
            filename="resume.docx",
            content=_minimal_docx(
                """
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body>
                    <w:p><w:r><w:t>谭博之简历</w:t></w:r></w:p>
                    <w:p><w:r><w:t>擅长 AI Agent 产品设计</w:t></w:r></w:p>
                    <w:tbl>
                      <w:tr>
                        <w:tc><w:p><w:r><w:t>经历</w:t></w:r></w:p></w:tc>
                        <w:tc><w:p><w:r><w:t>知识库问答项目</w:t></w:r></w:p></w:tc>
                      </w:tr>
                    </w:tbl>
                  </w:body>
                </w:document>
                """
            ),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        self.assertEqual(".docx" in SUPPORTED_EXTENSIONS, True)
        self.assertIn("谭博之简历", segments[0].content)
        self.assertIn("AI Agent 产品设计", segments[1].content)
        self.assertIn("经历 | 知识库问答项目", segments[2].content)
        self.assertEqual(segments[2].paragraph_index, 3)

    def test_duplicate_upload_is_rejected_without_duplicate_document(self):
        client = TestClient(app)
        kb = client.post("/api/knowledge-bases", json={"name": "售后政策库", "description": ""}).json()
        path = f"/api/knowledge-bases/{kb['id']}/documents?filename=refund.txt"
        first = client.post(path, content="退款超过 7 天需要人工审核。".encode("utf-8"))
        second = client.post(path, content="退款超过 7 天需要人工审核。".encode("utf-8"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertIn("已经上传过", second.text)
        documents = client.get(f"/api/knowledge-bases/{kb['id']}/documents").json()
        self.assertEqual(len(documents), 1)

    def test_document_chunk_preview_returns_first_five_traceable_chunks(self):
        client = TestClient(app)
        kb = client.post("/api/knowledge-bases", json={"name": "产品手册库", "description": ""}).json()
        lines = "\n".join([f"第 {index} 段内容" for index in range(1, 8)])
        document = client.post(
            f"/api/knowledge-bases/{kb['id']}/documents?filename=manual.txt",
            content=lines.encode("utf-8"),
            headers={"content-type": "text/plain"},
        ).json()

        preview = client.get(
            f"/api/knowledge-bases/{kb['id']}/documents/{document['id']}/chunks"
        )

        self.assertEqual(preview.status_code, 200)
        self.assertEqual(len(preview.json()), 5)
        self.assertIn("第 1 段内容", preview.json()[0]["content"])


if __name__ == "__main__":
    unittest.main()


def _minimal_docx(document_xml: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()
