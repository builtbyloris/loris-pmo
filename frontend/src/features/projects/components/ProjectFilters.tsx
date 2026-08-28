import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { ProjectFilters as Filters, ProjectPriority, ProjectStatus } from "../types";

export function ProjectFilters({ filters, onChange }: { filters: Filters; onChange: (next: Filters) => void }) {
  const { t } = useTranslation();
  return (
    <div className="project-filters">
      <label className="search-field"><Search size={17} /><input value={filters.search ?? ""} onChange={(event) => onChange({ ...filters, search: event.target.value })} placeholder={t("projects.filters.search")} /></label>
      <select aria-label={t("projects.filters.status")} value={filters.status ?? ""} onChange={(event) => onChange({ ...filters, status: event.target.value as ProjectStatus | "", include_archived: event.target.value === "ARCHIVED" })}>
        <option value="">{t("projects.filters.allStatuses")}</option>
        {(["NOT_STARTED", "ACTIVE", "ON_HOLD", "COMPLETED", "ARCHIVED"] as ProjectStatus[]).map((value) => <option key={value} value={value}>{t(`projects.status.${value}`)}</option>)}
      </select>
      <select aria-label={t("projects.filters.priority")} value={filters.priority ?? ""} onChange={(event) => onChange({ ...filters, priority: event.target.value as ProjectPriority | "" })}>
        <option value="">{t("projects.filters.allPriorities")}</option>
        {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as ProjectPriority[]).map((value) => <option key={value} value={value}>{t(`projects.priority.${value}`)}</option>)}
      </select>
      <select aria-label={t("projects.filters.sort")} value={`${filters.sort_by ?? "updated_at"}:${filters.sort_order ?? "desc"}`} onChange={(event) => { const [sort_by, sort_order] = event.target.value.split(":") as [Filters["sort_by"], Filters["sort_order"]]; onChange({ ...filters, sort_by, sort_order }); }}>
        <option value="updated_at:desc">{t("projects.filters.recentlyUpdated")}</option>
        <option value="name:asc">{t("projects.filters.nameAscending")}</option>
        <option value="target_end_date:asc">{t("projects.filters.targetDateAscending")}</option>
        <option value="created_at:desc">{t("projects.filters.newest")}</option>
      </select>
    </div>
  );
}
