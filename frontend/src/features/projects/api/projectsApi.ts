import { apiRequest } from "../../../services/api";
import type {
  Objective,
  ObjectiveStatus,
  PortfolioSummary,
  ProjectDetail,
  ProjectDraft,
  ProjectFilters,
  ProjectListResponse,
  ProjectUpdateInput,
  SuccessCriterion,
} from "../types";

function queryString(filters: ProjectFilters): string {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== false) query.set(key, String(value));
  });
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

function projectPayload(draft: ProjectDraft) {
  return {
    ...draft,
    code: draft.code.trim().toUpperCase(),
    description: draft.description.trim() || null,
    client_or_area: draft.client_or_area.trim() || null,
    start_date: draft.start_date || null,
    target_end_date: draft.target_end_date || null,
    planned_budget: draft.planned_budget || "0",
    objectives: draft.objectives.filter((item) => item.title.trim()),
    success_criteria: draft.success_criteria.filter((item) => item.description.trim()),
  };
}

export const projectsApi = {
  portfolio: () => apiRequest<PortfolioSummary>("/api/v1/portfolio/summary"),
  list: (filters: ProjectFilters = {}) =>
    apiRequest<ProjectListResponse>(`/api/v1/projects${queryString(filters)}`),
  get: (projectId: string) => apiRequest<ProjectDetail>(`/api/v1/projects/${projectId}`),
  create: (draft: ProjectDraft) =>
    apiRequest<ProjectDetail>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(projectPayload(draft)),
    }),
  update: (projectId: string, values: ProjectUpdateInput) =>
    apiRequest<ProjectDetail>(`/api/v1/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(values),
    }),
  archive: (projectId: string) =>
    apiRequest<ProjectDetail>(`/api/v1/projects/${projectId}/archive`, { method: "POST" }),
  addObjective: (projectId: string, title: string) =>
    apiRequest<Objective>(`/api/v1/projects/${projectId}/objectives`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  updateObjective: (projectId: string, objectiveId: string, values: { title?: string; status?: ObjectiveStatus }) =>
    apiRequest<Objective>(`/api/v1/projects/${projectId}/objectives/${objectiveId}`, {
      method: "PATCH",
      body: JSON.stringify(values),
    }),
  deleteObjective: (projectId: string, objectiveId: string) =>
    apiRequest<void>(`/api/v1/projects/${projectId}/objectives/${objectiveId}`, { method: "DELETE" }),
  addCriterion: (projectId: string, description: string, objectiveId?: string) =>
    apiRequest<SuccessCriterion>(`/api/v1/projects/${projectId}/success-criteria`, {
      method: "POST",
      body: JSON.stringify({ description, objective_id: objectiveId || null }),
    }),
  deleteCriterion: (projectId: string, criterionId: string) =>
    apiRequest<void>(`/api/v1/projects/${projectId}/success-criteria/${criterionId}`, { method: "DELETE" }),
};
