from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db


router = APIRouter(tags=["conversations"])


@router.get("/api/knowledge-bases/{knowledge_base_id}/history")
def list_history(knowledge_base_id: int, db: Session = Depends(get_db)):
    conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.knowledge_base_id == knowledge_base_id)
        .order_by(models.Conversation.updated_at.desc())
        .all()
    )
    return [
        {
            "id": conversation.id,
            "knowledge_base_id": conversation.knowledge_base_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "message_count": len(conversation.messages),
        }
        for conversation in conversations
    ]


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
