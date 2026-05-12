"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { KnowledgeBase } from "@/lib/types";

export default function KnowledgeBasesPage() {
  const [items, setItems] = useState<KnowledgeBase[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("全部");
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
    const target = items.find((item) => item.id === id);
    if (!window.confirm(`确定删除“${target?.name ?? "这个知识库"}”吗？文档和历史记录都会被删除。`)) {
      return;
    }
    await api.deleteKnowledgeBase(id);
    await load();
  }

  const typeOptions = ["全部", ...Array.from(new Set(items.map((item) => item.knowledge_type)))];
  const filteredItems = items.filter((item) => {
    const matchesType = typeFilter === "全部" || item.knowledge_type === typeFilter;
    const queryText = query.trim().toLowerCase();
    const matchesQuery =
      !queryText ||
      [item.name, item.description, item.recent_document ?? "", item.recent_question ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(queryText);
    return matchesType && matchesQuery;
  });

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span>可信知识问答工作台</span>
          <strong>智能知识库问答 Agent</strong>
        </div>
        <span className="tag">最小可用版：PDF / Word / TXT / Markdown / CSV</span>
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

      <section className="list-toolbar">
        <input
          aria-label="搜索知识库"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索知识库、文档或最近问题"
          value={query}
        />
        <div className="segmented">
          {typeOptions.map((type) => (
            <button
              className={typeFilter === type ? "active" : ""}
              key={type}
              onClick={() => setTypeFilter(type)}
              type="button"
            >
              {type}
            </button>
          ))}
        </div>
      </section>

      {error ? <p className="empty">{error}</p> : null}
      {items.length === 0 ? (
        <section className="empty">还没有知识库。先创建一个，再上传企业文档进行可信问答。</section>
      ) : filteredItems.length === 0 ? (
        <section className="empty">没有匹配的知识库。换个关键词或筛选条件试试。</section>
      ) : (
        <section className="grid kb-grid">
          {filteredItems.map((item) => (
            <article className={`card kb-card ${healthClass(item.health_status)}`} key={item.id}>
              <div>
                <div className="card-kicker">
                  <span>{item.knowledge_type}</span>
                  <span>#{item.id}</span>
                </div>
                <h2>{item.name}</h2>
                <p>{item.description || "未填写说明"}</p>
              </div>
              <div className="meta-row">
                <span className="tag ready">{item.ready_document_count} 份可用</span>
                <span className="tag">{item.document_count} 份文档</span>
                {item.failed_document_count > 0 ? <span className="tag failed">{item.failed_document_count} 份失败</span> : null}
                <span className="tag">{item.health_status}</span>
              </div>
              <div className="card-insights">
                <p><strong>最近文档</strong>{item.recent_document ?? "暂无"}</p>
                <p><strong>最近问题</strong>{item.recent_question ?? "还没有提问"}</p>
                <p><strong>更新时间</strong>{new Date(item.updated_at).toLocaleDateString()}</p>
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

function healthClass(status: string) {
  if (status.includes("失败")) return "health-bad";
  if (status.includes("暂无")) return "health-empty";
  return "health-good";
}
