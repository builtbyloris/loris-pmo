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


export type AIInsightSeverity = "INFO" | "WARNING" | "CRITICAL";
export type AIInsightStatus = "ACTIVE" | "DISMISSED" | "RESOLVED" | "EXPIRED";
export type AIRecommendationStatus =
  | "PENDING"
  | "ACCEPTED"
  | "REJECTED"
  | "IGNORED"
  | "EXPIRED";

export interface AIInsight {
  id: string;
  project_id: string;
  type: string;
  severity: AIInsightSeverity;
  title: string;
  summary: string;
  explanation: string;
  evidence: AIEvidence[];
  confidence: number;
  status: AIInsightStatus;
  generated_at: string;
  updated_at: string;
}

export interface AIRecommendation {
  id: string;
  project_id: string;
  insight_id: string | null;
  title: string;
  recommendation: string;
  reasoning_summary: string;
  expected_impact: string | null;
  alternatives: string[];
  evidence: AIEvidence[];
  confidence: number;
  status: AIRecommendationStatus;
  generated_at: string;
  reviewed_at: string | null;
  decision_reason: string | null;
  updated_at: string;
}

export interface AIAnalysisSummary {
  project_id: string;
  active_insights: number;
  critical_insights: number;
  pending_recommendations: number;
  last_analyzed_at: string | null;
  provider: string | null;
  model: string | null;
  usage: AIChatResponse["usage"] | null;
}

export interface AIAnalyzeResponse {
  insights: AIInsight[];
  recommendations: AIRecommendation[];
  summary: AIAnalysisSummary;
  generated: boolean;
  unchanged: boolean;
}
