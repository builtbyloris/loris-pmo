import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { AIAnalysisWorkspace } from "./components/AIAnalysisWorkspace";

const summary = {
  project_id: "project-1",
  active_insights: 1,
  critical_insights: 0,
  pending_recommendations: 1,
  last_analyzed_at: "2026-08-30T10:00:00Z",
  provider: "gemini",
  model: "gemini-3.6-flash",
  usage: { input_tokens: 80, output_tokens: 40, total_tokens: 120 },
};
const evidence = [{
  ref: "alert:one",
  type: "alert",
  id: "alert-1",
  label: "task_overdue",
  detail: "WARNING · ACTIVE",
}];
const insight = {
  id: "insight-1",
  project_id: "project-1",
  type: "task_overdue",
  severity: "WARNING",
  title: "Testing is late",
  summary: "A testing task is overdue.",
  explanation: "The deterministic alert remains active.",
  evidence,
  confidence: 0.91,
  status: "ACTIVE",
  generated_at: "2026-08-30T10:00:00Z",
  updated_at: "2026-08-30T10:00:00Z",
};
const recommendation = {
  id: "recommendation-1",
  project_id: "project-1",
  insight_id: "insight-1",
  title: "Review testing work",
  recommendation: "Consider reviewing the overdue testing task.",
  reasoning_summary: "The alert is supported by current evidence.",
  expected_impact: "A clearer recovery plan.",
  alternatives: ["Accept the schedule risk"],
  evidence,
  confidence: 0.82,
  status: "PENDING",
  generated_at: "2026-08-30T10:00:00Z",
  reviewed_at: null,
  decision_reason: null,
  updated_at: "2026-08-30T10:00:00Z",
};

function response(body: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

function loadResponses(insights = [insight], recommendations = [recommendation]) {
  return vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => response(summary))
    .mockImplementationOnce(() => response(insights))
    .mockImplementationOnce(() => response(recommendations));
}

describe("AI analysis workspace", () => {
  beforeEach(() => void i18n.changeLanguage("en"));
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it("renders insights, confidence, evidence, and dismiss lifecycle", async () => {
    const fetchMock = loadResponses();
    render(<AIAnalysisWorkspace projectId="project-1" view="insights" providerAvailable readOnly={false} />);
    expect(await screen.findByText("Testing is late")).toBeInTheDocument();
    expect(screen.getByText("Confidence 91%")).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Verified evidence/));
    expect(screen.getByText("task_overdue")).toBeInTheDocument();
    fetchMock.mockImplementationOnce(() => response({ ...insight, status: "DISMISSED" }));
    fireEvent.click(screen.getByRole("button", { name: "Dismiss insight" }));
    expect(await screen.findByText("Dismissed")).toBeInTheDocument();
  });

  it("records recommendation acceptance without presenting execution", async () => {
    const fetchMock = loadResponses();
    render(<AIAnalysisWorkspace projectId="project-1" view="recommendations" providerAvailable readOnly={false} />);
    expect(await screen.findByText("Review testing work")).toBeInTheDocument();
    fireEvent.change(screen.getByText("Decision reason (optional)").parentElement!.querySelector("textarea")!, { target: { value: "Agreed" } });
    fetchMock.mockImplementationOnce(() => response({ ...recommendation, status: "ACCEPTED", decision_reason: "Agreed" }));
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(screen.queryByText("Review testing work")).not.toBeInTheDocument());
    const body = JSON.parse(String(fetchMock.mock.calls[3][1]?.body));
    expect(body).toEqual({ reason: "Agreed" });
  });

  it("shows analysis loading and safe failure", async () => {
    const fetchMock = loadResponses([], []);
    render(<AIAnalysisWorkspace projectId="project-1" view="insights" providerAvailable readOnly={false} />);
    expect(await screen.findByText("No AI insights yet")).toBeInTheDocument();
    let resolveAnalysis: ((value: Response) => void) | undefined;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveAnalysis = resolve; }));
    fireEvent.click(screen.getByRole("button", { name: "Analyze project" }));
    expect(await screen.findByText("Analyzing…")).toBeInTheDocument();
    await act(async () => resolveAnalysis?.(await response({ error: { code: "ai_timeout" } }, 504)));
    expect(await screen.findByRole("alert")).toHaveTextContent("AI analysis took too long");
  });

  it("localizes recommendations in Italian", async () => {
    await act(async () => void await i18n.changeLanguage("it"));
    loadResponses([], []);
    render(<AIAnalysisWorkspace projectId="project-1" view="recommendations" providerAvailable readOnly={false} />);
    expect(await screen.findByRole("heading", { name: "Centro raccomandazioni" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /In attesa/ })).toBeInTheDocument();
    expect(screen.getByText("Nessuna raccomandazione in questo stato")).toBeInTheDocument();
  });
});
