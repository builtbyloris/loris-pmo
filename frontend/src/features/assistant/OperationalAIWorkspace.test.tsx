import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { assistantApi } from "./api/assistantApi";
import { OperationalAIWorkspace } from "./components/OperationalAIWorkspace";

vi.mock("./api/assistantApi", () => ({ assistantApi: {
  daily: vi.fn(async () => null), weekly: vi.fn(async () => []), scenarios: vi.fn(async () => []),
  generateDaily: vi.fn(), generateWeekly: vi.fn(), runScenario: vi.fn(),
} }));
vi.mock("../work-planning/api/workPlanningApi", () => ({ workPlanningApi: { listTasks: vi.fn(async () => ({ items: [{ id: "task-1", title: "Launch" }], total: 1 })), listMilestones: vi.fn(async () => []) } }));
vi.mock("../people/api/peopleApi", () => ({ peopleApi: { listMembers: vi.fn(async () => []) } }));
vi.mock("../control/api/controlApi", () => ({ controlApi: { listRisks: vi.fn(async () => ({ items: [], total: 0 })) } }));

const briefing = { id: "brief-1", project_id: "p1", kind: "DAILY", period_start: null, period_end: null,
  content: { summary: "Focus on launch.", attention_items: [{ priority: "critical", title: "Launch is late", reason: "Verified alert" }] },
  evidence: [{ ref: "alert:1", type: "alert", id: "1", label: "Overdue", detail: "ACTIVE" }], provider: "gemini", model: "gemini-3.6-flash",
  usage: { input_tokens: 10, output_tokens: 10, total_tokens: 20 }, generated_at: "2026-08-31T10:00:00Z", reused: false };

beforeEach(() => { void i18n.changeLanguage("en"); vi.clearAllMocks(); });
afterEach(cleanup);

describe("operational AI workspace", () => {
  it("generates and renders an evidence-backed daily briefing", async () => {
    vi.mocked(assistantApi.generateDaily).mockResolvedValue(briefing as never);
    render(<OperationalAIWorkspace projectId="p1" view="briefing" providerAvailable readOnly={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Generate" }));
    expect(await screen.findByText("Focus on launch.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Evidence"));
    expect(screen.getByText(/Overdue/)).toBeInTheDocument();
    expect(assistantApi.generateDaily).toHaveBeenCalledWith("p1", "en", false);
  });

  it("runs a typed simulation and labels it as non-mutating", async () => {
    vi.mocked(assistantApi.runScenario).mockResolvedValue({ id: "s1", project_id: "p1", type: "TASK_DELAY", parameters: {},
      deterministic_impact: { simulation_only: true }, interpretation: { interpretation: "Delivery may move.", impacts: [], options: [], assumptions: [], evidence_refs: [] },
      evidence: [], provider: "gemini", model: "gemini-3.6-flash", usage: { input_tokens: 1, output_tokens: 1, total_tokens: 2 }, created_at: "2026-08-31T10:00:00Z" } as never);
    render(<OperationalAIWorkspace projectId="p1" view="scenarios" providerAvailable readOnly={false} />);
    await screen.findByText("Simulation only. Results never change operational project data.");
    fireEvent.change(screen.getByLabelText("Subject"), { target: { value: "task-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(assistantApi.runScenario).toHaveBeenCalledWith("p1", expect.objectContaining({ type: "TASK_DELAY", task_id: "task-1", delay_days: 7 })));
    expect(await screen.findByText("Delivery may move.")).toBeInTheDocument();
  });
});
