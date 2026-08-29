import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import i18n from "../../i18n/config";
import { memoryApi } from "./api/memoryApi";
import { ProjectMemoryPage } from "./pages/ProjectMemoryPage";

vi.mock("../projects/api/projectsApi", () => ({ projectsApi: { get: vi.fn(async () => ({ id: "p1", name: "Apollo", archived_at: null })) } }));
vi.mock("../people/api/peopleApi", () => ({ peopleApi: { listMembers: vi.fn(async () => [{ id: "member-1", person: { name: "Ada" } }]) } }));
vi.mock("../work-planning/api/workPlanningApi", () => ({ workPlanningApi: { listTasks: vi.fn(async () => ({ items: [{ id: "task-1", title: "Prepare" }], total: 1 })), listMilestones: vi.fn(async () => [{ id: "milestone-1", title: "Launch" }]) } }));
vi.mock("./api/memoryApi", () => ({ memoryApi: {
  listLog: vi.fn(async () => ({ items: [{ id: "log-1", project_id: "p1", type: "DECISION", title: "Direction set", description: "Use staged delivery", source: "SYSTEM", created_by_user_id: "u1", links: [{ entity_type: "TASK", entity_id: "task-1", entity_name: "Prepare" }], created_at: "2026-08-29T10:00:00Z", updated_at: "2026-08-29T10:00:00Z" }], total: 1 })),
  listMeetings: vi.fn(async () => ({ items: [], total: 0 })), listDecisions: vi.fn(async () => ({ items: [], total: 0 })), activity: vi.fn(async () => ({ items: [], total: 0 })), summary: vi.fn(),
  createLog: vi.fn(async () => ({})), createMeeting: vi.fn(), updateMeeting: vi.fn(), createAction: vi.fn(), updateAction: vi.fn(), createDecision: vi.fn(), updateDecision: vi.fn(),
} }));

function renderPage() {
  return render(<MemoryRouter initialEntries={["/projects/p1/memory"]}><Routes><Route path="/projects/:projectId/memory" element={<ProjectMemoryPage />} /></Routes></MemoryRouter>);
}

beforeEach(() => { void i18n.changeLanguage("en"); vi.clearAllMocks(); });
afterEach(cleanup);

describe("project memory workspace", () => {
  it("distinguishes meaningful Project Log memory from system activity and creates linked notes", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Direction set" })).toBeInTheDocument();
    expect(screen.getByText("SYSTEM")).toBeInTheDocument();
    expect(screen.getByText("TASK · Prepare")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add log entry" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "New context" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Durable note" } });
    fireEvent.change(screen.getByLabelText("Related task"), { target: { value: "task-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(memoryApi.createLog).toHaveBeenCalledWith("p1", expect.objectContaining({ title: "New context", links: [{ entity_type: "TASK", entity_id: "task-1" }] })));
  });

  it("localizes the memory navigation in Italian", async () => {
    await i18n.changeLanguage("it");
    renderPage();
    expect(await screen.findByRole("tab", { name: "Registro progetto" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Riunioni" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Decisioni" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Attività" })).toBeInTheDocument();
  });
});
