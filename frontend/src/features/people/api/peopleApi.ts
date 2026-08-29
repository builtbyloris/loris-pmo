import { apiRequest } from "../../../services/api";
import type {
  MemberInput,
  MemberWorkload,
  PeopleSummary,
  Person,
  PersonInput,
  ProjectMember,
  Stakeholder,
  StakeholderInput,
} from "../types";

const projectRoot = (projectId: string) => `/api/v1/projects/${projectId}`;

export const peopleApi = {
  listPeople: () => apiRequest<Person[]>("/api/v1/people"),
  createPerson: (input: PersonInput) => apiRequest<Person>("/api/v1/people", { method: "POST", body: JSON.stringify(input) }),
  updatePerson: (personId: string, input: Partial<PersonInput>) => apiRequest<Person>(`/api/v1/people/${personId}`, { method: "PATCH", body: JSON.stringify(input) }),
  listMembers: (projectId: string) => apiRequest<ProjectMember[]>(`${projectRoot(projectId)}/members`),
  addMember: (projectId: string, input: MemberInput) => apiRequest<ProjectMember>(`${projectRoot(projectId)}/members`, { method: "POST", body: JSON.stringify(input) }),
  updateMember: (projectId: string, memberId: string, input: Partial<Omit<MemberInput, "person_id">>) => apiRequest<ProjectMember>(`${projectRoot(projectId)}/members/${memberId}`, { method: "PATCH", body: JSON.stringify(input) }),
  removeMember: (projectId: string, memberId: string) => apiRequest<void>(`${projectRoot(projectId)}/members/${memberId}`, { method: "DELETE" }),
  listStakeholders: (projectId: string) => apiRequest<Stakeholder[]>(`${projectRoot(projectId)}/stakeholders`),
  createStakeholder: (projectId: string, input: StakeholderInput) => apiRequest<Stakeholder>(`${projectRoot(projectId)}/stakeholders`, { method: "POST", body: JSON.stringify(input) }),
  updateStakeholder: (projectId: string, stakeholderId: string, input: Partial<StakeholderInput>) => apiRequest<Stakeholder>(`${projectRoot(projectId)}/stakeholders/${stakeholderId}`, { method: "PATCH", body: JSON.stringify(input) }),
  removeStakeholder: (projectId: string, stakeholderId: string) => apiRequest<void>(`${projectRoot(projectId)}/stakeholders/${stakeholderId}`, { method: "DELETE" }),
  workload: (projectId: string) => apiRequest<MemberWorkload[]>(`${projectRoot(projectId)}/workload`),
  summary: (projectId: string) => apiRequest<PeopleSummary>(`${projectRoot(projectId)}/people/summary`),
};
