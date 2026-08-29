import { Activity as ActivityIcon, ArrowLeft, CalendarClock, CheckCircle2, FileClock, Gavel, NotebookPen, Plus, Search, Users } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../services/api";
import { peopleApi } from "../../people/api/peopleApi";
import type { ProjectMember } from "../../people/types";
import { projectsApi } from "../../projects/api/projectsApi";
import { Modal } from "../../projects/components/Modal";
import type { ProjectDetail } from "../../projects/types";
import { formatDate } from "../../projects/utils/format";
import { workPlanningApi } from "../../work-planning/api/workPlanningApi";
import type { Milestone, Task } from "../../work-planning/types";
import { memoryApi } from "../api/memoryApi";
import type { Activity, Decision, Meeting, ProjectLogEntry } from "../types";

type View = "log" | "meetings" | "decisions" | "activity";
type FormKind = "log" | "meeting" | "decision" | "action" | null;

const initial = { title: "", description: "", type: "NOTE", scheduled_at: "", duration_minutes: "", agenda: "", notes: "", participant_ids: [] as string[], decision: "", decision_date: new Date().toISOString().slice(0, 10), decision_maker_member_id: "", meeting_id: "", reason: "", task_id: "", milestone_id: "", owner_member_id: "", due_date: "" };

export function ProjectMemoryPage() {
  const { t, i18n } = useTranslation();
  const { projectId = "" } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [logs, setLogs] = useState<ProjectLogEntry[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [view, setView] = useState<View>("log");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formKind, setFormKind] = useState<FormKind>(null);
  const [form, setForm] = useState(initial);
  const [actionMeeting, setActionMeeting] = useState<Meeting | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [nextProject, nextMembers, nextTasks, nextMilestones, nextLogs, nextMeetings, nextDecisions, nextActivity] = await Promise.all([
        projectsApi.get(projectId), peopleApi.listMembers(projectId), workPlanningApi.listTasks(projectId), workPlanningApi.listMilestones(projectId), memoryApi.listLog(projectId), memoryApi.listMeetings(projectId), memoryApi.listDecisions(projectId), memoryApi.activity(projectId),
      ]);
      setProject(nextProject); setMembers(nextMembers); setTasks(nextTasks.items); setMilestones(nextMilestones); setLogs(nextLogs.items); setMeetings(nextMeetings.items); setDecisions(nextDecisions.items); setActivities(nextActivity.items);
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("memory.loadError")); }
    finally { setLoading(false); }
  }, [projectId, t]);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    if (!term) return { logs, meetings, decisions, activities };
    return {
      logs: logs.filter((item) => `${item.title} ${item.description ?? ""}`.toLocaleLowerCase().includes(term)),
      meetings: meetings.filter((item) => `${item.title} ${item.agenda ?? ""} ${item.notes ?? ""}`.toLocaleLowerCase().includes(term)),
      decisions: decisions.filter((item) => `${item.title} ${item.decision} ${item.reason ?? ""}`.toLocaleLowerCase().includes(term)),
      activities: activities.filter((item) => `${item.action} ${item.entity_type} ${item.entity_name ?? ""}`.toLocaleLowerCase().includes(term)),
    };
  }, [activities, decisions, logs, meetings, search]);
  const memberName = (id: string | null) => members.find((item) => item.id === id)?.person.name ?? t("common.notProvided");
  const openForm = (kind: Exclude<FormKind, null>, meeting?: Meeting) => { setForm(initial); setActionMeeting(meeting ?? null); setFormKind(kind); setError(""); };
  const closeForm = () => { if (!saving) setFormKind(null); };
  const links = () => [form.task_id && { entity_type: "TASK", entity_id: form.task_id }, form.milestone_id && { entity_type: "MILESTONE", entity_id: form.milestone_id }].filter(Boolean);

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      if (formKind === "log") await memoryApi.createLog(projectId, { type: form.type, title: form.title, description: form.description || null, links: links() as never });
      if (formKind === "meeting") await memoryApi.createMeeting(projectId, { title: form.title, scheduled_at: new Date(form.scheduled_at).toISOString(), duration_minutes: form.duration_minutes ? Number(form.duration_minutes) : null, agenda: form.agenda || null, notes: form.notes || null, participant_ids: form.participant_ids });
      if (formKind === "decision") await memoryApi.createDecision(projectId, { title: form.title, decision: form.decision, decision_date: form.decision_date, decision_maker_member_id: form.decision_maker_member_id || null, meeting_id: form.meeting_id || null, reason: form.reason || null, status: "PROPOSED", links: links() });
      if (formKind === "action" && actionMeeting) await memoryApi.createAction(projectId, actionMeeting.id, { description: form.description, owner_member_id: form.owner_member_id || null, due_date: form.due_date || null });
      setFormKind(null); await load();
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("memory.actions.error")); }
    finally { setSaving(false); }
  }
  async function updateMeeting(meeting: Meeting, status: "COMPLETED" | "CANCELLED") { try { await memoryApi.updateMeeting(projectId, meeting.id, { status }); await load(); } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("memory.actions.error")); } }
  async function updateAction(meeting: Meeting, id: string, status: "CONFIRMED" | "COMPLETED" | "DISMISSED") { try { await memoryApi.updateAction(projectId, meeting.id, id, { status }); await load(); } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("memory.actions.error")); } }
  async function updateDecision(decision: Decision, status: "DECIDED" | "REVERSED" | "SUPERSEDED") { try { await memoryApi.updateDecision(projectId, decision.id, { status }); await load(); } catch (reason) { setError(reason instanceof ApiError ? reason.message : t("memory.actions.error")); } }

  if (loading) return <div className="content-state"><span className="spinner" />{t("common.loading")}</div>;
  if (!project) return <div className="content-state error-state"><h1>{t("projects.notFound")}</h1></div>;
  const archived = Boolean(project.archived_at);
  return <div className="memory-workspace page-stack">
    <Link className="back-link" to={`/projects/${projectId}`}><ArrowLeft size={16} />{t("memory.backToOverview")}</Link>
    <header className="page-header"><div><p className="eyebrow">{t("memory.eyebrow")}</p><h1>{t("memory.title")}</h1><p>{t("memory.subtitle", { project: project.name })}</p></div>{!archived && view !== "activity" && <button className="primary-button" onClick={() => openForm(view === "log" ? "log" : view === "meetings" ? "meeting" : "decision")}><Plus size={16} />{t(`memory.actions.add.${view}`)}</button>}</header>
    {archived && <div className="archived-notice">{t("memory.readOnly")}</div>}
    {error && <div className="error-banner" role="alert">{error}</div>}
    <div className="workspace-tabs" role="tablist" aria-label={t("memory.views.label")}>{(["log", "meetings", "decisions", "activity"] as View[]).map((item) => <button key={item} role="tab" aria-selected={view === item} className={view === item ? "active" : ""} onClick={() => setView(item)}>{item === "log" ? <NotebookPen size={16} /> : item === "meetings" ? <Users size={16} /> : item === "decisions" ? <Gavel size={16} /> : <ActivityIcon size={16} />}{t(`memory.views.${item}`)}</button>)}</div>
    <section className="workspace-panel memory-surface">
      <div className="memory-filters"><Search size={16} /><input aria-label={t("memory.search.label")} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("memory.search.placeholder")} /></div>
      {view === "log" && <MemoryList items={filtered.logs} locale={i18n.resolvedLanguage} empty={t("memory.log.empty")} />}
      {view === "meetings" && <div className="memory-card-list">{filtered.meetings.length === 0 ? <Empty text={t("memory.meetings.empty")} /> : filtered.meetings.map((meeting) => <article key={meeting.id}><header><div><span className={`control-badge status-${meeting.status.toLowerCase()}`}>{t(`memory.meetingStatus.${meeting.status}`)}</span><h2>{meeting.title}</h2><p><CalendarClock size={14} />{new Date(meeting.scheduled_at).toLocaleString(i18n.resolvedLanguage)}{meeting.duration_minutes ? ` · ${meeting.duration_minutes} min` : ""}</p></div>{!archived && meeting.status === "PLANNED" && <div className="control-actions"><button className="text-button compact" onClick={() => openForm("action", meeting)}>{t("memory.actions.addAction")}</button><button className="text-button compact" onClick={() => void updateMeeting(meeting, "COMPLETED")}>{t("memory.actions.completeMeeting")}</button><button className="text-button compact danger-text" onClick={() => void updateMeeting(meeting, "CANCELLED")}>{t("memory.actions.cancelMeeting")}</button></div>}</header>{meeting.agenda && <p>{meeting.agenda}</p>}<small>{t("memory.meetings.participants", { count: meeting.participant_ids.length })}</small><div className="action-item-list">{meeting.action_items.map((item) => <div key={item.id}><div><strong>{item.description}</strong><small>{memberName(item.owner_member_id)}{item.due_date ? ` · ${formatDate(item.due_date, i18n.resolvedLanguage)}` : ""}</small></div><span className="control-badge">{t(`memory.actionStatus.${item.status}`)}</span>{!archived && item.status === "PROPOSED" && <><button className="text-button compact" onClick={() => void updateAction(meeting, item.id, "CONFIRMED")}>{t("memory.actions.confirm")}</button><button className="text-button compact danger-text" onClick={() => void updateAction(meeting, item.id, "DISMISSED")}>{t("memory.actions.dismiss")}</button></>}{!archived && item.status === "CONFIRMED" && <button className="text-button compact" onClick={() => void updateAction(meeting, item.id, "COMPLETED")}>{t("memory.actions.complete")}</button>}</div>)}</div></article>)}</div>}
      {view === "decisions" && <div className="memory-card-list">{filtered.decisions.length === 0 ? <Empty text={t("memory.decisions.empty")} /> : filtered.decisions.map((item) => <article key={item.id}><header><div><span className="control-badge">{t(`memory.decisionStatus.${item.status}`)}</span><h2>{item.title}</h2><small>{formatDate(item.decision_date, i18n.resolvedLanguage)} · {memberName(item.decision_maker_member_id)}</small></div>{!archived && <div className="control-actions">{item.status === "PROPOSED" && <button className="text-button compact" onClick={() => void updateDecision(item, "DECIDED")}>{t("memory.actions.decide")}</button>}{item.status === "DECIDED" && <><button className="text-button compact danger-text" onClick={() => void updateDecision(item, "REVERSED")}>{t("memory.actions.reverse")}</button><button className="text-button compact" onClick={() => void updateDecision(item, "SUPERSEDED")}>{t("memory.actions.supersede")}</button></>}</div>}</header><p>{item.decision}</p>{item.reason && <small>{t("memory.fields.reason")}: {item.reason}</small>}<LinkChips links={item.links} /></article>)}</div>}
      {view === "activity" && <div className="table-scroll"><table className="data-table activity-table"><thead><tr><th>{t("memory.activity.when")}</th><th>{t("memory.activity.actor")}</th><th>{t("memory.activity.action")}</th><th>{t("memory.activity.entity")}</th><th>{t("memory.activity.changes")}</th></tr></thead><tbody>{filtered.activities.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString(i18n.resolvedLanguage)}</td><td>{item.actor_email ?? item.actor_user_id}</td><td><strong>{item.action}</strong></td><td>{item.entity_name ?? `${item.entity_type} · ${item.entity_id.slice(0, 8)}`}</td><td><code>{item.changes ? JSON.stringify(item.changes) : "—"}</code></td></tr>)}</tbody></table>{filtered.activities.length === 0 && <Empty text={t("memory.activity.empty")} />}</div>}
    </section>
    <MemoryForm open={Boolean(formKind)} kind={formKind} form={form} setForm={setForm} members={members} tasks={tasks} milestones={milestones} meetings={meetings} error={error} saving={saving} onClose={closeForm} onSubmit={submit} />
  </div>;
}

