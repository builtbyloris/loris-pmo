export type AIMessageRole = "user" | "assistant";

export interface AIHistoryMessage {
  role: AIMessageRole;
  content: string;
}

export interface AIStatus {
  available: boolean;
  provider: string;
  model: string;
  reason: string | null;
}

export interface AIEvidence {
  ref: string;
  type:
    | "project"
    | "task"
    | "milestone"
    | "risk"
    | "issue"
    | "change_request"
    | "budget"
    | "kpi"
    | "health"
    | "alert"
    | "team_member"
    | "meeting"
    | "decision"
    | "project_log";
  id: string | null;
  label: string;
  detail: string;
}

export interface AIChatResponse {
  answer: string;
  evidence: AIEvidence[];
  assumptions: string[];
  missing_information: string[];
  suggested_followups: string[];
  provider: string;
  model: string;
  usage: {
    input_tokens: number | null;
    output_tokens: number | null;
    total_tokens: number | null;
  };
  context_sections: string[];
}

export interface ConversationEntry {
  role: AIMessageRole;
  content: string;
  response?: AIChatResponse;
}
