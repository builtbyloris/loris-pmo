import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";

export function BudgetFormModal({ open, value, onClose, onSave }: { open: boolean; value: string; onClose: () => void; onSave: (value: string) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [plannedBudget, setPlannedBudget] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (open) { setPlannedBudget(value); setError(""); } }, [open, value]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (Number(plannedBudget) < 0) { setError(t("finance.validation.nonnegative")); return; }
    setSaving(true); const ok = await onSave(plannedBudget || "0"); setSaving(false);
    if (ok) onClose(); else setError(t("finance.actions.error"));
  }
  return <Modal open={open} onClose={onClose} title={t("finance.budget.editTitle")} description={t("finance.budget.editDescription")} footer={<><button type="button" className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button type="submit" form="budget-form" className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("common.save")}</button></>}><form id="budget-form" className="form-grid" onSubmit={submit}><label className="span-2"><span>{t("finance.fields.totalBudget")}</span><input type="number" min="0" step="0.01" value={plannedBudget} onChange={(event) => setPlannedBudget(event.target.value)} /></label></form>{error && <div className="inline-error" role="alert">{error}</div>}</Modal>;
}
