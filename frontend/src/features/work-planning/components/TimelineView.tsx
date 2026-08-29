import { CalendarClock, Diamond, GitBranch } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import type { ProjectMember } from "../../people/types";
import { formatDate } from "../../projects/utils/format";
import type { Milestone, Task, TaskDependency } from "../types";
import { WorkBadge } from "./WorkBadge";

const day = 86_400_000;
const toTime = (value: string) => new Date(`${value}T00:00:00Z`).getTime();

export function TimelineView({ tasks, milestones, dependencies, members }: { tasks: Task[]; milestones: Milestone[]; dependencies: TaskDependency[]; members: ProjectMember[] }) {
  const { t, i18n } = useTranslation();
  const scheduled = tasks.filter((task) => task.start_date && task.due_date);
  const range = useMemo(() => {
    const dates = [...scheduled.flatMap((task) => [task.start_date!, task.due_date!]), ...milestones.flatMap((milestone) => milestone.due_date ? [milestone.due_date] : [])];
    if (!dates.length) return null;
    const start = Math.min(...dates.map(toTime));
    const end = Math.max(...dates.map(toTime));
    return { start, end, span: Math.max(1, Math.round((end - start) / day) + 1) };
  }, [milestones, scheduled]);
  if (!range) return <div className="work-empty"><CalendarClock size={28} /><h2>{t("workPlanning.empty.timelineTitle")}</h2><p>{t("workPlanning.empty.timelineBody")}</p></div>;
  const position = (value: string) => ((toTime(value) - range.start) / day / range.span) * 100;
  return <div className="timeline-shell">
    <div className="timeline-scale"><span>{formatDate(new Date(range.start).toISOString().slice(0, 10), i18n.resolvedLanguage)}</span><strong>{t("workPlanning.timeline.range", { count: range.span })}</strong><span>{formatDate(new Date(range.end).toISOString().slice(0, 10), i18n.resolvedLanguage)}</span></div>
    <div className="timeline-milestones">{milestones.filter((milestone) => milestone.due_date).map((milestone) => <div className="milestone-marker" key={milestone.id} style={{ left: `${position(milestone.due_date!)}%` }} title={milestone.title}><Diamond size={14} /><span>{milestone.title}</span></div>)}</div>
    <div className="timeline-rows">{scheduled.map((task) => {
      const left = position(task.start_date!);
      const width = Math.max(2, ((toTime(task.due_date!) - toTime(task.start_date!)) / day + 1) / range.span * 100);
      const taskDependencies = dependencies.filter((dependency) => dependency.source_task_id === task.id || dependency.target_task_id === task.id);
      const assignees = task.assignee_ids.map((id) => members.find((member) => member.id === id)?.person.name).filter(Boolean);
      return <article className="timeline-row" key={task.id}><div className="timeline-label"><strong>{task.title}</strong>{assignees.length > 0 && <small>{assignees.join(", ")}</small>}<div><WorkBadge value={task.status} kind="status" />{taskDependencies.length > 0 && <span className="dependency-count"><GitBranch size={12} />{taskDependencies.length}</span>}</div></div><div className="timeline-track"><span className={`timeline-bar value-${task.status.toLowerCase().replaceAll("_", "-")}`} style={{ left: `${left}%`, width: `${width}%` }}><i style={{ width: `${task.completion_percentage}%` }} /><b>{task.completion_percentage}%</b></span></div></article>;
    })}</div>
    {tasks.length > scheduled.length && <p className="timeline-note">{t("workPlanning.timeline.unscheduled", { count: tasks.length - scheduled.length })}</p>}
    <p className="timeline-note"><GitBranch size={13} />{t("workPlanning.timeline.dependencyNote")}</p>
  </div>;
}
