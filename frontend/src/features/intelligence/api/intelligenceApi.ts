import { apiRequest } from "../../../services/api";
import type { AlertRead, PortfolioIntelligence, ProjectIntelligence } from "../types";

export const intelligenceApi = {
  get: (projectId: string) =>
    apiRequest<ProjectIntelligence>(`/api/v1/projects/${projectId}/intelligence`),
  recalculate: (projectId: string) =>
    apiRequest<ProjectIntelligence>(`/api/v1/projects/${projectId}/intelligence/recalculate`, {
      method: "POST",
    }),
  acknowledge: (projectId: string, alertId: string) =>
    apiRequest<AlertRead>(`/api/v1/projects/${projectId}/alerts/${alertId}/acknowledge`, {
      method: "POST",
    }),
  portfolio: () => apiRequest<PortfolioIntelligence>("/api/v1/portfolio/intelligence"),
};
