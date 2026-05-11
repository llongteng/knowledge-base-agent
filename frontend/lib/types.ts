export type KnowledgeBase = {
  id: number;
  name: string;
  description: string;
  document_count: number;
  ready_document_count: number;
  created_at: string;
  updated_at: string;
};

export type DocumentRecord = {
  id: number;
  knowledge_base_id: number;
  filename: string;
  source_type: string;
  status: "processing" | "ready" | "failed";
  error_message: string | null;
  chunk_count: number;
  created_at: string;
};

export type Citation = {
  id: string;
  source_type: string;
  document_id: number | null;
  chunk_id: number | null;
  document?: string | null;
  page?: number | null;
  paragraph?: number | null;
  title_path?: string | null;
  row?: number | null;
  snippet: string;
  score: number;
};

export type ConversationSummary = {
  id: number;
  knowledge_base_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

export type TraceStep = {
  label: string;
  state: "idle" | "running" | "done";
  detail?: string;
};
