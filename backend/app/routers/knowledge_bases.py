from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


def _with_counts(kb: models.KnowledgeBase) -> schemas.KnowledgeBaseOut:
    documents = kb.documents or []
    return schemas.KnowledgeBaseOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=len(documents),
        ready_document_count=len([doc for doc in documents if doc.status == "ready"]),
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


@router.post("", response_model=schemas.KnowledgeBaseOut)
def create_knowledge_base(payload: schemas.KnowledgeBaseCreate, db: Session = Depends(get_db)):
    kb = models.KnowledgeBase(name=payload.name, description=payload.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _with_counts(kb)


@router.get("", response_model=list[schemas.KnowledgeBaseOut])
def list_knowledge_bases(db: Session = Depends(get_db)):
    return [_with_counts(kb) for kb in db.query(models.KnowledgeBase).order_by(models.KnowledgeBase.id.desc())]


@router.get("/{knowledge_base_id}", response_model=schemas.KnowledgeBaseOut)
def get_knowledge_base(knowledge_base_id: int, db: Session = Depends(get_db)):
    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="未找到该知识库")
    return _with_counts(kb)


@router.delete("/{knowledge_base_id}")
def delete_knowledge_base(knowledge_base_id: int, db: Session = Depends(get_db)):
    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="未找到该知识库")
    db.delete(kb)
    db.commit()
    return {"ok": True}


def touch_knowledge_base(db: Session, knowledge_base_id: int) -> None:
    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if kb:
        kb.updated_at = datetime.utcnow()
