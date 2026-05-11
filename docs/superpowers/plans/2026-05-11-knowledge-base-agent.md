# Knowledge Base Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent MVP web app for document-backed knowledge base Q&A with citations, visible execution steps, document ingestion, and conversation history.

**Architecture:** Use a FastAPI backend for metadata, ingestion, retrieval, and SSE chat. Use SQLite for durable metadata and a vector-store abstraction that can use ChromaDB when installed while keeping a SQLite-backed fallback for local demo reliability. Use a Next.js frontend as a dense knowledge workbench with document management, streaming answers, execution trace, and citation source panel.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, optional ChromaDB, optional OpenAI-compatible API, Next.js App Router, TypeScript, CSS modules/global CSS.

---

### Task 1: Backend Core

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/document_parser.py`
- Create: `backend/app/services/chunker.py`
- Create: `backend/app/services/embedding_service.py`
- Create: `backend/app/services/vector_store.py`
- Create: `backend/tests/test_ingestion.py`

- [x] Write tests proving TXT, Markdown, and CSV parse into traceable chunks.
- [x] Run tests and confirm they fail before implementation.
- [x] Implement parser, chunker, embedding, and SQLite metadata.
- [x] Run tests and confirm they pass.

### Task 2: Retrieval and Answering

**Files:**
- Create: `backend/app/services/retrieval_service.py`
- Create: `backend/app/services/agent_planner.py`
- Create: `backend/app/services/answer_builder.py`
- Create: `backend/tests/test_chat.py`

- [x] Write tests for cited answers and low-confidence refusal.
- [x] Run tests and confirm they fail before implementation.
- [x] Implement retrieval thresholds, execution steps, answer building, and citation mapping.
- [x] Run tests and confirm they pass.

### Task 3: API Surface

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/routers/knowledge_bases.py`
- Create: `backend/app/routers/documents.py`
- Create: `backend/app/routers/chat.py`
- Create: `backend/app/routers/conversations.py`
- Create: `backend/smoke_test.py`

- [x] Implement knowledge base CRUD, document upload/list/delete, SSE chat, and conversation history.
- [x] Add smoke test for create knowledge base, upload TXT, ask question, and fetch history.

### Task 4: Frontend Workbench

**Files:**
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/knowledge-bases/page.tsx`
- Create: `frontend/app/knowledge-bases/[id]/page.tsx`
- Create: `frontend/app/knowledge-bases/[id]/history/page.tsx`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/types.ts`

- [x] Use frontend-design skill direction: credible, dense, document-native enterprise workbench.
- [x] Implement knowledge base list, create/delete controls, detail workbench, upload state, streaming chat, execution trace, citations, source panel, and history.
- [x] Run Next.js build or explain dependency blocker.

### Task 5: Packaging

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`

- [x] Document product positioning, quick start, architecture, API, demo path, and interview talking points.
- [x] Run backend tests and available frontend checks before handoff.
