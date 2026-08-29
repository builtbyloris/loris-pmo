import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { TaskListView } from "../work-planning/components/TaskListView";
import type { Task } from "../work-planning/types";
import { StakeholdersPanel } from "./components/StakeholdersPanel";
import { TeamPanel } from "./components/TeamPanel";
import { WorkloadPanel } from "./components/WorkloadPanel";
import type { MemberWorkload, Person, ProjectMember, Stakeholder } from "./types";

const person: Person = { id: "person-1", name: "Ada Lovelace", email: "ada@example.com", department: "Engineering", skills: ["Planning"], notes: null, created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z" };
const member: ProjectMember = { id: "member-1", project_id: "project-1", person_id: person.id, role: "DEVELOPER", responsibilities: "Delivery", availability_percent: 80, person, created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z" };
const commonTeamProps = { readOnly: false, onCreatePerson: vi.fn().mockResolvedValue(true), onUpdatePerson: vi.fn().mockResolvedValue(true), onAddMember: vi.fn().mockResolvedValue(true), onUpdateMember: vi.fn().mockResolvedValue(true), onRemoveMember: vi.fn().mockResolvedValue(true) };

beforeEach(() => void i18n.changeLanguage("en"));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("people management", () => {
  it("renders the empty team state and adds an existing person with a role", async () => {
    const onAddMember = vi.fn().mockResolvedValue(true);
    render(<TeamPanel people={[person]} members={[]} {...commonTeamProps} onAddMember={onAddMember} />);
    expect(screen.getByRole("heading", { name: "No team members yet" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add to team" }));
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "PROJECT_MANAGER" } });
    fireEvent.change(screen.getByLabelText("Availability"), { target: { value: "60" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onAddMember).toHaveBeenCalledWith(expect.objectContaining({ person_id: person.id, role: "PROJECT_MANAGER", availability_percent: 60 })));
  });

  it("creates a person and updates a project role", async () => {
    const onCreatePerson = vi.fn().mockResolvedValue(true); const onUpdateMember = vi.fn().mockResolvedValue(true);
    render(<TeamPanel people={[person]} members={[member]} {...commonTeamProps} onCreatePerson={onCreatePerson} onUpdateMember={onUpdateMember} />);
    fireEvent.click(screen.getByRole("button", { name: "Create person" }));
    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: "New Person" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onCreatePerson).toHaveBeenCalledWith(expect.objectContaining({ name: "New Person" })));
    fireEvent.click(screen.getByRole("button", { name: "Edit membership" }));
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "PRODUCT_OWNER" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onUpdateMember).toHaveBeenCalledWith(member.id, expect.objectContaining({ role: "PRODUCT_OWNER" })));
  });

  it("renders stakeholder records in the stored-value matrix", () => {
    const stakeholder: Stakeholder = { id: "stakeholder-1", project_id: "project-1", person_id: null, name: "Regulator", display_name: "Regulator", organization: "Authority", role: "Reviewer", influence: "HIGH", interest: "LOW", communication_frequency: "Monthly", communication_channel: "Email", notes: null, created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z" };
    render(<StakeholdersPanel people={[person]} stakeholders={[stakeholder]} readOnly={false} onCreate={vi.fn().mockResolvedValue(true)} onUpdate={vi.fn().mockResolvedValue(true)} onRemove={vi.fn().mockResolvedValue(true)} />);
    expect(screen.getAllByText("Regulator").length).toBeGreaterThan(1);
    expect(screen.getByRole("heading", { name: "Stakeholder matrix" })).toBeInTheDocument();
    expect(screen.getByText("High interest")).toBeInTheDocument();
  });

  it("renders workload facts and incomplete effort state", () => {
    const workload: MemberWorkload = { member_id: member.id, person_id: person.id, name: person.name, role: member.role, availability_percent: 40, active_task_count: 3, overdue_task_count: 1, due_soon_task_count: 1, estimated_effort: "8.00", actual_effort: "2.00", effort_data_complete: false, workload_status: "HIGH" };
    render(<WorkloadPanel workload={[workload]} />);
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("Incomplete effort data")).toBeInTheDocument();
    expect(screen.getAllByText("High").length).toBeGreaterThan(1);
  });

  it("shows task assignees and persists inline assignment changes", async () => {
    const task: Task = { id: "task-1", project_id: "project-1", parent_task_id: null, milestone_id: null, title: "Assigned delivery", description: null, status: "TODO", priority: "HIGH", start_date: null, due_date: null, estimated_effort: "4.00", actual_effort: "0.00", completion_percentage: 0, notes: null, assignee_ids: [member.id], archived_at: null, created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z" };
    const onAssigneeChange = vi.fn().mockResolvedValue(true);
    render(<TaskListView tasks={[task]} milestones={[]} dependencies={[]} members={[member]} readOnly={false} onStatusChange={vi.fn().mockResolvedValue(true)} onAssigneeChange={onAssigneeChange} />);
    const selector = screen.getByLabelText("Change assignees for Assigned delivery");
    const option = selector.querySelector("option") as HTMLOptionElement;
    option.selected = false;
    fireEvent.change(selector);
    await waitFor(() => expect(onAssigneeChange).toHaveBeenCalledWith(task.id, []));
  });
});
