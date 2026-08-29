import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n/config";
import { CategoriesPanel } from "./components/CategoriesPanel";
import { ExpensesPanel } from "./components/ExpensesPanel";
import { FinancialDashboard } from "./components/FinancialDashboard";
import type { Budget, BudgetAnalytics, BudgetCategory, Expense } from "./types";

const category: BudgetCategory = { id: "category-1", project_id: "project-1", name: "Development", planned_amount: "600.00", notes: "Delivery", created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z" };
const budget: Budget = { project_id: "project-1", planned_budget: "1000.00", total_category_allocation: "600.00", unallocated_budget: "400.00", allocation_exceeds_budget: false };
const expense: Expense = { id: "expense-1", project_id: "project-1", budget_category_id: category.id, category_name: category.name, description: "API delivery", amount: "300.00", date: "2026-08-29", supplier: "Partner", payer: "PMO", status: "PAID", task_id: null, milestone_id: null, notes: null, created_at: "2026-08-29T00:00:00Z", updated_at: "2026-08-29T00:00:00Z" };
const emptyTotals = { planned_budget: "1000.00", actual_cost: "0.00", committed_cost: "0.00", planned_expense_cost: "0.00", forecast: "0.00", remaining_budget: "1000.00", actual_variance: "1000.00", budget_utilization: "0.00", financial_status: "NORMAL" as const };
const analytics: BudgetAnalytics = { totals: { ...emptyTotals, actual_cost: "300.00", committed_cost: "200.00", planned_expense_cost: "100.00", forecast: "600.00", remaining_budget: "500.00", actual_variance: "700.00", budget_utilization: "50.00", financial_status: "NORMAL" }, categories: [{ ...emptyTotals, category_id: category.id, category_name: category.name, planned_budget: "600.00", actual_cost: "300.00", committed_cost: "200.00", planned_expense_cost: "100.00", forecast: "600.00", remaining_budget: "100.00", actual_variance: "300.00", budget_utilization: "83.33", financial_status: "WARNING" }], uncategorized: { ...emptyTotals, planned_budget: "0.00", remaining_budget: "0.00", actual_variance: "0.00", budget_utilization: null, financial_status: "UNAVAILABLE" }, monthly_trend: [{ month: "2026-08", planned: "100.00", committed: "200.00", actual: "300.00" }], total_category_allocation: "600.00", unallocated_budget: "400.00", allocation_exceeds_budget: false };

beforeEach(() => void i18n.changeLanguage("en"));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("finance workspace", () => {
  it("renders backend-calculated budget metrics, category analytics, and monthly trend", () => {
    render(<FinancialDashboard analytics={analytics} expenses={[expense]} language="en" readOnly={false} onEditBudget={vi.fn()} />);
    expect(screen.getByText("€1,000.00")).toBeInTheDocument();
    expect(screen.getAllByText("€300.00").length).toBeGreaterThan(1);
    expect(screen.getByText("50.00%")).toBeInTheDocument();
    expect(screen.getByText("83.33%")).toBeInTheDocument();
    expect(screen.getByText("2026-08")).toBeInTheDocument();
  });

  it("renders intentional empty financial states", () => {
    const empty = { ...analytics, categories: [], monthly_trend: [], totals: emptyTotals };
    render(<FinancialDashboard analytics={empty} expenses={[]} language="en" readOnly onEditBudget={vi.fn()} />);
    expect(screen.getByText("Create real categories when you are ready; no defaults are seeded.")).toBeInTheDocument();
    expect(screen.getByText("Add the first real expense to begin financial tracking.")).toBeInTheDocument();
  });

  it("creates an expense and filters the expense list", async () => {
    const onCreate = vi.fn().mockResolvedValue(true);
    render(<ExpensesPanel expenses={[expense]} categories={[category]} tasks={[]} milestones={[]} language="en" readOnly={false} onCreate={onCreate} onUpdate={vi.fn().mockResolvedValue(true)} onCancel={vi.fn().mockResolvedValue(true)} />);
    fireEvent.change(screen.getByLabelText("Search expenses"), { target: { value: "missing" } });
    expect(screen.getByRole("heading", { name: "No matching expenses" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search expenses"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Add expense" }));
    fireEvent.change(screen.getByLabelText(/Description/), { target: { value: "Planned hosting" } });
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "50" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ description: "Planned hosting", amount: "50", status: "PLANNED" })));
  });

  it("creates and edits real budget categories", async () => {
    const onCreate = vi.fn().mockResolvedValue(true); const onUpdate = vi.fn().mockResolvedValue(true);
    render(<CategoriesPanel budget={budget} categories={[category]} language="en" readOnly={false} onCreate={onCreate} onUpdate={onUpdate} onRemove={vi.fn().mockResolvedValue(true)} />);
    fireEvent.click(screen.getByRole("button", { name: "Create category" }));
    fireEvent.change(screen.getByLabelText(/Category name/), { target: { value: "Travel" } });
    fireEvent.change(screen.getByLabelText("Planned allocation"), { target: { value: "200" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ name: "Travel", planned_amount: "200" })));
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText(/Category name/), { target: { value: "Software" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(category.id, expect.objectContaining({ name: "Software" })));
  });
});
