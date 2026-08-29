export type ProjectRole = "PROJECT_MANAGER" | "SPONSOR" | "PRODUCT_OWNER" | "TEAM_MEMBER" | "DEVELOPER" | "DESIGNER" | "DATA_ANALYST" | "QA_TESTER" | "STAKEHOLDER" | "OTHER";
export type StakeholderLevel = "LOW" | "MEDIUM" | "HIGH";
export type WorkloadStatus = "NO_DATA" | "LOW" | "MEDIUM" | "HIGH";

export interface Person {
  id: string;
  name: string;
  email: string | null;
  department: string | null;
  skills: string[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonInput {
  name: string;
  email?: string | null;
  department?: string | null;
  skills?: string[];
  notes?: string | null;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  person_id: string;
  role: ProjectRole;
  responsibilities: string | null;
  availability_percent: number;
  person: Person;
  created_at: string;
  updated_at: string;
}

export interface MemberInput {
  person_id: string;
  role: ProjectRole;
  responsibilities?: string | null;
  availability_percent: number;
}

export interface Stakeholder {
  id: string;
  project_id: string;
  person_id: string | null;
  name: string | null;
  display_name: string;
  organization: string | null;
  role: string | null;
  influence: StakeholderLevel;
  interest: StakeholderLevel;
  communication_frequency: string | null;
  communication_channel: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface StakeholderInput {
  person_id?: string | null;
  name?: string | null;
  organization?: string | null;
  role?: string | null;
  influence: StakeholderLevel;
  interest: StakeholderLevel;
  communication_frequency?: string | null;
  communication_channel?: string | null;
  notes?: string | null;
}

export interface MemberWorkload {
  member_id: string;
  person_id: string;
  name: string;
  role: ProjectRole;
  availability_percent: number;
  active_task_count: number;
  overdue_task_count: number;
  due_soon_task_count: number;
  estimated_effort: string;
  actual_effort: string;
  effort_data_complete: boolean;
  workload_status: WorkloadStatus;
}

export interface PeopleSummary {
  team_size: number;
  stakeholder_count: number;
  workload_warning_count: number;
}
