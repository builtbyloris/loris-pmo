import { ArrowLeft, ArrowRight, Check, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../../services/api";
import { projectsApi } from "../api/projectsApi";
import type { ProjectDetail, ProjectDraft, ProjectPriority } from "../types";
import { formatCurrency, formatDate } from "../utils/format";
import { Modal } from "./Modal";

const emptyDraft: ProjectDraft = {
  name: "", code: "", description: "", client_or_area: "", priority: "MEDIUM",
  start_date: "", target_end_date: "", planned_budget: "0", objectives: [], success_criteria: [],
};

export function ProjectWizard({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (project: ProjectDetail) => void }) {
  const { t, i18n } = useTranslation();
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<ProjectDraft>(emptyDraft);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState("");

  function close() { if (!saving) { setStep(1); setDraft(emptyDraft); setErrors({}); setApiError(""); onClose(); } }
  function update<K extends keyof ProjectDraft>(key: K, value: ProjectDraft[K]) { setDraft((current) => ({ ...current, [key]: value })); setErrors((current) => ({ ...current, [key]: "" })); }
  function validate(currentStep: number) {
    const next: Record<string, string> = {};
    if (currentStep === 1) {
      if (!draft.name.trim()) next.name = t("projects.validation.nameRequired");
      if (!/^[A-Za-z0-9][A-Za-z0-9._-]{1,31}$/.test(draft.code.trim())) next.code = t("projects.validation.codeFormat");
    }
    if (currentStep === 2) {
      if (draft.start_date && draft.target_end_date && draft.target_end_date < draft.start_date) next.target_end_date = t("projects.validation.dateOrder");
      if (Number(draft.planned_budget) < 0) next.planned_budget = t("projects.validation.budgetNonnegative");
    }
    setErrors(next); return Object.keys(next).length === 0;
  }
  function next(event: FormEvent) { event.preventDefault(); if (validate(step)) setStep((value) => Math.min(3, value + 1)); }
  async function create() {
    setSaving(true); setApiError("");
    try { onCreated(await projectsApi.create(draft)); }
    catch (error) { setApiError(error instanceof ApiError ? error.message : t("projects.wizard.createError")); }
    finally { setSaving(false); }
  }
  function updateItem(group: "objectives" | "success_criteria", index: number, value: string) {
    update(group, draft[group].map((item, itemIndex) => itemIndex === index ? (group === "objectives" ? { title: value } : { description: value }) : item) as ProjectDraft[typeof group]);
  }
  function addItem(group: "objectives" | "success_criteria") { update(group, [...draft[group], group === "objectives" ? { title: "" } : { description: "" }] as ProjectDraft[typeof group]); }
  function removeItem(group: "objectives" | "success_criteria", index: number) { update(group, draft[group].filter((_, itemIndex) => itemIndex !== index) as ProjectDraft[typeof group]); }

  return (
    <Modal open={open} onClose={close} wide title={t("projects.wizard.title")} description={t("projects.wizard.subtitle")} footer={
      <><button className="secondary-button" type="button" onClick={step === 1 ? close : () => setStep((value) => value - 1)} disabled={saving}>{step === 1 ? t("common.cancel") : <><ArrowLeft size={17} />{t("common.back")}</>}</button>
      {step < 3 ? <button className="primary-button" type="submit" form="project-wizard-form">{t("common.continue")}<ArrowRight size={17} /></button> : <button className="primary-button" type="button" onClick={() => void create()} disabled={saving}>{saving ? t("projects.wizard.creating") : <><Check size={17} />{t("projects.wizard.create")}</>}</button>}</>
    }>
      <ol className="wizard-steps">
        {[1, 2, 3].map((value) => <li key={value} className={value === step ? "active" : value < step ? "complete" : ""}><span>{value < step ? <Check size={14} /> : value}</span><p>{t(`projects.wizard.step${value}`)}</p></li>)}
      </ol>
      <form id="project-wizard-form" onSubmit={next} className="wizard-form">
        {step === 1 && <div className="form-grid">
          <label className="span-2"><span>{t("projects.fields.name")} *</span><input autoFocus value={draft.name} onChange={(e) => update("name", e.target.value)} />{errors.name && <small className="field-error">{errors.name}</small>}</label>
          <label><span>{t("projects.fields.code")} *</span><input value={draft.code} onChange={(e) => update("code", e.target.value.toUpperCase())} placeholder={t("projects.wizard.codePlaceholder")} />{errors.code && <small className="field-error">{errors.code}</small>}</label>
          <label><span>{t("projects.fields.priority")}</span><select value={draft.priority} onChange={(e) => update("priority", e.target.value as ProjectPriority)}>{(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as ProjectPriority[]).map((value) => <option key={value} value={value}>{t(`projects.priority.${value}`)}</option>)}</select></label>
          <label className="span-2"><span>{t("projects.fields.description")}</span><textarea rows={4} value={draft.description} onChange={(e) => update("description", e.target.value)} /></label>
          <label className="span-2"><span>{t("projects.fields.client")}</span><input value={draft.client_or_area} onChange={(e) => update("client_or_area", e.target.value)} /></label>
        </div>}
        {step === 2 && <div className="planning-stack">
          <div className="form-grid">
            <label><span>{t("projects.fields.startDate")}</span><input type="date" value={draft.start_date} onChange={(e) => update("start_date", e.target.value)} /></label>
            <label><span>{t("projects.fields.targetDate")}</span><input type="date" value={draft.target_end_date} onChange={(e) => update("target_end_date", e.target.value)} />{errors.target_end_date && <small className="field-error">{errors.target_end_date}</small>}</label>
            <label className="span-2"><span>{t("projects.fields.plannedBudget")}</span><div className="money-input"><i>€</i><input type="number" min="0" step="0.01" value={draft.planned_budget} onChange={(e) => update("planned_budget", e.target.value)} /></div>{errors.planned_budget && <small className="field-error">{errors.planned_budget}</small>}</label>
          </div>
          {(["objectives", "success_criteria"] as const).map((group) => <section className="wizard-list" key={group}><header><div><h3>{t(`projects.${group}.title`)}</h3><p>{t(`projects.${group}.wizardHelp`)}</p></div><button type="button" className="text-button" onClick={() => addItem(group)}><Plus size={16} />{t(`projects.${group}.add`)}</button></header>{draft[group].map((item, index) => <div className="dynamic-input" key={index}><input aria-label={t(`projects.${group}.itemLabel`, { number: index + 1 })} value={"title" in item ? item.title : item.description} onChange={(e) => updateItem(group, index, e.target.value)} /><button className="icon-button" type="button" onClick={() => removeItem(group, index)} aria-label={t("common.remove")}><Trash2 size={16} /></button></div>)}</section>)}
        </div>}
        {step === 3 && <div className="review-stack">
          <section className="review-hero"><span>{draft.code}</span><h3>{draft.name}</h3><p>{draft.description || t("common.notProvided")}</p></section>
          <dl className="review-grid"><div><dt>{t("projects.fields.client")}</dt><dd>{draft.client_or_area || "—"}</dd></div><div><dt>{t("projects.fields.priority")}</dt><dd>{t(`projects.priority.${draft.priority}`)}</dd></div><div><dt>{t("projects.fields.startDate")}</dt><dd>{formatDate(draft.start_date || null, i18n.resolvedLanguage)}</dd></div><div><dt>{t("projects.fields.targetDate")}</dt><dd>{formatDate(draft.target_end_date || null, i18n.resolvedLanguage)}</dd></div><div><dt>{t("projects.fields.plannedBudget")}</dt><dd>{formatCurrency(draft.planned_budget || 0, i18n.resolvedLanguage)}</dd></div><div><dt>{t("projects.objectives.title")}</dt><dd>{draft.objectives.filter((item) => item.title.trim()).length}</dd></div><div><dt>{t("projects.success_criteria.title")}</dt><dd>{draft.success_criteria.filter((item) => item.description.trim()).length}</dd></div></dl>
        </div>}
      </form>
      {apiError && <div className="inline-error" role="alert">{apiError}</div>}
    </Modal>
  );
}
