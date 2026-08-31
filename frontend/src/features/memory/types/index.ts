export type ProjectLogType = "MEETING" | "DECISION" | "ISSUE" | "CHANGE" | "MILESTONE" | "TASK_UPDATE" | "RISK_UPDATE" | "NOTE" | "AI_EVENT";
export type MemoryEntityType = "TASK" | "MILESTONE" | "RISK" | "ISSUE" | "CHANGE_REQUEST" | "MEETING" | "DECISION";
export type MeetingStatus = "PLANNED" | "COMPLETED" | "CANCELLED";
export type ActionItemStatus = "PROPOSED" | "CONFIRMED" | "COMPLETED" | "DISMISSED";
export type DecisionStatus = "PROPOSED" | "DECIDED" | "REVERSED" | "SUPERSEDED";

export interface EntityLink { entity_type: MemoryEntityType; entity_id: string; entity_name?: string | null; }
export interface ProjectLogEntry { id: string; project_id: string; type: ProjectLogType; title: string; description: string | null; source: "MANUAL" | "SYSTEM"; created_by_user_id: string; links: EntityLink[]; created_at: string; updated_at: string; }
export interface ActionItem { id: string; project_id: string; meeting_id: string; description: string; owner_member_id: string | null; due_date: string | null; status: ActionItemStatus; task_id: string | null; created_at: string; updated_at: string; }
export interface Meeting { id: string; project_id: string; title: string; scheduled_at: string; duration_minutes: number | null; agenda: string | null; notes: string | null; status: MeetingStatus; participant_ids: string[]; action_items: ActionItem[]; created_at: string; updated_at: string; }
export interface Decision { id: string; project_id: string; meeting_id: string | null; title: string; decision: string; decision_date: string; decision_maker_member_id: string | null; reason: string | null; alternatives: string | null; selected_option: string | null; expected_impact: string | null; actual_impact: string | null; status: DecisionStatus; notes: string | null; links: EntityLink[]; created_at: string; updated_at: string; }
export interface Activity { id: string; actor_user_id: string; actor_email: string | null; actor_display_name: string | null; summary: string; action: string; entity_type: string; entity_id: string; entity_name: string | null; changes: Record<string, unknown> | null; created_at: string; }
export interface MemorySummaryItem { id: string; title: string; status: string | null; occurred_at: string; }
export interface MemorySummary { recent_meetings: MemorySummaryItem[]; recent_decisions: MemorySummaryItem[]; recent_log_entries: MemorySummaryItem[]; pending_action_items: number; }
export interface ListResponse<T> { items: T[]; total: number; }
