# 智能知识库问答 Agent

一个独立的企业知识库可信问答 Agent，用于演示从文档入库、RAG 检索、Agent 决策、流式回答到引用溯源的完整产品闭环。

## 解决的问题

企业文档分散、制度查找慢、普通大模型回答缺少依据。这个系统让用户上传 PDF、TXT、Markdown、CSV 文档后，用自然语言提问，并得到带 `[[S1]]` 来源编号的回答。没有可靠依据时，系统会明确拒答。

## 最小可用版功能

- 知识库创建、列表、删除
- 文档上传、解析状态、删除
- TXT、Markdown、CSV 稳定解析，PDF 解析接口已预留并依赖 `pdfplumber`
- 文档切片、向量化、SQLite 元数据存储
- SSE 流式问答，返回规划、检索、回答增量、引用和完成事件
- 引用标签点击后查看原文片段
- 对话历史保存
- 低置信检索拒绝编造

## 架构

```text
Next.js 工作台
  知识库列表 / 文档入库 / 可信问答 / 执行轨迹 / 来源面板
        |
        | HTTP + SSE
        v
FastAPI Agent 编排层
  routers + parser + chunker + retrieval + planner + answer builder
        |
        v
SQLite 元数据 + SQLite 向量检索兜底
  knowledge_bases / documents / document_chunks / conversations / messages / citations
```

当前代码提供 SQLite 向量检索兜底，保证本地演示不依赖外部服务。`requirements.txt` 保留 ChromaDB 和 OpenAI 依赖，后续可把 `vector_store.py` 替换为 Chroma 集合。

## 快速开始

后端：

```bash
cd /Users/litengteng/Github/knowledge-base-agent/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd /Users/litengteng/Github/knowledge-base-agent/frontend
npm install
npm run dev
```

打开 `http://localhost:3000/knowledge-bases`。

## 演示路径

1. 创建一个“售后政策库”。
2. 上传 TXT、Markdown 或 CSV 文档。
3. 在工作台提问：“退款超过 7 天还能处理吗？”
4. 查看右侧执行过程：问题识别、检索、生成、整理来源。
5. 点击答案里的 `[[S1]]`，查看原文片段。
6. 提一个文档外问题，观察“不编造”的拒答。

## API

- `POST /api/knowledge-bases`
- `GET /api/knowledge-bases`
- `GET /api/knowledge-bases/{id}`
- `DELETE /api/knowledge-bases/{id}`
- `POST /api/knowledge-bases/{id}/documents?filename=refund.txt`
- `GET /api/knowledge-bases/{id}/documents`
- `DELETE /api/knowledge-bases/{id}/documents/{doc_id}`
- `POST /api/knowledge-bases/{id}/chat`
- `GET /api/knowledge-bases/{id}/history`
- `GET /api/conversations/{conversation_id}`

文档上传为了减少本地依赖，使用原始文件流：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/knowledge-bases/1/documents?filename=refund.txt" \
  -H "content-type: text/plain" \
  --data-binary @refund.txt
```

## 面试讲解点

- MVP 范围控制：先做稳定格式和可信闭环，Office、网页、混合检索放到 V1.1。
- RAG 可信体验：回答必须带引用，点击可回到原文片段。
- Agent 产品化：展示执行轨迹，但不暴露模型真实思维链。
- 幻觉控制：低置信或无来源时拒答。
- 可演进架构：SQLite 兜底适合演示，ChromaDB/OpenAI 可作为生产增强替换。

## 验证

```bash
cd /Users/litengteng/Github/knowledge-base-agent/backend
python -m unittest discover -s tests -v
python smoke_test.py
```
