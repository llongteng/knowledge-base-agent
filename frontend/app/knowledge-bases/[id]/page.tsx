"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";
import { api, streamChat } from "@/lib/api";
import type { ChatMessage, Citation, DocumentRecord, KnowledgeBase, TraceStep } from "@/lib/types";

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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const readyCount = useMemo(() => documents.filter((document) => document.status === "ready").length, [documents]);

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
    for (const file of Array.from(fileList).slice(0, 5)) {
      await api.uploadDocument(knowledgeBaseId, file);
    }
    await load();
  }

  async function removeDocument(documentId: number) {
    await api.deleteDocument(knowledgeBaseId, documentId);
    await load();
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
            <span className="tag">PDF / TXT / Markdown / CSV，单文件 10MB</span>
            <input multiple onChange={(event) => upload(event.target.files)} type="file" />
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
                  </div>
                  <p className="document-name">{document.filename}</p>
                  {document.error_message ? <p>{document.error_message}</p> : null}
                  <button className="ghost-button" type="button" onClick={() => removeDocument(document.id)}>删除</button>
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
              <div className="empty">上传文档后，试试“退款超过 7 天还能处理吗？”或“企业版售后政策是什么？”</div>
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
