import { apiRequest } from "../../../services/api";
import type {
  DependencyType,
  Milestone,
  MilestoneInput,
  Task,
  TaskDependency,
  TaskInput,
  TaskStatus,
  WorkPlanningSummary,
} from "../types";

const root = (projectId: string) => `/api/v1/projects/${projectId}`;

export const workPlanningApi = {
  listTasks: (projectId: string) => apiRequest<{ items: Task[]; total: number }>(`${root(projectId)}/tasks?sort_by=created_at&sort_order=asc`),
  getTask: (projectId: string, taskId: string) => apiRequest<Task>(`${root(projectId)}/tasks/${taskId}`),
  createTask: (projectId: string, input: TaskInput) => apiRequest<Task>(`${root(projectId)}/tasks`, { method: "POST", body: JSON.stringify(input) }),
  updateTask: (projectId: string, taskId: string, input: Partial<TaskInput> & { status?: TaskStatus }) => apiRequest<Task>(`${root(projectId)}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(input) }),
  archiveTask: (projectId: string, taskId: string) => apiRequest<Task>(`${root(projectId)}/tasks/${taskId}/archive`, { method: "POST" }),
  listMilestones: (projectId: string) => apiRequest<Milestone[]>(`${root(projectId)}/milestones`),
  createMilestone: (projectId: string, input: MilestoneInput) => apiRequest<Milestone>(`${root(projectId)}/milestones`, { method: "POST", body: JSON.stringify(input) }),
  updateMilestone: (projectId: string, milestoneId: string, input: Partial<MilestoneInput>) => apiRequest<Milestone>(`${root(projectId)}/milestones/${milestoneId}`, { method: "PATCH", body: JSON.stringify(input) }),
  listDependencies: (projectId: string) => apiRequest<TaskDependency[]>(`${root(projectId)}/task-dependencies`),
  createDependency: (projectId: string, sourceTaskId: string, targetTaskId: string, dependencyType: DependencyType) => apiRequest<TaskDependency>(`${root(projectId)}/task-dependencies`, { method: "POST", body: JSON.stringify({ source_task_id: sourceTaskId, target_task_id: targetTaskId, dependency_type: dependencyType }) }),
  deleteDependency: (projectId: string, dependencyId: string) => apiRequest<void>(`${root(projectId)}/task-dependencies/${dependencyId}`, { method: "DELETE" }),
  summary: (projectId: string) => apiRequest<WorkPlanningSummary>(`${root(projectId)}/work-planning/summary`),
};

