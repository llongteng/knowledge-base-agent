import type { Citation, ConversationSummary, DocumentRecord, KnowledgeBase } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export const api = {
  listKnowledgeBases: () => request<KnowledgeBase[]>("/api/knowledge-bases"),
  createKnowledgeBase: (name: string, description: string) =>
    request<KnowledgeBase>("/api/knowledge-bases", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  getKnowledgeBase: (id: number) => request<KnowledgeBase>(`/api/knowledge-bases/${id}`),
  deleteKnowledgeBase: (id: number) =>
    request<{ ok: boolean }>(`/api/knowledge-bases/${id}`, { method: "DELETE" }),
  listDocuments: (knowledgeBaseId: number) =>
    request<DocumentRecord[]>(`/api/knowledge-bases/${knowledgeBaseId}/documents`),
  uploadDocument: async (knowledgeBaseId: number, file: File) => {
    const response = await fetch(
      `${API_BASE}/api/knowledge-bases/${knowledgeBaseId}/documents?filename=${encodeURIComponent(file.name)}`,
      {
        method: "POST",
        headers: { "content-type": file.type || "application/octet-stream" },
        body: await file.arrayBuffer(),
      },
    );
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json() as Promise<DocumentRecord>;
  },
  deleteDocument: (knowledgeBaseId: number, documentId: number) =>
    request<{ ok: boolean }>(`/api/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`, {
      method: "DELETE",
    }),
  listHistory: (knowledgeBaseId: number) =>
    request<ConversationSummary[]>(`/api/knowledge-bases/${knowledgeBaseId}/history`),
};

export async function streamChat(
  knowledgeBaseId: number,
  question: string,
  onEvent: (event: string, data: any) => void,
) {
  const response = await fetch(`${API_BASE}/api/knowledge-bases/${knowledgeBaseId}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const event = frame.match(/^event: (.+)$/m)?.[1];
      const dataLine = frame.match(/^data: (.+)$/m)?.[1];
      if (event && dataLine) {
        onEvent(event, JSON.parse(dataLine));
      }
    }
  }
}

export type ChatStreamCitationPayload = Citation[];
