"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ConversationSummary } from "@/lib/types";

export default function HistoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const knowledgeBaseId = Number(id);
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [error, setError] = useState("");

  async function load() {
    setItems(await api.listHistory(knowledgeBaseId));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [knowledgeBaseId]);

  async function removeConversation(conversationId: number) {
    if (!window.confirm("确定删除这条对话记录吗？")) return;
    await api.deleteConversation(conversationId);
    await load();
  }

  async function clearAll() {
    if (items.length === 0) return;
    if (!window.confirm("确定清空当前知识库的全部历史记录吗？文档不会被删除。")) return;
    await api.clearHistory(knowledgeBaseId);
    await load();
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span>对话留痕</span>
          <strong>对话历史</strong>
        </div>
        <div className="actions">
          <button className="danger-button" disabled={items.length === 0} onClick={clearAll} type="button">
            清空历史
          </button>
          <Link className="ghost-button" href={`/knowledge-bases/${knowledgeBaseId}`}>← 返回工作台</Link>
        </div>
      </header>
      {error ? <section className="empty">{error}</section> : null}
      <section className="history-list">
        {items.length === 0 ? (
          <div className="empty">还没有对话记录。回到工作台提一个问题，答案和引用会被保存。</div>
        ) : (
          items.map((item) => (
            <article className="history-item" key={item.id}>
              <div className="card-kicker">
                <span>对话 #{item.id}</span>
                <span>{new Date(item.updated_at).toLocaleString()}</span>
              </div>
              <h2>{item.title}</h2>
              <div className="meta-row">
                <span className="tag">{questionTypeText[item.question_type]}</span>
                <span className="tag">{item.message_count} 条消息</span>
                <span className="tag">{item.citation_count} 个引用</span>
                <span className={`tag ${confidenceClass(item.confidence_status)}`}>{item.confidence_status}</span>
              </div>
              <div className="actions">
                <Link className="ghost-button" href={`/knowledge-bases/${knowledgeBaseId}`}>继续提问</Link>
                <button className="danger-button" onClick={() => removeConversation(item.id)} type="button">
                  删除
                </button>
              </div>
            </article>
          ))
        )}
      </section>
    </main>
  );
}

const questionTypeText: Record<ConversationSummary["question_type"], string> = {
  resume_identity: "文档身份",
  policy: "政策判断",
  extraction: "信息抽取",
  summary: "总结归纳",
  knowledge: "知识问答",
};

function confidenceClass(status: ConversationSummary["confidence_status"]) {
  if (status === "有引用依据") return "ready";
  if (status === "已拒答") return "failed";
  return "";
}
