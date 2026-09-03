export type TaskStatus = "BACKLOG" | "TODO" | "IN_PROGRESS" | "BLOCKED" | "REVIEW" | "DONE" | "CANCELLED";
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type MilestoneStatus = "NOT_STARTED" | "IN_PROGRESS" | "AT_RISK" | "COMPLETED";
export type DependencyType = "BLOCKS" | "DEPENDS_ON" | "RELATED_TO";

export interface Task {
  id: string;
  project_id: string;
  parent_task_id: string | null;
  milestone_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  start_date: string | null;
  due_date: string | null;
  estimated_effort: string;
  actual_effort: string;
  completion_percentage: number;
  notes: string | null;
  assignee_ids: string[];
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Milestone {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: MilestoneStatus;
  notes: string | null;
  progress: number | null;
  linked_task_count: number;
  completed_task_count: number;
  overdue_task_count: number;
  created_at: string;
  updated_at: string;
}

export interface TaskDependency {
  id: string;
  project_id: string;
  source_task_id: string;
  target_task_id: string;
  dependency_type: DependencyType;
  created_at: string;
  updated_at: string;
}

export interface WorkPlanningSummary {
  total_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  upcoming_milestones: number;
  progress: number | null;
}

export interface TaskInput {
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  parent_task_id?: string | null;
  milestone_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  estimated_effort: string;
  actual_effort: string;
  completion_percentage: number;
  notes?: string | null;
  assignee_ids: string[];
}

export interface MilestoneInput {
  title: string;
  description?: string | null;
  due_date?: string | null;
  status: MilestoneStatus;
  notes?: string | null;
}

export type DeadlineStatus = "ON_TRACK" | "AT_RISK" | "LATE" | "UNAVAILABLE";
export interface ScheduleTask { id: string; title: string; start: string | null; finish: string | null; duration_days: number | null; progress: number; milestone_id: string | null; dependencies: string[]; critical: boolean | null; earliest_start_offset: number | null; earliest_finish_offset: number | null; latest_start_offset: number | null; latest_finish_offset: number | null; total_float: number | null; free_float: number | null; baseline_start: string | null; baseline_finish: string | null; start_variance: number | null; finish_variance: number | null; warnings: string[]; }
export interface ScheduleMilestone { id: string; title: string; current_date: string | null; projected_date: string | null; baseline_date: string | null; variance_days: number | null; status: DeadlineStatus; affected_task_ids: string[]; }
export interface CriticalPath { complete: boolean; reasons: string[]; project_duration_days: number | null; critical_task_ids: string[]; critical_sequences: string[][]; }
export interface DeadlineImpact { projected_finish: string | null; deadline: string | null; variance_days: number | null; status: DeadlineStatus; }
export interface Schedule { project_id: string; generated_at: string; fingerprint: string; calendar_model: "CALENDAR_DAYS"; calculation_complete: boolean; scheduling_completeness_percent: number; tasks: ScheduleTask[]; milestones: ScheduleMilestone[]; dependencies: Array<{ predecessor_id: string; successor_id: string; type: "FINISH_TO_START" }>; critical_path: CriticalPath; deadline_impact: DeadlineImpact; baseline_variance_days: number | null; baseline_created_at: string | null; }
export type ScheduleChange = { entity_type: "TASK"; task_id: string; start_date: string; due_date: string } | { entity_type: "MILESTONE"; milestone_id: string; due_date: string };
export interface SchedulePreview { preview_token: string; schedule_fingerprint: string; proposed_change: ScheduleChange; affected_tasks: Array<{ id: string; title: string; before_start: string | null; before_finish: string | null; projected_start: string; projected_finish: string; shift_days: number | null; source: boolean }>; milestone_impacts: ScheduleMilestone[]; deadline_impact: DeadlineImpact; critical_path: CriticalPath; warnings: string[]; }

export interface WorkPlanningData {
  tasks: Task[];
  milestones: Milestone[];
  dependencies: TaskDependency[];
  summary: WorkPlanningSummary;
  members: import("../../people/types").ProjectMember[];
  schedule: Schedule;
}
