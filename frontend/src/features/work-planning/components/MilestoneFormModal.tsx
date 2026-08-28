import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { MilestoneInput, MilestoneStatus } from "../types";

const initial: MilestoneInput = { title: "", description: "", due_date: null, status: "NOT_STARTED", notes: "" };

export function MilestoneFormModal({ open, onClose, onCreate }: { open: boolean; onClose: () => void; onCreate: (input: MilestoneInput) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [values, setValues] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (open) { setValues(initial); setError(""); } }, [open]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!values.title.trim()) { setError(t("workPlanning.validation.milestoneTitle")); return; }
    setSaving(true); setError("");
    const ok = await onCreate({ ...values, title: values.title.trim(), description: values.description?.trim() || null, notes: values.notes?.trim() || null });
    setSaving(false);
    if (ok) onClose(); else setError(t("workPlanning.actions.error"));
  }
  return <Modal open={open} onClose={onClose} title={t("workPlanning.milestoneForm.title")} description={t("workPlanning.milestoneForm.subtitle")} footer={<><button type="button" className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button type="submit" form="create-milestone-form" className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("workPlanning.milestoneForm.create")}</button></>}>
    <form id="create-milestone-form" className="single-field-form" onSubmit={submit}>
      <label><span>{t("workPlanning.fields.title")} *</span><input autoFocus value={values.title} onChange={(event) => setValues({ ...values, title: event.target.value })} /></label>
      <label><span>{t("workPlanning.fields.description")}</span><textarea rows={3} value={values.description ?? ""} onChange={(event) => setValues({ ...values, description: event.target.value })} /></label>
      <label><span>{t("workPlanning.fields.dueDate")}</span><input type="date" value={values.due_date ?? ""} onChange={(event) => setValues({ ...values, due_date: event.target.value || null })} /></label>
      <label><span>{t("workPlanning.fields.status")}</span><select value={values.status} onChange={(event) => setValues({ ...values, status: event.target.value as MilestoneStatus })}>{(["NOT_STARTED", "IN_PROGRESS", "AT_RISK", "COMPLETED"] as MilestoneStatus[]).map((value) => <option value={value} key={value}>{t(`workPlanning.milestone.${value}`)}</option>)}</select></label>
      <label><span>{t("workPlanning.fields.notes")}</span><textarea rows={2} value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}

