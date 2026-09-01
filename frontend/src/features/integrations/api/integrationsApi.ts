import { apiRequest } from "../../../services/api";
import type { CalendarEvent, CalendarInfo, CalendarPreview, EmailMessage, ExternalLink, IntegrationAccount, IntegrationKind, IntegrationsStatus, LinkVisibility, ProjectIntegration, Repository, SourceObject } from "../types";

const projectRoot = (projectId: string) => `/api/v1/projects/${projectId}`;

export const integrationsApi = {
  status: () => apiRequest<IntegrationsStatus>("/api/v1/integrations/status"),
  accounts: () => apiRequest<IntegrationAccount[]>("/api/v1/integrations/accounts"),
  startOAuth: (provider: "google" | "github", returnPath: string) => apiRequest<{ authorization_url: string }>(`/api/v1/integrations/oauth/${provider}/start`, { method: "POST", body: JSON.stringify({ return_path: returnPath }) }),
  disconnectAccount: (accountId: string) => apiRequest<void>(`/api/v1/integrations/accounts/${accountId}`, { method: "DELETE" }),
  calendars: (accountId: string) => apiRequest<CalendarInfo[]>(`/api/v1/integrations/accounts/${accountId}/calendars`),
  repositories: (accountId: string) => apiRequest<Repository[]>(`/api/v1/integrations/accounts/${accountId}/github/repositories`),
  projectIntegrations: (projectId: string) => apiRequest<ProjectIntegration[]>(`${projectRoot(projectId)}/integrations`),
  connectProject: (projectId: string, accountId: string, kind: IntegrationKind, resourceId: string, displayName: string) => apiRequest<ProjectIntegration>(`${projectRoot(projectId)}/integrations`, { method: "POST", body: JSON.stringify({ integration_account_id: accountId, kind, external_resource_id: resourceId, display_name: displayName }) }),
  disconnectProject: (projectId: string, integrationId: string) => apiRequest<void>(`${projectRoot(projectId)}/integrations/${integrationId}`, { method: "DELETE" }),
  refreshProject: (projectId: string, integrationId: string) => apiRequest<ProjectIntegration>(`${projectRoot(projectId)}/integrations/${integrationId}/refresh`, { method: "POST" }),
  calendarEvents: (projectId: string, integrationId: string, start: string, end: string) => apiRequest<CalendarEvent[]>(`${projectRoot(projectId)}/integrations/${integrationId}/calendar/events?time_min=${encodeURIComponent(start)}&time_max=${encodeURIComponent(end)}`),
  previewMeeting: (projectId: string, integrationId: string, eventId: string) => apiRequest<CalendarPreview>(`${projectRoot(projectId)}/integrations/${integrationId}/calendar/meeting-preview`, { method: "POST", body: JSON.stringify({ event_id: eventId }) }),
  linkCalendarEvent: (projectId: string, integrationId: string, eventId: string) => apiRequest<ExternalLink>(`${projectRoot(projectId)}/integrations/${integrationId}/calendar/links`, { method: "POST", body: JSON.stringify({ event_id: eventId }) }),
  importMeeting: (projectId: string, integrationId: string, confirmationToken: string) => apiRequest<{ meeting_id: string; external_link_id: string; already_imported: boolean }>(`${projectRoot(projectId)}/integrations/${integrationId}/calendar/import-meeting`, { method: "POST", body: JSON.stringify({ confirmation_token: confirmationToken }) }),
  searchEmail: (projectId: string, integrationId: string, query: string) => apiRequest<EmailMessage[]>(`${projectRoot(projectId)}/integrations/${integrationId}/gmail/search?q=${encodeURIComponent(query)}`),
  linkEmail: (projectId: string, integrationId: string, messageId: string, visibility: LinkVisibility) => apiRequest<ExternalLink>(`${projectRoot(projectId)}/integrations/${integrationId}/gmail/links`, { method: "POST", body: JSON.stringify({ message_id: messageId, visibility, target_entity_type: "PROJECT" }) }),
  sourceObjects: (projectId: string, integrationId: string, collection: "issues" | "pull-requests" | "commits") => apiRequest<SourceObject[]>(`${projectRoot(projectId)}/integrations/${integrationId}/github/${collection}`),
  linkTask: (projectId: string, integrationId: string, objectType: "GITHUB_ISSUE" | "GITHUB_PULL_REQUEST", externalId: string, taskId: string, relationshipType: "IMPLEMENTS" | "TRACKS" | "RELATES_TO") => apiRequest<ExternalLink>(`${projectRoot(projectId)}/integrations/${integrationId}/github/task-links`, { method: "POST", body: JSON.stringify({ object_type: objectType, external_id: externalId, task_id: taskId, relationship_type: relationshipType }) }),
  externalLinks: (projectId: string) => apiRequest<ExternalLink[]>(`${projectRoot(projectId)}/external-links`),
  refreshLink: (projectId: string, linkId: string) => apiRequest<ExternalLink>(`${projectRoot(projectId)}/external-links/${linkId}/refresh`, { method: "POST" }),
  deleteLink: (projectId: string, linkId: string) => apiRequest<void>(`${projectRoot(projectId)}/external-links/${linkId}`, { method: "DELETE" }),
};
