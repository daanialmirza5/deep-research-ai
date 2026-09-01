// Mirrors backend/app/schemas/{user,auth}.py — kept in sync by hand for now;
// generating these from the OpenAPI schema at /api/v1/openapi.json is a
// natural follow-up once the API surface stabilizes (Phase 8+).

export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "member";
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ApiProblem {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
}

// Mirrors backend/app/schemas/project.py
export interface ProjectRead {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
}

// Mirrors backend/app/schemas/document.py
export type DocumentSourceType =
  | "pdf"
  | "docx"
  | "txt"
  | "csv"
  | "markdown"
  | "url"
  | "youtube";

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";

export interface DocumentRead {
  id: string;
  project_id: string;
  source_type: DocumentSourceType;
  original_filename: string | null;
  status: DocumentStatus;
  created_at: string;
}

// GET /projects/{id}/documents only — DocumentReadWithChunkCount on the backend.
export interface DocumentWithChunkCount extends DocumentRead {
  chunk_count: number;
}

// Mirrors backend/app/schemas/knowledge_base.py
export interface SearchResult {
  document_id: string;
  chunk_index: number;
  chunk_text: string;
  score: number;
}

// Mirrors backend/app/schemas/analytics.py
export interface SessionsOverTimePoint {
  date: string;
  count: number;
}

export interface AgentRejectionRate {
  agent_name: string;
  rejection_rate: number;
  total_runs: number;
}

export interface AnalyticsOverview {
  sessions_run: number;
  avg_completion_seconds: number | null;
  success_rate: number;
  sessions_over_time: SessionsOverTimePoint[];
  agent_rejection_rates: AgentRejectionRate[];
}

export interface UsageByAgent {
  agent_name: string;
  call_count: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface AnalyticsUsage {
  usage_by_agent: UsageByAgent[];
}

export interface RecentActivityItem {
  event_type: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

// Mirrors backend/app/schemas/session.py
export type SessionStatus = "queued" | "running" | "completed" | "failed";

export interface SessionRead {
  id: string;
  project_id: string;
  user_id: string;
  query: string;
  status: SessionStatus;
  revision_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface MessageRead {
  id: string;
  role: string;
  content: string;
  agent_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ReportRead {
  id: string;
  title: string;
  content_markdown: string;
  quality_score: number | null;
  status: string;
  version: number;
  created_at: string;
}

// app/api/ws.py's two event shapes, relayed verbatim over /ws/sessions/{id}
export interface SessionStatusEvent {
  type: "status";
  status: SessionStatus;
  detail?: string;
}

export interface SessionNodeUpdateEvent {
  type: "node_update";
  node: string;
  messages: string[];
}

export type SessionEvent = SessionStatusEvent | SessionNodeUpdateEvent;
