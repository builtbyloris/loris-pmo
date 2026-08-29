export type ExpenseStatus = "PLANNED" | "PENDING" | "PAID" | "CANCELLED";
export type FinancialStatus = "NORMAL" | "WARNING" | "CRITICAL" | "UNAVAILABLE";

export interface Budget {
  project_id: string;
  planned_budget: string;
  total_category_allocation: string;
  unallocated_budget: string;
  allocation_exceeds_budget: boolean;
}

export interface BudgetCategory {
  id: string;
  project_id: string;
  name: string;
  planned_amount: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BudgetCategoryInput {
  name: string;
  planned_amount: string;
  notes?: string | null;
}

export interface Expense {
  id: string;
  project_id: string;
  budget_category_id: string | null;
  category_name: string | null;
  description: string;
  amount: string;
  date: string;
  supplier: string | null;
  payer: string | null;
  status: ExpenseStatus;
  task_id: string | null;
  milestone_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseInput {
  budget_category_id?: string | null;
  description: string;
  amount: string;
  date: string;
  supplier?: string | null;
  payer?: string | null;
  status: ExpenseStatus;
  task_id?: string | null;
  milestone_id?: string | null;
  notes?: string | null;
}

export interface ExpenseList {
  items: Expense[];
  total: number;
}

export interface FinancialTotals {
  planned_budget: string;
  actual_cost: string;
  committed_cost: string;
  planned_expense_cost: string;
  forecast: string;
  remaining_budget: string;
  actual_variance: string;
  budget_utilization: string | null;
  financial_status: FinancialStatus;
}

export interface CategoryAnalytics extends FinancialTotals {
  category_id: string;
  category_name: string;
}

export interface MonthlyTrend {
  month: string;
  planned: string;
  committed: string;
  actual: string;
}

export interface BudgetAnalytics {
  totals: FinancialTotals;
  categories: CategoryAnalytics[];
  uncategorized: FinancialTotals;
  monthly_trend: MonthlyTrend[];
  total_category_allocation: string;
  unallocated_budget: string;
  allocation_exceeds_budget: boolean;
}

export interface ExpenseFilters {
  search?: string;
  status?: ExpenseStatus | "";
  category_id?: string;
  sort_by?: "date" | "amount";
  sort_order?: "asc" | "desc";
}
