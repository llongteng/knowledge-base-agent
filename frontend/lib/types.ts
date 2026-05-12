export type KnowledgeBase = {
  id: number;
  name: string;
  description: string;
  document_count: number;
  ready_document_count: number;
  failed_document_count: number;
  knowledge_type: string;
  health_status: string;
  recent_document: string | null;
  recent_question: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentRecord = {
  id: number;
  knowledge_base_id: number;
  filename: string;
  content_hash?: string | null;
  source_type: string;
  status: "processing" | "ready" | "failed";
  error_message: string | null;
  chunk_count: number;
  created_at: string;
};

export type DocumentChunkPreview = {
  id: number;
  chunk_index: number;
  page_number: number | null;
  paragraph_index: number | null;
  title_path: string | null;
  row_number: number | null;
  content: string;
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
  reason?: string | null;
  score: number;
};

export type ConversationSummary = {
  id: number;
  knowledge_base_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  question_type: "resume_identity" | "policy" | "extraction" | "summary" | "knowledge";
  citation_count: number;
  confidence_status: "有引用依据" | "已拒答" | "待核验";
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
