import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";

export function ControlDecisionModal({ open, mode, onClose, onSave }: { open: boolean; mode: "resolve" | "approve" | "reject"; onClose: () => void; onSave: (text: string) => Promise<boolean> }) {
  const { t } = useTranslation(); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); const value = String(data.get("decision") ?? "").trim(); if (!value) { setError(t("control.validation.decision")); return; } setSaving(true); const ok = await onSave(value); setSaving(false); if (ok) onClose(); else setError(t("control.actions.error")); }
  return <Modal open={open} onClose={onClose} title={t(`control.decision.${mode}Title`)} footer={<><button className="secondary-button" type="button" onClick={onClose}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="control-decision-form" disabled={saving}>{saving ? t("common.saving") : t(`control.decision.${mode}`)}</button></>}><form key={`${mode}-${open}`} id="control-decision-form" className="single-field-form" onSubmit={submit}><label><span>{t(`control.decision.${mode}Label`)}</span><textarea autoFocus rows={5} name="decision" /></label></form>{error && <div role="alert" className="inline-error">{error}</div>}</Modal>;
}
