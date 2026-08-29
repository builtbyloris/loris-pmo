import { AlertCircle, AlertTriangle, Archive, CheckCircle2, FolderKanban, Gauge, PauseCircle, Plus, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { projectsApi } from "../api/projectsApi";
import { intelligenceApi } from "../../intelligence/api/intelligenceApi";
import type { PortfolioIntelligence } from "../../intelligence/types";
import { ProjectCard } from "../components/ProjectCard";
import { ProjectWizard } from "../components/ProjectWizard";
import type { PortfolioSummary, ProjectListResponse } from "../types";

export function PortfolioPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [projects, setProjects] = useState<ProjectListResponse | null>(null);
  const [intelligence, setIntelligence] = useState<PortfolioIntelligence | null>(null);
  const [error, setError] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const load = useCallback(() => { setError(false); Promise.all([projectsApi.portfolio(), projectsApi.list({ sort_by: "updated_at", sort_order: "desc" }), intelligenceApi.portfolio()]).then(([nextSummary, nextProjects, nextIntelligence]) => { setSummary(nextSummary); setProjects(nextProjects); setIntelligence(nextIntelligence); }).catch(() => setError(true)); }, []);
  useEffect(load, [load]);
  if (error) return <div className="content-state error-state" role="alert"><AlertCircle size={28} /><h1>{t("portfolio.loadError")}</h1><button className="secondary-button" onClick={load}>{t("common.retry")}</button></div>;
  if (!summary || !projects || !intelligence) return <div className="content-state" role="status"><span className="spinner" />{t("common.loading")}</div>;
  const metrics = [["total", summary.total_projects, FolderKanban], ["active", summary.active_projects, CheckCircle2], ["onHold", summary.on_hold_projects, PauseCircle], ["completed", summary.completed_projects, Archive]] as const;
  return <div className="page-stack">
    <header className="page-header"><div><p className="eyebrow">{t("portfolio.eyebrow")}</p><h1>{t("portfolio.title")}</h1><p>{t("portfolio.subtitle")}</p></div>{summary.total_projects > 0 && <button className="primary-button" onClick={() => setWizardOpen(true)}><Plus size={17} />{t("projects.newProject")}</button>}</header>
    <section className="metric-grid portfolio-metrics">{metrics.map(([key, value, Icon]) => <article className="metric-card" key={key}><div className="metric-icon"><Icon size={19} /></div><span>{t(`portfolio.metrics.${key}`)}</span><strong>{value}</strong></article>)}</section>
    {summary.total_projects > 0 && <section className="overview-section portfolio-intelligence"><header><div><p className="eyebrow">{t("intelligence.portfolio.eyebrow")}</p><h2>{t("intelligence.portfolio.title")}</h2></div><Gauge /></header><div className="metric-grid intelligence-portfolio-metrics">{[["healthy", intelligence.healthy_projects, CheckCircle2], ["watch", intelligence.watch_projects, Gauge], ["atRisk", intelligence.at_risk_projects, AlertTriangle], ["critical", intelligence.critical_projects, ShieldAlert], ["criticalAlerts", intelligence.active_critical_alerts, AlertCircle], ["overdue", intelligence.total_overdue_tasks, AlertTriangle], ["risks", intelligence.total_high_critical_risks, ShieldAlert]].map(([key, value, Icon]) => { const MetricIcon = Icon as typeof Gauge; return <article className="metric-card" key={String(key)}><MetricIcon size={18} /><span>{t(`intelligence.portfolio.metrics.${key}`)}</span><strong>{String(value)}</strong></article>; })}</div><div className="portfolio-intelligence-table"><div className="portfolio-intelligence-row header"><span>{t("intelligence.portfolio.project")}</span><span>{t("intelligence.health.title")}</span><span>{t("intelligence.kpis.labels.overdue_tasks")}</span><span>{t("intelligence.portfolio.risks")}</span><span>{t("intelligence.portfolio.alerts")}</span></div>{intelligence.projects.map((item) => <Link className="portfolio-intelligence-row" to={`/projects/${item.project_id}`} key={item.project_id}><strong>{item.project_code} · {item.project_name}</strong><span>{item.health_score ?? "—"} {item.health_status ? t(`intelligence.health.status.${item.health_status}`) : ""}</span><span>{item.overdue_tasks}</span><span>{item.high_critical_risks}</span><span>{item.active_alerts}</span></Link>)}</div></section>}
    {summary.total_projects === 0 ? <section className="empty-portfolio"><div className="empty-visual"><FolderKanban size={32} /><span /></div><div><p className="eyebrow">{t("portfolio.startHere")}</p><h2>{t("portfolio.emptyTitle")}</h2><p>{t("portfolio.emptyBody")}</p></div><button className="primary-button" onClick={() => setWizardOpen(true)}>{t("portfolio.createProject")}<Plus size={18} /></button></section> : <section className="portfolio-projects"><header><div><h2>{t("portfolio.recentProjects")}</h2><p>{t("portfolio.recentProjectsBody")}</p></div><Link to="/projects" className="text-link">{t("portfolio.viewAll")}</Link></header><div className="projects-grid">{projects.items.slice(0, 3).map((project) => <ProjectCard project={project} key={project.id} />)}</div></section>}
    <ProjectWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCreated={(project) => navigate(`/projects/${project.id}`, { state: { created: true } })} />
  </div>;
}
