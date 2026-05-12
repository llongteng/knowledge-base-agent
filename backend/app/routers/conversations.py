from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.routers.knowledge_bases import touch_knowledge_base
from app.services.agent_planner import plan_question


router = APIRouter(tags=["conversations"])


@router.get("/api/knowledge-bases/{knowledge_base_id}/history")
def list_history(knowledge_base_id: int, db: Session = Depends(get_db)):
    conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.knowledge_base_id == knowledge_base_id)
        .order_by(models.Conversation.updated_at.desc())
        .all()
    )
    return [_conversation_summary(conversation) for conversation in conversations]


@router.delete("/api/knowledge-bases/{knowledge_base_id}/history")
def clear_history(knowledge_base_id: int, db: Session = Depends(get_db)):
    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="未找到该知识库")
    deleted_count = len(kb.conversations)
    for conversation in list(kb.conversations):
        db.delete(conversation)
    touch_knowledge_base(db, knowledge_base_id)
    db.commit()
    return {"ok": True, "deleted_count": deleted_count}


@router.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="未找到该对话")

    messages = []
    for message in conversation.messages:
        messages.append(
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
                "citations": [
                    {
                        "id": citation.source_id,
                        "source_type": citation.source_type,
                        "document_id": citation.document_id,
                        "chunk_id": citation.chunk_id,
                        "document": citation.title,
                        "snippet": citation.snippet,
                        "reason": citation.reason,
                        "score": citation.score,
                    }
                    for citation in message.citations
                ],
            }
        )
    return {
        "id": conversation.id,
        "knowledge_base_id": conversation.knowledge_base_id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages,
    }


@router.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="未找到该对话")
    knowledge_base_id = conversation.knowledge_base_id
    db.delete(conversation)
    touch_knowledge_base(db, knowledge_base_id)
    db.commit()
    return {"ok": True}


def _conversation_summary(conversation: models.Conversation) -> dict:
    citation_count = sum(len(message.citations) for message in conversation.messages)
    assistant_messages = [message for message in conversation.messages if message.role == "assistant"]
    refused = any("未找到可靠依据" in message.content for message in assistant_messages)
    question_type = plan_question(conversation.title)["question_type"]
    if citation_count > 0:
        confidence_status = "有引用依据"
    elif refused:
        confidence_status = "已拒答"
    else:
        confidence_status = "待核验"
    return {
        "id": conversation.id,
        "knowledge_base_id": conversation.knowledge_base_id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "message_count": len(conversation.messages),
        "question_type": question_type,
        "citation_count": citation_count,
        "confidence_status": confidence_status,
    }
