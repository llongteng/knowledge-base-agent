"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { KnowledgeBase } from "@/lib/types";

export default function KnowledgeBasesPage() {
  const [items, setItems] = useState<KnowledgeBase[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setItems(await api.listKnowledgeBases());
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await api.createKnowledgeBase(name.trim(), description.trim());
    setName("");
    setDescription("");
    await load();
  }

  async function remove(id: number) {
    await api.deleteKnowledgeBase(id);
    await load();
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span>可信知识问答工作台</span>
          <strong>智能知识库问答 Agent</strong>
        </div>
        <span className="tag">最小可用版：PDF / TXT / Markdown / CSV</span>
      </header>

      <form className="create-form" onSubmit={create}>
        <div className="field">
          <label>知识库名称</label>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：售后政策库" />
        </div>
        <div className="field">
          <label>说明</label>
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="用于退款、企业版、数据保留等制度问答"
          />
        </div>
        <button className="button" type="submit">+ 创建</button>
      </form>

      {error ? <p className="empty">{error}</p> : null}
      {items.length === 0 ? (
        <section className="empty">还没有知识库。先创建一个，再上传企业文档进行可信问答。</section>
      ) : (
        <section className="grid kb-grid">
          {items.map((item) => (
            <article className="card" key={item.id}>
              <div>
                <p className="eyebrow">知识库 #{item.id}</p>
                <h2>{item.name}</h2>
                <p>{item.description || "未填写说明"}</p>
              </div>
              <div className="meta-row">
                <span className="tag ready">{item.ready_document_count} 份可用</span>
                <span className="tag">{item.document_count} 份文档</span>
                <span className="tag">更新于 {new Date(item.updated_at).toLocaleDateString()}</span>
              </div>
              <div className="actions">
                <Link className="button" href={`/knowledge-bases/${item.id}`}>打开工作台</Link>
                <button className="danger-button" type="button" onClick={() => remove(item.id)}>删除</button>
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
