import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { ProjectAssistantPage } from "./pages/ProjectAssistantPage";

const project = {
  id: "a1000000-0000-4000-8000-000000000001",
  name: "Launch",
  code: "LAUNCH",
  description: null,
  client_or_area: null,
  status: "ACTIVE",
  priority: "HIGH",
  start_date: "2026-08-01",
  target_end_date: "2026-10-01",
  planned_budget: "10000.00",
  notes: null,
  archived_at: null,
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-30T10:00:00Z",
};

const status = {
  available: true,
  provider: "gemini",
  model: "gemini-2.5-flash",
  reason: null,
};

const answer = {
  answer: "One critical task is overdue.",
  evidence: [
    {
      ref: "task:one",
      type: "task",
      id: "a2000000-0000-4000-8000-000000000001",
      label: "Validate release",
      detail: "TODO · CRITICAL · due 2026-08-28",
    },
  ],
  assumptions: [],
  missing_information: ["No milestone is linked."],
  suggested_followups: ["Why is it overdue?"],
  provider: "gemini",
  model: "gemini-2.5-flash",
  usage: { input_tokens: 100, output_tokens: 30, total_tokens: 130 },
  context_sections: ["project", "intelligence", "work"],
};

function response(body: object, statusCode = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: statusCode,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function renderPage(path = "/copilot") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/copilot" element={<ProjectAssistantPage />} />
        <Route path="/projects/:projectId/assistant" element={<ProjectAssistantPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Project Assistant", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders conversation, loading, evidence, missing information, and recent history", async () => {
    let resolveFirstChat: ((value: Response) => void) | undefined;
    const firstChat = new Promise<Response>((resolve) => {
      resolveFirstChat = resolve;
    });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => response({ items: [project], total: 1 }))
      .mockImplementationOnce(() => response(status))
      .mockImplementationOnce(() => firstChat)
      .mockImplementationOnce(() => response({ ...answer, answer: "It is blocked by review." }));

    renderPage();
    expect(await screen.findByRole("heading", { name: "Project Assistant" })).toBeInTheDocument();
    expect(await screen.findByText("AI available")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What needs my attention right now?" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "What needs my attention right now?" }));
    expect(await screen.findByText("Reviewing verified project context…")).toBeInTheDocument();
    await act(async () => {
      resolveFirstChat?.(await response(answer));
    });
    expect(await screen.findByText("One critical task is overdue.")).toBeInTheDocument();
    expect(screen.getByText("Validate release")).toBeInTheDocument();
    expect(screen.getByText("No milestone is linked.")).toBeInTheDocument();
    expect(screen.getByText("Why is it overdue?")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Ask about this project"), {
      target: { value: "Why is it overdue?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("It is blocked by review.")).toBeInTheDocument();
    const secondBody = JSON.parse(String(fetchMock.mock.calls[3][1]?.body));
    expect(secondBody.history).toEqual([
      { role: "user", content: "What needs my attention right now?" },
      { role: "assistant", content: "One critical task is overdue." },
    ]);
    expect(secondBody.language).toBe("en");
  });

  it("shows a clear no-key state while keeping project navigation available", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => response({ items: [project], total: 1 }))
      .mockImplementationOnce(() =>
        response({
          available: false,
          provider: "gemini",
          model: "gemini-2.5-flash",
          reason: "not_configured",
        }),
      );
    renderPage();
    expect(
      await screen.findByRole("heading", { name: "AI assistance is not configured" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open project/ })).toHaveAttribute(
      "href",
      `/projects/${project.id}`,
    );
    expect(screen.queryByPlaceholderText(/Ask about schedule/)).not.toBeInTheDocument();
  });

  it("renders a safe timeout error without losing the project workspace", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => response({ items: [project], total: 1 }))
      .mockImplementationOnce(() => response(status))
      .mockImplementationOnce(() =>
        response(
          { error: { code: "ai_timeout", message: "AI request failed." } },
          504,
        ),
      );
    renderPage();
    expect(await screen.findByText("AI available")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "What needs my attention right now?" }));
    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("AI assistance took too long to respond. Please try again.");
    expect(screen.getByRole("link", { name: /Open project/ })).toBeInTheDocument();
  });

  it("localizes the contextual project route in Italian", async () => {
    await act(async () => {
      await i18n.changeLanguage("it");
    });
    vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => response({ items: [project], total: 1 }))
      .mockImplementationOnce(() => response(status));
    renderPage(`/projects/${project.id}/assistant`);
    expect(
      await screen.findByRole("heading", { name: "Assistente di progetto" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna al progetto" })).toHaveAttribute(
      "href",
      `/projects/${project.id}`,
    );
    expect(screen.getByRole("button", { name: "Come sta andando il budget?" })).toBeInTheDocument();
  });
});
