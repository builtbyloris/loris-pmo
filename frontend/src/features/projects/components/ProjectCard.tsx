import { ArrowUpRight, Building2, CalendarDays, WalletCards } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { Project } from "../types";
import { formatCurrency, formatDate } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

export function ProjectCard({ project }: { project: Project }) {
  const { t, i18n } = useTranslation();
  return (
    <Link to={`/projects/${project.id}`} className="project-card">
      <header>
        <div><span className="project-code">{project.code}</span><h3>{project.name}</h3></div>
        <ArrowUpRight size={18} aria-hidden="true" />
      </header>
      <div className="badge-row"><StatusBadge value={project.status} /><StatusBadge value={project.priority} kind="priority" /></div>
      <dl className="project-card-details">
        <div><dt><Building2 size={15} />{t("projects.fields.client")}</dt><dd>{project.client_or_area || "—"}</dd></div>
        <div><dt><CalendarDays size={15} />{t("projects.fields.targetDate")}</dt><dd>{formatDate(project.target_end_date, i18n.resolvedLanguage)}</dd></div>
        <div><dt><WalletCards size={15} />{t("projects.fields.plannedBudget")}</dt><dd>{formatCurrency(project.planned_budget, i18n.resolvedLanguage)}</dd></div>
      </dl>
    </Link>
  );
}
