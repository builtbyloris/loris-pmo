import { useTranslation } from "react-i18next";

import type { ObjectiveStatus, ProjectPriority, ProjectStatus } from "../types";

export function StatusBadge({ value, kind = "status" }: { value: ProjectStatus | ProjectPriority | ObjectiveStatus; kind?: "status" | "priority" | "objective" }) {
  const { t } = useTranslation();
  return <span className={`project-badge ${kind} value-${value.toLowerCase().replaceAll("_", "-")}`}>{t(`projects.${kind}.${value}`)}</span>;
}
