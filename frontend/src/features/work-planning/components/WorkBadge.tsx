import { useTranslation } from "react-i18next";

import type { MilestoneStatus, TaskPriority, TaskStatus } from "../types";

export function WorkBadge({ value, kind }: { value: TaskStatus | TaskPriority | MilestoneStatus; kind: "status" | "priority" | "milestone" }) {
  const { t } = useTranslation();
  return <span className={`project-badge value-${value.toLowerCase().replaceAll("_", "-")}`}>{t(`workPlanning.${kind}.${value}`)}</span>;
}

