import { AlertCircle, GripVertical } from "lucide-react";
import { type DragEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Milestone, Task, TaskStatus } from "../types";
import { WorkBadge } from "./WorkBadge";

const columns: TaskStatus[] = ["BACKLOG", "TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE", "CANCELLED"];

export function KanbanBoard({ tasks, milestones, readOnly, error, movingTaskId = "", onMove }: { tasks: Task[]; milestones: Milestone[]; readOnly: boolean; error: string; movingTaskId?: string; onMove: (taskId: string, status: TaskStatus) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState("");
  const [target, setTarget] = useState<TaskStatus | null>(null);
  function start(event: DragEvent, taskId: string) { event.dataTransfer.setData("text/task-id", taskId); event.dataTransfer.effectAllowed = "move"; setDragging(taskId); }
  async function drop(event: DragEvent, status: TaskStatus) { event.preventDefault(); const taskId = event.dataTransfer.getData("text/task-id") || dragging; setDragging(""); setTarget(null); if (taskId) await onMove(taskId, status); }
  return <div className="kanban-stack">{error && <div className="inline-error" role="alert"><AlertCircle size={15} />{error}</div>}<div className="kanban-board">{columns.map((status) => {
    const columnTasks = tasks.filter((task) => task.status === status);
    return <section key={status} aria-label={t(`workPlanning.status.${status}`)} className={`kanban-column ${target === status ? "drop-target" : ""}`} onDragOver={(event) => { if (!readOnly && !movingTaskId) { event.preventDefault(); setTarget(status); } }} onDragLeave={() => setTarget(null)} onDrop={(event) => void drop(event, status)}><header><WorkBadge value={status} kind="status" /><span>{columnTasks.length}</span></header><div className="kanban-cards">{columnTasks.map((task) => <article key={task.id} aria-busy={movingTaskId === task.id} className={`kanban-card ${dragging === task.id ? "dragging" : ""} ${movingTaskId === task.id ? "saving" : ""}`} draggable={!readOnly && !movingTaskId} onDragStart={(event) => start(event, task.id)} onDragEnd={() => { setDragging(""); setTarget(null); }}><div className="kanban-card-top">{!readOnly && <GripVertical size={15} />}<WorkBadge value={task.priority} kind="priority" /></div><h3>{task.title}</h3>{!readOnly && <select className="kanban-status-select" aria-label={t("workPlanning.actions.changeStatus", { title: task.title })} value={task.status} disabled={Boolean(movingTaskId)} onChange={(event) => void onMove(task.id, event.target.value as TaskStatus)}>{columns.map((value) => <option key={value} value={value}>{t(`workPlanning.status.${value}`)}</option>)}</select>}{task.parent_task_id && <small>{t("workPlanning.subtask")}</small>}<div className="kanban-progress"><span><i style={{ width: `${task.completion_percentage}%` }} /></span><strong>{task.completion_percentage}%</strong></div>{task.milestone_id && <p>{milestones.find((item) => item.id === task.milestone_id)?.title}</p>}</article>)}</div></section>;
  })}</div></div>;
}
