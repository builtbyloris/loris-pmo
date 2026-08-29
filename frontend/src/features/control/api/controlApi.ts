import { apiRequest } from "../../../services/api";
import type { ChangeInput, ChangeRequest, ControlSummary, Issue, IssueInput, ListResponse, Risk, RiskInput } from "../types";

const root = (projectId: string) => `/api/v1/projects/${projectId}`;

export const controlApi = {
  listRisks: (projectId: string) => apiRequest<ListResponse<Risk>>(`${root(projectId)}/risks`),
  createRisk: (projectId: string, input: RiskInput) => apiRequest<Risk>(`${root(projectId)}/risks`, { method: "POST", body: JSON.stringify(input) }),
  updateRisk: (projectId: string, id: string, input: Partial<RiskInput>) => apiRequest<Risk>(`${root(projectId)}/risks/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  closeRisk: (projectId: string, id: string) => apiRequest<Risk>(`${root(projectId)}/risks/${id}/close`, { method: "POST" }),
  listIssues: (projectId: string) => apiRequest<ListResponse<Issue>>(`${root(projectId)}/issues`),
  createIssue: (projectId: string, input: IssueInput) => apiRequest<Issue>(`${root(projectId)}/issues`, { method: "POST", body: JSON.stringify(input) }),
  updateIssue: (projectId: string, id: string, input: Partial<IssueInput>) => apiRequest<Issue>(`${root(projectId)}/issues/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  resolveIssue: (projectId: string, id: string, decision: { resolution: string; actual_delay_days?: number | null; actual_cost?: string | null }) => apiRequest<Issue>(`${root(projectId)}/issues/${id}/resolve`, { method: "POST", body: JSON.stringify(decision) }),
  closeIssue: (projectId: string, id: string) => apiRequest<Issue>(`${root(projectId)}/issues/${id}/close`, { method: "POST" }),
  listChanges: (projectId: string) => apiRequest<ListResponse<ChangeRequest>>(`${root(projectId)}/changes`),
  createChange: (projectId: string, input: ChangeInput) => apiRequest<ChangeRequest>(`${root(projectId)}/changes`, { method: "POST", body: JSON.stringify(input) }),
  updateChange: (projectId: string, id: string, input: Partial<ChangeInput>) => apiRequest<ChangeRequest>(`${root(projectId)}/changes/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  transitionChange: (projectId: string, id: string, action: "submit" | "approve" | "reject" | "implement" | "cancel", decision?: string) => apiRequest<ChangeRequest>(`${root(projectId)}/changes/${id}/${action}`, { method: "POST", body: decision === undefined ? undefined : JSON.stringify({ decision }) }),
  summary: (projectId: string) => apiRequest<ControlSummary>(`${root(projectId)}/control/summary`),
};
