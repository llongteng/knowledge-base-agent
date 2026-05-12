from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    document_count: int = 0
    ready_document_count: int = 0
    failed_document_count: int = 0
    knowledge_type: str = "通用知识库"
    health_status: str = "暂无文档"
    recent_document: Optional[str] = None
    recent_question: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    filename: str
    content_hash: Optional[str] = None
    source_type: str
    status: str
    error_message: Optional[str]
    chunk_count: int
    created_at: datetime


class DocumentChunkPreviewOut(BaseModel):
    id: int
    chunk_index: int
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    title_path: Optional[str] = None
    row_number: Optional[int] = None
    content: str


class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None


class CitationOut(BaseModel):
    id: str
    source_type: str
    document_id: Optional[int]
    chunk_id: Optional[int]
    document: Optional[str] = None
    page: Optional[int] = None
    paragraph: Optional[int] = None
    title_path: Optional[str] = None
    row: Optional[int] = None
    snippet: str
    reason: Optional[str] = None
    score: float


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    citations: list[CitationOut] = []


class ConversationOut(BaseModel):
    id: int
    knowledge_base_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []
