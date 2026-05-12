from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import database
from app.main import app


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "rag_quality_cases.json"


def main() -> None:
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmpdir:
        previous_engine = database.engine
        engine = create_engine(
            f"sqlite:///{Path(tmpdir) / 'eval.db'}",
            connect_args={"check_same_thread": False},
        )
        database.engine = engine
        database.SessionLocal.configure(bind=engine)
        database.Base.metadata.create_all(bind=engine)
        try:
            client = TestClient(app)
            failures = [_run_case(client, case) for case in cases]
        finally:
            database.SessionLocal.configure(bind=previous_engine)
            database.engine = previous_engine

    failures = [failure for failure in failures if failure]
    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    print(f"RAG quality eval passed: {len(cases)} cases")


def _run_case(client: TestClient, case: dict) -> str | None:
    kb = client.post(
        "/api/knowledge-bases",
        json={"name": case["knowledge_base"], "description": "RAG quality eval"},
    ).json()
    for document in case["documents"]:
        response = client.post(
            f"/api/knowledge-bases/{kb['id']}/documents?filename={document['filename']}",
            content=document["content"].encode("utf-8"),
            headers={"content-type": "text/plain"},
        )
        if response.status_code != 200:
            return f"{case['id']}: upload failed: {response.text}"

    response = client.post(
        f"/api/knowledge-bases/{kb['id']}/chat",
        json={"question": case["question"]},
    )
    if response.status_code != 200:
        return f"{case['id']}: chat failed: {response.text}"

    body = response.text
    for term in case["expected_answer_terms"]:
        if term not in body:
            return f"{case['id']}: missing answer term {term!r}"
    for term in case["expected_citation_terms"]:
        if term not in body:
            return f"{case['id']}: missing citation term {term!r}"
    if not case["expected_citation_terms"] and "[[S" in body:
        return f"{case['id']}: unexpected citation in refusal"
    return None


if __name__ == "__main__":
    main()
