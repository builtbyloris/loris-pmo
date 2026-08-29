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

export interface WorkPlanningData {
  tasks: Task[];
  milestones: Milestone[];
  dependencies: TaskDependency[];
  summary: WorkPlanningSummary;
  members: import("../../people/types").ProjectMember[];
}
