import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import i18n from "../../../i18n/config";
import { ProjectsPage } from "./ProjectsPage";

beforeEach(() => void i18n.changeLanguage("en"));

it("renders projects returned by the API without invented metrics", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [{ id: "project-1", name: "Real Project", code: "REAL-1", description: null, client_or_area: "Operations", status: "ACTIVE", priority: "HIGH", start_date: "2026-09-01", target_end_date: "2026-11-01", planned_budget: "5000.00", notes: null, archived_at: null, created_at: "2026-08-28T10:00:00Z", updated_at: "2026-08-28T10:00:00Z" }], total: 1 }), { status: 200, headers: { "Content-Type": "application/json" } }),
  );
  render(<MemoryRouter><ProjectsPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Real Project" })).toBeInTheDocument();
  expect(screen.getByText("REAL-1")).toBeInTheDocument();
  expect(screen.queryByText(/health/i)).not.toBeInTheDocument();
});
