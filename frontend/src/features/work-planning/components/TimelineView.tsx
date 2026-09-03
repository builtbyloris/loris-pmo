import { AlertTriangle, CalendarClock, Check, Diamond, GitBranch, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatDate } from "../../projects/utils/format";
import type { Schedule, ScheduleChange, SchedulePreview } from "../types";

const day = 86_400_000;
const toTime = (value: string) => new Date(`${value}T00:00:00Z`).getTime();
const variance = (value: number | null) => value === null ? "—" : `${value > 0 ? "+" : ""}${value}d`;

export function TimelineView({ schedule, canManage, preview, onPreview, onApply, onCancel, onBaseline }: {
  schedule: Schedule; canManage: boolean; preview: SchedulePreview | null;
  onPreview: (change: ScheduleChange) => Promise<boolean>; onApply: () => Promise<boolean>;
  onCancel: () => void; onBaseline: (replace?: boolean) => Promise<boolean>;
}) {
  const { t, i18n } = useTranslation();
  const dated = schedule.tasks.filter((task) => task.start && task.finish);
  const [taskId, setTaskId] = useState(dated[0]?.id ?? "");
  const selected = dated.find((item) => item.id === taskId);
  const [start, setStart] = useState(selected?.start ?? "");
  const [finish, setFinish] = useState(selected?.finish ?? "");
  const range = useMemo(() => {
    const dates = [...dated.flatMap((task) => [task.start!, task.finish!, task.baseline_start, task.baseline_finish].filter(Boolean) as string[]),
      ...schedule.milestones.flatMap((item) => [item.current_date, item.projected_date, item.baseline_date].filter(Boolean) as string[])];
    if (!dates.length) return null;
    const first = Math.min(...dates.map(toTime)); const last = Math.max(...dates.map(toTime));
    return { start: first, end: last, span: Math.max(1, Math.round((last - first) / day) + 1) };
  }, [dated, schedule.milestones]);
  if (!range) return <div className="work-empty"><CalendarClock size={28} /><h2>{t("workPlanning.empty.timelineTitle")}</h2><p>{t("workPlanning.empty.timelineBody")}</p></div>;
  const position = (value: string) => ((toTime(value) - range.start) / day / range.span) * 100;
  const selectTask = (id: string) => { setTaskId(id); const item = dated.find((task) => task.id === id); setStart(item?.start ?? ""); setFinish(item?.finish ?? ""); };
  return <div className="schedule-workspace">
    <div className="schedule-summary">
      <article><span>{t("workPlanning.schedule.projectedFinish")}</span><strong>{formatDate(schedule.deadline_impact.projected_finish, i18n.resolvedLanguage)}</strong></article>
      <article className={`schedule-${schedule.deadline_impact.status.toLowerCase()}`}><span>{t("workPlanning.schedule.deadlineVariance")}</span><strong>{variance(schedule.deadline_impact.variance_days)}</strong></article>
      <article><span>{t("workPlanning.schedule.criticalTasks")}</span><strong>{schedule.critical_path.critical_task_ids.length}</strong></article>
      <article><span>{t("workPlanning.schedule.baselineVariance")}</span><strong>{variance(schedule.baseline_variance_days)}</strong></article>
      <article><span>{t("workPlanning.schedule.completeness")}</span><strong>{schedule.scheduling_completeness_percent}%</strong></article>
    </div>
    <div className="schedule-legend"><span><i className="legend-current" />{t("workPlanning.schedule.current")}</span><span><i className="legend-baseline" />{t("workPlanning.schedule.baseline")}</span><span><i className="legend-projected" />{t("workPlanning.schedule.projected")}</span><span><i className="legend-critical" />{t("workPlanning.schedule.critical")}</span></div>
    {canManage && <div className="schedule-toolbar"><button className="secondary-button" onClick={() => { const replacing = Boolean(schedule.baseline_created_at); if (!replacing || window.confirm(t("workPlanning.schedule.replaceBaselineConfirm"))) void onBaseline(replacing); }}><RotateCcw size={15} />{schedule.baseline_created_at ? t("workPlanning.schedule.replaceBaseline") : t("workPlanning.schedule.createBaseline")}</button>{schedule.baseline_created_at && <small>{t("workPlanning.schedule.baselineAt", { date: new Date(schedule.baseline_created_at).toLocaleString(i18n.resolvedLanguage) })}</small>}</div>}
    <div className="timeline-shell">
      <div className="timeline-scale"><span>{formatDate(new Date(range.start).toISOString().slice(0, 10), i18n.resolvedLanguage)}</span><strong>{t("workPlanning.timeline.range", { count: range.span })}</strong><span>{formatDate(new Date(range.end).toISOString().slice(0, 10), i18n.resolvedLanguage)}</span></div>
      <div className="timeline-milestones">{schedule.milestones.filter((item) => item.current_date).map((item) => <div className={`milestone-marker schedule-${item.status.toLowerCase()}`} key={item.id} style={{ left: `${position(item.current_date!)}%` }} title={`${item.title} · ${variance(item.variance_days)}`}><Diamond size={14} /><span>{item.title}</span></div>)}</div>
      <div className="timeline-rows">{dated.map((task) => {
        const left = position(task.start!); const width = Math.max(2, ((toTime(task.finish!) - toTime(task.start!)) / day + 1) / range.span * 100);
        const baselineLeft = task.baseline_start ? position(task.baseline_start) : 0; const baselineWidth = task.baseline_start && task.baseline_finish ? Math.max(2, ((toTime(task.baseline_finish) - toTime(task.baseline_start)) / day + 1) / range.span * 100) : 0;
        return <article className={`timeline-row ${task.critical ? "is-critical" : ""}`} key={task.id}><div className="timeline-label"><strong>{task.title}</strong><small>{task.duration_days}d · {task.total_float === null ? t("workPlanning.schedule.floatUnavailable") : t("workPlanning.schedule.float", { count: task.total_float })} · {variance(task.finish_variance)}</small>{task.critical && <span className="critical-badge"><AlertTriangle size={12} />{t("workPlanning.schedule.critical")}</span>}</div><div className="timeline-track">{baselineWidth > 0 && <span className="timeline-baseline" style={{ left: `${baselineLeft}%`, width: `${baselineWidth}%` }} />}<span className="timeline-bar" style={{ left: `${left}%`, width: `${width}%` }}><i style={{ width: `${task.progress}%` }} /><b>{task.progress}%</b></span></div></article>;
      })}</div>
    </div>
    <div className="schedule-dependencies"><h3><GitBranch size={16} />{t("workPlanning.schedule.dependencies")}</h3>{schedule.dependencies.length ? schedule.dependencies.map((item) => <span key={`${item.predecessor_id}-${item.successor_id}`}>{schedule.tasks.find((task) => task.id === item.predecessor_id)?.title} → {schedule.tasks.find((task) => task.id === item.successor_id)?.title}</span>) : <p>{t("workPlanning.schedule.noDependencies")}</p>}</div>
    {canManage && dated.length > 0 && <section className="schedule-editor"><h3>{t("workPlanning.schedule.changeTitle")}</h3><div className="schedule-form"><label>{t("workPlanning.schedule.task")}<select value={taskId} onChange={(event) => selectTask(event.target.value)}>{dated.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</select></label><label>{t("workPlanning.fields.startDate")}<input type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label><label>{t("workPlanning.fields.dueDate")}<input type="date" value={finish} onChange={(event) => setFinish(event.target.value)} /></label><button className="primary-button" disabled={!taskId || !start || !finish || finish < start} onClick={() => void onPreview({ entity_type: "TASK", task_id: taskId, start_date: start, due_date: finish })}>{t("workPlanning.schedule.preview")}</button></div></section>}
    {preview && <section className="schedule-preview" aria-label={t("workPlanning.schedule.previewTitle")}><h3><span className="schedule-hypothetical">{t("workPlanning.schedule.hypothetical")}</span>{t("workPlanning.schedule.previewTitle")}</h3><p>{t("workPlanning.schedule.previewBody", { count: preview.affected_tasks.length })}</p><ul>{preview.affected_tasks.map((task) => <li key={task.id}><strong>{task.title}</strong><span>{task.before_start} → {task.projected_start}</span><span>{task.before_finish} → {task.projected_finish}</span><b>{variance(task.shift_days)}</b></li>)}</ul>{preview.milestone_impacts.length > 0 && <div><strong>{t("workPlanning.schedule.milestoneImpacts")}</strong><ul>{preview.milestone_impacts.map((item) => <li key={item.id}><span>{item.title}</span><span>{formatDate(item.current_date, i18n.resolvedLanguage)} → {formatDate(item.projected_date, i18n.resolvedLanguage)}</span><b>{variance(item.variance_days)}</b></li>)}</ul></div>}{preview.warnings.length > 0 && <div className="schedule-preview-warnings"><strong>{t("workPlanning.schedule.warnings")}</strong><ul>{preview.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}<p>{t("workPlanning.schedule.deadlineImpact")}: <strong>{preview.deadline_impact.status} · {variance(preview.deadline_impact.variance_days)}</strong></p><div className="modal-actions"><button className="secondary-button" onClick={onCancel}>{t("common.cancel")}</button><button className="primary-button" onClick={() => void onApply()}><Check size={15} />{t("workPlanning.schedule.confirmApply")}</button></div></section>}
  </div>;
}
