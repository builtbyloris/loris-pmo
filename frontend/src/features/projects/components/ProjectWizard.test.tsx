import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../../i18n/config";
import { ProjectWizard } from "./ProjectWizard";

const createdProject = {
  id: "8e56cc5c-cee3-4f67-8f0c-62d40fd6e066",
  name: "Platform Launch",
  code: "PLAT-01",
  description: null,
  client_or_area: null,
  status: "NOT_STARTED",
  priority: "HIGH",
  start_date: "2026-09-01",
  target_end_date: "2026-12-01",
  planned_budget: "1000.00",
  notes: null,
  archived_at: null,
  created_at: "2026-08-28T10:00:00Z",
  updated_at: "2026-08-28T10:00:00Z",
  objectives: [],
  success_criteria: [],
};

describe("ProjectWizard", () => {
  beforeEach(() => void i18n.changeLanguage("en"));

  it("validates each step, preserves values, and creates the project", async () => {
    const onCreated = vi.fn();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(createdProject), { status: 201, headers: { "Content-Type": "application/json" } }),
    );
    render(<ProjectWizard open onClose={() => undefined} onCreated={onCreated} />);

    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Project name is required.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Project name/), { target: { value: "Platform Launch" } });
    fireEvent.change(screen.getByLabelText(/Project code/), { target: { value: "plat-01" } });
    fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "HIGH" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-09-01" } });
    fireEvent.change(screen.getByLabelText("Target end date"), { target: { value: "2026-08-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Target end date cannot be before the start date.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Target end date/), { target: { value: "2026-12-01" } });
    fireEvent.change(screen.getByLabelText(/Planned budget/), { target: { value: "1000" } });
    fireEvent.click(screen.getByRole("button", { name: "Add objective" }));
    fireEvent.change(screen.getByLabelText("Objective 1"), { target: { value: "Deliver launch" } });
    fireEvent.click(screen.getByRole("button", { name: "Add criterion" }));
    fireEvent.change(screen.getByLabelText("Success criterion 1"), { target: { value: "Release before year end" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByRole("heading", { name: "Platform Launch" })).toBeInTheDocument();
    expect(screen.getByText("PLAT-01")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create project" }));
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(createdProject));
    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(body.objectives).toEqual([{ title: "Deliver launch" }]);
    expect(body.success_criteria).toEqual([{ description: "Release before year end" }]);
  });
});
