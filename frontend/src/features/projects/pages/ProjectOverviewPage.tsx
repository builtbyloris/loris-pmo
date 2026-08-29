import { AlertCircle, AlertTriangle, Archive, ArrowLeft, Building2, CalendarDays, CheckCircle2, CircleDollarSign, Edit3, Flag, ListChecks, Network, Plus, Target, TimerOff, Trash2, UsersRound } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../../../services/api";
import { peopleApi } from "../../people/api/peopleApi";
import type { PeopleSummary } from "../../people/types";
import { workPlanningApi } from "../../work-planning/api/workPlanningApi";
import type { WorkPlanningSummary } from "../../work-planning/types";
import { projectsApi } from "../api/projectsApi";
import { Modal } from "../components/Modal";
import { ProjectEditModal } from "../components/ProjectEditModal";
import { StatusBadge } from "../components/StatusBadge";
import type { ObjectiveStatus, ProjectDetail } from "../types";
import { formatCurrency, formatDate } from "../utils/format";

export function ProjectOverviewPage() {
  const { t, i18n } = useTranslation();
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [workSummary, setWorkSummary] = useState<WorkPlanningSummary | null>(null);
  const [peopleSummary, setPeopleSummary] = useState<PeopleSummary | null>(null);
  const [error, setError] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [objectiveOpen, setObjectiveOpen] = useState(false);
  const [criterionOpen, setCriterionOpen] = useState(false);
  const [input, setInput] = useState("");
  const [selectedObjective, setSelectedObjective] = useState("");
  const [actionError, setActionError] = useState("");
  const [saving, setSaving] = useState(false);
  const load = useCallback(() => {
    setError(false);
    Promise.all([projectsApi.get(projectId), workPlanningApi.summary(projectId), peopleApi.summary(projectId)])
      .then(([nextProject, summary, nextPeopleSummary]) => { setProject(nextProject); setWorkSummary(summary); setPeopleSummary(nextPeopleSummary); })
      .catch(() => setError(true));
  }, [projectId]);
  useEffect(load, [load]);
  async function addObjective(event: FormEvent) { event.preventDefault(); if (!input.trim()) return; setSaving(true); setActionError(""); try { await projectsApi.addObjective(projectId, input); setInput(""); setObjectiveOpen(false); load(); } catch (reason) { setActionError(reason instanceof ApiError ? reason.message : t("projects.actions.error")); } finally { setSaving(false); } }
  async function addCriterion(event: FormEvent) { event.preventDefault(); if (!input.trim()) return; setSaving(true); setActionError(""); try { await projectsApi.addCriterion(projectId, input, selectedObjective); setInput(""); setSelectedObjective(""); setCriterionOpen(false); load(); } catch (reason) { setActionError(reason instanceof ApiError ? reason.message : t("projects.actions.error")); } finally { setSaving(false); } }
  async function archive() { setSaving(true); try { await projectsApi.archive(projectId); navigate("/projects", { replace: true, state: { archived: true } }); } catch (reason) { setActionError(reason instanceof ApiError ? reason.message : t("projects.actions.error")); } finally { setSaving(false); } }
  if (error) return <div className="content-state error-state"><AlertCircle /><h1>{t("projects.notFound")}</h1><Link className="secondary-button" to="/projects">{t("projects.backToProjects")}</Link></div>;
  if (!project) return <div className="content-state"><span className="spinner" />{t("common.loading")}</div>;
  const archived = Boolean(project.archived_at);
  return <div className="project-overview page-stack">
    {(location.state as { created?: boolean } | null)?.created && <div className="success-banner"><CheckCircle2 size={18} />{t("projects.createdSuccess")}</div>}
    <Link className="back-link" to="/projects"><ArrowLeft size={16} />{t("projects.backToProjects")}</Link>
    <header className="project-hero"><div><div className="badge-row"><span className="project-code">{project.code}</span><StatusBadge value={project.status} /><StatusBadge value={project.priority} kind="priority" /></div><h1>{project.name}</h1><p>{project.client_or_area || t("common.notProvided")}</p></div>{!archived && <div className="project-actions"><button className="secondary-button" onClick={() => setEditOpen(true)}><Edit3 size={16} />{t("common.edit")}</button><button className="danger-button" onClick={() => setArchiveOpen(true)}><Archive size={16} />{t("projects.archive.action")}</button></div>}</header>
    {archived && <div className="archived-notice">{t("projects.archive.readOnly")}</div>}
    <section className="overview-section"><header><div><p className="eyebrow">{t("projects.overview.detailsEyebrow")}</p><h2>{t("projects.overview.information")}</h2></div></header><div className="info-grid"><article><Building2 /><span>{t("projects.fields.client")}</span><strong>{project.client_or_area || "—"}</strong></article><article><CalendarDays /><span>{t("projects.fields.startDate")}</span><strong>{formatDate(project.start_date, i18n.resolvedLanguage)}</strong></article><article><CalendarDays /><span>{t("projects.fields.targetDate")}</span><strong>{formatDate(project.target_end_date, i18n.resolvedLanguage)}</strong></article><article><CircleDollarSign /><span>{t("projects.fields.plannedBudget")}</span><strong>{formatCurrency(project.planned_budget, i18n.resolvedLanguage)}</strong></article></div><div className="description-block"><h3>{t("projects.fields.description")}</h3><p>{project.description || t("common.notProvided")}</p></div></section>
    <div className="overview-columns">
      <section className="overview-section"><header><div><p className="eyebrow">{t("projects.objectives.eyebrow")}</p><h2>{t("projects.objectives.title")}</h2></div>{!archived && <button className="text-button" onClick={() => { setInput(""); setActionError(""); setObjectiveOpen(true); }}><Plus size={16} />{t("projects.objectives.add")}</button>}</header>{project.objectives.length === 0 ? <div className="section-empty"><Target size={22} /><p>{t("projects.objectives.empty")}</p></div> : <ul className="record-list">{project.objectives.map((objective) => <li key={objective.id}><div><strong>{objective.title}</strong><StatusBadge value={objective.status} kind="objective" /></div>{!archived && <div className="record-actions"><select aria-label={t("projects.objectives.statusLabel", { title: objective.title })} value={objective.status} onChange={(e) => void projectsApi.updateObjective(projectId, objective.id, { status: e.target.value as ObjectiveStatus }).then(load)}>{(["NOT_STARTED", "IN_PROGRESS", "ACHIEVED", "CANCELLED"] as ObjectiveStatus[]).map((value) => <option value={value} key={value}>{t(`projects.objective.${value}`)}</option>)}</select><button className="icon-button danger" onClick={() => window.confirm(t("projects.objectives.deleteConfirm")) && void projectsApi.deleteObjective(projectId, objective.id).then(load)} aria-label={t("common.delete")}><Trash2 size={15} /></button></div>}</li>)}</ul>}</section>
      <section className="overview-section"><header><div><p className="eyebrow">{t("projects.success_criteria.eyebrow")}</p><h2>{t("projects.success_criteria.title")}</h2></div>{!archived && <button className="text-button" onClick={() => { setInput(""); setSelectedObjective(""); setActionError(""); setCriterionOpen(true); }}><Plus size={16} />{t("projects.success_criteria.add")}</button>}</header>{project.success_criteria.length === 0 ? <div className="section-empty"><CheckCircle2 size={22} /><p>{t("projects.success_criteria.empty")}</p></div> : <ul className="record-list criteria">{project.success_criteria.map((criterion) => <li key={criterion.id}><div><strong>{criterion.description}</strong>{criterion.objective_id && <small>{project.objectives.find((item) => item.id === criterion.objective_id)?.title}</small>}</div>{!archived && <button className="icon-button danger" onClick={() => window.confirm(t("projects.success_criteria.deleteConfirm")) && void projectsApi.deleteCriterion(projectId, criterion.id).then(load)} aria-label={t("common.delete")}><Trash2 size={15} /></button>}</li>)}</ul>}</section>
    </div>
    <section className="overview-section planning-overview"><header><div><p className="eyebrow">{t("workPlanning.overview.eyebrow")}</p><h2>{t("workPlanning.overview.title")}</h2><p>{t("workPlanning.overview.description")}</p></div><Link className="secondary-button" to={`/projects/${projectId}/work`}>{t("workPlanning.overview.open")}</Link></header>{workSummary && <div className="planning-overview-grid"><article><ListChecks /><span>{t("workPlanning.summary.total")}</span><strong>{workSummary.total_tasks}</strong></article><article><CheckCircle2 /><span>{t("workPlanning.summary.completed")}</span><strong>{workSummary.completed_tasks}</strong></article><article className={workSummary.overdue_tasks ? "attention" : ""}><TimerOff /><span>{t("workPlanning.summary.overdue")}</span><strong>{workSummary.overdue_tasks}</strong></article><article><Flag /><span>{t("workPlanning.summary.upcoming")}</span><strong>{workSummary.upcoming_milestones}</strong></article><article><CalendarDays /><span>{t("workPlanning.summary.progress")}</span><strong>{workSummary.progress === null ? t("workPlanning.overview.noProgress") : `${workSummary.progress}%`}</strong></article></div>}</section>
    <section className="overview-section planning-overview"><header><div><p className="eyebrow">{t("people.overview.eyebrow")}</p><h2>{t("people.overview.title")}</h2><p>{t("people.overview.description")}</p></div><Link className="secondary-button" to={`/projects/${projectId}/people`}>{t("people.overview.open")}</Link></header>{peopleSummary && <div className="planning-overview-grid people-overview-grid"><article><UsersRound /><span>{t("people.overview.team")}</span><strong>{peopleSummary.team_size}</strong></article><article><Network /><span>{t("people.overview.stakeholders")}</span><strong>{peopleSummary.stakeholder_count}</strong></article><article className={peopleSummary.workload_warning_count ? "attention" : ""}><AlertTriangle /><span>{t("people.overview.warnings")}</span><strong>{peopleSummary.workload_warning_count}</strong></article></div>}</section>
    <section className="future-metrics"><Target size={22} /><div><h2>{t("projects.overview.futureMetrics")}</h2><p>{t("projects.overview.futureMetricsBody")}</p></div></section>
    <ProjectEditModal project={project} open={editOpen} onClose={() => setEditOpen(false)} onSaved={(next) => { setProject(next); setEditOpen(false); }} />
    <Modal open={archiveOpen} onClose={() => setArchiveOpen(false)} title={t("projects.archive.title")} description={t("projects.archive.description")} footer={<><button className="secondary-button" onClick={() => setArchiveOpen(false)}>{t("common.cancel")}</button><button className="danger-button" onClick={() => void archive()} disabled={saving}>{saving ? t("common.saving") : t("projects.archive.confirm")}</button></>}><div className="confirm-content"><Archive size={28} /><p>{t("projects.archive.preservation")}</p></div>{actionError && <div className="inline-error">{actionError}</div>}</Modal>
    <Modal open={objectiveOpen} onClose={() => setObjectiveOpen(false)} title={t("projects.objectives.addTitle")} footer={<><button className="secondary-button" onClick={() => setObjectiveOpen(false)}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="add-objective" disabled={saving}>{t("common.add")}</button></>}><form id="add-objective" onSubmit={addObjective} className="single-field-form"><label><span>{t("projects.objectives.objectiveTitle")}</span><input autoFocus value={input} onChange={(e) => setInput(e.target.value)} /></label></form>{actionError && <div className="inline-error">{actionError}</div>}</Modal>
    <Modal open={criterionOpen} onClose={() => setCriterionOpen(false)} title={t("projects.success_criteria.addTitle")} footer={<><button className="secondary-button" onClick={() => setCriterionOpen(false)}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="add-criterion" disabled={saving}>{t("common.add")}</button></>}><form id="add-criterion" onSubmit={addCriterion} className="single-field-form"><label><span>{t("projects.success_criteria.description")}</span><textarea autoFocus rows={3} value={input} onChange={(e) => setInput(e.target.value)} /></label><label><span>{t("projects.success_criteria.linkObjective")}</span><select value={selectedObjective} onChange={(e) => setSelectedObjective(e.target.value)}><option value="">{t("projects.success_criteria.projectLevel")}</option>{project.objectives.map((objective) => <option key={objective.id} value={objective.id}>{objective.title}</option>)}</select></label></form>{actionError && <div className="inline-error">{actionError}</div>}</Modal>
  </div>;
}
