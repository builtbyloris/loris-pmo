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
    | "project_log"
    | "meeting_action"
    | "ai_insight"
    | "ai_recommendation"
    | "period_fact"
    | "simulation";
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

export interface AIBriefing {
  id: string;
  project_id: string;
  kind: "DAILY" | "WEEKLY";
  period_start: string | null;
  period_end: string | null;
  content: Record<string, unknown>;
  evidence: AIEvidence[];
  provider: string | null;
  model: string | null;
  usage: AIChatResponse["usage"];
  generated_at: string;
  reused: boolean;
}

export type AIScenarioType = "TASK_DELAY" | "MILESTONE_DELAY" | "COST_INCREASE" | "RESOURCE_UNAVAILABLE" | "RISK_OCCURS";
export interface AIScenario {
  id: string;
  project_id: string;
  type: AIScenarioType;
  parameters: Record<string, unknown>;
  deterministic_impact: Record<string, unknown>;
  interpretation: { interpretation: string; impacts: string[]; options: string[]; assumptions: string[]; evidence_refs: string[] };
  evidence: AIEvidence[];
  provider: string;
  model: string;
  usage: AIChatResponse["usage"];
  created_at: string;
}

export type MeetingAIProposalStatus = "PENDING" | "CONFIRMED" | "REJECTED";
export interface MeetingAIProposal {
  id: string;
  kind: "ACTION_ITEM" | "DECISION" | "RISK" | "ISSUE";
  payload: { title: string; description: string; due_date?: string | null; expected_impact?: string | null };
  evidence: AIEvidence[];
  status: MeetingAIProposalStatus;
  confirmed_entity_type: string | null;
  confirmed_entity_id: string | null;
}
export interface MeetingAIAnalysis {
  id: string;
  project_id: string;
  meeting_id: string;
  summary: string;
  evidence: AIEvidence[];
  provider: string;
  model: string;
  usage: AIChatResponse["usage"];
  generated_at: string;
  proposals: MeetingAIProposal[];
  reused: boolean;
}
