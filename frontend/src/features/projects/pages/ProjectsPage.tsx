import { AlertCircle, FolderKanban, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { ProjectCard } from "../components/ProjectCard";
import { ProjectFilters } from "../components/ProjectFilters";
import { ProjectWizard } from "../components/ProjectWizard";
import { useProjects } from "../hooks/useProjects";
import type { ProjectFilters as Filters } from "../types";

export function ProjectsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Filters>({ sort_by: "updated_at", sort_order: "desc" });
  const [wizardOpen, setWizardOpen] = useState(false);
  const stableFilters = useMemo(() => filters, [filters]);
  const { data, error, reload } = useProjects(stableFilters);
  return <div className="page-stack">
    <header className="page-header"><div><p className="eyebrow">{t("projects.eyebrow")}</p><h1>{t("projects.title")}</h1><p>{t("projects.subtitle")}</p></div><button className="primary-button" type="button" onClick={() => setWizardOpen(true)}><Plus size={17} />{t("projects.newProject")}</button></header>
    <ProjectFilters filters={filters} onChange={setFilters} />
    {error ? <div className="content-state compact" role="alert"><AlertCircle size={25} /><p>{t("projects.listError")}</p><button className="secondary-button" onClick={reload}>{t("common.retry")}</button></div> : !data ? <div className="content-state compact" role="status"><span className="spinner" />{t("common.loading")}</div> : data.total === 0 ? <section className="list-empty"><FolderKanban size={28} /><h2>{filters.search || filters.status || filters.priority ? t("projects.noMatches") : t("projects.emptyTitle")}</h2><p>{filters.search || filters.status || filters.priority ? t("projects.noMatchesBody") : t("projects.emptyBody")}</p>{!filters.search && !filters.status && !filters.priority && <button className="primary-button" onClick={() => setWizardOpen(true)}>{t("projects.createFirst")}</button>}</section> : <><div className="result-count">{t("projects.resultCount", { count: data.total })}</div><section className="projects-grid">{data.items.map((project) => <ProjectCard key={project.id} project={project} />)}</section></>}
    <ProjectWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCreated={(project) => navigate(`/projects/${project.id}`, { state: { created: true } })} />
  </div>;
}
