import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ProjectMember } from "../../people/types";
import { Modal } from "../../projects/components/Modal";
import type { Milestone, Task } from "../../work-planning/types";
import type { ChangeInput, ChangeRequest, ImpactLevel, Issue, IssueInput, Risk, RiskInput } from "../types";

type Kind = "risk" | "issue" | "change";
type RecordValue = Risk | Issue | ChangeRequest | null;
type FormRecord = {
  id: string; title: string; description: string | null; category?: string | null;
  probability?: number; impact?: number; priority?: string; owner_member_id?: string | null;
  identified_date?: string; review_date?: string | null; mitigation?: string | null;
  contingency?: string | null; requested_by?: string | null; requested_date?: string;
  reason?: string | null; schedule_impact?: ImpactLevel; budget_impact?: ImpactLevel;
  scope_impact?: ImpactLevel; quality_impact?: ImpactLevel; resource_impact?: ImpactLevel;
  estimated_delay_days?: number | null; estimated_cost?: string | null; notes: string | null;
  task_ids: string[]; milestone_ids: string[]; risk_ids?: string[]; issue_ids?: string[];
  status?: string;
};

const today = () => new Date().toISOString().slice(0, 10);
const selected = (form: FormData, name: string) => form.getAll(name).map(String);
const text = (form: FormData, name: string) => String(form.get(name) ?? "").trim() || null;
const optionalNumber = (form: FormData, name: string) => {
  const value = String(form.get(name) ?? "");
  return value === "" ? null : Number(value);
};

