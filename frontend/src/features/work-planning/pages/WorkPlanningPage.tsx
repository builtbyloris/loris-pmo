import { AlertCircle, ArrowLeft, CalendarRange, CheckCircle2, Columns3, Flag, GitBranch, ListChecks, Plus, TimerOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { projectsApi } from "../../projects/api/projectsApi";
import type { ProjectDetail } from "../../projects/types";
import { DependencyFormModal } from "../components/DependencyFormModal";
import { KanbanBoard } from "../components/KanbanBoard";
import { MilestoneFormModal } from "../components/MilestoneFormModal";
import { MilestonePanel } from "../components/MilestonePanel";
import { TaskFormModal } from "../components/TaskFormModal";
import { TaskListView } from "../components/TaskListView";
import { TimelineView } from "../components/TimelineView";
import { useWorkPlanning } from "../hooks/useWorkPlanning";
import type { MilestoneStatus } from "../types";

type View = "list" | "kanban" | "timeline" | "milestones";

export function WorkPlanningPage() {
  const { t } = useTranslation();
  const { projectId = "" } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [projectError, setProjectError] = useState(false);
  const [view, setView] = useState<View>("list");
  const [taskOpen, setTaskOpen] = useState(false);
  const [milestoneOpen, setMilestoneOpen] = useState(false);
  const [dependencyOpen, setDependencyOpen] = useState(false);
  const planning = useWorkPlanning(projectId);
  useEffect(() => { projectsApi.get(projectId).then(setProject).catch(() => setProjectError(true)); }, [projectId]);
  if (projectError || planning.error) return <div className="content-state error-state" role="alert"><AlertCircle /><h1>{t("workPlanning.loadError")}</h1><Link className="secondary-button" to="/projects">{t("projects.backToProjects")}</Link></div>;
  if (!project || !planning.data) return <div className="content-state"><span className="spinner" />{t("common.loading")}</div>;
  const { tasks, milestones, dependencies, summary, members } = planning.data;
  const readOnly = Boolean(project.archived_at);
  const tabs: Array<[View, typeof ListChecks]> = [["list", ListChecks], ["kanban", Columns3], ["timeline", CalendarRange], ["milestones", Flag]];
  return <div className="work-planning-page page-stack">
    <Link className="back-link" to={`/projects/${projectId}`}><ArrowLeft size={16} />{t("workPlanning.backToOverview")}</Link>
    <header className="work-header"><div><div className="badge-row"><span className="project-code">{project.code}</span>{readOnly && <span className="project-badge value-archived">{t("projects.status.ARCHIVED")}</span>}</div><p className="eyebrow">{t("workPlanning.eyebrow")}</p><h1>{t("workPlanning.title")}</h1><p>{t("workPlanning.subtitle", { project: project.name })}</p></div>{!readOnly && <div className="work-header-actions"><button type="button" className="secondary-button" onClick={() => setDependencyOpen(true)} disabled={tasks.length < 2}><GitBranch size={16} />{t("workPlanning.actions.addDependency")}</button><button type="button" className="secondary-button" onClick={() => setMilestoneOpen(true)}><Flag size={16} />{t("workPlanning.actions.newMilestone")}</button><button type="button" className="primary-button" onClick={() => setTaskOpen(true)}><Plus size={16} />{t("workPlanning.actions.newTask")}</button></div>}</header>
    {readOnly && <div className="archived-notice">{t("workPlanning.readOnly")}</div>}
    <section className="work-summary"><article><ListChecks /><span>{t("workPlanning.summary.total")}</span><strong>{summary.total_tasks}</strong></article><article><CheckCircle2 /><span>{t("workPlanning.summary.completed")}</span><strong>{summary.completed_tasks}</strong></article><article className={summary.overdue_tasks ? "attention" : ""}><TimerOff /><span>{t("workPlanning.summary.overdue")}</span><strong>{summary.overdue_tasks}</strong></article><article><Flag /><span>{t("workPlanning.summary.upcoming")}</span><strong>{summary.upcoming_milestones}</strong></article><article><CalendarRange /><span>{t("workPlanning.summary.progress")}</span><strong>{summary.progress === null ? "—" : `${summary.progress}%`}</strong></article></section>
    {planning.mutationError && <div className="inline-error" role="alert"><AlertCircle size={15} />{planning.mutationError}</div>}
    <nav className="work-tabs" aria-label={t("workPlanning.views.label")}>{tabs.map(([key, Icon]) => <button type="button" key={key} className={view === key ? "active" : ""} onClick={() => setView(key)}><Icon size={16} />{t(`workPlanning.views.${key}`)}</button>)}</nav>
    <section className="work-surface">
      {view === "list" && <TaskListView tasks={tasks} milestones={milestones} dependencies={dependencies} members={members} readOnly={readOnly} onStatusChange={planning.updateTaskStatus} onAssigneeChange={planning.updateTaskAssignees} />}
      {view === "kanban" && <KanbanBoard tasks={tasks} milestones={milestones} members={members} readOnly={readOnly} error={planning.mutationError} movingTaskId={planning.movingTaskId} onMove={planning.updateTaskStatus} />}
      {view === "timeline" && <TimelineView tasks={tasks} milestones={milestones} dependencies={dependencies} members={members} />}
      {view === "milestones" && <MilestonePanel milestones={milestones} tasks={tasks} dependencies={dependencies} readOnly={readOnly} onStatus={(id, status: MilestoneStatus) => planning.updateMilestone(id, { status })} onDeleteDependency={planning.deleteDependency} />}
    </section>
    <TaskFormModal open={taskOpen} onClose={() => setTaskOpen(false)} onCreate={planning.createTask} tasks={tasks} milestones={milestones} members={members} />
    <MilestoneFormModal open={milestoneOpen} onClose={() => setMilestoneOpen(false)} onCreate={planning.createMilestone} />
    <DependencyFormModal open={dependencyOpen} onClose={() => setDependencyOpen(false)} onCreate={planning.createDependency} tasks={tasks} />
  </div>;
}
