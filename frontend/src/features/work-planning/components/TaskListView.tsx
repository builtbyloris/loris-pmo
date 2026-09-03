import { ArrowDownUp, CalendarDays, GitBranch, MessageSquare, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { CommentsPanel } from "../../collaboration/components/CommentsPanel";
import { formatDate } from "../../projects/utils/format";
import type { ProjectMember } from "../../people/types";
import type { Milestone, Task, TaskDependency, TaskPriority, TaskStatus } from "../types";
import { WorkBadge } from "./WorkBadge";

type Sort = "title" | "due" | "priority" | "status";

export function TaskListView({ projectId = "", tasks, milestones, dependencies, members, readOnly, canComment = false, onStatusChange, onAssigneeChange }: { projectId?: string; tasks: Task[]; milestones: Milestone[]; dependencies: TaskDependency[]; members: ProjectMember[]; readOnly: boolean; canComment?: boolean; onStatusChange: (taskId: string, status: TaskStatus) => Promise<boolean>; onAssigneeChange: (taskId: string, assigneeIds: string[]) => Promise<boolean> }) {
  const { t, i18n } = useTranslation();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<TaskStatus | "">("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [milestone, setMilestone] = useState("");
  const [sort, setSort] = useState<Sort>("due");
  const [commentTaskId, setCommentTaskId] = useState<string | null>(null);
  const visible = useMemo(() => {
    const filtered = tasks.filter((task) => (!search || `${task.title} ${task.description ?? ""}`.toLowerCase().includes(search.toLowerCase())) && (!status || task.status === status) && (!priority || task.priority === priority) && (!milestone || task.milestone_id === milestone));
    return [...filtered].sort((a, b) => {
      if (sort === "title") return a.title.localeCompare(b.title);
      if (sort === "priority") return a.priority.localeCompare(b.priority);
      if (sort === "status") return a.status.localeCompare(b.status);
      return (a.due_date ?? "9999").localeCompare(b.due_date ?? "9999");
    });
  }, [milestone, priority, search, sort, status, tasks]);
  if (tasks.length === 0) return <div className="work-empty"><CalendarDays size={28} /><h2>{t("workPlanning.empty.tasksTitle")}</h2><p>{t("workPlanning.empty.tasksBody")}</p></div>;
  return <div className="task-list-stack">
    <div className="work-filters">
      <label className="search-field"><Search size={15} /><input aria-label={t("workPlanning.filters.searchLabel")} placeholder={t("workPlanning.filters.search")} value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      <select aria-label={t("workPlanning.filters.status")} value={status} onChange={(event) => setStatus(event.target.value as TaskStatus | "")}><option value="">{t("workPlanning.filters.allStatuses")}</option>{(["BACKLOG", "TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE", "CANCELLED"] as TaskStatus[]).map((value) => <option key={value} value={value}>{t(`workPlanning.status.${value}`)}</option>)}</select>
      <select aria-label={t("workPlanning.filters.priority")} value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority | "")}><option value="">{t("workPlanning.filters.allPriorities")}</option>{(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as TaskPriority[]).map((value) => <option key={value} value={value}>{t(`workPlanning.priority.${value}`)}</option>)}</select>
      <select aria-label={t("workPlanning.filters.milestone")} value={milestone} onChange={(event) => setMilestone(event.target.value)}><option value="">{t("workPlanning.filters.allMilestones")}</option>{milestones.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
      <label className="sort-field"><ArrowDownUp size={14} /><select aria-label={t("workPlanning.filters.sort")} value={sort} onChange={(event) => setSort(event.target.value as Sort)}><option value="due">{t("workPlanning.filters.due")}</option><option value="title">{t("workPlanning.filters.title")}</option><option value="priority">{t("workPlanning.filters.prioritySort")}</option><option value="status">{t("workPlanning.filters.statusSort")}</option></select></label>
    </div>
    {visible.length === 0 ? <div className="work-empty compact"><Search size={24} /><h2>{t("workPlanning.empty.noMatches")}</h2></div> : <div className="task-table-wrap"><table className="task-table"><thead><tr><th>{t("workPlanning.fields.title")}</th><th>{t("workPlanning.fields.status")}</th><th>{t("workPlanning.fields.priority")}</th><th>{t("workPlanning.fields.assignees")}</th><th>{t("workPlanning.fields.dates")}</th><th>{t("workPlanning.fields.milestone")}</th><th>{t("workPlanning.fields.completion")}</th><th>{t("workPlanning.fields.dependencies")}</th></tr></thead><tbody>{visible.map((task) => {
      const linked = dependencies.filter((dependency) => dependency.source_task_id === task.id || dependency.target_task_id === task.id).length;
      const milestoneTitle = milestones.find((item) => item.id === task.milestone_id)?.title;
      const names = task.assignee_ids.map((id) => members.find((member) => member.id === id)?.person.name).filter(Boolean);
      return <tr key={task.id}><td><div className={`task-title-cell ${task.parent_task_id ? "subtask" : ""}`}><strong>{task.title}</strong><button type="button" className="icon-button compact" aria-label={t("collaboration.comments.title")} onClick={() => setCommentTaskId(task.id)}><MessageSquare size={13} /></button>{task.parent_task_id && <small>{t("workPlanning.subtask")}</small>}</div></td><td>{readOnly ? <WorkBadge value={task.status} kind="status" /> : <select className="inline-select" aria-label={t("workPlanning.actions.changeStatus", { title: task.title })} value={task.status} onChange={(event) => void onStatusChange(task.id, event.target.value as TaskStatus)}>{(["BACKLOG", "TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE", "CANCELLED"] as TaskStatus[]).map((value) => <option key={value} value={value}>{t(`workPlanning.status.${value}`)}</option>)}</select>}</td><td><WorkBadge value={task.priority} kind="priority" /></td><td>{readOnly ? names.join(", ") || "—" : <select multiple className="inline-assignee-select" aria-label={t("workPlanning.actions.changeAssignees", { title: task.title })} value={task.assignee_ids} onChange={(event) => void onAssigneeChange(task.id, Array.from(event.target.selectedOptions, (option) => option.value))}>{members.map((member) => <option key={member.id} value={member.id}>{member.person.name}</option>)}</select>}</td><td><div className="date-pair"><span>{formatDate(task.start_date, i18n.resolvedLanguage)}</span><span>{formatDate(task.due_date, i18n.resolvedLanguage)}</span></div></td><td>{milestoneTitle || "—"}</td><td><div className="completion-cell"><span><i style={{ width: `${task.completion_percentage}%` }} /></span><strong>{task.completion_percentage}%</strong></div></td><td>{linked ? <span className="dependency-count"><GitBranch size={13} />{linked}</span> : "—"}</td></tr>;
    })}</tbody></table></div>}
    {commentTaskId && projectId && <CommentsPanel projectId={projectId} entityType="TASK" entityId={commentTaskId} canWrite={canComment} />}
  </div>;
}
