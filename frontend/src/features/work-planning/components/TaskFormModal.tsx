import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { Milestone, Task, TaskInput, TaskPriority, TaskStatus } from "../types";

const initial: TaskInput = {
  title: "",
  description: "",
  status: "BACKLOG",
  priority: "MEDIUM",
  parent_task_id: null,
  milestone_id: null,
  start_date: null,
  due_date: null,
  estimated_effort: "0",
  actual_effort: "0",
  completion_percentage: 0,
  notes: "",
};

export function TaskFormModal({ open, onClose, onCreate, tasks, milestones }: { open: boolean; onClose: () => void; onCreate: (input: TaskInput) => Promise<boolean>; tasks: Task[]; milestones: Milestone[] }) {
  const { t } = useTranslation();
  const [values, setValues] = useState<TaskInput>(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setValues(initial); setError(""); } }, [open]);
  function update<K extends keyof TaskInput>(key: K, value: TaskInput[K]) { setValues((current) => ({ ...current, [key]: value })); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!values.title.trim()) { setError(t("workPlanning.validation.titleRequired")); return; }
    if (values.start_date && values.due_date && values.due_date < values.start_date) { setError(t("workPlanning.validation.dateOrder")); return; }
    if (Number(values.estimated_effort) < 0 || Number(values.actual_effort) < 0) { setError(t("workPlanning.validation.effort")); return; }
    setSaving(true); setError("");
    const ok = await onCreate({ ...values, title: values.title.trim(), description: values.description?.trim() || null, notes: values.notes?.trim() || null });
    setSaving(false);
    if (ok) onClose(); else setError(t("workPlanning.actions.error"));
  }
  const topLevelTasks = tasks.filter((task) => !task.parent_task_id);
  return <Modal open={open} onClose={onClose} wide title={t("workPlanning.taskForm.title")} description={t("workPlanning.taskForm.subtitle")} footer={<><button type="button" className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button type="submit" form="create-task-form" className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("workPlanning.taskForm.create")}</button></>}>
    <form id="create-task-form" className="form-grid" onSubmit={submit}>
      <label className="span-2"><span>{t("workPlanning.fields.title")} *</span><input autoFocus value={values.title} onChange={(event) => update("title", event.target.value)} /></label>
      <label><span>{t("workPlanning.fields.status")}</span><select value={values.status} onChange={(event) => update("status", event.target.value as TaskStatus)}>{(["BACKLOG", "TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE", "CANCELLED"] as TaskStatus[]).map((value) => <option key={value} value={value}>{t(`workPlanning.status.${value}`)}</option>)}</select></label>
      <label><span>{t("workPlanning.fields.priority")}</span><select value={values.priority} onChange={(event) => update("priority", event.target.value as TaskPriority)}>{(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as TaskPriority[]).map((value) => <option key={value} value={value}>{t(`workPlanning.priority.${value}`)}</option>)}</select></label>
      <label className="span-2"><span>{t("workPlanning.fields.description")}</span><textarea rows={3} value={values.description ?? ""} onChange={(event) => update("description", event.target.value)} /></label>
      <label><span>{t("workPlanning.fields.parent")}</span><select value={values.parent_task_id ?? ""} onChange={(event) => update("parent_task_id", event.target.value || null)}><option value="">{t("workPlanning.taskForm.noParent")}</option>{topLevelTasks.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</select></label>
      <label><span>{t("workPlanning.fields.milestone")}</span><select value={values.milestone_id ?? ""} onChange={(event) => update("milestone_id", event.target.value || null)}><option value="">{t("workPlanning.taskForm.noMilestone")}</option>{milestones.map((milestone) => <option key={milestone.id} value={milestone.id}>{milestone.title}</option>)}</select></label>
      <label><span>{t("workPlanning.fields.startDate")}</span><input type="date" value={values.start_date ?? ""} onChange={(event) => update("start_date", event.target.value || null)} /></label>
      <label><span>{t("workPlanning.fields.dueDate")}</span><input type="date" value={values.due_date ?? ""} onChange={(event) => update("due_date", event.target.value || null)} /></label>
      <label><span>{t("workPlanning.fields.estimatedEffort")}</span><input type="number" min="0" step="0.25" value={values.estimated_effort} onChange={(event) => update("estimated_effort", event.target.value)} /></label>
      <label><span>{t("workPlanning.fields.actualEffort")}</span><input type="number" min="0" step="0.25" value={values.actual_effort} onChange={(event) => update("actual_effort", event.target.value)} /></label>
      <label className="span-2"><span>{t("workPlanning.fields.completion")}</span><div className="range-field"><input type="range" min="0" max="100" value={values.completion_percentage} onChange={(event) => update("completion_percentage", Number(event.target.value))} /><strong>{values.status === "DONE" ? 100 : values.completion_percentage}%</strong></div></label>
      <label className="span-2"><span>{t("workPlanning.fields.notes")}</span><textarea rows={2} value={values.notes ?? ""} onChange={(event) => update("notes", event.target.value)} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}

