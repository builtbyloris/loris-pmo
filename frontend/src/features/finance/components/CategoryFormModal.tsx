import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { BudgetCategory, BudgetCategoryInput } from "../types";

export function CategoryFormModal({ open, category, onClose, onSave }: { open: boolean; category: BudgetCategory | null; onClose: () => void; onSave: (input: BudgetCategoryInput) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [name, setName] = useState(""); const [amount, setAmount] = useState("0"); const [notes, setNotes] = useState(""); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  useEffect(() => { if (open) { setName(category?.name ?? ""); setAmount(category?.planned_amount ?? "0"); setNotes(category?.notes ?? ""); setError(""); } }, [open, category]);
  async function submit(event: FormEvent) { event.preventDefault(); if (!name.trim()) { setError(t("finance.validation.categoryName")); return; } if (Number(amount) < 0) { setError(t("finance.validation.nonnegative")); return; } setSaving(true); const ok = await onSave({ name: name.trim(), planned_amount: amount || "0", notes: notes.trim() || null }); setSaving(false); if (ok) onClose(); else setError(t("finance.actions.error")); }
  return <Modal open={open} onClose={onClose} title={category ? t("finance.categories.edit") : t("finance.categories.create")} footer={<><button type="button" className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button type="submit" form="category-form" className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("common.save")}</button></>}><form id="category-form" className="form-grid" onSubmit={submit}><label className="span-2"><span>{t("finance.fields.categoryName")} *</span><input value={name} onChange={(event) => setName(event.target.value)} /></label><label className="span-2"><span>{t("finance.fields.allocation")}</span><input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label><label className="span-2"><span>{t("finance.fields.notes")}</span><textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label></form>{error && <div className="inline-error" role="alert">{error}</div>}</Modal>;
}
