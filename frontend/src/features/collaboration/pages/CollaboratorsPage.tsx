import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { peopleApi } from "../../people/api/peopleApi";
import type { ProjectMember } from "../../people/types";
import { collaborationApi } from "../api/collaborationApi";
import { useProjectAccess } from "../hooks/useProjectAccess";
import type { Collaborator, ProjectAccessRole } from "../types";

const ROLES: ProjectAccessRole[] = [
  "PROJECT_ADMIN", "PROJECT_MANAGER", "CONTRIBUTOR", "VIEWER",
];

export function CollaboratorsPage() {
  const { t, i18n } = useTranslation();
  const { projectId = "" } = useParams();
  const { access, can } = useProjectAccess(projectId);
  const [items, setItems] = useState<Collaborator[]>([]);
  const [people, setPeople] = useState<ProjectMember[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectAccessRole>("CONTRIBUTOR");
  const [error, setError] = useState("");
  const load = useCallback(
    () => Promise.all([collaborationApi.collaborators(projectId), peopleApi.listMembers(projectId)]).then(([nextItems, nextPeople]) => { setItems(nextItems); setPeople(nextPeople); }),
    [projectId],
  );
  useEffect(() => { void load(); }, [load]);
  async function add(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await collaborationApi.addCollaborator(projectId, email, role); setEmail(""); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : t("collaboration.error")); }
  }
  const manage = can("members.manage");
  const changeRoles = can("members.change_role");
  const assignableRoles = access?.role === "OWNER" ? ROLES : ROLES.filter((value) => value !== "PROJECT_ADMIN");
  const mayManage = (item: Collaborator) => manage && item.role !== "OWNER" && (access?.role === "OWNER" || item.role !== "PROJECT_ADMIN");
  return <div className="page-stack">
    <Link className="back-link" to={`/projects/${projectId}`}>{t("collaboration.back")}</Link>
    <header className="page-header"><div><p className="eyebrow">{t("collaboration.eyebrow")}</p><h1>{t("collaboration.title")}</h1><p>{t("collaboration.subtitle")}</p></div>{access && <span className="role-badge">{t(`collaboration.roles.${access.role}`)}</span>}</header>
    {manage && <form className="collaborator-form" onSubmit={add}><label><span>{t("collaboration.email")}</span><input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label><span>{t("collaboration.role")}</span><select value={role} onChange={(event) => setRole(event.target.value as ProjectAccessRole)}>{assignableRoles.map((value) => <option key={value} value={value}>{t(`collaboration.roles.${value}`)}</option>)}</select></label><button className="primary-button">{t("collaboration.add")}</button>{error && <p className="inline-error">{error}</p>}</form>}
    <div className="table-scroll"><table className="data-table"><thead><tr><th>{t("collaboration.member")}</th><th>{t("collaboration.role")}</th><th>{t("collaboration.status")}</th><th>{t("collaboration.joined")}</th><th>{t("collaboration.person")}</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id}>
      <td><strong>{item.display_name ?? item.email}</strong>{item.display_name && <small>{item.email}</small>}</td>
      <td>{changeRoles && mayManage(item) ? <select value={item.role} onChange={(event) => void collaborationApi.updateCollaborator(projectId, item.id, { role: event.target.value as ProjectAccessRole }).then(load)}>{assignableRoles.map((value) => <option key={value} value={value}>{t(`collaboration.roles.${value}`)}</option>)}</select> : <span className="role-badge">{t(`collaboration.roles.${item.role}`)}</span>}</td>
      <td>{mayManage(item) ? <button className="text-button" onClick={() => void collaborationApi.updateCollaborator(projectId, item.id, { status: item.status === "ACTIVE" ? "DISABLED" : "ACTIVE" }).then(load)}>{item.status}</button> : item.status}</td>
      <td>{item.joined_at ? new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" }).format(new Date(item.joined_at)) : "—"}</td>
      <td>{mayManage(item) ? <select aria-label={t("collaboration.person")} value={item.person_id ?? ""} onChange={(event) => void collaborationApi.updateCollaborator(projectId, item.id, { person_id: event.target.value || null }).then(load)}><option value="">—</option>{people.map((member) => <option key={member.person_id} value={member.person_id}>{member.person.name}</option>)}</select> : item.person_name ?? "—"}</td>
      <td>{mayManage(item) && <button className="text-button danger" onClick={() => void collaborationApi.removeCollaborator(projectId, item.id).then(load)}>{t("common.remove")}</button>}</td>
    </tr>)}</tbody></table></div>
  </div>;
}
