import { apiRequest } from "../../../services/api";
import type { Collaborator, CommentEntityType, Notification, NotificationList, ProjectAccess, ProjectAccessRole, ProjectComment } from "../types";
export const collaborationApi = {
  access: (projectId: string) => apiRequest<ProjectAccess>(`/api/v1/projects/${projectId}/access`),
  collaborators: (projectId: string) => apiRequest<Collaborator[]>(`/api/v1/projects/${projectId}/collaborators`),
  addCollaborator: (projectId: string, email: string, role: ProjectAccessRole) => apiRequest<Collaborator>(`/api/v1/projects/${projectId}/collaborators`, { method: "POST", body: JSON.stringify({ email, role }) }),
  updateCollaborator: (projectId: string, id: string, data: Partial<Pick<Collaborator, "role" | "status" | "person_id">>) => apiRequest<Collaborator>(`/api/v1/projects/${projectId}/collaborators/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  removeCollaborator: (projectId: string, id: string) => apiRequest<void>(`/api/v1/projects/${projectId}/collaborators/${id}`, { method: "DELETE" }),
  comments: (projectId: string, type: CommentEntityType, entityId: string) => apiRequest<ProjectComment[]>(`/api/v1/projects/${projectId}/comments?entity_type=${type}&entity_id=${entityId}`),
  addComment: (projectId: string, entity_type: CommentEntityType, entity_id: string, body: string) => apiRequest<ProjectComment>(`/api/v1/projects/${projectId}/comments`, { method: "POST", body: JSON.stringify({ entity_type, entity_id, body }) }),
  updateComment: (projectId: string, id: string, body: string) => apiRequest<ProjectComment>(`/api/v1/projects/${projectId}/comments/${id}`, { method: "PATCH", body: JSON.stringify({ body }) }),
  removeComment: (projectId: string, id: string) => apiRequest<void>(`/api/v1/projects/${projectId}/comments/${id}`, { method: "DELETE" }),
  notifications: () => apiRequest<NotificationList>("/api/v1/notifications"),
  readNotification: (id: string) => apiRequest<Notification>(`/api/v1/notifications/${id}/read`, { method: "PATCH" }),
  readAll: () => apiRequest<void>("/api/v1/notifications/read-all", { method: "POST" }),
};
