from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


def main() -> None:
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


if __name__ == "__main__":
    main()
