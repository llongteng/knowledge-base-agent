from __future__ import annotations

from collections import defaultdict

from app.database import SessionLocal, init_db
from app import models


def main() -> None:
    init_db()
    with SessionLocal() as db:
        groups: dict[tuple[str, str], list[models.KnowledgeBase]] = defaultdict(list)
        for kb in db.query(models.KnowledgeBase).all():
            groups[(kb.name, kb.description)].append(kb)

        removed = 0
        for (name, description), items in groups.items():
            if name != "示例政策库" or description != "面试演示知识库" or len(items) <= 1:
                continue
            items.sort(key=lambda kb: kb.updated_at, reverse=True)
            for duplicate in items[1:]:
                db.delete(duplicate)
                removed += 1
        db.commit()
    print(f"已清理 {removed} 个重复示例知识库")


if __name__ == "__main__":
    main()
