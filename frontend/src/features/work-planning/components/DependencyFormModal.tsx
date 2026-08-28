import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Modal } from "../../projects/components/Modal";
import type { DependencyType, Task } from "../types";

export function DependencyFormModal({ open, tasks, onClose, onCreate }: { open: boolean; tasks: Task[]; onClose: () => void; onCreate: (source: string, target: string, type: DependencyType) => Promise<boolean> }) {
  const { t } = useTranslation();
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [type, setType] = useState<DependencyType>("BLOCKS");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (open) { setSource(""); setTarget(""); setType("BLOCKS"); setError(""); } }, [open]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!source || !target || source === target) { setError(t("workPlanning.validation.dependencyTasks")); return; }
    setSaving(true); setError("");
    const ok = await onCreate(source, target, type);
    setSaving(false);
    if (ok) onClose(); else setError(t("workPlanning.actions.error"));
  }
  return <Modal open={open} onClose={onClose} title={t("workPlanning.dependencyForm.title")} description={t("workPlanning.dependencyForm.subtitle")} footer={<><button type="button" className="secondary-button" onClick={onClose}>{t("common.cancel")}</button><button type="submit" form="create-dependency-form" className="primary-button" disabled={saving}>{saving ? t("common.saving") : t("workPlanning.dependencyForm.create")}</button></>}>
    <form id="create-dependency-form" className="single-field-form" onSubmit={submit}>
      <label><span>{t("workPlanning.dependencyForm.source")}</span><select value={source} onChange={(event) => setSource(event.target.value)}><option value="">{t("workPlanning.dependencyForm.chooseTask")}</option>{tasks.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</select></label>
      <label><span>{t("workPlanning.dependencyForm.type")}</span><select value={type} onChange={(event) => setType(event.target.value as DependencyType)}>{(["BLOCKS", "DEPENDS_ON", "RELATED_TO"] as DependencyType[]).map((value) => <option value={value} key={value}>{t(`workPlanning.dependency.${value}`)}</option>)}</select></label>
      <label><span>{t("workPlanning.dependencyForm.target")}</span><select value={target} onChange={(event) => setTarget(event.target.value)}><option value="">{t("workPlanning.dependencyForm.chooseTask")}</option>{tasks.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</select></label>
    </form>{error && <div className="inline-error" role="alert">{error}</div>}
  </Modal>;
}

