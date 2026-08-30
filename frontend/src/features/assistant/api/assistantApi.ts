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
};
