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

  useEffect(() => {
    api.listHistory(knowledgeBaseId).then(setItems).catch((err) => setError(err.message));
  }, [knowledgeBaseId]);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span>对话留痕</span>
          <strong>对话历史</strong>
        </div>
        <Link className="ghost-button" href={`/knowledge-bases/${knowledgeBaseId}`}>← 返回工作台</Link>
      </header>
      {error ? <section className="empty">{error}</section> : null}
      <section className="history-list">
        {items.length === 0 ? (
          <div className="empty">还没有对话记录。回到工作台提一个问题，答案和引用会被保存。</div>
        ) : (
          items.map((item) => (
            <article className="history-item" key={item.id}>
              <p className="eyebrow">对话 #{item.id}</p>
              <h2>{item.title}</h2>
              <div className="meta-row">
                <span className="tag">{item.message_count} 条消息</span>
                <span className="tag">{new Date(item.updated_at).toLocaleString()}</span>
              </div>
            </article>
          ))
        )}
      </section>
    </main>
  );
}
