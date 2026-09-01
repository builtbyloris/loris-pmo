export type IntegrationProvider = "GOOGLE" | "GITHUB";
export type IntegrationKind = "GOOGLE_CALENDAR" | "GMAIL" | "GITHUB_REPOSITORY";
export type ExternalObjectType = "CALENDAR_EVENT" | "EMAIL_MESSAGE" | "GITHUB_ISSUE" | "GITHUB_PULL_REQUEST" | "GITHUB_COMMIT";
export type LinkVisibility = "PRIVATE" | "PROJECT" | "FINANCE";

export interface ProviderStatus { provider: IntegrationProvider; configured: boolean; reason: string | null; }
export interface IntegrationsStatus { encryption_configured: boolean; providers: ProviderStatus[]; }
export interface IntegrationAccount { id: string; provider: IntegrationProvider; provider_account_id: string; display_name: string; status: "CONNECTED" | "REAUTH_REQUIRED" | "ERROR" | "DISCONNECTED"; scopes: string[]; token_expires_at: string | null; last_used_at: string | null; }
export interface ProjectIntegration { id: string; project_id: string; integration_account_id: string; created_by_user_id: string; kind: IntegrationKind; external_resource_id: string; display_name: string; status: "ACTIVE" | "STALE" | "UNAVAILABLE"; last_synced_at: string | null; }
export interface CalendarInfo { id: string; name: string; primary: boolean; }
export interface CalendarEvent { id: string; title: string; starts_at: string; ends_at: string | null; description: string | null; location: string | null; attendees: string[]; url: string; updated_at: string | null; }
export interface CalendarPreview { event: CalendarEvent; confirmation_token: string; expires_at: string; }
export interface EmailMessage { id: string; thread_id: string | null; subject: string; sender: string | null; sent_at: string | null; snippet: string | null; url: string; }
export interface Repository { id: string; full_name: string; private: boolean; url: string; default_branch: string | null; }
export interface SourceObject { id: string; number: number | null; title: string; state: string | null; url: string; summary: string | null; metadata: Record<string, unknown>; }
export interface ExternalLink { id: string; project_id: string; project_integration_id: string; created_by_user_id: string; object_type: ExternalObjectType; external_id: string; external_url: string; title: string; summary: string | null; safe_metadata: Record<string, unknown>; visibility: LinkVisibility; target_entity_type: string; target_entity_id: string; relationship_type: string | null; available: boolean; last_checked_at: string | null; }
