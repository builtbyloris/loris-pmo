import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { Person, Stakeholder, StakeholderInput, StakeholderLevel } from "../types";

const levels: StakeholderLevel[] = ["LOW", "MEDIUM", "HIGH"];

export function StakeholderFormModal({ open, stakeholder, people, onClose, onSave }: { open: boolean; stakeholder?: Stakeholder | null; people: Person[]; onClose: () => void; onSave: (input: StakeholderInput) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [personId, setPersonId] = useState(""); const [name, setName] = useState(""); const [organization, setOrganization] = useState(""); const [role, setRole] = useState("");
  const [influence, setInfluence] = useState<StakeholderLevel>("MEDIUM"); const [interest, setInterest] = useState<StakeholderLevel>("MEDIUM"); const [frequency, setFrequency] = useState(""); const [channel, setChannel] = useState(""); const [notes, setNotes] = useState(""); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  useEffect(() => { if (open) { setPersonId(stakeholder?.person_id ?? ""); setName(stakeholder?.name ?? ""); setOrganization(stakeholder?.organization ?? ""); setRole(stakeholder?.role ?? ""); setInfluence(stakeholder?.influence ?? "MEDIUM"); setInterest(stakeholder?.interest ?? "MEDIUM"); setFrequency(stakeholder?.communication_frequency ?? ""); setChannel(stakeholder?.communication_channel ?? ""); setNotes(stakeholder?.notes ?? ""); setError(""); } }, [open, stakeholder]);
  async function submit(event: FormEvent) { event.preventDefault(); if (!personId && !name.trim()) { setError(t("people.validation.stakeholderIdentity")); return; } setSaving(true); const ok = await onSave({ person_id: personId || null, name: personId ? null : name.trim(), organization: organization.trim() || null, role: role.trim() || null, influence, interest, communication_frequency: frequency.trim() || null, communication_channel: channel.trim() || null, notes: notes.trim() || null }); setSaving(false); if (ok) onClose(); else setError(t("people.actions.error")); }
  return <Modal open={open} onClose={onClose} wide title={t(stakeholder ? "people.stakeholders.editTitle" : "people.stakeholders.createTitle")} footer={<><button className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="stakeholder-form" disabled={saving}>{saving ? t("common.saving") : t("common.saveChanges")}</button></>}>
    <form id="stakeholder-form" className="form-grid" onSubmit={submit}>
      <label><span>{t("people.fields.linkedPerson")}</span><select value={personId} onChange={(event) => setPersonId(event.target.value)}><option value="">{t("people.stakeholders.standalone")}</option>{people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      <label><span>{t("people.fields.name")}</span><input disabled={Boolean(personId)} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label><span>{t("people.fields.organization")}</span><input value={organization} onChange={(event) => setOrganization(event.target.value)} /></label><label><span>{t("people.fields.role")}</span><input value={role} onChange={(event) => setRole(event.target.value)} /></label>
      <label><span>{t("people.fields.influence")}</span><select value={influence} onChange={(event) => setInfluence(event.target.value as StakeholderLevel)}>{levels.map((value) => <option key={value} value={value}>{t(`people.levels.${value}`)}</option>)}</select></label>
      <label><span>{t("people.fields.interest")}</span><select value={interest} onChange={(event) => setInterest(event.target.value as StakeholderLevel)}>{levels.map((value) => <option key={value} value={value}>{t(`people.levels.${value}`)}</option>)}</select></label>
      <label><span>{t("people.fields.frequency")}</span><input value={frequency} onChange={(event) => setFrequency(event.target.value)} /></label><label><span>{t("people.fields.channel")}</span><input value={channel} onChange={(event) => setChannel(event.target.value)} /></label>
      <label className="span-2"><span>{t("people.fields.notes")}</span><textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}
