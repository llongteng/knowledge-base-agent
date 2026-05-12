"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";
import { api, streamChat } from "@/lib/api";
import type { ChatMessage, Citation, DocumentChunkPreview, DocumentRecord, KnowledgeBase, TraceStep } from "@/lib/types";

const initialTrace: TraceStep[] = [
  { label: "识别问题类型", state: "idle" },
  { label: "检索知识库", state: "idle" },
  { label: "生成带引用回答", state: "idle" },
  { label: "整理来源", state: "idle" },
];

const traceStateText: Record<TraceStep["state"], string> = {
  idle: "等待中",
  running: "进行中",
  done: "已完成",
};

const documentStatusText: Record<DocumentRecord["status"], string> = {
  processing: "解析中",
  ready: "可用",
  failed: "失败",
};

export default function KnowledgeBaseDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const knowledgeBaseId = Number(id);
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [trace, setTrace] = useState<TraceStep[]>(initialTrace);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [activeCitation, setActiveCitation] = useState<string | null>(null);
  const [expandedDocumentId, setExpandedDocumentId] = useState<number | null>(null);
  const [chunkPreviews, setChunkPreviews] = useState<Record<number, DocumentChunkPreview[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const readyCount = useMemo(() => documents.filter((document) => document.status === "ready").length, [documents]);
  const suggestedQuestions = useMemo(() => buildSuggestedQuestions(documents), [documents]);

  async function load() {
    const [nextKb, nextDocuments] = await Promise.all([
      api.getKnowledgeBase(knowledgeBaseId),
      api.listDocuments(knowledgeBaseId),
    ]);
    setKb(nextKb);
    setDocuments(nextDocuments);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [knowledgeBaseId]);

  async function upload(fileList: FileList | null) {
    if (!fileList?.length) return;
    setError("");
    const failures: string[] = [];
    for (const file of Array.from(fileList).slice(0, 5)) {
      try {
        await api.uploadDocument(knowledgeBaseId, file);
      } catch (err) {
        failures.push(`${file.name}：${err instanceof Error ? err.message : "上传失败"}`);
      }
    }
    await load();
    if (failures.length) {
      setError(failures.join("\n"));
    }
  }

  async function removeDocument(documentId: number) {
    await api.deleteDocument(knowledgeBaseId, documentId);
    setChunkPreviews((current) => {
      const copy = { ...current };
      delete copy[documentId];
      return copy;
    });
    await load();
  }

  async function togglePreview(documentId: number) {
    if (expandedDocumentId === documentId) {
      setExpandedDocumentId(null);
      return;
    }
    setExpandedDocumentId(documentId);
    if (!chunkPreviews[documentId]) {
      const preview = await api.previewDocumentChunks(knowledgeBaseId, documentId);
      setChunkPreviews((current) => ({ ...current, [documentId]: preview }));
    }
  }

  async function ask() {
    const text = question.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setQuestion("");
    setTrace(initialTrace.map((step, index) => ({ ...step, state: index === 0 ? "running" : "idle" })));
    setCitations([]);
    setActiveCitation(null);
    setMessages((current) => [
      ...current,
      { id: `u-${Date.now()}`, role: "user", content: text },
      { id: `a-${Date.now()}`, role: "assistant", content: "" },
    ]);

    try {
      await streamChat(knowledgeBaseId, text, (event, data) => {
        if (event === "planning") {
          setTrace(data.steps.map((label: string, index: number) => ({ label, state: index === 1 ? "running" : "done" })));
        }
        if (event === "retrieval") {
          setTrace((current) =>
            current.map((step) =>
              step.label === "检索知识库"
                ? { ...step, state: "done", detail: `${data.hits} 个片段，最高分 ${Number(data.top_score).toFixed(2)}` }
                : step.label === "生成带引用回答"
                  ? { ...step, state: "running" }
                  : step,
            ),
          );
        }
        if (event === "answer_delta") {
          setMessages((current) => {
            const copy = [...current];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = { ...last, content: last.content + data.text };
            return copy;
          });
        }
        if (event === "citations") {
          setCitations(data);
          setMessages((current) => {
            const copy = [...current];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = { ...last, citations: data };
            return copy;
          });
          setTrace((current) =>
            current.map((step) =>
              step.label === "生成带引用回答" || step.label === "整理来源"
                ? { ...step, state: "done", detail: step.label === "整理来源" ? `${data.length} 个引用` : step.detail }
                : step,
            ),
          );
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "回答生成失败");
    } finally {
      setBusy(false);
    }
  }

  function renderAnswer(text: string, messageCitations?: Citation[]) {
    const sourceMap = new Map((messageCitations ?? []).map((citation) => [citation.id, citation]));
    return text.split(/(\[\[S\d+\]\])/g).map((part, index) => {
      const id = part.match(/\[\[(S\d+)\]\]/)?.[1];
      if (!id) return <span key={index}>{part}</span>;
      const citation = sourceMap.get(id);
      return (
        <button
          className="citation"
          key={index}
          onClick={() => {
            setCitations(messageCitations ?? []);
            setActiveCitation(id);
          }}
          type="button"
        >
          {id}{citation?.score ? ` ${(citation.score * 100).toFixed(0)}%` : ""}
        </button>
      );
    });
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span>有来源依据的问答台</span>
          <strong>{kb?.name ?? "知识库"}</strong>
        </div>
        <div className="actions">
          <Link className="ghost-button" href="/knowledge-bases">← 知识库</Link>
          <Link className="ghost-button" href={`/knowledge-bases/${knowledgeBaseId}/history`}>历史</Link>
          <span className="tag ready">{readyCount} 份可用文档</span>
        </div>
      </header>

      {error ? <p className="empty">{error}</p> : null}

      <section className="workbench">
        <aside className="panel">
          <p className="eyebrow">文档资料</p>
          <h2>文档入库</h2>
          <label className="upload-zone">
            <strong>上传材料</strong>
            <span className="tag">PDF / Word / TXT / Markdown / CSV，单文件 10MB</span>
            <input
              accept=".pdf,.docx,.txt,.md,.markdown,.csv"
              multiple
              onChange={(event) => upload(event.target.files)}
              type="file"
            />
          </label>
          <div className="document-list">
            {documents.length === 0 ? (
              <div className="empty">当前知识库还没有可用于问答的文档。</div>
            ) : (
              documents.map((document) => (
                <article className="document-item" key={document.id}>
                  <div className="status-row">
                    <span className={`tag ${document.status}`}>{documentStatusText[document.status]}</span>
                    <span className="tag">{document.chunk_count} 个片段</span>
                    {document.chunk_count > 80 ? <span className="tag failed">解析较碎</span> : null}
                  </div>
                  <p className="document-name">{document.filename}</p>
                  {document.error_message ? <p>{document.error_message}</p> : null}
                  {document.status === "failed" ? (
                    <p className="document-hint">可重新选择修正后的文件上传；系统会阻止重复内容再次入库。</p>
                  ) : null}
                  <div className="actions">
                    <button
                      className="ghost-button"
                      disabled={document.chunk_count === 0}
                      type="button"
                      onClick={() => togglePreview(document.id)}
                    >
                      {expandedDocumentId === document.id ? "收起片段" : "预览片段"}
                    </button>
                    <button className="ghost-button" type="button" onClick={() => removeDocument(document.id)}>删除</button>
                  </div>
                  {expandedDocumentId === document.id ? (
                    <div className="chunk-preview-list">
                      {(chunkPreviews[document.id] ?? []).length === 0 ? (
                        <p className="document-hint">暂无可预览片段。</p>
                      ) : (
                        chunkPreviews[document.id].map((chunk) => (
                          <article className="chunk-preview" key={chunk.id}>
                            <span>
                              {chunk.title_path || `片段 ${chunk.chunk_index + 1}`}
                              {chunk.page_number ? ` · 第 ${chunk.page_number} 页` : ""}
                            </span>
                            <p>{chunk.content}</p>
                          </article>
                        ))
                      )}
                    </div>
                  ) : null}
                </article>
              ))
            )}
          </div>
        </aside>

        <section className="panel chat-panel">
          <div>
            <p className="eyebrow">带依据提问</p>
            <h2>可信问答</h2>
          </div>
          <div className="message-list">
            {messages.length === 0 ? (
              <div className="empty">
                上传文档后，可以从下方推荐问题开始，也可以直接输入需要依据的问题。
              </div>
            ) : (
              messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  {message.role === "assistant" ? renderAnswer(message.content, message.citations) : message.content}
                </article>
              ))
            )}
          </div>
          <div className="question-box">
            <textarea
              disabled={busy}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="输入一个需要依据的问题..."
              value={question}
            />
            <div className="actions">
              <button className="button" disabled={busy || !question.trim()} onClick={ask} type="button">
                {busy ? "生成中" : "发送问题"}
              </button>
              <button className="ghost-button" type="button" onClick={() => setQuestion("如果文档里没有相关规定，请告诉我不要编造。")}>
                拒答测试
              </button>
            </div>
            <div className="suggestion-row">
              {suggestedQuestions.map((suggestion) => (
                <button
                  className="ghost-button"
                  key={suggestion}
                  onClick={() => setQuestion(suggestion)}
                  type="button"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </section>

        <aside className="panel">
          <p className="eyebrow">执行轨迹与来源</p>
          <h2>执行过程</h2>
          <div className="trace-list">
            {trace.map((step) => (
              <article className={`trace-step ${step.state}`} key={step.label}>
                <strong>{step.label}</strong>
                <p>{step.detail ?? traceStateText[step.state]}</p>
              </article>
            ))}
          </div>
          <h3 style={{ marginTop: 18 }}>来源</h3>
          <div className="source-list">
            {citations.length === 0 ? (
              <div className="empty">回答产生引用后，这里会显示原文片段。</div>
            ) : (
              citations.map((citation) => (
                <article className={`source-item ${activeCitation === citation.id ? "active" : ""}`} key={citation.id}>
                  <div className="status-row">
                    <button className="citation" onClick={() => setActiveCitation(citation.id)} type="button">{citation.id}</button>
                    <span className="tag">{citation.document}</span>
                  </div>
                  <p>{citation.title_path || `第 ${citation.paragraph ?? citation.row ?? "-"} 段`}</p>
                  {citation.reason ? <p className="source-reason">{citation.reason}</p> : null}
                  <p className="snippet">{citation.snippet}</p>
                </article>
              ))
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}

function buildSuggestedQuestions(documents: DocumentRecord[]) {
  const filenames = documents.map((document) => document.filename.toLowerCase()).join(" ");
  if (filenames.includes("简历") || filenames.includes("resume")) {
    return ["这是谁的简历？", "候选人有哪些 AI Agent 相关经历？", "教育背景是什么？"];
  }
  if (filenames.includes("退款") || filenames.includes("政策") || filenames.includes("refund")) {
    return ["退款超过 7 天还能处理吗？", "需要满足什么条件？", "企业版和个人版有什么差异？"];
  }
  if (documents.length > 0) {
    return ["这份文档主要讲什么？", "请总结关键规则", "有哪些需要注意的例外？"];
  }
  return ["上传文档后自动推荐问题", "当前知识库有什么内容？", "如果没有依据请不要编造"];
}
