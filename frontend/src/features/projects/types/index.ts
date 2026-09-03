export type ProjectStatus = "NOT_STARTED" | "ACTIVE" | "ON_HOLD" | "COMPLETED" | "ARCHIVED";
export type ProjectPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ObjectiveStatus = "NOT_STARTED" | "IN_PROGRESS" | "ACHIEVED" | "CANCELLED";
export type CriterionStatus = "NOT_MET" | "MET" | "NOT_APPLICABLE";

export interface Objective {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: ObjectiveStatus;
  created_at: string;
  updated_at: string;
}

export interface SuccessCriterion {
  id: string;
  project_id: string;
  objective_id: string | null;
  description: string;
  target_value: string | null;
  status: CriterionStatus;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  code: string;
  description: string | null;
  client_or_area: string | null;
  status: ProjectStatus;
  priority: ProjectPriority;
  start_date: string | null;
  target_end_date: string | null;
  planned_budget: string | null;
  notes: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  objectives: Objective[];
  success_criteria: SuccessCriterion[];
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
}

export interface PortfolioSummary {
  total_projects: number;
  active_projects: number;
  on_hold_projects: number;
  completed_projects: number;
}

export interface ProjectDraft {
  name: string;
  code: string;
  description: string;
  client_or_area: string;
  status?: ProjectStatus;
  priority: ProjectPriority;
  start_date: string;
  target_end_date: string;
  planned_budget: string | null;
  notes?: string;
  objectives: Array<{ title: string }>;
  success_criteria: Array<{ description: string }>;
}

export interface ProjectUpdateInput {
  name?: string;
  code?: string;
  description?: string | null;
  client_or_area?: string | null;
  status?: ProjectStatus;
  priority?: ProjectPriority;
  start_date?: string | null;
  target_end_date?: string | null;
  planned_budget?: string;
  notes?: string | null;
}

export interface ProjectFilters {
  search?: string;
  status?: ProjectStatus | "";
  priority?: ProjectPriority | "";
  include_archived?: boolean;
  sort_by?: "updated_at" | "created_at" | "name" | "start_date" | "target_end_date";
  sort_order?: "asc" | "desc";
}
