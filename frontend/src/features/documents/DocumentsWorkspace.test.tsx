import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ReportsPage } from "./pages/ReportsPage";

const documentRecord = {
  id: "d1000000-0000-4000-8000-000000000001",
  project_id: "p1000000-0000-4000-8000-000000000001",
  original_filename: "requirements.txt",
  file_type: "txt",
  mime_type: "text/plain",
  size_bytes: 1024,
  category: "REQUIREMENTS",
  description: "Release requirements",
  status: "READY",
  processing_error: null,
  created_at: "2026-08-31T00:00:00Z",
  updated_at: "2026-08-31T00:00:00Z",
};

function response(body: object) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

beforeEach(() => void i18n.changeLanguage("en"));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Sprint 12 data workspaces", () => {
  it("renders extracted document metadata and knowledge controls", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => String(input).endsWith("/access")
      ? response({ project_id: documentRecord.project_id, role: "PROJECT_MANAGER", status: "ACTIVE", capabilities: ["documents.read", "documents.manage", "finance.read", "finance.manage", "reports.generate"] })
      : response([documentRecord]));
    render(<MemoryRouter initialEntries={[`/projects/${documentRecord.project_id}/documents`]}><Routes><Route path="/projects/:projectId/documents" element={<DocumentsPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Documents", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText("requirements.txt")).toBeInTheDocument();
    expect(screen.getByText(/Requirements · 1.0 KB · READY/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("renders deterministic report, export and validated import controls", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => response({ project_id: documentRecord.project_id, role: "PROJECT_MANAGER", status: "ACTIVE", capabilities: ["documents.read", "documents.manage", "finance.read", "finance.manage", "reports.generate"] }));
    render(<MemoryRouter initialEntries={[`/projects/${documentRecord.project_id}/reports`]}><Routes><Route path="/projects/:projectId/reports" element={<ReportsPage />} /></Routes></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Reports & data", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Report preview")).toBeInTheDocument();
    expect(screen.getByText("Data export")).toBeInTheDocument();
    expect(await screen.findByText("Validated import")).toBeInTheDocument();
  });
});
