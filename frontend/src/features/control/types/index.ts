export type RiskStatus = "IDENTIFIED" | "MONITORING" | "MITIGATING" | "OCCURRED" | "ACCEPTED" | "CLOSED";
export type RiskSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type IssueStatus = "OPEN" | "IN_ANALYSIS" | "ACTION_PLANNED" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
export type ControlPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ImpactLevel = "NONE" | "LOW" | "MEDIUM" | "HIGH";
export type ChangeStatus = "DRAFT" | "PENDING" | "APPROVED" | "REJECTED" | "IMPLEMENTED" | "CANCELLED";

export interface Risk {
  id: string; project_id: string; title: string; description: string | null; category: string | null;
  probability: number; impact: number; risk_score: number; severity: RiskSeverity;
  owner_member_id: string | null; mitigation: string | null; contingency: string | null;
  status: RiskStatus; identified_date: string; review_date: string | null; notes: string | null;
  task_ids: string[]; milestone_ids: string[]; created_at: string; updated_at: string;
}

export interface RiskInput {
  title: string; description?: string | null; category?: string | null; probability: number;
  impact: number; owner_member_id?: string | null; mitigation?: string | null;
  contingency?: string | null; status?: RiskStatus; identified_date: string;
  review_date?: string | null; notes?: string | null; task_ids?: string[]; milestone_ids?: string[];
}

export interface Issue {
  id: string; project_id: string; title: string; description: string | null; category: string | null;
  priority: ControlPriority; status: IssueStatus; owner_member_id: string | null; identified_date: string;
  schedule_impact: ImpactLevel; budget_impact: ImpactLevel; scope_impact: ImpactLevel;
  quality_impact: ImpactLevel; estimated_delay_days: number | null; estimated_cost: string | null;
  actual_delay_days: number | null; actual_cost: string | null; resolution: string | null;
  notes: string | null; resolved_at: string | null; task_ids: string[]; milestone_ids: string[];
  created_at: string; updated_at: string;
}

export interface IssueInput {
  title: string; description?: string | null; category?: string | null; priority?: ControlPriority;
  status?: IssueStatus; owner_member_id?: string | null; identified_date: string;
  schedule_impact?: ImpactLevel; budget_impact?: ImpactLevel; scope_impact?: ImpactLevel;
  quality_impact?: ImpactLevel; estimated_delay_days?: number | null; estimated_cost?: string | null;
  notes?: string | null; task_ids?: string[]; milestone_ids?: string[];
}

export interface ChangeRequest {
  id: string; project_id: string; title: string; description: string | null; reason: string | null;
  requested_by: string | null; requested_date: string; status: ChangeStatus;
  scope_impact: ImpactLevel; schedule_impact: ImpactLevel; budget_impact: ImpactLevel;
  resource_impact: ImpactLevel; estimated_delay_days: number | null; estimated_cost: string | null;
  decision: string | null; decision_date: string | null; notes: string | null;
  task_ids: string[]; milestone_ids: string[]; issue_ids: string[]; risk_ids: string[];
  created_at: string; updated_at: string;
}

export interface ChangeInput {
  title: string; description?: string | null; reason?: string | null; requested_by?: string | null;
  requested_date: string; scope_impact?: ImpactLevel; schedule_impact?: ImpactLevel;
  budget_impact?: ImpactLevel; resource_impact?: ImpactLevel; estimated_delay_days?: number | null;
  estimated_cost?: string | null; notes?: string | null; task_ids?: string[]; milestone_ids?: string[];
  issue_ids?: string[]; risk_ids?: string[];
}

export interface ListResponse<T> { items: T[]; total: number; }
export interface ControlSummary { open_risks: number; high_critical_risks: number; open_issues: number; critical_issues: number; pending_changes: number; }
