import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { integrationsApi } from "./api/integrationsApi";

vi.mock("../collaboration/hooks/useProjectAccess", () => ({
  useProjectAccess: vi.fn(() => ({ can: () => true })),
}));
vi.mock("../work-planning/api/workPlanningApi", () => ({
  workPlanningApi: { listTasks: vi.fn(async () => ({ items: [{ id: "task-1", title: "Local task" }], total: 1 })) },
}));
vi.mock("./api/integrationsApi", () => ({
  integrationsApi: {
    status: vi.fn(), accounts: vi.fn(), projectIntegrations: vi.fn(), externalLinks: vi.fn(),
    searchEmail: vi.fn(), linkEmail: vi.fn(), calendarEvents: vi.fn(), previewMeeting: vi.fn(),
    importMeeting: vi.fn(), linkCalendarEvent: vi.fn(), sourceObjects: vi.fn(), linkTask: vi.fn(),
    refreshProject: vi.fn(), disconnectProject: vi.fn(), disconnectAccount: vi.fn(),
    refreshLink: vi.fn(), deleteLink: vi.fn(), calendars: vi.fn(), repositories: vi.fn(),
    connectProject: vi.fn(), startOAuth: vi.fn(),
  },
}));

const googleAccount = { id: "account-1", provider: "GOOGLE", provider_account_id: "ga", display_name: "person@example.com", status: "CONNECTED", scopes: ["read"], token_expires_at: null, last_used_at: null };
const gmailConnection = { id: "gmail-1", project_id: "p1", integration_account_id: "account-1", created_by_user_id: "u1", kind: "GMAIL", external_resource_id: "me", display_name: "Gmail · person@example.com", status: "ACTIVE", last_synced_at: null };
const sharedLink = { id: "link-1", project_id: "p1", project_integration_id: "gmail-1", created_by_user_id: "u1", object_type: "EMAIL_MESSAGE", external_id: "m1", external_url: "https://mail.google.com/m1", title: "Linked subject", summary: "Safe preview", safe_metadata: {}, visibility: "PROJECT", target_entity_type: "PROJECT", target_entity_id: "p1", relationship_type: "REFERENCE", available: true, last_checked_at: null };

function renderPage() {
  return render(<MemoryRouter initialEntries={["/projects/p1/integrations"]}><Routes><Route path="/projects/:projectId/integrations" element={<IntegrationsPage />} /></Routes></MemoryRouter>);
}

afterEach(() => cleanup());

beforeEach(() => {
  void i18n.changeLanguage("en");
  vi.clearAllMocks();
  vi.mocked(integrationsApi.status).mockResolvedValue({ encryption_configured: true, providers: [{ provider: "GOOGLE", configured: true, reason: null }, { provider: "GITHUB", configured: false, reason: "GitHub OAuth is not configured." }] });
  vi.mocked(integrationsApi.accounts).mockResolvedValue([googleAccount as never]);
  vi.mocked(integrationsApi.projectIntegrations).mockResolvedValue([gmailConnection as never]);
  vi.mocked(integrationsApi.externalLinks).mockResolvedValue([sharedLink as never]);
  vi.mocked(integrationsApi.searchEmail).mockResolvedValue([{ id: "m2", thread_id: "t2", subject: "Search result", sender: "sender@example.com", sent_at: "today", snippet: "Bounded preview", url: "https://mail.google.com/m2" }]);
  vi.mocked(integrationsApi.linkEmail).mockResolvedValue(sharedLink as never);
});

describe("Integrations workspace", () => {
  it("performs an explicit bounded Gmail search and private-by-default link", async () => {
    renderPage();
    expect(await screen.findByText("Gmail · person@example.com")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search Gmail"), { target: { value: "subject:project" } });
    fireEvent.click(screen.getByRole("button", { name: "Search Gmail" }));
    expect(await screen.findByText("Search result")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Link" }).at(-1)!);
    await waitFor(() => expect(integrationsApi.linkEmail).toHaveBeenCalledWith("p1", "gmail-1", "m2", "PRIVATE"));
  });

  it("shows safe provider-unavailable and linked-reference states", async () => {
    renderPage();
    expect(await screen.findByText("GitHub OAuth is not configured.")).toBeInTheDocument();
    expect(screen.getAllByText("Linked subject")[0]).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute("href", "https://mail.google.com/m1");
  });
});
