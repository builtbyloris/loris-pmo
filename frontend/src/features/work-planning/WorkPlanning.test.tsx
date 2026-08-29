import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { peopleApi } from "../people/api/peopleApi";
import { workPlanningApi } from "./api/workPlanningApi";
import { KanbanBoard } from "./components/KanbanBoard";
import { MilestonePanel } from "./components/MilestonePanel";
import { TaskFormModal } from "./components/TaskFormModal";
import { TaskListView } from "./components/TaskListView";
import { useWorkPlanning } from "./hooks/useWorkPlanning";
import type { Milestone, Task, WorkPlanningSummary } from "./types";

const task: Task = {
  id: "task-1",
  project_id: "project-1",
  parent_task_id: null,
  milestone_id: "milestone-1",
  title: "Prepare launch plan",
  description: "Coordinate the release",
  status: "TODO",
  priority: "HIGH",
  start_date: "2026-09-01",
  due_date: "2026-09-10",
  estimated_effort: "8.00",
  actual_effort: "2.00",
  completion_percentage: 25,
  notes: null,
  assignee_ids: [],
  archived_at: null,
  created_at: "2026-08-29T00:00:00Z",
  updated_at: "2026-08-29T00:00:00Z",
};

const milestone: Milestone = {
  id: "milestone-1",
  project_id: "project-1",
  title: "Launch",
  description: "Release milestone",
  due_date: "2026-09-12",
  status: "IN_PROGRESS",
  notes: null,
  progress: 25,
  linked_task_count: 1,
  completed_task_count: 0,
  overdue_task_count: 0,
  created_at: "2026-08-29T00:00:00Z",
  updated_at: "2026-08-29T00:00:00Z",
};

const summary: WorkPlanningSummary = {
  total_tasks: 1,
  completed_tasks: 0,
  overdue_tasks: 0,
  upcoming_milestones: 1,
  progress: 25,
};

beforeEach(() => void i18n.changeLanguage("en"));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("work-planning views", () => {
  it("renders an intentional empty state, then a task list with working filters", () => {
    const properties = {
      milestones: [milestone],
      dependencies: [],
      readOnly: false,
      onStatusChange: vi.fn().mockResolvedValue(true),
      onAssigneeChange: vi.fn().mockResolvedValue(true),
      members: [],
    };
    const { rerender } = render(<TaskListView tasks={[]} {...properties} />);
    expect(screen.getByRole("heading", { name: "No tasks yet" })).toBeInTheDocument();

    rerender(<TaskListView tasks={[task]} {...properties} />);
    expect(screen.getByText("Prepare launch plan")).toBeInTheDocument();
    expect(screen.getAllByText("Launch")).toHaveLength(2);

    fireEvent.change(screen.getByLabelText("Search tasks"), { target: { value: "missing" } });
    expect(screen.getByRole("heading", { name: "No matching tasks" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search tasks"), { target: { value: "launch" } });
    fireEvent.change(screen.getByLabelText("Filter by priority"), { target: { value: "HIGH" } });
    expect(screen.getByText("Prepare launch plan")).toBeInTheDocument();
  });

  it("renders every Kanban status and persists a drag status move", async () => {
    const onMove = vi.fn().mockResolvedValue(true);
    render(<KanbanBoard tasks={[task]} milestones={[milestone]} members={[]} readOnly={false} error="" onMove={onMove} />);
    expect(screen.getByLabelText("Backlog")).toBeInTheDocument();
    expect(screen.getByLabelText("Done")).toBeInTheDocument();

    const values = new Map<string, string>();
    const dataTransfer = {
      effectAllowed: "none",
      setData: (type: string, value: string) => values.set(type, value),
      getData: (type: string) => values.get(type) ?? "",
    } as unknown as DataTransfer;
    const card = screen.getByRole("heading", { name: task.title }).closest("article");
    expect(card).not.toBeNull();
    fireEvent.dragStart(card!, { dataTransfer });
    const doneColumn = screen.getByLabelText("Done");
    fireEvent.dragOver(doneColumn, { dataTransfer });
    fireEvent.drop(doneColumn, { dataTransfer });
    await waitFor(() => expect(onMove).toHaveBeenCalledWith(task.id, "DONE"));
    fireEvent.change(screen.getByLabelText(`Change status for ${task.title}`), { target: { value: "IN_PROGRESS" } });
    await waitFor(() => expect(onMove).toHaveBeenCalledWith(task.id, "IN_PROGRESS"));
  });

  it("renders derived milestone progress", () => {
    render(<MilestonePanel milestones={[milestone]} tasks={[task]} dependencies={[]} readOnly={false} onStatus={vi.fn().mockResolvedValue(true)} onDeleteDependency={vi.fn().mockResolvedValue(true)} />);
    expect(screen.getByRole("heading", { name: "Launch" })).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("0 of 1 tasks complete")).toBeInTheDocument();
  });

  it("validates and submits the task creation form", async () => {
    const onCreate = vi.fn().mockResolvedValue(true);
    render(<TaskFormModal open onClose={vi.fn()} onCreate={onCreate} tasks={[]} milestones={[milestone]} members={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Task title is required");
    fireEvent.change(screen.getByLabelText(/Task title/), { target: { value: "Draft release notes" } });
    fireEvent.change(screen.getByLabelText("Milestone"), { target: { value: milestone.id } });
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-09-01" } });
    fireEvent.change(screen.getByLabelText("Due date"), { target: { value: "2026-09-10" } });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ title: "Draft release notes", milestone_id: milestone.id, start_date: "2026-09-01", due_date: "2026-09-10" })));
  });
});

it("refreshes the shared task state after a Kanban-style status update", async () => {
  const doneTask = { ...task, status: "DONE" as const, completion_percentage: 100 };
  const listTasks = vi.spyOn(workPlanningApi, "listTasks")
    .mockResolvedValueOnce({ items: [task], total: 1 })
    .mockResolvedValue({ items: [doneTask], total: 1 });
  vi.spyOn(workPlanningApi, "listMilestones").mockResolvedValue([milestone]);
  vi.spyOn(workPlanningApi, "listDependencies").mockResolvedValue([]);
  vi.spyOn(workPlanningApi, "summary").mockResolvedValue(summary);
  vi.spyOn(peopleApi, "listMembers").mockResolvedValue([]);
  const updateTask = vi.spyOn(workPlanningApi, "updateTask").mockResolvedValue(doneTask);

  const { result } = renderHook(() => useWorkPlanning("project-1"));
  await waitFor(() => expect(result.current.data?.tasks[0].status).toBe("TODO"));
  await act(async () => { expect(await result.current.updateTaskStatus(task.id, "DONE")).toBe(true); });
  await waitFor(() => expect(result.current.data?.tasks[0].status).toBe("DONE"));
  expect(updateTask).toHaveBeenCalledWith("project-1", task.id, { status: "DONE" });
  expect(listTasks).toHaveBeenCalledTimes(2);
});
