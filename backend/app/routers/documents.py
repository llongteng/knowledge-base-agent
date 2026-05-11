from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.knowledge_bases import touch_knowledge_base
from app.services.chunker import chunk_segments
from app.services.document_parser import parse_bytes
from app.services.vector_store import vector_store


router = APIRouter(prefix="/api/knowledge-bases/{knowledge_base_id}/documents", tags=["documents"])


@router.post("", response_model=schemas.DocumentOut)
async def upload_document(
    knowledge_base_id: int,
    request: Request,
    filename: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="未找到该知识库")

    document = models.Document(
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        content = await request.body()
        segments = parse_bytes(document.filename, content, request.headers.get("content-type"))
        chunks = chunk_segments(segments)
        if not chunks:
            raise ValueError("文档中没有可入库的文本内容")
        for chunk in chunks:
            db.add(
                models.DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    paragraph_index=chunk.paragraph_index,
                    row_number=chunk.row_number,
                    title_path=chunk.title_path,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    vector=vector_store.encode(chunk.content),
                )
            )
        document.status = "ready"
        document.chunk_count = len(chunks)
        document.error_message = None
    except ValueError as exc:
        document.status = "failed"
        document.error_message = str(exc)
    touch_knowledge_base(db, knowledge_base_id)
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(knowledge_base_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Document)
        .filter(models.Document.knowledge_base_id == knowledge_base_id)
        .order_by(models.Document.id.desc())
        .all()
    )


@router.get("/{document_id}", response_model=schemas.DocumentOut)
def get_document(knowledge_base_id: int, document_id: int, db: Session = Depends(get_db)):
    document = db.get(models.Document, document_id)
    if not document or document.knowledge_base_id != knowledge_base_id:
        raise HTTPException(status_code=404, detail="未找到该文档")
    return document


@router.delete("/{document_id}")
def delete_document(knowledge_base_id: int, document_id: int, db: Session = Depends(get_db)):
    document = db.get(models.Document, document_id)
    if not document or document.knowledge_base_id != knowledge_base_id:
        raise HTTPException(status_code=404, detail="未找到该文档")
    db.delete(document)
    touch_knowledge_base(db, knowledge_base_id)
    db.commit()
    return {"ok": True}