export function ControlFormModal({ kind, open, value, members, tasks, milestones, risks, issues, onClose, onSave }: {
  kind: Kind; open: boolean; value: RecordValue; members: ProjectMember[]; tasks: Task[];
  milestones: Milestone[]; risks: Risk[]; issues: Issue[]; onClose: () => void;
  onSave: (input: RiskInput | IssueInput | ChangeInput) => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const record = value as FormRecord | null;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    const title = String(form.get("title") ?? "").trim();
    if (!title) { setError(t("control.validation.title")); return; }
    let input: RiskInput | IssueInput | ChangeInput;
    if (kind === "risk") {
      input = { title, description: text(form, "description"), category: text(form, "category"), probability: Number(form.get("probability")), impact: Number(form.get("impact")), status: String(form.get("status")) as RiskInput["status"], owner_member_id: text(form, "owner_member_id"), mitigation: text(form, "mitigation"), contingency: text(form, "contingency"), identified_date: String(form.get("identified_date")), review_date: text(form, "review_date"), notes: text(form, "notes"), task_ids: selected(form, "task_ids"), milestone_ids: selected(form, "milestone_ids") };
    } else if (kind === "issue") {
      input = { title, description: text(form, "description"), category: text(form, "category"), priority: String(form.get("priority")) as IssueInput["priority"], status: form.has("status") ? String(form.get("status")) as IssueInput["status"] : undefined, owner_member_id: text(form, "owner_member_id"), identified_date: String(form.get("identified_date")), schedule_impact: String(form.get("schedule_impact")) as ImpactLevel, budget_impact: String(form.get("budget_impact")) as ImpactLevel, scope_impact: String(form.get("scope_impact")) as ImpactLevel, quality_impact: String(form.get("quality_impact")) as ImpactLevel, estimated_delay_days: optionalNumber(form, "estimated_delay_days"), estimated_cost: text(form, "estimated_cost"), notes: text(form, "notes"), task_ids: selected(form, "task_ids"), milestone_ids: selected(form, "milestone_ids") };
    } else {
      input = { title, description: text(form, "description"), reason: text(form, "reason"), requested_by: text(form, "requested_by"), requested_date: String(form.get("requested_date")), scope_impact: String(form.get("scope_impact")) as ImpactLevel, schedule_impact: String(form.get("schedule_impact")) as ImpactLevel, budget_impact: String(form.get("budget_impact")) as ImpactLevel, resource_impact: String(form.get("resource_impact")) as ImpactLevel, estimated_delay_days: optionalNumber(form, "estimated_delay_days"), estimated_cost: text(form, "estimated_cost"), notes: text(form, "notes"), task_ids: selected(form, "task_ids"), milestone_ids: selected(form, "milestone_ids"), risk_ids: selected(form, "risk_ids"), issue_ids: selected(form, "issue_ids") };
    }
    setSaving(true); const ok = await onSave(input); setSaving(false);
    if (ok) onClose(); else setError(t("control.actions.error"));
  }
  const impacts: ImpactLevel[] = ["NONE", "LOW", "MEDIUM", "HIGH"];
  const selectedIds = (name: "task_ids" | "milestone_ids" | "risk_ids" | "issue_ids") => record?.[name] ?? [];
  return <Modal open={open} onClose={onClose} wide title={t(`control.forms.${kind}.${value ? "edit" : "create"}`)} footer={<><button type="button" className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button type="submit" form="control-record-form" className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("common.save")}</button></>}>
    <form key={`${kind}-${record?.id ?? "new"}-${open}`} id="control-record-form" className="form-grid" onSubmit={submit}>
      <label className="span-2"><span>{t("control.fields.title")} *</span><input name="title" defaultValue={record?.title ?? ""} /></label>
      <label className="span-2"><span>{t("control.fields.description")}</span><textarea name="description" rows={2} defaultValue={record?.description ?? ""} /></label>
      {kind !== "change" && <label><span>{t("control.fields.category")}</span><input name="category" defaultValue={record?.category ?? ""} /></label>}
      {kind === "risk" && <><label><span>{t("control.fields.probability")}</span><select name="probability" defaultValue={record?.probability ?? 3}>{[1,2,3,4,5].map((item) => <option key={item}>{item}</option>)}</select></label><label><span>{t("control.fields.impact")}</span><select name="impact" defaultValue={record?.impact ?? 3}>{[1,2,3,4,5].map((item) => <option key={item}>{item}</option>)}</select></label></>}
      {kind === "risk" && <label><span>{t("control.fields.status")}</span><select name="status" defaultValue={record?.status ?? "IDENTIFIED"}>{["IDENTIFIED","MONITORING","MITIGATING","OCCURRED","ACCEPTED","CLOSED"].map((item) => <option value={item} key={item}>{t(`control.status.${item}`)}</option>)}</select></label>}
      {kind === "issue" && <label><span>{t("control.fields.priority")}</span><select name="priority" defaultValue={record?.priority ?? "MEDIUM"}>{["LOW","MEDIUM","HIGH","CRITICAL"].map((item) => <option key={item} value={item}>{t(`control.priority.${item}`)}</option>)}</select></label>}
      {kind === "issue" && value && <label><span>{t("control.fields.status")}</span><select name="status" defaultValue={record?.status ?? "OPEN"}>{["OPEN","IN_ANALYSIS","ACTION_PLANNED","IN_PROGRESS"].map((item) => <option value={item} key={item}>{t(`control.status.${item}`)}</option>)}</select></label>}
      {kind !== "change" && <label><span>{t("control.fields.owner")}</span><select name="owner_member_id" defaultValue={record?.owner_member_id ?? ""}><option value="">{t("common.none")}</option>{members.map((member) => <option key={member.id} value={member.id}>{member.person.name}</option>)}</select></label>}
      {kind === "risk" && <><label><span>{t("control.fields.identifiedDate")}</span><input name="identified_date" type="date" required defaultValue={record?.identified_date ?? today()} /></label><label><span>{t("control.fields.reviewDate")}</span><input name="review_date" type="date" defaultValue={record?.review_date ?? ""} /></label><label className="span-2"><span>{t("control.fields.mitigation")}</span><textarea name="mitigation" rows={2} defaultValue={record?.mitigation ?? ""} /></label><label className="span-2"><span>{t("control.fields.contingency")}</span><textarea name="contingency" rows={2} defaultValue={record?.contingency ?? ""} /></label></>}
      {kind === "issue" && <><label><span>{t("control.fields.identifiedDate")}</span><input name="identified_date" type="date" required defaultValue={record?.identified_date ?? today()} /></label>{(["schedule","budget","scope","quality"] as const).map((field) => <label key={field}><span>{t(`control.fields.${field}Impact`)}</span><select name={`${field}_impact`} defaultValue={record?.[`${field}_impact`] ?? "NONE"}>{impacts.map((item) => <option key={item} value={item}>{t(`control.impact.${item}`)}</option>)}</select></label>)}</>}
      {kind === "change" && <><label><span>{t("control.fields.requestedBy")}</span><input name="requested_by" defaultValue={record?.requested_by ?? ""} /></label><label><span>{t("control.fields.requestedDate")}</span><input name="requested_date" type="date" required defaultValue={record?.requested_date ?? today()} /></label><label className="span-2"><span>{t("control.fields.reason")}</span><textarea name="reason" rows={2} defaultValue={record?.reason ?? ""} /></label>{(["scope","schedule","budget","resource"] as const).map((field) => <label key={field}><span>{t(`control.fields.${field}Impact`)}</span><select name={`${field}_impact`} defaultValue={record?.[`${field}_impact`] ?? "NONE"}>{impacts.map((item) => <option key={item} value={item}>{t(`control.impact.${item}`)}</option>)}</select></label>)}</>}
      {kind !== "risk" && <><label><span>{t("control.fields.estimatedDelay")}</span><input name="estimated_delay_days" type="number" min="0" defaultValue={record?.estimated_delay_days ?? ""} /></label><label><span>{t("control.fields.estimatedCost")}</span><input name="estimated_cost" type="number" min="0" step="0.01" defaultValue={record?.estimated_cost ?? ""} /></label></>}
      <label><span>{t("control.fields.tasks")}</span><select className="multi-select" name="task_ids" multiple defaultValue={selectedIds("task_ids")}>{tasks.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      <label><span>{t("control.fields.milestones")}</span><select className="multi-select" name="milestone_ids" multiple defaultValue={selectedIds("milestone_ids")}>{milestones.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      {kind === "change" && <><label><span>{t("control.fields.risks")}</span><select className="multi-select" name="risk_ids" multiple defaultValue={selectedIds("risk_ids")}>{risks.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label><span>{t("control.fields.issues")}</span><select className="multi-select" name="issue_ids" multiple defaultValue={selectedIds("issue_ids")}>{issues.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label></>}
      <label className="span-2"><span>{t("control.fields.notes")}</span><textarea name="notes" rows={2} defaultValue={record?.notes ?? ""} /></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}
