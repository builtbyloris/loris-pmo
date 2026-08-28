import { AlertCircle, Archive, CheckCircle2, FolderKanban, PauseCircle, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { projectsApi } from "../api/projectsApi";
import { ProjectCard } from "../components/ProjectCard";
import { ProjectWizard } from "../components/ProjectWizard";
import type { PortfolioSummary, ProjectListResponse } from "../types";

export function PortfolioPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [projects, setProjects] = useState<ProjectListResponse | null>(null);
  const [error, setError] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const load = useCallback(() => { setError(false); Promise.all([projectsApi.portfolio(), projectsApi.list({ sort_by: "updated_at", sort_order: "desc" })]).then(([nextSummary, nextProjects]) => { setSummary(nextSummary); setProjects(nextProjects); }).catch(() => setError(true)); }, []);
  useEffect(load, [load]);
  if (error) return <div className="content-state error-state" role="alert"><AlertCircle size={28} /><h1>{t("portfolio.loadError")}</h1><button className="secondary-button" onClick={load}>{t("common.retry")}</button></div>;
  if (!summary || !projects) return <div className="content-state" role="status"><span className="spinner" />{t("common.loading")}</div>;
  const metrics = [["total", summary.total_projects, FolderKanban], ["active", summary.active_projects, CheckCircle2], ["onHold", summary.on_hold_projects, PauseCircle], ["completed", summary.completed_projects, Archive]] as const;
  return <div className="page-stack">
    <header className="page-header"><div><p className="eyebrow">{t("portfolio.eyebrow")}</p><h1>{t("portfolio.title")}</h1><p>{t("portfolio.subtitle")}</p></div>{summary.total_projects > 0 && <button className="primary-button" onClick={() => setWizardOpen(true)}><Plus size={17} />{t("projects.newProject")}</button>}</header>
    <section className="metric-grid portfolio-metrics">{metrics.map(([key, value, Icon]) => <article className="metric-card" key={key}><div className="metric-icon"><Icon size={19} /></div><span>{t(`portfolio.metrics.${key}`)}</span><strong>{value}</strong></article>)}</section>
    {summary.total_projects === 0 ? <section className="empty-portfolio"><div className="empty-visual"><FolderKanban size={32} /><span /></div><div><p className="eyebrow">{t("portfolio.startHere")}</p><h2>{t("portfolio.emptyTitle")}</h2><p>{t("portfolio.emptyBody")}</p></div><button className="primary-button" onClick={() => setWizardOpen(true)}>{t("portfolio.createProject")}<Plus size={18} /></button></section> : <section className="portfolio-projects"><header><div><h2>{t("portfolio.recentProjects")}</h2><p>{t("portfolio.recentProjectsBody")}</p></div><Link to="/projects" className="text-link">{t("portfolio.viewAll")}</Link></header><div className="projects-grid">{projects.items.slice(0, 3).map((project) => <ProjectCard project={project} key={project.id} />)}</div></section>}
    <ProjectWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCreated={(project) => navigate(`/projects/${project.id}`, { state: { created: true } })} />
  </div>;
}
