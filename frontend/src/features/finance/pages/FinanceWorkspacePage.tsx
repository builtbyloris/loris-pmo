import { AlertCircle, ArrowLeft, ChartNoAxesCombined, ReceiptText, Tags } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { projectsApi } from "../../projects/api/projectsApi";
import type { ProjectDetail } from "../../projects/types";
import { workPlanningApi } from "../../work-planning/api/workPlanningApi";
import type { Milestone, Task } from "../../work-planning/types";
import { financeApi } from "../api/financeApi";
import { BudgetFormModal } from "../components/BudgetFormModal";
import { CategoriesPanel } from "../components/CategoriesPanel";
import { ExpensesPanel } from "../components/ExpensesPanel";
import { FinancialDashboard } from "../components/FinancialDashboard";
import type { Budget, BudgetAnalytics, BudgetCategory, BudgetCategoryInput, Expense, ExpenseInput } from "../types";

type View = "dashboard" | "expenses" | "categories";

export function FinanceWorkspacePage() {
  const { t, i18n } = useTranslation(); const { projectId = "" } = useParams(); const [view, setView] = useState<View>("dashboard"); const [project, setProject] = useState<ProjectDetail | null>(null); const [budget, setBudget] = useState<Budget | null>(null); const [analytics, setAnalytics] = useState<BudgetAnalytics | null>(null); const [categories, setCategories] = useState<BudgetCategory[]>([]); const [expenses, setExpenses] = useState<Expense[]>([]); const [tasks, setTasks] = useState<Task[]>([]); const [milestones, setMilestones] = useState<Milestone[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [mutationError, setMutationError] = useState(""); const [budgetOpen, setBudgetOpen] = useState(false);
  const load = useCallback(async () => { setError(""); try { const [nextProject, nextBudget, nextAnalytics, nextCategories, expenseList, taskList, nextMilestones] = await Promise.all([projectsApi.get(projectId), financeApi.getBudget(projectId), financeApi.analytics(projectId), financeApi.listCategories(projectId), financeApi.listExpenses(projectId), workPlanningApi.listTasks(projectId), workPlanningApi.listMilestones(projectId)]); setProject(nextProject); setBudget(nextBudget); setAnalytics(nextAnalytics); setCategories(nextCategories); setExpenses(expenseList.items); setTasks(taskList.items); setMilestones(nextMilestones); } catch { setError(t("finance.loadError")); } finally { setLoading(false); } }, [projectId, t]);
  useEffect(() => void load(), [load]);
  async function mutate(operation: () => Promise<unknown>) { setMutationError(""); try { await operation(); await load(); return true; } catch { setMutationError(t("finance.actions.error")); return false; } }
  if (loading) return <div className="content-state"><span className="spinner" />{t("common.loading")}</div>;
  if (error || !project || !budget || !analytics) return <div className="content-state error-state" role="alert"><AlertCircle /><h1>{error || t("finance.loadError")}</h1><Link className="secondary-button" to="/projects">{t("projects.backToProjects")}</Link></div>;
  const readOnly = Boolean(project.archived_at); const tabs: Array<[View, typeof ChartNoAxesCombined]> = [["dashboard", ChartNoAxesCombined], ["expenses", ReceiptText], ["categories", Tags]];
  return <div className="finance-workspace page-stack"><Link className="back-link" to={`/projects/${projectId}`}><ArrowLeft size={16} />{t("finance.backToOverview")}</Link><header className="work-header"><div><span className="project-code">{project.code}</span><p className="eyebrow">{t("finance.eyebrow")}</p><h1>{t("finance.title")}</h1><p>{t("finance.subtitle", { project: project.name })}</p></div></header>{readOnly && <div className="archived-notice">{t("finance.readOnly")}</div>}{mutationError && <div className="inline-error" role="alert"><AlertCircle size={15} />{mutationError}</div>}<nav className="work-tabs" aria-label={t("finance.views.label")}>{tabs.map(([key, Icon]) => <button key={key} type="button" className={view === key ? "active" : ""} onClick={() => setView(key)}><Icon size={16} />{t(`finance.views.${key}`)}</button>)}</nav><section className="work-surface finance-surface">
    {view === "dashboard" && <FinancialDashboard analytics={analytics} expenses={expenses} language={i18n.resolvedLanguage ?? "en"} readOnly={readOnly} onEditBudget={() => setBudgetOpen(true)} />}
    {view === "expenses" && <ExpensesPanel expenses={expenses} categories={categories} tasks={tasks} milestones={milestones} language={i18n.resolvedLanguage ?? "en"} readOnly={readOnly} onCreate={(input) => mutate(() => financeApi.createExpense(projectId, input))} onUpdate={(id, input) => mutate(() => financeApi.updateExpense(projectId, id, input))} onCancel={(id) => mutate(() => financeApi.cancelExpense(projectId, id))} />}
    {view === "categories" && <CategoriesPanel budget={budget} categories={categories} language={i18n.resolvedLanguage ?? "en"} readOnly={readOnly} onCreate={(input) => mutate(() => financeApi.createCategory(projectId, input))} onUpdate={(id, input) => mutate(() => financeApi.updateCategory(projectId, id, input))} onRemove={(id) => mutate(() => financeApi.removeCategory(projectId, id))} />}
  </section><BudgetFormModal open={budgetOpen} value={budget.planned_budget} onClose={() => setBudgetOpen(false)} onSave={(value) => mutate(() => financeApi.updateBudget(projectId, value))} /></div>;
}
