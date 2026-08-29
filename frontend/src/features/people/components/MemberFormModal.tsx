import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { MemberInput, Person, ProjectMember, ProjectRole } from "../types";

export const roles: ProjectRole[] = ["PROJECT_MANAGER", "SPONSOR", "PRODUCT_OWNER", "TEAM_MEMBER", "DEVELOPER", "DESIGNER", "DATA_ANALYST", "QA_TESTER", "STAKEHOLDER", "OTHER"];

export function MemberFormModal({ open, member, people, onClose, onSave }: { open: boolean; member?: ProjectMember | null; people: Person[]; onClose: () => void; onSave: (input: MemberInput) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [personId, setPersonId] = useState("");
  const [role, setRole] = useState<ProjectRole>("TEAM_MEMBER");
  const [responsibilities, setResponsibilities] = useState("");
  const [availability, setAvailability] = useState(100);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (open) { setPersonId(member?.person_id ?? people[0]?.id ?? ""); setRole(member?.role ?? "TEAM_MEMBER"); setResponsibilities(member?.responsibilities ?? ""); setAvailability(member?.availability_percent ?? 100); setError(""); } }, [member, open, people]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!personId) { setError(t("people.validation.personRequired")); return; }
    if (availability < 0 || availability > 100) { setError(t("people.validation.availability")); return; }
    setSaving(true);
    const ok = await onSave({ person_id: personId, role, responsibilities: responsibilities.trim() || null, availability_percent: availability });
    setSaving(false);
    if (ok) onClose(); else setError(t("people.actions.error"));
  }
  return <Modal open={open} onClose={onClose} title={t(member ? "people.team.editTitle" : "people.team.addTitle")} footer={<><button className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="member-form" disabled={saving}>{saving ? t("common.saving") : t("common.saveChanges")}</button></>}>
    <form id="member-form" className="form-grid" onSubmit={submit}>
      <label className="span-2"><span>{t("people.fields.person")}</span><select disabled={Boolean(member)} value={personId} onChange={(event) => setPersonId(event.target.value)}><option value="">{t("people.team.choosePerson")}</option>{people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      <label><span>{t("people.fields.role")}</span><select value={role} onChange={(event) => setRole(event.target.value as ProjectRole)}>{roles.map((value) => <option key={value} value={value}>{t(`people.roles.${value}`)}</option>)}</select></label>
      <label><span>{t("people.fields.availability")}</span><input type="number" min="0" max="100" value={availability} onChange={(event) => setAvailability(Number(event.target.value))} /></label>
      <label className="span-2"><span>{t("people.fields.responsibilities")}</span><textarea rows={3} value={responsibilities} onChange={(event) => setResponsibilities(event.target.value)} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}
