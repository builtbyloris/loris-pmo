import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { ControlDecisionModal } from "./components/ControlDecisionModal";
import { ControlFormModal } from "./components/ControlFormModal";
import { RiskMatrix } from "./pages/ControlWorkspacePage";
import type { Risk } from "./types";

const risk = (overrides: Partial<Risk> = {}): Risk => ({
  id: "risk-1", project_id: "project-1", title: "Supplier failure", description: null,
  category: "Supply", probability: 5, impact: 4, risk_score: 20, severity: "CRITICAL",
  owner_member_id: null, mitigation: null, contingency: null, status: "IDENTIFIED",
  identified_date: "2026-08-29", review_date: null, notes: null, task_ids: [],
  milestone_ids: [], created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z",
  ...overrides,
});

beforeEach(() => void i18n.changeLanguage("en"));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("control workspace", () => {
  it("renders the deterministic 5x5 matrix and excludes closed risks from cell counts", () => {
    render(<RiskMatrix risks={[risk(), risk({ id: "risk-2", title: "Closed", status: "CLOSED" })]} />);
    expect(screen.getByRole("heading", { name: "5×5 risk matrix" })).toBeInTheDocument();
    expect(screen.getByLabelText("Risk probability and impact matrix")).toBeInTheDocument();
    expect(screen.getAllByText("20").length).toBeGreaterThan(0);
    expect(screen.getByTitle("Supplier failure")).toHaveTextContent("1");
  });

  it("creates a risk with probability, impact, and normalized related records", async () => {
    const onSave = vi.fn().mockResolvedValue(true);
    render(<ControlFormModal kind="risk" open value={null} members={[]} tasks={[{ id: "task-1", title: "Mitigate" } as never]} milestones={[{ id: "milestone-1", title: "Review" } as never]} risks={[]} issues={[]} onClose={vi.fn()} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: "New risk" } });
    fireEvent.change(screen.getByLabelText("Probability"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Impact"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Related tasks"), { target: { value: "task-1" } });
    fireEvent.change(screen.getByLabelText("Related milestones"), { target: { value: "milestone-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ title: "New risk", probability: 5, impact: 4, task_ids: ["task-1"], milestone_ids: ["milestone-1"] })));
  });

  it("requires and submits an explicit change decision", async () => {
    const onSave = vi.fn().mockResolvedValue(true);
    render(<ControlDecisionModal open mode="approve" onClose={vi.fn()} onSave={onSave} />);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(screen.getByRole("alert")).toHaveTextContent("A recorded resolution or decision is required.");
    fireEvent.change(screen.getByLabelText("Decision rationale"), { target: { value: "Approved by the board" } });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(onSave).toHaveBeenCalledWith("Approved by the board"));
  });
});
