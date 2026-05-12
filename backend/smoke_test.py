from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _use_temporary_database() -> tempfile.TemporaryDirectory:
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "smoke_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    return temp_dir


def main() -> None:
    temp_dir = _use_temporary_database()
    from fastapi.testclient import TestClient

    from app.database import init_db
    from app.main import app

    init_db()
    client = TestClient(app)
    kb = client.post(
        "/api/knowledge-bases",
        json={"name": "示例政策库", "description": "面试演示知识库"},
    ).json()
    upload = client.post(
        f"/api/knowledge-bases/{kb['id']}/documents?filename=refund.txt",
        content="退款超过 7 天需要人工审核。".encode("utf-8"),
        headers={"content-type": "text/plain"},
    )
    assert upload.status_code == 200, upload.text
    response = client.post(
        f"/api/knowledge-bases/{kb['id']}/chat",
        json={"question": "退款超过 7 天还能处理吗？"},
    )
    assert response.status_code == 200, response.text
    assert "citations" in response.text
    history = client.get(f"/api/knowledge-bases/{kb['id']}/history")
    assert history.status_code == 200, history.text
    print("烟测通过")
    temp_dir.cleanup()


if __name__ == "__main__":
    main()
