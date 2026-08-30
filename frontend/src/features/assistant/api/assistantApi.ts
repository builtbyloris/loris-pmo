import { apiRequest } from "../../../services/api";
import type {
  AIAnalysisSummary,
  AIAnalyzeResponse,
  AIChatResponse,
  AIHistoryMessage,
  AIInsight,
  AIInsightStatus,
  AIRecommendation,
  AIRecommendationStatus,
  AIStatus,
  AIBriefing,
  AIScenario,
  AIScenarioType,
  MeetingAIAnalysis,
  MeetingAIProposal,
} from "../types";

export const assistantApi = {
  status: (projectId: string) =>
    apiRequest<AIStatus>(`/api/v1/projects/${projectId}/ai/status`),
  analysisSummary: (projectId: string) =>
    apiRequest<AIAnalysisSummary>(`/api/v1/projects/${projectId}/ai/analysis`),
  analyze: (projectId: string, language: "en" | "it", force = false) =>
    apiRequest<AIAnalyzeResponse>(`/api/v1/projects/${projectId}/ai/analyze`, {
      method: "POST",
      body: JSON.stringify({ language, force }),
    }),
  insights: (projectId: string, status?: AIInsightStatus) =>
    apiRequest<AIInsight[]>(
      `/api/v1/projects/${projectId}/ai/insights${status ? `?status=${status}` : ""}`,
    ),
  dismissInsight: (projectId: string, insightId: string) =>
    apiRequest<AIInsight>(`/api/v1/projects/${projectId}/ai/insights/${insightId}/dismiss`, {
      method: "POST",
    }),
  recommendations: (projectId: string, status?: AIRecommendationStatus) =>
    apiRequest<AIRecommendation[]>(
      `/api/v1/projects/${projectId}/ai/recommendations${status ? `?status=${status}` : ""}`,
    ),
  decideRecommendation: (
    projectId: string,
    recommendationId: string,
    action: "accept" | "reject" | "ignore",
    reason?: string,
  ) =>
    apiRequest<AIRecommendation>(
      `/api/v1/projects/${projectId}/ai/recommendations/${recommendationId}/${action}`,
      { method: "POST", body: JSON.stringify({ reason: reason || null }) },
    ),
  chat: (
    projectId: string,
    message: string,
    history: AIHistoryMessage[],
    language: "en" | "it",
  ) =>
    apiRequest<AIChatResponse>(`/api/v1/projects/${projectId}/ai/chat`, {
      method: "POST",
      body: JSON.stringify({
        message,
        history: history.slice(-6),
        language,
      }),
    }),
  daily: (projectId: string) => apiRequest<AIBriefing | null>(`/api/v1/projects//ai/daily-briefing`),
  generateDaily: (projectId: string, language: "en" | "it", force = false) => apiRequest<AIBriefing>(`/api/v1/projects//ai/daily-briefing/generate`, { method: "POST", body: JSON.stringify({ language, force }) }),
  weekly: (projectId: string) => apiRequest<AIBriefing[]>(`/api/v1/projects//ai/weekly-reviews`),
  generateWeekly: (projectId: string, language: "en" | "it", force = false) => apiRequest<AIBriefing>(`/api/v1/projects//ai/weekly-reviews/generate`, { method: "POST", body: JSON.stringify({ language, force }) }),
  scenarios: (projectId: string) => apiRequest<AIScenario[]>(`/api/v1/projects//ai/scenarios`),
  runScenario: (projectId: string, input: { type: AIScenarioType; language: "en" | "it"; task_id?: string; milestone_id?: string; member_id?: string; risk_id?: string; delay_days?: number; cost_increase?: string }) => apiRequest<AIScenario>(`/api/v1/projects//ai/scenarios`, { method: "POST", body: JSON.stringify(input) }),
  meetingAnalysis: (projectId: string, meetingId: string) => apiRequest<MeetingAIAnalysis | null>(`/api/v1/projects//ai/meetings/`),
  analyzeMeeting: (projectId: string, meetingId: string, language: "en" | "it", force = false) => apiRequest<MeetingAIAnalysis>(`/api/v1/projects//ai/meetings//analyze`, { method: "POST", body: JSON.stringify({ language, force }) }),
  reviewMeetingProposal: (projectId: string, meetingId: string, proposalId: string, action: "confirm" | "reject") => apiRequest<MeetingAIProposal>(`/api/v1/projects//ai/meetings//proposals//`, { method: "POST" }),
};
