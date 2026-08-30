import { apiRequest } from "../../../services/api";
import type { AIChatResponse, AIHistoryMessage, AIStatus } from "../types";

export const assistantApi = {
  status: (projectId: string) =>
    apiRequest<AIStatus>(`/api/v1/projects/${projectId}/ai/status`),
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