function Empty({ text }: { text: string }) { return <div className="section-empty"><FileClock size={24} /><p>{text}</p></div>; }
function LinkChips({ links }: { links: { entity_type: string; entity_name?: string | null; entity_id: string }[] }) { return links.length ? <div className="memory-links">{links.map((link) => <span key={`${link.entity_type}-${link.entity_id}`}>{link.entity_type} · {link.entity_name ?? link.entity_id.slice(0, 8)}</span>)}</div> : null; }
function MemoryList({ items, locale, empty }: { items: ProjectLogEntry[]; locale?: string; empty: string }) { return <div className="memory-timeline">{items.length === 0 ? <Empty text={empty} /> : items.map((item) => <article key={item.id}><i aria-hidden="true" /><div><header><span className="control-badge">{item.type}</span><span className={`control-badge ${item.source === "SYSTEM" ? "severity-low" : ""}`}>{item.source}</span><time>{new Date(item.created_at).toLocaleString(locale)}</time></header><h2>{item.title}</h2>{item.description && <p>{item.description}</p>}<LinkChips links={item.links} /></div></article>)}</div>; }

function MemoryForm({ open, kind, form, setForm, members, tasks, milestones, meetings, error, saving, onClose, onSubmit }: { open: boolean; kind: FormKind; form: typeof initial; setForm: React.Dispatch<React.SetStateAction<typeof initial>>; members: ProjectMember[]; tasks: Task[]; milestones: Milestone[]; meetings: Meeting[]; error: string; saving: boolean; onClose: () => void; onSubmit: (event: FormEvent) => void }) {
  const { t } = useTranslation();
  const title = kind ? t(`memory.forms.${kind}.title`) : "";
  return <Modal open={open} onClose={onClose} title={title} description={kind ? t(`memory.forms.${kind}.description`) : ""} footer={<><button className="secondary-button" type="button" onClick={onClose}>{t("common.cancel")}</button><button className="primary-button" type="submit" form="memory-form" disabled={saving}>{saving ? t("common.saving") : t("common.save")}</button></>}><form id="memory-form" className="form-grid" onSubmit={onSubmit}>
    {kind !== "action" && <label className="span-2">{t("memory.fields.title")}<input required value={form.title} onChange={(e) => setForm((v) => ({ ...v, title: e.target.value }))} /></label>}
    {kind === "log" && <label>{t("memory.fields.type")}<select value={form.type} onChange={(e) => setForm((v) => ({ ...v, type: e.target.value }))}>{["NOTE", "MEETING", "DECISION", "ISSUE", "CHANGE", "MILESTONE", "TASK_UPDATE", "RISK_UPDATE"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>}
    {(kind === "log" || kind === "action") && <label className="span-2">{kind === "action" ? t("memory.fields.action") : t("memory.fields.description")}<textarea required={kind === "action"} value={form.description} onChange={(e) => setForm((v) => ({ ...v, description: e.target.value }))} /></label>}
    {kind === "meeting" && <><label>{t("memory.fields.scheduledAt")}<input required type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm((v) => ({ ...v, scheduled_at: e.target.value }))} /></label><label>{t("memory.fields.duration")}<input type="number" min="1" max="1440" value={form.duration_minutes} onChange={(e) => setForm((v) => ({ ...v, duration_minutes: e.target.value }))} /></label><label className="span-2">{t("memory.fields.agenda")}<textarea value={form.agenda} onChange={(e) => setForm((v) => ({ ...v, agenda: e.target.value }))} /></label><label className="span-2">{t("memory.fields.participants")}<select multiple value={form.participant_ids} onChange={(e) => setForm((v) => ({ ...v, participant_ids: Array.from(e.target.selectedOptions, (option) => option.value) }))}>{members.map((item) => <option key={item.id} value={item.id}>{item.person.name}</option>)}</select></label></>}
    {kind === "decision" && <><label className="span-2">{t("memory.fields.decision")}<textarea required value={form.decision} onChange={(e) => setForm((v) => ({ ...v, decision: e.target.value }))} /></label><label>{t("memory.fields.date")}<input required type="date" value={form.decision_date} onChange={(e) => setForm((v) => ({ ...v, decision_date: e.target.value }))} /></label><label>{t("memory.fields.maker")}<select value={form.decision_maker_member_id} onChange={(e) => setForm((v) => ({ ...v, decision_maker_member_id: e.target.value }))}><option value="">{t("common.none")}</option>{members.map((item) => <option key={item.id} value={item.id}>{item.person.name}</option>)}</select></label><label>{t("memory.fields.meeting")}<select value={form.meeting_id} onChange={(e) => setForm((v) => ({ ...v, meeting_id: e.target.value }))}><option value="">{t("common.none")}</option>{meetings.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label className="span-2">{t("memory.fields.reason")}<textarea value={form.reason} onChange={(e) => setForm((v) => ({ ...v, reason: e.target.value }))} /></label></>}
    {(kind === "log" || kind === "decision") && <><label>{t("memory.fields.task")}<select value={form.task_id} onChange={(e) => setForm((v) => ({ ...v, task_id: e.target.value }))}><option value="">{t("common.none")}</option>{tasks.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label>{t("memory.fields.milestone")}<select value={form.milestone_id} onChange={(e) => setForm((v) => ({ ...v, milestone_id: e.target.value }))}><option value="">{t("common.none")}</option>{milestones.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label></>}
    {kind === "action" && <><label>{t("memory.fields.owner")}<select value={form.owner_member_id} onChange={(e) => setForm((v) => ({ ...v, owner_member_id: e.target.value }))}><option value="">{t("common.none")}</option>{members.map((item) => <option key={item.id} value={item.id}>{item.person.name}</option>)}</select></label><label>{t("memory.fields.dueDate")}<input type="date" value={form.due_date} onChange={(e) => setForm((v) => ({ ...v, due_date: e.target.value }))} /></label></>}
    {error && <p className="field-error span-2" role="alert">{error}</p>}
  </form></Modal>;
}
