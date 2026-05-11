from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.agent_planner import plan_question
from app.services.answer_builder import build_answer
from app.services.retrieval_service import decide_retrieval
from app.services.vector_store import vector_store


router = APIRouter(prefix="/api/knowledge-bases/{knowledge_base_id}/chat", tags=["chat"])


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
def ask_question(
    knowledge_base_id: int,
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
):
    kb = db.get(models.KnowledgeBase, knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="未找到该知识库")

    conversation = None
    if payload.conversation_id:
        conversation = db.get(models.Conversation, payload.conversation_id)
    if not conversation:
        conversation = models.Conversation(
            knowledge_base_id=knowledge_base_id,
            title=payload.question[:60],
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_message = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.question,
    )
    db.add(user_message)
    db.commit()

    plan = plan_question(payload.question)
    retrieved = vector_store.search(db, knowledge_base_id, payload.question)
    decision = decide_retrieval(retrieved)
    answer, citations = build_answer(payload.question, retrieved if decision.can_answer else [])

    assistant_message = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
    )
    conversation.updated_at = datetime.utcnow()
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    assistant_message_id = assistant_message.id
    conversation_id = conversation.id

    for citation in citations:
        db.add(
            models.Citation(
                message_id=assistant_message.id,
                source_id=citation["id"],
                source_type=citation["source_type"],
                document_id=citation["document_id"],
                chunk_id=citation["chunk_id"],
                title=citation.get("document"),
                snippet=citation["snippet"],
                score=citation["score"],
            )
        )
    db.commit()

    def stream():
        yield _sse("planning", plan)
        yield _sse(
            "retrieval",
            {
                "hits": len(retrieved),
                "top_score": retrieved[0].score if retrieved else 0,
                "decision": decision.reason,
                "confidence": decision.confidence_label,
            },
        )
        for word in answer.split(" "):
            yield _sse("answer_delta", {"text": word + " "})
        yield _sse("citations", citations)
        yield _sse(
            "done",
            {"message_id": assistant_message_id, "conversation_id": conversation_id},
        )

    return StreamingResponse(stream(), media_type="text/event-stream")
