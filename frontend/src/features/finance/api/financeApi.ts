import { apiRequest } from "../../../services/api";
import type {
  Budget,
  BudgetAnalytics,
  BudgetCategory,
  BudgetCategoryInput,
  Expense,
  ExpenseFilters,
  ExpenseInput,
  ExpenseList,
} from "../types";

const root = (projectId: string) => `/api/v1/projects/${projectId}`;

export const financeApi = {
  getBudget: (projectId: string) => apiRequest<Budget>(`${root(projectId)}/budget`),
  updateBudget: (projectId: string, planned_budget: string) =>
    apiRequest<Budget>(`${root(projectId)}/budget`, {
      method: "PATCH",
      body: JSON.stringify({ planned_budget }),
    }),
  listCategories: (projectId: string) =>
    apiRequest<BudgetCategory[]>(`${root(projectId)}/budget/categories`),
  createCategory: (projectId: string, input: BudgetCategoryInput) =>
    apiRequest<BudgetCategory>(`${root(projectId)}/budget/categories`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateCategory: (projectId: string, categoryId: string, input: Partial<BudgetCategoryInput>) =>
    apiRequest<BudgetCategory>(`${root(projectId)}/budget/categories/${categoryId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  removeCategory: (projectId: string, categoryId: string) =>
    apiRequest<void>(`${root(projectId)}/budget/categories/${categoryId}`, {
      method: "DELETE",
    }),
  listExpenses: (projectId: string, filters: ExpenseFilters = {}) => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const suffix = query.size ? `?${query.toString()}` : "";
    return apiRequest<ExpenseList>(`${root(projectId)}/expenses${suffix}`);
  },
  createExpense: (projectId: string, input: ExpenseInput) =>
    apiRequest<Expense>(`${root(projectId)}/expenses`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateExpense: (projectId: string, expenseId: string, input: Partial<ExpenseInput>) =>
    apiRequest<Expense>(`${root(projectId)}/expenses/${expenseId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  cancelExpense: (projectId: string, expenseId: string) =>
    apiRequest<Expense>(`${root(projectId)}/expenses/${expenseId}/cancel`, {
      method: "POST",
    }),
  analytics: (projectId: string) =>
    apiRequest<BudgetAnalytics>(`${root(projectId)}/budget/analytics`),
};
