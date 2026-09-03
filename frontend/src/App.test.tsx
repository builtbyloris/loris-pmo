import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { AuthProvider } from "./features/auth/AuthContext";
import i18n from "./i18n/config";

const user = { id: "d432e9f0-f798-4e36-97ac-952590b7c9a6", email: "manager@example.com", created_at: "2026-08-28T10:00:00Z" };
const emptySummary = { total_projects: 0, active_projects: 0, on_hold_projects: 0, completed_projects: 0 };
const emptyProjects = { items: [], total: 0 };
const emptyIntelligence = { healthy_projects: 0, watch_projects: 0, at_risk_projects: 0, critical_projects: 0, active_critical_alerts: 0, total_overdue_tasks: 0, total_high_critical_risks: 0, projects: [] };

function jsonResponse(body: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

function renderApp(path = "/portfolio") {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>);
}

describe("application foundation", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.dataset.theme = "dark";
    void i18n.changeLanguage("en");
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("redirects an anonymous user to login and signs in", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => jsonResponse({ error: { message: "Authentication required" } }, 401))
      .mockImplementationOnce(() => jsonResponse({ user }))
      .mockImplementationOnce(() => jsonResponse(emptyProjects));
    renderApp("/projects");
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "manager@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Projects" })).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it("renders the real empty portfolio and supports appearance and language preferences", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const path = String(input);
      if (path.endsWith("/auth/me")) return jsonResponse(user);
      if (path.endsWith("/notifications")) return jsonResponse({ items: [], unread_count: 0 });
      if (path.endsWith("/portfolio/summary")) return jsonResponse(emptySummary);
      if (path.includes("/portfolio/intelligence")) return jsonResponse(emptyIntelligence);
      return jsonResponse(emptyProjects);
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Portfolio overview" })).toBeInTheDocument();
    expect(screen.getByText("You don’t have any projects yet.")).toBeInTheDocument();
    expect(screen.getAllByText("0").length).toBeGreaterThan(2);

    fireEvent.click(screen.getAllByRole("button", { name: "Use light theme" })[0]);
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));

    const language = screen.getByLabelText("Language");
    await act(async () => { fireEvent.change(language, { target: { value: "it" } }); });
    expect(await screen.findByRole("heading", { name: "Panoramica portfolio" })).toBeInTheDocument();
  });
});
