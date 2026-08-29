import { AlertCircle, ArrowLeft, BriefcaseBusiness, Network, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { projectsApi } from "../../projects/api/projectsApi";
import type { ProjectDetail } from "../../projects/types";
import { peopleApi } from "../api/peopleApi";
import { StakeholdersPanel } from "../components/StakeholdersPanel";
import { TeamPanel } from "../components/TeamPanel";
import { WorkloadPanel } from "../components/WorkloadPanel";
import type { MemberInput, MemberWorkload, Person, PersonInput, ProjectMember, Stakeholder, StakeholderInput } from "../types";

type View = "team" | "stakeholders" | "workload";

export function PeopleWorkspacePage() {
  const { t } = useTranslation(); const { projectId = "" } = useParams(); const [view, setView] = useState<View>("team"); const [project, setProject] = useState<ProjectDetail | null>(null); const [people, setPeople] = useState<Person[]>([]); const [members, setMembers] = useState<ProjectMember[]>([]); const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]); const [workload, setWorkload] = useState<MemberWorkload[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [mutationError, setMutationError] = useState("");
  const load = useCallback(async () => { setError(""); try { const [nextProject, nextPeople, nextMembers, nextStakeholders, nextWorkload] = await Promise.all([projectsApi.get(projectId), peopleApi.listPeople(), peopleApi.listMembers(projectId), peopleApi.listStakeholders(projectId), peopleApi.workload(projectId)]); setProject(nextProject); setPeople(nextPeople); setMembers(nextMembers); setStakeholders(nextStakeholders); setWorkload(nextWorkload); } catch { setError(t("people.loadError")); } finally { setLoading(false); } }, [projectId, t]);
  useEffect(() => void load(), [load]);
  async function mutate(operation: () => Promise<unknown>) { setMutationError(""); try { await operation(); await load(); return true; } catch { setMutationError(t("people.actions.error")); return false; } }
  if (loading) return <div className="content-state"><span className="spinner" />{t("common.loading")}</div>;
  if (error || !project) return <div className="content-state error-state" role="alert"><AlertCircle /><h1>{error || t("people.loadError")}</h1><Link className="secondary-button" to="/projects">{t("projects.backToProjects")}</Link></div>;
  const readOnly = Boolean(project.archived_at); const tabs: Array<[View, typeof Users]> = [["team", Users], ["stakeholders", Network], ["workload", BriefcaseBusiness]];
  return <div className="people-workspace page-stack"><Link className="back-link" to={`/projects/${projectId}`}><ArrowLeft size={16} />{t("people.backToOverview")}</Link><header className="work-header"><div><div className="badge-row"><span className="project-code">{project.code}</span></div><p className="eyebrow">{t("people.eyebrow")}</p><h1>{t("people.title")}</h1><p>{t("people.subtitle", { project: project.name })}</p></div></header>{readOnly && <div className="archived-notice">{t("people.readOnly")}</div>}{mutationError && <div className="inline-error" role="alert"><AlertCircle size={15} />{mutationError}</div>}<nav className="work-tabs" aria-label={t("people.views.label")}>{tabs.map(([key, Icon]) => <button key={key} type="button" className={view === key ? "active" : ""} onClick={() => setView(key)}><Icon size={16} />{t(`people.views.${key}`)}</button>)}</nav><section className="work-surface people-surface">
    {view === "team" && <TeamPanel people={people} members={members} readOnly={readOnly} onCreatePerson={(input) => mutate(() => peopleApi.createPerson(input))} onUpdatePerson={(id, input) => mutate(() => peopleApi.updatePerson(id, input))} onAddMember={(input) => mutate(() => peopleApi.addMember(projectId, input))} onUpdateMember={(id, input) => mutate(() => peopleApi.updateMember(projectId, id, { role: input.role, responsibilities: input.responsibilities, availability_percent: input.availability_percent }))} onRemoveMember={(id) => mutate(() => peopleApi.removeMember(projectId, id))} />}
    {view === "stakeholders" && <StakeholdersPanel people={people} stakeholders={stakeholders} readOnly={readOnly} onCreate={(input) => mutate(() => peopleApi.createStakeholder(projectId, input))} onUpdate={(id, input) => mutate(() => peopleApi.updateStakeholder(projectId, id, input))} onRemove={(id) => mutate(() => peopleApi.removeStakeholder(projectId, id))} />}
    {view === "workload" && <WorkloadPanel workload={workload} />}
  </section></div>;
}
