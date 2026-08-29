import { apiRequest } from "../../../services/api";
import type { ActionItem, Activity, Decision, EntityLink, ListResponse, Meeting, MemorySummary, ProjectLogEntry } from "../types";

const root = (projectId: string) => `/api/v1/projects/${projectId}`;

export const memoryApi = {
  listLog: (projectId: string, search = "") => apiRequest<ListResponse<ProjectLogEntry>>(`${root(projectId)}/log${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createLog: (projectId: string, input: { type: string; title: string; description?: string | null; links?: EntityLink[] }) => apiRequest<ProjectLogEntry>(`${root(projectId)}/log`, { method: "POST", body: JSON.stringify(input) }),
  updateLog: (projectId: string, id: string, input: Partial<{ type: string; title: string; description: string | null; links: EntityLink[] }>) => apiRequest<ProjectLogEntry>(`${root(projectId)}/log/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  listMeetings: (projectId: string, search = "") => apiRequest<ListResponse<Meeting>>(`${root(projectId)}/meetings${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createMeeting: (projectId: string, input: Record<string, unknown>) => apiRequest<Meeting>(`${root(projectId)}/meetings`, { method: "POST", body: JSON.stringify(input) }),
  updateMeeting: (projectId: string, id: string, input: Record<string, unknown>) => apiRequest<Meeting>(`${root(projectId)}/meetings/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  createAction: (projectId: string, meetingId: string, input: Record<string, unknown>) => apiRequest<ActionItem>(`${root(projectId)}/meetings/${meetingId}/action-items`, { method: "POST", body: JSON.stringify(input) }),
  updateAction: (projectId: string, meetingId: string, id: string, input: Record<string, unknown>) => apiRequest<ActionItem>(`${root(projectId)}/meetings/${meetingId}/action-items/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  listDecisions: (projectId: string, search = "") => apiRequest<ListResponse<Decision>>(`${root(projectId)}/decisions${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createDecision: (projectId: string, input: Record<string, unknown>) => apiRequest<Decision>(`${root(projectId)}/decisions`, { method: "POST", body: JSON.stringify(input) }),
  updateDecision: (projectId: string, id: string, input: Record<string, unknown>) => apiRequest<Decision>(`${root(projectId)}/decisions/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  activity: (projectId: string, search = "") => apiRequest<ListResponse<Activity>>(`${root(projectId)}/activity${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  summary: (projectId: string) => apiRequest<MemorySummary>(`${root(projectId)}/memory/summary`),
};
