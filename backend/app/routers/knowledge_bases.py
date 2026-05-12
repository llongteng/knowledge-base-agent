from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


def _with_counts(kb: models.KnowledgeBase) -> schemas.KnowledgeBaseOut:
    documents = kb.documents or []
    conversations = kb.conversations or []
    ready_count = len([doc for doc in documents if doc.status == "ready"])
    failed_count = len([doc for doc in documents if doc.status == "failed"])
    recent_document = max(documents, key=lambda doc: doc.created_at).filename if documents else None
    recent_question = max(conversations, key=lambda item: item.updated_at).title if conversations else None
    return schemas.KnowledgeBaseOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=len(documents),
        ready_document_count=ready_count,
        failed_document_count=failed_count,
        knowledge_type=_infer_knowledge_type(kb.name, kb.description, documents),
        health_status=_infer_health_status(len(documents), ready_count, failed_count),
        recent_document=recent_document,
        recent_question=recent_question,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


def _infer_knowledge_type(name: str, description: str, documents: list[models.Document]) -> str:
    text = " ".join([name, description, *[document.filename for document in documents]]).lower()
    if "简历" in text or "resume" in text:
        return "简历知识库"
    if "退款" in text or "售后" in text or "政策" in text or "policy" in text:
        return "政策知识库"
    if "faq" in text or "问答" in text:
        return "FAQ 知识库"
    if "手册" in text or "manual" in text or "产品" in text:
        return "产品手册库"
    if "制度" in text or "治理" in text or "安全" in text:
        return "制度知识库"
    return "通用知识库"


def _infer_health_status(document_count: int, ready_count: int, failed_count: int) -> str:
    if document_count == 0:
        return "暂无文档"
    if ready_count == 0 and failed_count > 0:
        return "全部解析失败"
    if failed_count > 0:
        return "部分文档失败"
    return "可问答"


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
