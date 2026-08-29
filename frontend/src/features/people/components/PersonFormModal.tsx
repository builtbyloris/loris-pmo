import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { Person, PersonInput } from "../types";

export function PersonFormModal({ open, person, onClose, onSave }: { open: boolean; person?: Person | null; onClose: () => void; onSave: (input: PersonInput) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [skills, setSkills] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (open) { setName(person?.name ?? ""); setEmail(person?.email ?? ""); setDepartment(person?.department ?? ""); setSkills(person?.skills.join(", ") ?? ""); setNotes(person?.notes ?? ""); setError(""); } }, [open, person]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) { setError(t("people.validation.nameRequired")); return; }
    setSaving(true);
    const ok = await onSave({ name: name.trim(), email: email.trim() || null, department: department.trim() || null, skills: skills.split(",").map((item) => item.trim()).filter(Boolean), notes: notes.trim() || null });
    setSaving(false);
    if (ok) onClose(); else setError(t("people.actions.error"));
  }
  return <Modal open={open} onClose={onClose} title={t(person ? "people.person.editTitle" : "people.person.createTitle")} footer={<><button className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="person-form" disabled={saving}>{saving ? t("common.saving") : t("common.saveChanges")}</button></>}>
    <form id="person-form" className="form-grid" onSubmit={submit}>
      <label className="span-2"><span>{t("people.fields.name")} *</span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label><span>{t("people.fields.email")}</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label><span>{t("people.fields.department")}</span><input value={department} onChange={(event) => setDepartment(event.target.value)} /></label>
      <label className="span-2"><span>{t("people.fields.skills")}</span><input value={skills} onChange={(event) => setSkills(event.target.value)} placeholder={t("people.person.skillsHint")} /></label>
      <label className="span-2"><span>{t("people.fields.notes")}</span><textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}
