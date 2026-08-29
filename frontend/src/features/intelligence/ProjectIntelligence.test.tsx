import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { intelligenceApi } from "./api/intelligenceApi";
import { ProjectIntelligencePanel } from "./components/ProjectIntelligencePanel";
import type { ProjectIntelligence } from "./types";

vi.mock("./api/intelligenceApi", () => ({
  intelligenceApi: { acknowledge: vi.fn() },
}));

const value: ProjectIntelligence = {
  project_id: "p1",
  kpis: [
    { key: "task_completion_rate", value: 50, unit: "percent", status: "normal", available: true, reason: null },
    { key: "overdue_tasks", value: 1, unit: "count", status: "critical", available: true, reason: null },
    { key: "budget_utilization", value: null, unit: "percent", status: "unavailable", available: false, reason: "no_planned_budget" },
    { key: "critical_risks", value: 1, unit: "count", status: "critical", available: true, reason: null },
    { key: "critical_issues", value: 0, unit: "count", status: "normal", available: true, reason: null },
    { key: "overloaded_members", value: 0, unit: "count", status: "normal", available: true, reason: null },
  ],
  health: {
    score: 62,
    status: "AT_RISK",
    calculated_at: "2026-08-29T10:00:00Z",
    history: [],
    drivers: [{ key: "overdue_tasks", severity: "WARNING", evidence: { count: 1 } }],
    dimensions: [
      { key: "schedule", score: 60, status: "AT_RISK", available: true, reason: null, weight: 25, effective_weight: 55.56, evidence: {} },
      { key: "budget", score: null, status: null, available: false, reason: "no_planned_budget", weight: 20, effective_weight: 0, evidence: {} },
      { key: "tasks", score: 65, status: "AT_RISK", available: true, reason: null, weight: 20, effective_weight: 44.44, evidence: {} },
    ],
  },
  alerts: [{
    id: "a1", project_id: "p1", rule_type: "task_overdue", severity: "CRITICAL", title_key: "intelligence.alerts.taskOverdue.title", reason_key: "intelligence.alerts.taskOverdue.reason", evidence: { title: "Launch", days: 3 }, related_entity_type: "task", related_entity_id: "t1", status: "ACTIVE", first_detected_at: "2026-08-29T10:00:00Z", last_detected_at: "2026-08-29T10:00:00Z", acknowledged_at: null, read_at: null, resolved_at: null,
  }],
  automation_rules: Array.from({ length: 8 }, (_, index) => ({ key: `rule-${index}`, trigger: "changed", conditions: [], actions: [], enabled: true })),
};

beforeEach(() => { void i18n.changeLanguage("en"); vi.clearAllMocks(); });
afterEach(cleanup);

describe("project intelligence", () => {
  it("renders health, unavailable dimensions, KPIs, attention and acknowledges alerts", async () => {
    vi.mocked(intelligenceApi.acknowledge).mockResolvedValue({ ...value.alerts[0], status: "ACKNOWLEDGED", acknowledged_at: "2026-08-29T11:00:00Z" });
    const onChange = vi.fn();
    render(<ProjectIntelligencePanel projectId="p1" value={value} onChange={onChange} readOnly={false} />);
    expect(screen.getByRole("heading", { name: "Project Health" })).toBeInTheDocument();
    expect(screen.getByText("At risk")).toBeInTheDocument();
    expect(screen.getAllByText("No planned budget").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Attention Required" })).toBeInTheDocument();
    expect(screen.getAllByText("Task overdue").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
    await waitFor(() => expect(intelligenceApi.acknowledge).toHaveBeenCalledWith("p1", "a1"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ alerts: [expect.objectContaining({ status: "ACKNOWLEDGED" })] }));
  });

  it("localizes health and alert controls in Italian", async () => {
    await i18n.changeLanguage("it");
    render(<ProjectIntelligencePanel projectId="p1" value={value} onChange={vi.fn()} readOnly />);
    expect(screen.getByRole("heading", { name: "Salute del progetto" })).toBeInTheDocument();
    expect(screen.getByText("A rischio")).toBeInTheDocument();
    expect(screen.getAllByText("Nessun budget pianificato").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Prendi in carico" })).not.toBeInTheDocument();
  });
});
