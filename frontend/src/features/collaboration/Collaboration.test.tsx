import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { NotificationsMenu } from "./components/NotificationsMenu";
import { CollaboratorsPage } from "./pages/CollaboratorsPage";

const member = { id: "m1", project_id: "p1", user_id: "u1", email: "owner@example.com", display_name: "Project Owner", role: "OWNER", status: "ACTIVE", person_id: null, person_name: null, joined_at: "2026-09-01T00:00:00Z", invited_at: null, created_at: "2026-09-01T00:00:00Z" };
function json(body: object) { return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } })); }
function renderMembers() { return render(<MemoryRouter initialEntries={["/projects/p1/collaborators"]}><Routes><Route path="/projects/:projectId/collaborators" element={<CollaboratorsPage />} /></Routes></MemoryRouter>); }

beforeEach(() => void i18n.changeLanguage("en"));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("V2.1 collaboration", () => {
  it("shows management controls to an owner and preserves the owner row", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => { const path = String(input); if (path.endsWith("/access")) return json({ project_id: "p1", role: "OWNER", status: "ACTIVE", capabilities: ["members.read", "members.manage"] }); return json([member]); });
    renderMembers();
    expect(await screen.findByRole("heading", { name: "Members & access" })).toBeInTheDocument();
    expect(await screen.findByText("owner@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add member" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });

  it("keeps viewer membership UI read-only", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => { const path = String(input); if (path.endsWith("/access")) return json({ project_id: "p1", role: "VIEWER", status: "ACTIVE", capabilities: ["members.read"] }); return json([member]); });
    renderMembers();
    expect(await screen.findByText("Viewer")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add member" })).not.toBeInTheDocument();
  });

  it("shows bounded recipient notifications and marks them read", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => { if (init?.method === "PATCH") return json({}); return json({ unread_count: 1, items: [{ id: "n1", project_id: "p1", type: "COMMENT_ADDED", title: "New project comment", message: "A comment was added to task.", entity_type: "TASK", entity_id: "t1", read_at: null, created_at: "2026-09-01T00:00:00Z" }] }); });
    render(<MemoryRouter><NotificationsMenu /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Notifications" }));
    fireEvent.click(await screen.findByText("New project comment"));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/notifications/n1/read", expect.objectContaining({ method: "PATCH" }));
  });
});
