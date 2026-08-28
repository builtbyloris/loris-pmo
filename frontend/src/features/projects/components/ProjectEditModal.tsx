import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../../services/api";
import { projectsApi } from "../api/projectsApi";
import type { ProjectDetail, ProjectPriority, ProjectStatus, ProjectUpdateInput } from "../types";
import { Modal } from "./Modal";

export function ProjectEditModal({ project, open, onClose, onSaved }: { project: ProjectDetail; open: boolean; onClose: () => void; onSaved: (project: ProjectDetail) => void }) {
  const { t } = useTranslation();
  const [values, setValues] = useState<ProjectUpdateInput>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setValues({ name: project.name, code: project.code, description: project.description ?? "", client_or_area: project.client_or_area ?? "", status: project.status, priority: project.priority, start_date: project.start_date ?? "", target_end_date: project.target_end_date ?? "", planned_budget: project.planned_budget, notes: project.notes ?? "" });
    setError("");
  }, [project, open]);
  function update(key: string, value: string) { setValues((current) => ({ ...current, [key]: value })); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!values.name?.trim()) { setError(t("projects.validation.nameRequired")); return; }
    if (values.start_date && values.target_end_date && values.target_end_date < values.start_date) { setError(t("projects.validation.dateOrder")); return; }
    setSaving(true); setError("");
    try { onSaved(await projectsApi.update(project.id, { ...values, description: values.description || null, client_or_area: values.client_or_area || null, start_date: values.start_date || null, target_end_date: values.target_end_date || null, notes: values.notes || null })); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : t("projects.edit.error")); }
    finally { setSaving(false); }
  }
  return <Modal open={open} onClose={onClose} wide title={t("projects.edit.title")} description={t("projects.edit.subtitle")} footer={<><button className="secondary-button" type="button" onClick={onClose}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="edit-project-form" disabled={saving}>{saving ? t("common.saving") : t("common.saveChanges")}</button></>}>
    <form id="edit-project-form" className="form-grid" onSubmit={submit}>
      <label className="span-2"><span>{t("projects.fields.name")}</span><input value={values.name ?? ""} onChange={(e) => update("name", e.target.value)} /></label>
      <label><span>{t("projects.fields.code")}</span><input value={values.code ?? ""} onChange={(e) => update("code", e.target.value.toUpperCase())} /></label>
      <label><span>{t("projects.fields.status")}</span><select value={values.status ?? "NOT_STARTED"} onChange={(e) => update("status", e.target.value)}>{(["NOT_STARTED", "ACTIVE", "ON_HOLD", "COMPLETED"] as ProjectStatus[]).map((value) => <option key={value} value={value}>{t(`projects.status.${value}`)}</option>)}</select></label>
      <label><span>{t("projects.fields.priority")}</span><select value={values.priority ?? "MEDIUM"} onChange={(e) => update("priority", e.target.value)}>{(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as ProjectPriority[]).map((value) => <option key={value} value={value}>{t(`projects.priority.${value}`)}</option>)}</select></label>
      <label><span>{t("projects.fields.client")}</span><input value={values.client_or_area ?? ""} onChange={(e) => update("client_or_area", e.target.value)} /></label>
      <label className="span-2"><span>{t("projects.fields.description")}</span><textarea rows={3} value={values.description ?? ""} onChange={(e) => update("description", e.target.value)} /></label>
      <label><span>{t("projects.fields.startDate")}</span><input type="date" value={values.start_date ?? ""} onChange={(e) => update("start_date", e.target.value)} /></label>
      <label><span>{t("projects.fields.targetDate")}</span><input type="date" value={values.target_end_date ?? ""} onChange={(e) => update("target_end_date", e.target.value)} /></label>
      <label className="span-2"><span>{t("projects.fields.plannedBudget")}</span><input type="number" min="0" step="0.01" value={values.planned_budget ?? "0"} onChange={(e) => update("planned_budget", e.target.value)} /></label>
      <label className="span-2"><span>{t("projects.fields.notes")}</span><textarea rows={3} value={values.notes ?? ""} onChange={(e) => update("notes", e.target.value)} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}
