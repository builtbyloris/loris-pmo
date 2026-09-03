export type ProjectAccessRole = "OWNER" | "PROJECT_ADMIN" | "PROJECT_MANAGER" | "CONTRIBUTOR" | "VIEWER";
export interface ProjectAccess { project_id: string; role: ProjectAccessRole; status: "ACTIVE" | "INVITED" | "DISABLED"; capabilities: string[]; }
export interface Collaborator { id: string; project_id: string; user_id: string; email: string; display_name: string | null; role: ProjectAccessRole; status: string; person_id: string | null; person_name: string | null; joined_at: string | null; invited_at: string | null; created_at: string; }
export type CommentEntityType = "TASK" | "RISK" | "ISSUE" | "CHANGE_REQUEST" | "MEETING" | "DECISION";
export interface ProjectComment { id: string; project_id: string; entity_type: CommentEntityType; entity_id: string; author_user_id: string; author_email: string; author_display_name: string | null; body: string; created_at: string; updated_at: string; can_edit: boolean; }
export interface Notification { id: string; project_id: string | null; type: string; title: string; message: string; entity_type: string | null; entity_id: string | null; read_at: string | null; created_at: string; }
export interface NotificationList { items: Notification[]; unread_count: number; }
